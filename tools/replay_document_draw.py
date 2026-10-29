"""Replay actual document setup -> UTF-8 renderer -> glyph-submit gate offline.

Only font lookup/color and final glyph submission are controlled callbacks. The
field/collection branch, row measurements, font renderer and native draw-enable
flag are actual supplied EXE instructions. No window, game or save is accessed.
"""
from native_profile import rva as map_rva, active_build
import io
import json
import struct
from functools import lru_cache
from pathlib import Path
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn.x86_const import *
from localize import Zar,extract

BASE=0x140000000
# Build 1.0.4 extends into the former 0xc00000 fixture region. Keep all replay
# objects and stack outside every supplied image, including localization code.
OBJECT=BASE+0xe00000
NODE=BASE+0xe01000
FONT=BASE+0xe02000
MANAGER=BASE+0xe03000
GLYPH=BASE+0xe04000
STACK=BASE+0xf00000
FLAG_RVA=0x4c21ff
SENTINEL_RVA=0x4c2200
SENTINEL=b'p0_000\0'



@lru_cache(maxsize=2)
def _archive_text_and_metrics(path,size,modified_ns):
    zar=Zar(Path(path).read_bytes())
    texts={r['resource']:r['source'] for r in extract(zar)}
    return texts,json.loads(zar.read('FONTS/D2FONT_12X15.JSON'))


