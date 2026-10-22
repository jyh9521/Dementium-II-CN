"""Execute native context/window construction and complete ImGui CPU frames.

Only imported CRT allocation/memory/math and Win32 boundaries use deterministic
doubles. Context defaults, navigation, mouse ownership, windows, complete
Checkbox (including layout/decision/draw-list writes), End and EndFrame execute
the supplied PE instructions. Minimal font metadata intentionally contains no
glyph art: this is input/state regression evidence, not raster acceptance.
"""
import math
import struct
from native_replay import Replay,BASE
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *


class ImGuiReplay(Replay):
    def __init__(self,path,image_base=None):
        super().__init__(path,image_base=image_base)
        self.uc.mem_map(0x50000000,0x2000000)
        self.next_allocation=0x50000000
        # Native __chkstk reads the current TEB's stack limit.
        self.uc.mem_map(0x60000000,0x10000)
        self.uc.reg_write(UC_X86_REG_GS_BASE,0x60000000)
        self.uc.mem_write(0x60000010,struct.pack('<Q',0x20000000))
        for dll in self.pe.DIRECTORY_ENTRY_IMPORT:
            for imp in dll.imports:
                if imp.name is None:continue
                slot=imp.address if self.base<=imp.address<self.base+self.pe.OPTIONAL_HEADER.SizeOfImage else self.base+imp.address-BASE
                current=struct.unpack('<Q',self.uc.mem_read(slot,8))[0]
                if current in self.stubs:continue
                stub=0x40002000+len(self.stubs)*16
                self.stubs[stub]=imp.name.decode()
                self.uc.mem_write(stub,b'\xc3')
                self.uc.mem_write(slot,struct.pack('<Q',stub))

    def allocate(self,size):
        address=self.next_allocation
        self.next_allocation+=(size+15)&~15
        if self.next_allocation>=0x52000000:raise RuntimeError('Native ImGui replay heap exhausted')
        return address

    def float_at(self,address):return struct.unpack('<f',self.uc.mem_read(address,4))[0]
    def pointer_at(self,address):return struct.unpack('<Q',self.uc.mem_read(address,8))[0]

    def boundary(self,u,address,size,user):
        if address not in self.stubs:return
        name=self.stubs[address]
        math_functions={'cosf':math.cos,'sinf':math.sin,'floorf':math.floor,
                        'ceilf':math.ceil,'sqrtf':math.sqrt,'acosf':math.acos}
        empty_os={'DefWindowProcA','DefWindowProcW','GetMessageExtraInfo'}
        if name in {'malloc','calloc','memset','memcpy','memmove','memcmp','free'} or name in math_functions or name in empty_os:
            a,b,c=[u.reg_read(r) for r in (UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8)]
            result=0
            if name=='malloc':result=self.allocate(a)
            elif name=='calloc':result=self.allocate(a*b)
            elif name=='memset':u.mem_write(a,bytes([b&255])*c);result=a
            elif name in ('memcpy','memmove'):u.mem_write(a,bytes(u.mem_read(b,c)));result=a
            elif name=='memcmp':
                x,y=bytes(u.mem_read(a,c)),bytes(u.mem_read(b,c))
                result=(x>y)-(x<y)
            elif name=='free':pass
            elif name in empty_os:pass
            else:
                x=struct.unpack('<f',struct.pack('<I',u.reg_read(UC_X86_REG_XMM0)&0xffffffff))[0]
                u.reg_write(UC_X86_REG_XMM0,struct.unpack('<I',struct.pack('<f',math_functions[name](x)))[0])
            u.reg_write(UC_X86_REG_RAX,result&0xffffffffffffffff)
            rsp=u.reg_read(UC_X86_REG_RSP)
            ret=self.pointer_at(rsp)
            u.reg_write(UC_X86_REG_RSP,rsp+8)
            u.reg_write(UC_X86_REG_RIP,ret)
            return
        if name in {'LoadCursorA','SetCursor','ClipCursor','GetClientRect','ClientToScreen','SetCursorPos','MapWindowPoints'}:
            return super().boundary(u,address,size,user)
        raise RuntimeError('Unexpected native ImGui import: '+name)

    def run(self,rva,stop=None,**registers):
        result=super().run(rva,stop=stop,**registers)
        expected=self.base+self.rva(stop) if stop is not None else self.stop
        if self.uc.reg_read(UC_X86_REG_RIP)!=expected:raise RuntimeError('Native replay instruction budget ended before return')
        return result

    def initialize_message_path(self):
        self.uc.mem_write(self.obj,struct.pack('<Q',self.base+self.rva(0x3bb4d8)))
        self.uc.mem_write(self.window,struct.pack('<Q',self.base+self.rva(0x433850)))
        self.run(0x2f010,stop=0x2f020,rdi=self.obj)
        self.run(0x62b75,stop=0x62b8a)
        self.run(0x1a8060,stop=0x1a80ee,rcx=self.obj)
        # Initialized TLS singleton getter boundary, not a mouse-event bypass.
        def window_getter(u,address,size,user):
            if address!=self.base+self.rva(0x2deb90):return
            sp=u.reg_read(UC_X86_REG_RSP)
            ret=self.pointer_at(sp)
            u.reg_write(UC_X86_REG_RAX,self.window)
            u.reg_write(UC_X86_REG_RSP,sp+8)
            u.reg_write(UC_X86_REG_RIP,ret)
        self.uc.hook_add(UC_HOOK_CODE,window_getter)

    def windows_mouse_message(self,message,x,y):
        self.run(0x2f3650,rcx=0x1234,rdx=message,r8=0,r9=(int(x)&65535)|((int(y)&65535)<<16))
        self.run(0x1a86a0,rcx=self.obj)

    def open_menu(self):
        self.rect=(0,0,1280,720)
        self.byte(0x4a2f1d,1)
        self.run(0x4fa66,stop=0x4fa6e,rcx=1)

    def native_owned_input_frame(self):
        self.run(0x2f3236,stop=0x2f3250,rdi=self.window,rbx=self.window+0x19)
        self.run(0x2f49e,stop=0x2f5b5,rbx=0,rbp=0,rdi=0)

    def initialize_imgui(self):
        self.run(0x63f20,rcx=self.io,rdx=0)  # real ImGuiContext constructor
        atlas=self.pointer_at(self.io+0xa8)
        font=self.allocate(0x100)
        fonts=self.allocate(8)
        self.uc.mem_write(fonts,struct.pack('<Q',font))
        self.uc.mem_write(atlas+0x48,struct.pack('<Q',fonts))
        self.uc.mem_write(atlas+0x40,struct.pack('<I',1))
        self.uc.mem_write(font+0x50,struct.pack('<Q',atlas))
        self.uc.mem_write(font+0x14,struct.pack('<f',24))
        self.uc.mem_write(font+0x68,struct.pack('<f',1))
        # The actual game's init enables NavGamepad and HasGamepad, not NoMouse.
        self.uc.mem_write(self.io+8,struct.pack('<II',2,1))
        self.uc.mem_write(self.io+0x10,struct.pack('<2f',1280,720))
        self.uc.mem_write(self.io+0x18,struct.pack('<f',1/60))
        self.uc.mem_write(self.io+0x3070,b'\1')  # no filesystem INI load
        self.title=self.allocate(64)
        self.label=self.allocate(64)
        self.checkbox_value=self.allocate(8)
        self.window_open=self.allocate(8)
        self.uc.mem_write(self.title,b'DEMENTIUM II DEBUG\0')
        self.uc.mem_write(self.label,b'Invulnerable\0')
        self.uc.mem_write(self.window_open,b'\1')

    def complete_checkbox_frame(self):
        # Execute the original input-to-IO transfer followed by COMPLETE native
        # NewFrame, including NavUpdate, MouseDownOwned and hover suppression.
        self.run(0x4fb44,stop=0x4fb52,r8=self.obj,rsi=self.io)
        unit=struct.unpack('<I',struct.pack('<f',1))[0]
        self.uc.reg_write(UC_X86_REG_XMM3,unit)
        self.uc.reg_write(UC_X86_REG_XMM4,unit)
        self.run(0x4fc4e,stop=0x4fc7e,r8=self.obj,rsi=self.io)
        self.run(0x68640)
        # Match the original debug window's position and size producer data.
        flags=struct.unpack('<I',self.uc.mem_read(self.io+0x1b50,4))[0]|3
        self.uc.mem_write(self.io+0x1b50,struct.pack('<I',flags))
        self.uc.mem_write(self.io+0x1b60,struct.pack('<2f',20,20))
        self.uc.mem_write(self.io+0x1b70,struct.pack('<2f',1240,680))
        self.uc.mem_write(self.io+0x1b58,struct.pack('<II',1,1))
        self.run(0x6cbf0,rcx=self.title,rdx=self.window_open,r8=0)
        window=self.pointer_at(self.io+0x1aa8)
        changed=self.run(0x86f60,rcx=self.label,rdx=self.checkbox_value)&255
        result=dict(value=bytes(self.uc.mem_read(self.checkbox_value,1))[0],changed=changed,
                    rect=struct.unpack('<4f',self.uc.mem_read(window+0x11c,16)),
                    window=window,hovered=self.pointer_at(self.io+0x1ab0),
                    owned=bytes(self.uc.mem_read(self.io+0x43f,1))[0],
                    nav_disable_mouse=bytes(self.uc.mem_read(self.io+0x1c7f,1))[0])
        self.run(0x6ef30)
        self.run(0x696c0)
        return result
