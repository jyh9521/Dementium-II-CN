"""Actual PE right-stick axis setter -> field/collection reader; no game launch."""
import os,struct,unittest
import test_reader_transition_audit as transitions
from unicorn.x86_const import UC_X86_REG_XMM3,UC_X86_REG_XMM9,UC_X86_REG_XMM12

class ReaderGamepadTests(unittest.TestCase):
    def setUp(self):
        self.f=transitions.ReaderTransitionAuditTests('test_deactivation_clears_pending_wheel_owner_repeat')
        self.f.setUp();self.v=self.f.v;self.v.byte(0xa314f0,1)
    def axis(self,value,index=3,pad=0):
        bits=struct.unpack('<I',struct.pack('<f',value))[0]
        self.v.uc.reg_write(UC_X86_REG_XMM3,bits)
        self.v.run(0x2ed10,rcx=self.v.obj,edx=pad,r8=index)
    def render(self,**kw):self.f.render(**kw)
    def line(self):return self.f.state(16)
    def test_native_xinput_packet_normalization_and_callback_axis_three(self):
        v=self.v
        for raw,sign in ((32767,1),(-32768,-1)):
            v.write(0xa314ee,struct.pack('<h',raw))
            v.uc.reg_write(UC_X86_REG_XMM12,struct.unpack('<I',v.read(0x439d98,4))[0])
            v.run(0x31ad35,stop=0x31ad9a,r12=v.base,rdi=0,r13=0)
            bits=v.uc.reg_read(UC_X86_REG_XMM9)&0xffffffff
            value=struct.unpack('<f',struct.pack('<I',bits))[0]
            self.assertEqual(1 if value>0 else -1,sign)
            v.write(0xa2ca78,struct.pack('<Q',v.obj))
            v.uc.reg_write(UC_X86_REG_XMM3,bits)
            v.run(0x2ed10,rcx=v.obj,edx=0,r8=3)
            self.assertEqual(bytes(v.uc.mem_read(v.obj+0x2cc,4)),struct.pack('<I',bits))
    def test_stick_down_up_equals_one_wheel_notch(self):
        for collection in (False,True):
            with self.subTest(collection=collection):
                self.setUp();self.render(collection=collection)
                self.axis(-1);self.render(collection=collection);self.assertEqual(self.line(),3)
                self.axis(0);self.render(collection=collection)
                self.axis(1);self.render(collection=collection);self.assertEqual(self.line(),0)
    def test_hold_repeat_neutral_and_direction_reversal(self):
        self.render();self.axis(-1);self.render();self.assertEqual(self.line(),3)
        for _ in range(23):self.render()
        self.assertEqual(self.line(),3)
        self.render();self.assertEqual(self.line(),6)
        self.axis(1);self.render();self.assertEqual(self.line(),3)
        self.axis(0);self.render()
        for _ in range(40):self.render()
        self.assertEqual(self.line(),3)
        self.axis(-1);self.render();self.assertEqual(self.line(),6)
    def test_deadzone_invalid_values_horizontal_left_and_other_pad_do_not_scroll(self):
        self.render()
        for value in (0,.1,-.1,.35,-.35,float('nan'),float('inf'),-float('inf'),1.1,-1.1):
            self.axis(value);self.render();self.assertEqual(self.line(),0,str(value))
        self.axis(0)
        for index,pad in ((0,0),(1,0),(2,0),(3,1)):
            self.axis(-1,index,pad);self.render();self.assertEqual(self.line(),0)
        self.axis(-.5);self.render();self.assertEqual(self.line(),3)
    def test_clamps_and_last_line_reachable(self):
        for collection in (False,True):
            self.setUp();self.render(collection=collection);self.axis(-1)
            for _ in range(200):self.render(collection=collection)
            self.assertEqual(self.line(),11)
            self.axis(1)
            for _ in range(200):self.render(collection=collection)
            self.assertEqual(self.line(),0)
    def test_menu_and_focus_suspend_stick_without_pending_repeat(self):
        for gate in ('menu','focus','active','window','input','disconnect'):
            with self.subTest(gate=gate):
                self.setUp();self.render();self.axis(-1)
                if gate=='disconnect':self.v.byte(0xa314f0,0)
                elif gate=='menu':self.v.byte(0x4a2f1d,1)
                elif gate in ('focus','active'):self.v.uc.mem_write(self.v.window+(0x7a if gate=='focus' else 0x79),b'\0')
                elif gate=='window':self.v.write(0xa312b0,b'\0'*8)
                else:self.v.write(0x4c2228,b'\0'*8)
                for _ in range(30):self.render()
                self.assertEqual(self.line(),0)
                self.assertEqual(self.f.state(44),0);self.assertEqual(self.f.state(48),0)
                self.v.byte(0x4a2f1d,0);self.v.byte(0xa314f0,1)
                self.v.write(0xa312b0,struct.pack('<Q',self.v.window))
                self.v.write(0x4c2228,struct.pack('<Q',self.v.obj))
                self.v.uc.mem_write(self.v.window+0x79,b'\1\1')
                self.axis(0);self.render();self.assertEqual(self.line(),0)
                self.axis(-1);self.render();self.assertEqual(self.line(),3)
    def test_short_card_puzzle_never_acquire_stick(self):
        self.axis(-1)
        for resource,lines in ((504,2),(41,5),(535,20),(78,3)):
            self.render(resource=resource,lines=lines)
            self.assertEqual(self.f.state(0),0);self.assertEqual(self.line(),0)
            self.assertEqual(self.f.state(44),0)
    def test_open_close_resource_change_clear_stick_repeat_not_axis(self):
        for collection in (False,True):
            self.setUp();self.render(collection=collection);self.axis(-1);self.render(collection=collection)
            self.assertEqual(self.f.state(44),1)
            self.f.f.close(collection);self.assertEqual(self.f.state(44),0);self.assertEqual(self.f.state(48),0)
            self.assertEqual(struct.unpack('<f',self.v.uc.mem_read(self.v.obj+0x2cc,4))[0],-1)
            self.render(collection=collection);self.assertEqual(self.line(),3)
            self.render(resource=90,collection=collection);self.assertEqual(self.line(),3)
            self.render(resource=41,lines=5,collection=collection)
            self.assertEqual(self.f.state(44),0);self.assertEqual(self.f.state(48),0)
    def test_axis_and_keyboard_fields_preserved_and_existing_wheel_works(self):
        self.render();self.axis(-1);before=bytes(self.v.uc.mem_read(self.v.obj,0x500))
        self.render();self.assertEqual(bytes(self.v.uc.mem_read(self.v.obj,0x500)),before)
        self.axis(0);self.render()
        self.v.run(0x2ee30,rcx=self.v.obj,edx=-1);self.render();self.assertEqual(self.line(),6)
        self.f.f.key(0x28,1);self.render();self.assertEqual(self.line(),7)
        self.f.f.key(0x28,0)

if __name__=='__main__':unittest.main()