def _replay(executable,archive,resource='EN/EXAMINE.041',collection=False,events=()):
    pe=pefile.PE(data=Path(executable).read_bytes())
    machine=Uc(UC_ARCH_X86,UC_MODE_64)
    if pe.OPTIONAL_HEADER.SizeOfImage > OBJECT-BASE:
        raise ValueError('Native image overlaps replay fixture objects')
    machine.mem_map(BASE,0x1100000)
    machine.mem_write(BASE,pe.get_memory_mapped_image())
    archive=Path(archive).resolve();stat=archive.stat()
    texts,meta=_archive_text_and_metrics(str(archive),stat.st_size,stat.st_mtime_ns)
    text=texts[resource]
    glyphs=meta['glyphs']
    number=int(resource.rsplit('.',1)[1])
    def write(address,data):machine.mem_write(address,data)
    def q(address,value):write(address,struct.pack('<Q',value))
    def d(address,value):write(address,struct.pack('<I',value))
    write(BASE+map_rva(FLAG_RVA),b'\0');write(BASE+map_rva(SENTINEL_RVA),SENTINEL)
    write(FONT+0x18,bytes([meta['linefeed']]));write(FONT+0xc,b'\x0f')
    q(BASE+map_rva(0x4c2158),MANAGER);q(MANAGER+0x50,FONT);d(FONT+0x84,1)
    write(OBJECT+0x128,struct.pack('<hh',number,41 if number<500 else -1))
    d(OBJECT+0x1d0,number)
    rsp=STACK+0x80000
    machine.reg_write(UC_X86_REG_RSP,rsp)
    machine.reg_write(UC_X86_REG_RBP,rsp+0x91)
    current = active_build() == '26260428'
    # 1.0.4 owns both views through RSI. The actual prologue below populates
    # RDI/RBX itself; passing former-build register values would bypass it.
    machine.reg_write(UC_X86_REG_RDI,0 if current else OBJECT)
    machine.reg_write(UC_X86_REG_RSI,OBJECT if current else 0)
    machine.reg_write(UC_X86_REG_R12,0)
    machine.reg_write(UC_X86_REG_R15,0)
    if collection:
        q(OBJECT+0x1c8,NODE)
        write(OBJECT+0x1e0,text.encode('utf8')+b'\0')
        q(NODE+0x30,FONT);q(NODE+0x40,FONT);d(NODE+0x38,1);d(NODE+0x3c,0)
        start,stop=BASE+map_rva(0x1232fc),BASE+map_rva(0x1233bf)
    else:
        q(OBJECT+0x88,NODE)
        write(OBJECT+0x12c,text.encode('utf8')+b'\0')
        q(NODE+0x58,FONT);q(NODE+0x68,FONT);d(NODE+0x60,1);d(NODE+0x64,0)
        for off,val in [(0xa0,0),(0xa4,104),(0xa8,256),(0xac,72)]:d(NODE+off,val)
        start,stop=BASE+map_rva(0x11b450),BASE+map_rva(0x11b536)
    drawn=[];lookup=[];calls=[];measure_calls=[]
    def return_stub(uc,result=0):
        sp=uc.reg_read(UC_X86_REG_RSP)
        ret=struct.unpack('<Q',uc.mem_read(sp,8))[0]
        uc.reg_write(UC_X86_REG_RAX,result)
        uc.reg_write(UC_X86_REG_RSP,sp+8);uc.reg_write(UC_X86_REG_RIP,ret)
    def hook(uc,address,size,_):
        if address==stop:uc.emu_stop();return
        if current and address==BASE+0xb6320:
            # Observe but do not replace the new native UTF-8 measurement helper.
            measure_calls.append(uc.reg_read(UC_X86_REG_R8))
        if address==BASE+map_rva(0x111800):
            code=uc.reg_read(UC_X86_REG_EDX)&0xffff
            g=glyphs.get(str(code),glyphs.get('0',{'logw':12}))
            d(GLYPH+0x14,g['logw']);lookup.append(code);return_stub(uc,GLYPH)
        elif address==BASE+map_rva(0x1118e0):return_stub(uc,0xffffffff)
        elif address==BASE+map_rva(0x111950):
            drawn.append(dict(code=uc.reg_read(UC_X86_REG_EDX)&0xffff,
                              x=uc.reg_read(UC_X86_REG_R8D),y=uc.reg_read(UC_X86_REG_R9D),
                              draw_flag=uc.mem_read(BASE+map_rva(FLAG_RVA),1)[0]))
            return_stub(uc)
        elif address==BASE+map_rva(0xb05c0):
            calls.append(dict(x=uc.reg_read(UC_X86_REG_EDX),y=uc.reg_read(UC_X86_REG_R8D),
                              flag=uc.mem_read(BASE+map_rva(FLAG_RVA),1)[0],
                              sentinel=bytes(uc.mem_read(BASE+map_rva(SENTINEL_RVA),len(SENTINEL))).hex()))
    machine.hook_add(UC_HOOK_CODE,hook)
    initial_context=machine.context_save()
    machine.emu_start(start,stop,count=1000000)
    if machine.reg_read(UC_X86_REG_RIP)!=stop:
        raise RuntimeError('Native document draw did not reach its expected exit')
    # Subsequent frames preserve actual native state and dispatch real wheel /
    # key-handler instructions. Only the renderer's external boundaries above
    # remain doubled, exactly as for the first frame.
    input_object=OBJECT+0x7000
    q(BASE+map_rva(0x4c2228),input_object)
    for event in events:
        temporary_stack=STACK+0x70008
        q(temporary_stack,stop)
        machine.reg_write(UC_X86_REG_RSP,temporary_stack)
        machine.reg_write(UC_X86_REG_RCX,input_object)
        if event[0]=='wheel':
            machine.reg_write(UC_X86_REG_EDX,event[1]&0xffffffff)
            entry=BASE+map_rva(0x2ee30)
        elif event[0]=='key':
            machine.reg_write(UC_X86_REG_EDX,event[1])
            machine.reg_write(UC_X86_REG_R8D,event[2])
            entry=BASE+map_rva(0x1a7c50)
        else:raise ValueError('Unsupported replay input event')
        machine.emu_start(entry,stop,count=100000)
        if machine.reg_read(UC_X86_REG_RIP)!=stop:
            raise RuntimeError('Native document input did not return to the expected boundary')
        machine.context_restore(initial_context)
        drawn.clear();lookup.clear();calls.clear();measure_calls.clear()
        machine.emu_start(start,stop,count=1000000)
        if machine.reg_read(UC_X86_REG_RIP)!=stop:
            raise RuntimeError('Native document redraw did not reach its expected exit')
    return dict(resource=resource,path='collection' if collection else 'field',
                text=text,glyph_count=len(drawn),drawn=drawn,renderer_calls=calls,
                lookup_count=len(lookup),native_measure_calls=len(measure_calls),
                draw_flag_after=machine.mem_read(BASE+map_rva(FLAG_RVA),1)[0],
                sentinel_before=SENTINEL.hex(),sentinel_after=bytes(machine.mem_read(BASE+map_rva(SENTINEL_RVA),len(SENTINEL))).hex(),
                reader_active=struct.unpack('<I',machine.mem_read(BASE+map_rva(0xa68980),4))[0],
                scroll_line=struct.unpack('<I',machine.mem_read(BASE+map_rva(0xa68990),4))[0],
                scope='actual supplied native field/collection branch and UTF-8 renderer; controlled font metadata lookup and final glyph-submit callbacks, no game launch')


def replay(executable,archive,resource='EN/EXAMINE.041',collection=False,events=(),native_profile='26099941'):
    from native_profile import _ACTIVE,restore
    if native_profile not in ('26099941','26123896','26152271','26260428'):raise ValueError('Unknown native replay profile')
    pe=pefile.PE(str(executable),fast_load=True)
    data_section=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.data')
    expected={'26099941':0x49f000,'26123896':0x4a1000,'26152271':0x4a4000,'26260428':0x4cd000}[native_profile]
    if data_section.VirtualAddress!=expected:raise ValueError('Native replay fixture/profile mismatch')
    token=_ACTIVE.set(native_profile)
    try:return _replay(executable,archive,resource,collection,events)
    finally:restore(token)
