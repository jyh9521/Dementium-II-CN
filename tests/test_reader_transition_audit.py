"""Actual selected PE reader transitions and paired native key event audit."""
import hashlib,json,os,struct,unittest
from pathlib import Path
import test_reader_key_lifecycle as keys
ROOT=Path(__file__).resolve().parents[1]

class ReaderTransitionAuditTests(unittest.TestCase):
    def setUp(self):
        self.f=keys.ReaderKeyLifecycleTests('test_e_release_after_reader_close_does_not_leave_native_interact_held')
        self.f.setUp();self.v=self.f.v
    def render(self,resource=504,lines=20,owner=None,collection=False):
        f=self.f;v=self.v;o=owner or f.owner
        v.uc.mem_write(o+0x128,struct.pack('<hh',resource,41 if resource==41 else -1))
        v.uc.mem_write(o+0x1d0,struct.pack('<I',resource))
        text=('甲乙\n'*(lines-1)+'甲乙').encode()+b'\0'
        v.uc.mem_write(o+0x12c,text)
        if collection:
            v.uc.mem_write(o+0x1e0,text)
            v.uc.mem_write(f.node+0x40,struct.pack('<Q',f.font))
            v.run(0x123379,stop=0x123383,r14=o+0x1e0,rsi=f.node,rdi=lines,ecx=lines*8,r8=0)
        else:v.run(0x11b4f7,stop=0x11b501,rdi=o,r15=f.node,r12=o+0x12c,rsi=lines,edx=lines*8,r8=86,rax=13)
    def state(self,offset):return self.v.dword(0xa68980+offset)
    def test_active_to_nonreader_preserves_keyup_and_game_actions(self):
        for mode in (0,1):
            for collection in (False,True):
                for resource,lines in ((504,2),(41,5),(535,20),(78,3)):
                    with self.subTest(mode=mode,collection=collection,resource=resource,lines=lines):
                        self.setUp();f=self.f;v=self.v
                        v.run(0x2eb90,rcx=v.obj,edx=mode)
                        self.render(collection=collection);self.assertEqual(self.state(0),1)
                        f.key(0x28,1);self.render(collection=collection)
                        self.assertEqual(f.field(0x22e),1)
                        self.render(resource,lines,collection=collection);self.assertEqual(self.state(0),0)
                        f.key(0x28,0)
                        self.assertEqual(f.field(0x22e),0,'Inactive transition must not strand a reader-introduced key')
                        self.assertEqual(f.collect()[0]&0xc0,0)
                        self.assertEqual(f.field(0x458),mode)
    def test_open_reset_while_arrow_held_does_not_strand_key(self):
        for mode in (0,1):
            for collection in (False,True):
                with self.subTest(mode=mode,collection=collection):
                    self.setUp();f=self.f;v=self.v;v.run(0x2eb90,rcx=v.obj,edx=mode)
                    self.render();f.key(0x26,1)
                    v.run(0x121e50 if collection else 0x11a7b0,stop=0x121e55 if collection else 0x11a7b5,rcx=f.owner)
                    self.assertEqual(self.state(0),0)
                    f.key(0x26,0);self.assertEqual(f.field(0x22d),0)
    def test_long_resource_owner_switch_resets_scroll_wheel_repeat(self):
        for collection in (False,True):
            for change in ('resource','owner'):
                with self.subTest(collection=collection,change=change):
                    self.setUp();f=self.f;v=self.v;self.render(collection=collection)
                    v.write(0xa68984,struct.pack('<i',-3));self.render(collection=collection)
                    self.assertEqual(self.state(16),9)
                    v.write(0xa68984,struct.pack('<i',-5));v.write(0xa6899c,struct.pack('<I',19))
                    self.render(90 if change=='resource' else 504,20,0x3000c000 if change=='owner' else None,collection)
                    self.assertEqual(self.state(0),1);self.assertEqual(self.state(16),0)
                    self.assertEqual(self.state(4),0);self.assertEqual(self.state(28),0)
                    self.assertEqual(self.state(24),4 if change=='resource' else 9)
    def test_deactivation_clears_pending_wheel_owner_repeat(self):
        for collection in (False,True):
            self.setUp();self.render(collection=collection)
            self.v.write(0xa68984,struct.pack('<i',-7));self.v.write(0xa6899c,struct.pack('<I',19))
            self.render(41,5,collection=collection)
            for offset in (0,4,8,12,16,20,28):self.assertEqual(self.state(offset),0)
            self.render(collection=collection);self.assertEqual(self.state(16),0)
    def test_unrelated_inactive_page_does_not_clear_enabled_game_arrows(self):
        self.v.run(0x2eb90,rcx=self.v.obj,edx=1);self.f.key(0x28,1)
        self.render(41,5);self.assertEqual(self.f.field(0x22e),1)
        self.f.key(0x28,0);self.assertEqual(self.f.field(0x22e),0)
    def test_inactive_open_close_never_clears_unowned_arrows(self):
        for mode in (0,1):
            for collection in (False,True):
                with self.subTest(mode=mode,collection=collection):
                    self.setUp();v=self.v;f=self.f
                    v.run(0x2eb90,rcx=v.obj,edx=mode)
                    v.uc.mem_write(v.obj+0x22d,b'\1\1')
                    v.run(0x121e50 if collection else 0x11a7b0,stop=0x121e55 if collection else 0x11a7b5,rcx=f.owner)
                    self.assertEqual(bytes(v.uc.mem_read(v.obj+0x22d,2)),b'\1\1')
                    f.close(collection)
                    self.assertEqual(bytes(v.uc.mem_read(v.obj+0x22d,2)),b'\1\1')
                    self.assertEqual(f.field(0x458),mode)
    def test_null_input_is_valid_for_deactivation_open_close(self):
        for transition in ('inactive','open','close'):
            for collection in (False,True):
                with self.subTest(transition=transition,collection=collection):
                    self.setUp();v=self.v;f=self.f;self.render(collection=collection)
                    v.write(0x4c2228,b'\0'*8)
                    if transition=='inactive':self.render(41,5,collection=collection)
                    elif transition=='open':v.run(0x121e50 if collection else 0x11a7b0,stop=0x121e55 if collection else 0x11a7b5,rcx=f.owner)
                    else:f.close(collection)
                    self.assertEqual(self.state(0),0)
    def test_held_arrows_across_active_owner_resource_change_release_normally(self):
        for mode in (0,1):
            for collection in (False,True):
                with self.subTest(mode=mode,collection=collection):
                    self.setUp();v=self.v;f=self.f;v.run(0x2eb90,rcx=v.obj,edx=mode)
                    self.render(collection=collection);f.key(0x28,1)
                    self.render(90,20,collection=collection)
                    self.assertEqual(self.state(0),1)
                    f.key(0x28,0);self.render(504,20,0x3000c000,collection)
                    self.assertEqual(f.field(0x22e),0)
                    self.assertEqual(self.state(16),0);self.assertEqual(self.state(20),0)
                    self.assertEqual(self.state(28),0)
if __name__=='__main__':unittest.main(verbosity=2)
