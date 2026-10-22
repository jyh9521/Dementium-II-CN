"""Portable PE instruction replay with deterministic Win32 boundary doubles."""
import struct
import pefile
from unicorn import Uc,UC_ARCH_X86,UC_MODE_64,UC_HOOK_CODE
from unicorn.x86_const import *
BASE=0x140000000
def require_native_fixture(path,profile='26099941'):
    """Require the named shipped-build coordinate space, never silently rebase it."""
    import unittest
    from pathlib import Path
    if not Path(path).is_file():raise unittest.SkipTest('requires local native build '+profile+' fixture: '+str(path))
    pe=pefile.PE(str(path),fast_load=True)
    data_section=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.data')
    actual={0x4a1000:'26123896',0x49f000:'26099941'}.get(data_section.VirtualAddress,'unknown')
    if actual!=profile:raise unittest.SkipTest('requires native build '+profile+' fixture; supplied PE is '+actual)

class Replay:
    def __init__(self,path,image_base=None,native_profile='26099941'):
        require_native_fixture(path,native_profile)
        self.pe=pefile.PE(str(path));old_base=self.pe.OPTIONAL_HEADER.ImageBase
        if image_base is not None:self.pe.relocate_image(image_base)
        self.base=self.pe.OPTIONAL_HEADER.ImageBase
        self.uc=Uc(UC_ARCH_X86,UC_MODE_64)
        self.uc.mem_map(self.base,(self.pe.OPTIONAL_HEADER.SizeOfImage+4095)&~4095)
        self.uc.mem_write(self.base,self.pe.get_memory_mapped_image())
        self.uc.mem_map(0x20000000,0x20000);self.stack=0x2001ff00;self.stop=0x20000000
        self.uc.mem_map(0x30000000,0x20000)
        self.obj=0x30000000;self.window=0x30001000;self.io=0x30002000
        self.write(0x4c2228,struct.pack('<Q',self.obj));self.write(0x4c2248,struct.pack('<Q',self.io))
        self.write(0xa312b0,struct.pack('<Q',self.window))
        self.uc.mem_write(self.window+0x20,struct.pack('<Q',0x1234))
        for o in [0x18,0x19,0x1a,0x79,0x7a]:self.uc.mem_write(self.window+o,b'\x01')
        self.calls=[];self.rect=(0,0,1920,1080);self.origin=(100,50)
        self.uc.mem_map(0x40000000,0x10000);self.stubs={}
        names={b'LoadCursorA',b'SetCursor',b'ClipCursor',b'GetClientRect',b'ClientToScreen',b'SetCursorPos',b'MapWindowPoints'}
        for dll in self.pe.DIRECTORY_ENTRY_IMPORT:
            for imp in dll.imports:
                if imp.name in names:
                    stub=0x40000000+len(self.stubs)*16
                    self.stubs[stub]=imp.name.decode();slot=imp.address if self.base<=imp.address<self.base+self.pe.OPTIONAL_HEADER.SizeOfImage else self.base+imp.address-old_base
                    self.uc.mem_write(slot,struct.pack('<Q',stub));self.uc.mem_write(stub,b'\xc3')
        self.uc.hook_add(UC_HOOK_CODE,self.boundary)
    def rva(self,value):return value
    def write(self,rva,data):self.uc.mem_write(self.base+rva,data)
    def read(self,rva,size):return bytes(self.uc.mem_read(self.base+rva,size))
    def byte(self,rva,value=None):
        if value is not None:self.write(rva,bytes([value]))
        return self.read(rva,1)[0]
    def dword(self,rva):return struct.unpack('<I',self.read(rva,4))[0]
    def boundary(self,u,address,size,user):
        if address not in self.stubs:return
        name=self.stubs[address];a=u.reg_read(UC_X86_REG_RCX);b=u.reg_read(UC_X86_REG_RDX)
        result=1;detail=None
        if name=='LoadCursorA':result=0x7777
        elif name=='GetClientRect':u.mem_write(b,struct.pack('<4i',*self.rect))
        elif name=='ClientToScreen':
            x,y=struct.unpack('<2i',u.mem_read(b,8));u.mem_write(b,struct.pack('<2i',x+self.origin[0],y+self.origin[1]))
        elif name=='MapWindowPoints':
            point=u.reg_read(UC_X86_REG_R8);count=u.reg_read(UC_X86_REG_R9)
            for i in range(count):
                x,y=struct.unpack('<2i',u.mem_read(point+i*8,8));u.mem_write(point+i*8,struct.pack('<2i',x+self.origin[0],y+self.origin[1]))
        elif name=='ClipCursor':detail=None if not a else struct.unpack('<4i',u.mem_read(a,16))
        if name=='SetCursorPos':
            a=struct.unpack('<i',struct.pack('<I',a&0xffffffff))[0]
            b=struct.unpack('<i',struct.pack('<I',b&0xffffffff))[0]
        self.calls.append((name,a,b,detail))
        u.reg_write(UC_X86_REG_RAX,result)
        rsp=u.reg_read(UC_X86_REG_RSP);ret=struct.unpack('<Q',u.mem_read(rsp,8))[0]
        u.reg_write(UC_X86_REG_RSP,rsp+8);u.reg_write(UC_X86_REG_RIP,ret)
    def run(self,rva,stop=None,**registers):
        self.uc.reg_write(UC_X86_REG_RSP,self.stack)
        self.uc.mem_write(self.stack,struct.pack('<Q',self.stop))
        for name,val in registers.items():self.uc.reg_write(globals()['UC_X86_REG_'+name.upper()],val)
        self.uc.emu_start(self.base+rva,self.base+stop if stop is not None else self.stop,count=100000)
        return self.uc.reg_read(UC_X86_REG_RAX)
