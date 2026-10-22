"""Actual built code: mode-gated keys, wheel consumption and focus ownership."""
import os,struct,unittest
from pathlib import Path
from native_replay import Replay,BASE
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(os.environ.get('DEMENTIUM_UI_TEST_EXE',ROOT/'build/reader-input-fix/menu-patched.exe'))
@unittest.skipUnless(SOURCE.is_file(),'requires supplied built PE')
class MenuFocusTests(unittest.TestCase):
    def setUp(self):self.vm=Replay(SOURCE)
    def press(self,key,value=1):
        v=self.vm;v.run(0x1a7c50,rcx=v.obj,edx=key,r8=value)
    def field(self,offset):return bytes(self.vm.uc.mem_read(self.vm.obj+offset,1))[0]
    def test_keyboard_only_owned_by_visible_menu_or_reader(self):
        v=self.vm;v.byte(0x4a2f1d,1)
        for key,offset in [(0xf,0x22d),(0x11,0x22e),(0xe,0x22f),(0x10,0x230),(5,0x221),(1,0x222)]:
            self.press(key);self.assertEqual(self.field(offset),1)
            self.press(key,0);self.assertEqual(self.field(offset),0)
        v.byte(0x4a2f1d,0);self.press(0xf);self.assertEqual(self.field(0x22d),0)
        self.press(0x1c);self.assertEqual(self.field(0x22c),1)
        self.assertEqual(self.field(0x458),0)
        v.write(0xa68980,struct.pack('<I',1));self.press(0xf);self.assertEqual(self.field(0x22d),1)
    def test_keyboard_also_works_when_original_direct_mode_is_enabled(self):
        v=self.vm;v.byte(0x4a2f1d,1);v.uc.mem_write(v.obj+0x458,b'\1')
        self.press(5);self.assertEqual(self.field(0x221),1)
        self.press(5,0);self.assertEqual(self.field(0x221),0)
        v.byte(0x4a2f1d,0);self.press(0xf);self.assertEqual(self.field(0x22d),1)
    def test_reader_only_bypasses_mode_gate_for_up_and_down_not_gameplay_keys(self):
        v=self.vm;v.write(0xa68980,struct.pack('<I',1))
        for key,offset in [(0xf,0x22d),(0x11,0x22e)]:
            self.press(key);self.assertEqual(self.field(offset),1)
            self.press(key,0);self.assertEqual(self.field(offset),0)
        self.press(0x6d);self.assertEqual(self.field(0x227),0,'E must not latch while native direct mode is off')
        self.press(0xe);self.assertEqual(self.field(0x22f),0,'reader must not unlock unrelated directions')
        v.write(0xa68980,b'\0'*4);self.press(0x6d,0);self.assertEqual(self.field(0x227),0)
        v.uc.mem_write(v.obj+0x458,b'\1');v.write(0xa68980,struct.pack('<I',1))
        self.press(0x6d);self.assertEqual(self.field(0x227),1,'native-enabled input remains original')
        self.press(0x6d,0);self.assertEqual(self.field(0x227),0)
    def test_wheel_priority_menu_then_reader_then_original_game(self):
        v=self.vm;v.byte(0x4a2f1d,1)
        v.run(0x2ee30,rcx=v.obj,edx=1)
        self.assertEqual(struct.unpack('<f',v.uc.mem_read(v.io+0x140,4))[0],1.)
        self.assertEqual(v.dword(0xa136b4),0)
        v.write(0xa68980,struct.pack('<I',1));v.run(0x2ee30,rcx=v.obj,edx=0xffffffff)
        self.assertEqual(struct.unpack('<f',v.uc.mem_read(v.io+0x140,4))[0],0.)
        self.assertEqual(v.dword(0xa68984),0)
        v.byte(0x4a2f1d,0);v.run(0x2ee30,rcx=v.obj,edx=1)
        self.assertEqual(v.dword(0xa68984),1)
        v.write(0xa68980,b'\0'*4);v.run(0x2ee30,rcx=v.obj,edx=1)
        self.assertEqual(v.dword(0xa136b4),1)
    def test_native_windows_wheel_normalization_and_raw_event_ownership(self):
        v=self.vm;v.byte(0x4a2f1d,1)
        # Follow the native WM_MOUSEWHEEL high-word normalization, callback
        # wrappers and original vtable slots rather than injecting a fake delta.
        table=0x30006000;listener=0x30008000;listener_vtable=0x30009000;callback=0x40000800
        v.uc.mem_write(v.obj,struct.pack('<Q',table))
        v.uc.mem_write(table+0x60,struct.pack('<Q',v.base+0x2ee30))
        v.uc.mem_write(table+0x68,struct.pack('<Q',v.base+0x1a7d90))
        v.write(0xa2ca78,struct.pack('<Q',v.obj))
        v.write(0x4a3468,struct.pack('<Q',v.base+0x1a8020))
        v.write(0x4a3470,struct.pack('<Q',v.base+0x1a8030))
        v.uc.mem_write(v.obj+0x450,struct.pack('<Q',listener))
        v.uc.mem_write(listener,struct.pack('<Q',listener_vtable))
        v.uc.mem_write(listener_vtable+0x10,struct.pack('<Q',callback))
        v.stubs[callback]='RAW_GAME';v.uc.mem_write(callback,b'\xc3')
        for delta,expected in [(120,1.),(60,1.),(60,2.),(-120,1.)]:
            v.run(0x2deab1,stop=0x2deb33,rbx=(delta&0xffff)<<16)
            self.assertEqual(struct.unpack('<f',v.uc.mem_read(v.io+0x140,4))[0],expected)
        self.assertFalse(any(c[0]=='RAW_GAME' for c in v.calls),'menu must consume raw wheel before game listeners')
        v.byte(0x4a2f1d,0);v.run(0x1a7d90,rcx=v.obj,edx=120)
        self.assertTrue(any(c[0]=='RAW_GAME' for c in v.calls))
    def test_reader_arrows_do_not_leak_to_game_actions_or_close_letter_view(self):
        from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EDX,UC_X86_REG_EBX
        v=self.vm;v.write(0xa68980,struct.pack('<I',1))
        for rva in range(0xa121a0,0xa121c8,4):v.write(rva,struct.pack('<I',0x1ff))
        v.run(0x15587b,stop=0x1558c7,rax=0x1ff,rdx=0xc4,rbx=0x80,rdi=0)
        self.assertEqual(v.uc.reg_read(UC_X86_REG_EAX)&0xc0,0)
        self.assertEqual(v.uc.reg_read(UC_X86_REG_EDX)&0xc0,0)
        self.assertEqual(v.uc.reg_read(UC_X86_REG_EBX)&0xc0,0)
        self.assertTrue(all(v.dword(rva)&0xc0==0 for rva in range(0xa121a0,0xa121c8,4)))
        self.assertEqual(v.dword(0xa121b8),4,'unrelated previous/next-item action remains available')
        v.write(0xa68980,b'\0'*4)
        v.run(0x15587b,stop=0x1558c7,rax=0x80,rdx=0x80,rbx=0x80,rdi=0)
        self.assertEqual(v.dword(0xa121b8),0x80,'ordinary gameplay input remains unchanged')
    def frame(self):
        v=self.vm;v.run(0x4fa66,stop=0x4fa6e,rax=v.byte(0x4a2f1d),rcx=1)
    def test_open_cursor_visible_centered_clipped_and_close_restores_capture(self):
        v=self.vm;v.byte(0x4a2f1d,1);self.frame()
        calls=v.calls
        self.assertIn(('SetCursorPos',1060,590,None),calls)
        self.assertIn(('ClipCursor',next(c[1] for c in calls if c[0]=='ClipCursor' and c[3]),0,(100,50,2020,1130)),[(a,b,0,d) for a,b,c,d in calls])
        self.assertTrue(any(c[0]=='SetCursor' and c[1]==0x7777 for c in calls))
        self.assertEqual(bytes(v.uc.mem_read(v.window+0x19,1)),b'\0')
        n=len(calls);self.frame();self.assertEqual(len(calls),n,'holding open must not recenter every frame')
        v.byte(0x4a2f1d,0);self.frame()
        self.assertEqual(bytes(v.uc.mem_read(v.window+0x19,1)),b'\1')
        self.assertTrue(any(c[0]=='SetCursor' and c[1]==0 for c in v.calls))
        self.assertEqual(v.byte(0xa68e81),0)
    def test_focus_loss_unclips_and_refocus_recenters_without_losing_original_capture(self):
        v=self.vm;v.byte(0x4a2f1d,1);self.frame()
        v.uc.mem_write(v.window+0x79,b'\0');self.frame()
        self.assertTrue(v.calls,'focus transition must call cursor APIs')
        self.assertEqual(v.calls[-1][0:2],('ClipCursor',0))
        v.uc.mem_write(v.window+0x79,b'\1');self.frame()
        self.assertEqual(sum(c[0]=='SetCursorPos' for c in v.calls),2)
        v.byte(0x4a2f1d,0);self.frame()
        self.assertEqual(bytes(v.uc.mem_read(v.window+0x19,1)),b'\1')
    def test_f1_event_edge_to_cursor_ownership_and_release(self):
        v=self.vm
        states=[]
        for key in [0,1,1,0,1]:
            self.press(0x1c,key)
            v.run(0x4fa2e,stop=0x4fa6e,rcx=self.field(0x22c),rsi=0)
            states.append(v.byte(0x4a2f1d))
        self.assertEqual(states,[0,1,1,1,0])
        self.assertEqual(sum(c[0]=='SetCursorPos' for c in v.calls),1)
        self.assertEqual(bytes(v.uc.mem_read(v.window+0x19,1)),b'\1')
    def test_relative_hooks_work_after_image_relocation(self):
        self.vm=Replay(SOURCE,image_base=0x180000000)
        v=self.vm;v.byte(0x4a2f1d,1);self.frame()
        self.assertTrue(any(c[0]=='SetCursorPos' for c in v.calls))
        self.press(0xf);self.assertEqual(self.field(0x22d),1)
        v.run(0x2ee30,rcx=v.obj,edx=1)
        self.assertEqual(struct.unpack('<f',v.uc.mem_read(v.io+0x140,4))[0],1.)
    def test_client_center_and_clip_follow_resolution_and_desktop_origin(self):
        for width,height,origin in [(1280,720,(0,0)),(3840,2160,(-3840,0)),(3440,1440,(200,80))]:
            with self.subTest(size=(width,height),origin=origin):
                self.vm=Replay(SOURCE);v=self.vm;v.rect=(0,0,width,height);v.origin=origin
                v.byte(0x4a2f1d,1);self.frame()
                self.assertIn(('SetCursorPos',origin[0]+width//2,origin[1]+height//2,None),v.calls)
                self.assertTrue(any(c[0]=='ClipCursor' and c[3]==(origin[0],origin[1],origin[0]+width,origin[1]+height) for c in v.calls))
    def test_focus_hook_preserves_caller_registers_flags_and_stack(self):
        from unicorn import x86_const as regs
        v=self.vm;v.byte(0x4a2f1d,1)
        expected=dict(rax=1,rcx=0x123456,rdx=0x456789,r8=0x333333,r9=0x444444,r10=0x555555,r11=0x666666)
        v.run(0x4fa66,stop=0x4fa6e,eflags=0x246,**expected)
        for name,value in expected.items():self.assertEqual(v.uc.reg_read(getattr(regs,'UC_X86_REG_'+name.upper())),value)
        self.assertEqual(v.uc.reg_read(regs.UC_X86_REG_RSP),v.stack)
        self.assertEqual(v.uc.reg_read(regs.UC_X86_REG_EFLAGS)&0x8d5,0x246&0x8d5)
    def test_close_clears_menu_keys_but_keeps_f1_debounce_state(self):
        v=self.vm;v.byte(0x4a2f1d,1);self.frame()
        self.press(0xf);self.press(0x1c)
        v.byte(0x4a2f1d,0);self.frame()
        self.assertEqual(self.field(0x22d),0)
        self.assertEqual(self.field(0x22c),1)
    def test_native_platform_keeps_visible_cursor_and_game_capture_off(self):
        v=self.vm;v.byte(0x4a2f1d,1)
        out=v.run(0x2f3236,stop=0x2f3250,rdi=v.window,rbx=v.window+0x19,rax=0)
        self.assertEqual(out&255,1)
        v.run(0x2f4ad,stop=0x2f4b3,rbx=1)
        self.assertEqual(v.byte(0x49f1a5),0)
        v.byte(0x4a2f1d,0);v.run(0x2f4ad,stop=0x2f4b3,rbx=1)
        self.assertEqual(v.byte(0x49f1a5),1)
if __name__=='__main__':unittest.main(verbosity=2)
