"""Native checkbox bool transitions with intervening real engine mouse polling.

Rendering/GPU calls are not run: the native Checkbox calls ButtonBehavior and
executes its actual bool-flip/edited-state branch; drawing follows the stop point.
"""
import os
from pathlib import Path
import struct
import unittest
import test_menu_pointer_dispatch as pointer

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(os.environ.get('DEMENTIUM_UI_TEST_EXE',ROOT/'build/full-zh-CN/Dementium II.exe'))

@unittest.skipUnless(SOURCE.is_file(),'requires supplied native executable')
class MenuWidgetActivationTests(unittest.TestCase):
    image_base=None
    memfloat=pointer.MenuPointerDispatchTests.memfloat
    number=pointer.MenuPointerDispatchTests.number
    open=pointer.MenuPointerDispatchTests.open
    event=pointer.MenuPointerDispatchTests.event
    consume=pointer.MenuPointerDispatchTests.consume
    def setUp(self):
        # Reuse the same native platform/callback fixture, but not its shallow
        # click-field assertions. Point its explicit source at this test input.
        previous=pointer.SOURCE
        pointer.SOURCE=SOURCE
        try: pointer.MenuPointerDispatchTests.setUp(self)
        finally: pointer.SOURCE=previous
        v=self.vm
        v.uc.mem_write(v.io+0x1aa8,struct.pack('<Q',self.menu))
        v.uc.mem_write(v.io+0x1c28,struct.pack('<Q',self.menu))
        v.uc.mem_write(v.io+0x1a60,struct.pack('<I',1))
        v.uc.mem_write(v.io+0x1a68,struct.pack('<Q',self.table+0x100))
        v.uc.mem_write(self.menu+0x268,struct.pack('<4f',100,100,500,500))
        self.checkbox=0x3000b000
        self.widget_frame=0x3000a000
        self.rect=self.widget_frame-0x79
        v.uc.mem_write(self.rect,struct.pack('<4f',180,200,240,250))

    def checkbox_frame(self,poll=True):
        v=self.vm
        if poll:
            # Engine UpdateInput, after queued messages but BEFORE DrawDebugMenu.
            # Capture is false; raw gameplay left/right are neutral while UI owns it.
            v.run(0x2f49e,stop=0x2f5b5,rbx=0,rbp=0,rdi=0)
        self.consume()
        v.uc.mem_write(v.stack+0x20,struct.pack('<I',0))
        v.run(0x87168,stop=0x8719e,rcx=self.rect,edx=0x1234,
              r8=self.widget_frame+0x77,r9=self.widget_frame+0x7f,
              rbp=self.widget_frame,r12=self.checkbox,r15=0)
        return bytes(v.uc.mem_read(self.checkbox,1))[0]

    def sequence(self,poll=True):
        values=[]
        self.event(0x200)
        values.append(self.checkbox_frame(poll))
        for message in (0x201,None,0x202,None,0x201,0x202):
            if message is not None: self.event(message)
            values.append(self.checkbox_frame(poll))
        return values

    def test_native_checkbox_control_without_intervening_engine_poll(self):
        self.assertEqual(self.sequence(False),[0,0,0,1,1,1,0])

    def test_native_checkbox_toggles_after_real_engine_mouse_poll(self):
        self.assertEqual(self.sequence(),[0,0,0,1,1,1,0],
                         'engine mouse synthesis overwrote UI button before Checkbox')

    def action_frame(self,poll=True):
        from unicorn.x86_const import UC_X86_REG_RAX
        v=self.vm
        if poll: v.run(0x2f49e,stop=0x2f5b5,rbx=0,rbp=0,rdi=0)
        self.consume()
        v.uc.mem_write(v.stack+0x20,struct.pack('<I',0))
        # Actual ButtonEx call to the untouched native ButtonBehavior.
        v.run(0x860ca,stop=0x860cf,rcx=self.rect,edx=0x4321,
              r8=self.widget_frame+0x77,r9=self.widget_frame+0x7f,
              rbp=self.widget_frame)
        pressed=v.uc.reg_read(UC_X86_REG_RAX)&255
        queue,wrapper,callback,table=0x3000c000,0x3000d000,0x3000e000,0x3000f000
        # Local callback boundary increments a fixture counter only. Its native
        # vtable invocation, menu queue ownership transfer and decision are real.
        v.uc.mem_write(callback,struct.pack('<Q',table))
        v.uc.mem_write(table+0x10,struct.pack('<Q',0x40001000))
        v.uc.mem_write(0x40001000,bytes.fromhex('ff4108c3'))
        v.uc.mem_write(wrapper+0x38,struct.pack('<Q',callback))
        v.write(0xa261c0,struct.pack('<3Q',queue,queue,queue+0x400))
        v.run(0x4e364,stop=0x4e3e2,rax=pressed,rbx=wrapper,rdi=1)
        end=struct.unpack('<Q',v.read(0xa261c8,8))[0]
        # Real gameplay callback-dispatch loop executes exactly the queued items.
        v.run(0xac0e9,stop=0xac10f,rsi=queue,rdi=end)
        return struct.unpack('<I',v.uc.mem_read(callback+8,4))[0]

    def test_native_action_button_dispatches_one_callback_per_complete_click(self):
        values=[]
        for message in (0x200,0x201,None,0x202,None,0x201,0x202):
            if message is not None:self.event(message)
            values.append(self.action_frame())
        self.assertEqual(values,[0,0,0,1,1,1,2])

    def frame_visibility(self,value):
        v=self.vm;v.byte(0x4a2f1d,value)
        v.run(0x4fa66,stop=0x4fa6e,rax=value,rcx=1)

    def test_close_reopen_cancels_held_widget_without_phantom_release(self):
        self.event(0x200);self.checkbox_frame()
        self.event(0x201);self.assertEqual(self.checkbox_frame(),0)
        self.frame_visibility(0);self.frame_visibility(1)
        self.event(0x200);self.assertEqual(self.checkbox_frame(),0)
        self.event(0x202);self.assertEqual(self.checkbox_frame(),0)
        self.event(0x201);self.assertEqual(self.checkbox_frame(),0)
        self.event(0x202);self.assertEqual(self.checkbox_frame(),1)

    def test_focus_loss_cancels_held_widget_and_refocus_accepts_fresh_click(self):
        v=self.vm
        self.event(0x200);self.checkbox_frame()
        self.event(0x201);self.assertEqual(self.checkbox_frame(),0)
        v.uc.mem_write(v.window+0x79,b'\0');self.frame_visibility(1)
        v.run(0x2f49e,stop=0x2f5b5,rbx=0,rbp=0,rdi=0)
        v.uc.mem_write(v.window+0x79,b'\1');self.frame_visibility(1)
        self.event(0x200);self.assertEqual(self.checkbox_frame(),0)
        self.event(0x202);self.assertEqual(self.checkbox_frame(),0)
        self.event(0x201);self.checkbox_frame()
        self.event(0x202);self.assertEqual(self.checkbox_frame(),1)

    def test_closed_menu_gameplay_polling_writes_original_button_fields(self):
        v=self.vm;self.frame_visibility(0)
        v.byte(0xa12455,1);v.byte(0xa1245b,1)
        v.run(0x2f49e,stop=0x2f5b5,rbx=1,rbp=1,rdi=0)
        self.assertEqual(bytes(v.uc.mem_read(v.obj+0x231,2)),b'\1\1')

class RelocatedMenuWidgetActivationTests(MenuWidgetActivationTests):
    image_base=0x180000000

if __name__=='__main__':unittest.main(verbosity=2)
