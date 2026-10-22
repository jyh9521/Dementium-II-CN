"""Replay real platform dispatch, queued callbacks and native ImGui consumers.

Unlike the old direct-input tests, this starts BEFORE the window capture gate.
No game process or OS input is generated; Win32 cursor calls use Replay doubles.
"""
import os
from pathlib import Path
import struct
import unittest
from native_replay import Replay

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get('DEMENTIUM_UI_TEST_EXE', ROOT/'build/menu-click-fix/modified.exe'))

@unittest.skipUnless(SOURCE.is_file(), 'requires supplied native executable')
class MenuPointerDispatchTests(unittest.TestCase):
    image_base = None
    def setUp(self):
        self.vm = v = Replay(SOURCE,image_base=self.image_base)
        self.table = 0x30006000
        self.menu = 0x30008000
        v.uc.mem_write(v.obj, struct.pack('<Q', self.table))
        v.uc.mem_write(self.table+0x50, struct.pack('<Q', v.base+0x2ed60))
        for field in (0x218, 0x219): v.uc.mem_write(v.obj+field, b'\1')
        for slot, callback in [(0x4a3450,0x1a7fe0), (0x4a3458,0x1a7f80), (0x4a3460,0x1a7fc0)]:
            v.write(slot, struct.pack('<Q',v.base+callback))
        self.memfloat(v.io+0x18, 1/60)
        for index in range(5): self.memfloat(v.io+0x44c+index*4, -1)
        # Native hovered-window selection: the menu occupies this client rectangle.
        v.uc.mem_write(v.io+0x1a50, struct.pack('<I',1))
        v.uc.mem_write(v.io+0x1a58, struct.pack('<Q',self.table+0x100))
        v.uc.mem_write(self.table+0x100, struct.pack('<Q',self.menu))
        v.uc.mem_write(self.menu+0x7e,b'\1')
        v.uc.mem_write(self.menu+0x218,struct.pack('<4f',100,100,500,500))
        v.uc.mem_write(self.menu+0x3c8,struct.pack('<Q',self.menu))
        self.memfloat(self.menu+0x2c0,1)
        self.memfloat(self.menu+0x234,500)
        self.memfloat(self.menu+0x22c,100)
        self.memfloat(v.io+0x194c,13)
        self.open()

    def memfloat(self,address,value): self.vm.uc.mem_write(address,struct.pack('<f',value))
    def number(self,address): return struct.unpack('<f',self.vm.uc.mem_read(address,4))[0]
    def open(self):
        v=self.vm; v.byte(0x4a2f1d,1)
        v.run(0x4fa66,stop=0x4fa6e,rax=1,rcx=1)
        self.assertEqual(bytes(v.uc.mem_read(v.window+0x19,1)),b'\0')

    def event(self,message,x=200,y=220):
        v=self.vm
        # Native platform handler -> native queue -> native input object vtable.
        v.run(0x2f5350,rcx=v.window,edx=message,r8=x,r9=y)
        v.run(0x1a86a0,rcx=v.obj)

    def consume(self):
        from unicorn.x86_const import UC_X86_REG_XMM3,UC_X86_REG_XMM4
        v=self.vm
        # Original DrawDebugMenu's button and client-to-menu coordinate transfer.
        v.run(0x4fb44,stop=0x4fb52,r8=v.obj,rsi=v.io)
        unit=struct.unpack('<I',struct.pack('<f',1))[0]
        v.uc.reg_write(UC_X86_REG_XMM3,unit); v.uc.reg_write(UC_X86_REG_XMM4,unit)
        v.run(0x4fc4e,stop=0x4fc7e,r8=v.obj,rsi=v.io)
        v.run(0x678e0)  # actual ImGui UpdateMouseInputs, not a reimplementation
        v.run(0x69d40)  # actual ImGui hovered-window selection

    def test_uncaptured_menu_move_click_hold_release_reaches_imgui(self):
        v=self.vm
        self.event(0x200); self.consume()
        self.assertEqual((self.number(v.io+0x130),self.number(v.io+0x134)),(200,220),
                         'visible cursor movement was blocked by native capture gate')
        self.assertEqual(struct.unpack('<Q',v.uc.mem_read(v.io+0x1ab0,8))[0],self.menu)
        self.event(0x201); self.consume()
        self.assertEqual(bytes(v.uc.mem_read(v.io+0x430,1)),b'\1','ImGui did not receive click edge')
        self.consume()
        self.assertEqual(bytes(v.uc.mem_read(v.io+0x430,1)),b'\0','hold must not repeat click')
        self.event(0x202); self.consume()
        self.assertEqual(bytes(v.uc.mem_read(v.io+0x43a,1)),b'\1','ImGui did not receive release edge')

    def test_wheel_uses_native_hover_and_changes_real_menu_scroll_target(self):
        v=self.vm
        self.event(0x200); self.consume()
        v.run(0x2ee30,rcx=v.obj,edx=0xffffffff)
        v.run(0x67c70)  # actual ImGui UpdateMouseWheel
        self.assertGreater(self.number(self.menu+0x68),0,
                           'wheel arrived but menu never hovered because mouse move was dropped')
        self.assertEqual(v.dword(0xa136b4),0,'menu wheel must not reach gameplay')

    def test_closed_menu_and_unfocused_window_keep_original_dispatch_gate(self):
        v=self.vm; v.byte(0x4a2f1d,0)
        self.event(0x201)
        self.assertEqual(v.dword(0xa2ca68),0)
        v.byte(0x4a2f1d,1)
        for flag in (0x79,0x7a):
            v.uc.mem_write(v.window+flag,b'\0'); self.event(0x201)
            self.assertEqual(v.dword(0xa2ca68),0)
            v.uc.mem_write(v.window+flag,b'\1')

class RelocatedMenuPointerDispatchTests(MenuPointerDispatchTests):
    image_base = 0x180000000

if __name__=='__main__': unittest.main(verbosity=2)
