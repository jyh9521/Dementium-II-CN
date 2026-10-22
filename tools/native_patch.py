"""Guarded x64 relative hooks and a shared RX section; no RWX or new imports."""
from native_profile import rva as map_rva, guard
import re
import struct
import pefile
from keystone import Ks,KS_ARCH_X86,KS_MODE_64
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
BASE=0x140000000
READER_STATE=0xa68980
MENU_STATE=0xa68e80

def assemble(text,address,symbols=None):
    """Assemble labels/relative calls; @NAME denotes a RIP-relative memory target."""
    symbols=symbols or {}
    lines=[line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith('#')]
    plain=[re.sub(r'@([A-Za-z_][A-Za-z_0-9]*)','0',line) for line in lines]
    ks=Ks(KS_ARCH_X86,KS_MODE_64)
    code=bytearray(ks.asm('\n'.join(plain),addr=address)[0])
    instructions=list(Cs(CS_ARCH_X86,CS_MODE_64).disasm(bytes(code),address))
    sources=[line for line in lines if not line.endswith(':')]
    if len(instructions)!=len(sources):raise ValueError('Assembly instruction/source mismatch')
    for source,ins in zip(sources,instructions):
        names=re.findall(r'@([A-Za-z_][A-Za-z_0-9]*)',source)
        if not names:continue
        fixed=source
        for name in names:
            target=symbols[name]
            fixed=fixed.replace('@'+name,hex(target-ins.address-ins.size))
        replacement=bytes(ks.asm(fixed,addr=ins.address)[0])
        if len(replacement)!=ins.size:raise ValueError('RIP fixup changed instruction size')
        start=ins.address-address;code[start:start+ins.size]=replacement
    return bytes(code)

def guarded_write(out,pe,rva,expected,replacement):
    expected=guard(expected,rva)
    pos=pe.get_offset_from_rva(rva)
    if bytes(out[pos:pos+len(expected)])!=expected:raise ValueError('Native UI byte guard mismatch at '+hex(rva))
    if len(expected)!=len(replacement):raise ValueError('Native hook length mismatch')
    out[pos:pos+len(expected)]=replacement

def jump(source,target,length):
    if length<5:raise ValueError('Jump patch too short')
    return b'\xe9'+struct.pack('<i',target-(source+5))+b'\x90'*(length-5)

def prepare_ui_section(data):
    pe=pefile.PE(data=data)
    if pe.OPTIONAL_HEADER.ImageBase!=BASE:raise ValueError('Unexpected native image base')
    if any(s.Name.rstrip(b'\0')==b'.locui' for s in pe.sections):raise ValueError('UI hooks already applied')
    last=pe.sections[-1];header=last.get_file_offset()+40
    if header+40>pe.OPTIONAL_HEADER.SizeOfHeaders or any(data[header:header+40]):raise ValueError('No section header space')
    align=lambda n,a:(n+a-1)//a*a
    va=align(last.VirtualAddress+max(last.Misc_VirtualSize,last.SizeOfRawData),pe.OPTIONAL_HEADER.SectionAlignment)
    raw=align(len(data),pe.OPTIONAL_HEADER.FileAlignment);size=0x2000
    if len(data)!=last.PointerToRawData+last.SizeOfRawData:raise ValueError('Unexpected overlay')
    out=bytearray(data)
    struct.pack_into('<8sIIIIIIHHI',out,header,b'.locui',size,va,size,raw,0,0,0,0,0x60000020)
    struct.pack_into('<H',out,pe.DOS_HEADER.e_lfanew+6,len(pe.sections)+1)
    struct.pack_into('<I',out,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfImage'),align(va+size,pe.OPTIONAL_HEADER.SectionAlignment))
    struct.pack_into('<I',out,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfCode'),pe.OPTIONAL_HEADER.SizeOfCode+size)
    section=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.data')
    if section.VirtualAddress+section.Misc_VirtualSize!=map_rva(READER_STATE):raise ValueError('Native data tail differs')
    nextva=min(s.VirtualAddress for s in pe.sections if s.VirtualAddress>section.VirtualAddress)
    if nextva!=map_rva(0xa69000) or section.Characteristics&0x20000000:raise ValueError('Writable state reservation differs')
    # Newly declared zero-fill space only: never repurpose existing engine data.
    struct.pack_into('<I',out,section.get_field_absolute_offset('Misc_VirtualSize'),nextva-section.VirtualAddress)
    out.extend(b'\0'*(raw-len(out)));out.extend(b'\xcc'*size)
    return bytes(out),dict(code_rva=va,code_size=size,reader_state=map_rva(READER_STATE),menu_state=map_rva(MENU_STATE))
