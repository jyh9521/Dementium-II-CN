"""Actual PE open/read/close -> Win32 key translation -> native action edges.

The viewport is a bounded 20-line fixture. Native initialization, reader hooks,
key callbacks, mode gates, action collection and edge computation all come from
selected shipped/built instructions; no game or save is opened.
"""
import os
from pathlib import Path
import struct
import unittest
from native_replay import Replay
from unicorn.x86_const import *
ROOT=Path(__file__).resolve().parents[1]
EXE=Path(os.environ.get('DEMENTIUM_UI_TEST_EXE') or os.environ.get('DEMENTIUM_MODIFIED_EXE') or ROOT/'build/full-zh-CN/Dementium II.exe')

class KeyReplay(Replay):
    def boundary(self,u,address,size,user):
        if self.stubs.get(address)=='RAWKEY':
            key=struct.unpack('<I',u.mem_read(u.reg_read(UC_X86_REG_RDX),4))[0]
            pressed=u.mem_read(u.reg_read(UC_X86_REG_R8),1)[0]
            self.raw_events.append((key,pressed))
        super().boundary(u,address,size,user)

@unittest.skipUnless(EXE.is_file(),'locally supplied patched PE required')
class ReaderKeyLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.v=KeyReplay(EXE);v=self.v;v.raw_events=[]
        v.uc.mem_write(v.obj,struct.pack('<Q',v.base+0x3bb4d8))
        v.write(0xa2ca78,struct.pack('<Q',v.obj))
        # Native startup disables direct-input mode through the original vtable.
        v.run(0x2f171,stop=0x2f199)
        self.assertEqual(self.field(0x458),0)
        v.write(0x4c2148,struct.pack('<Q',0x30018000))
        self.owner=0x30005000;self.node=0x30007000;self.font=0x30008000
        v.uc.mem_write(self.font+0x18,b'\x10')
        v.uc.mem_write(self.node+0x68,struct.pack('<Q',self.font))
        v.uc.mem_write(self.owner+0x128,struct.pack('<hh',504,-1))
        v.uc.mem_write(self.owner+0x12c,('甲乙\n'*19+'甲乙').encode('utf8')+b'\0')
        # Original listener tail must keep delivering ordinary game keys.
        listener=0x3000a000;table=0x3000b000;stub=0x40000800
        v.uc.mem_write(v.obj+0x390,struct.pack('<Q',listener))
        v.uc.mem_write(listener,struct.pack('<Q',table))
        v.uc.mem_write(table+0x10,struct.pack('<Q',stub))
        v.stubs[stub]='RAWKEY';v.uc.mem_write(stub,b'\xc3')

    def field(self,offset):return self.v.uc.mem_read(self.v.obj+offset,1)[0]
    def key(self,vk,pressed):
        v=self.v;internal=v.run(0x2dd940,rcx=vk)
        v.run(0x1a7dc0 if pressed else 0x1a7de0,rcx=internal)
        return internal
    def open_read(self):
        v=self.v
        v.run(0x11a7b0,stop=0x11a7b5,rcx=self.owner)
        v.run(0x11b4f7,stop=0x11b501,rdi=self.owner,r15=self.node,
              r12=self.owner+0x12c,rsi=20,edx=160,r8=86,rax=13)
        self.assertEqual(v.dword(0xa68980),1)
    def close(self,collection=False):
        v=self.v
        if collection:v.run(0x122a10,stop=0x122a1b,rcx=self.owner)
        else:v.run(0x11af80,stop=0x11af86,rcx=self.owner)
        self.assertEqual(v.dword(0xa68980),0)
    def collect(self):
        v=self.v
        v.run(0x155400,stop=0x1555d4)
        old=v.uc.reg_read(UC_X86_REG_EBX)
        v.run(0x15585d,stop=0x1558f4,rbx=old,rdi=0)
        return v.dword(0xa121b8),v.dword(0xa121ac)

    def test_e_release_after_reader_close_does_not_leave_native_interact_held(self):
        self.open_read();key=self.key(0x45,1)
        self.assertEqual(key,0x6d)
        self.collect();self.close();self.key(0x45,0)
        self.collect()
        print('READER_KEY_CLOSE E_field=%d active=%d direct_mode=%d raw_events=%s'%
              (self.field(0x227),self.v.dword(0xa68980),self.field(0x458),self.v.raw_events))
        self.assertEqual(self.field(0x227),0,'Reader must not latch a gameplay E field whose key-up will be mode-gated')
        self.assertEqual(self.field(0x458),0,'Closing reader must preserve original native direct mode')
        self.assertIn((0x6d,1),self.v.raw_events);self.assertIn((0x6d,0),self.v.raw_events)
        self.assertEqual(self.collect()[0]&0x4000,0)

    def test_reader_only_arrows_bypass_disabled_mode_not_wasd_or_e(self):
        self.open_read()
        for vk,field in [(0x45,0x227),(0x57,0x226),(0x41,0x223),(0x53,0x224)]:
            with self.subTest(vk=vk):
                self.key(vk,1);self.assertEqual(self.field(field),0)
                self.key(vk,0);self.assertEqual(self.field(field),0)
        for vk,field in [(0x26,0x22d),(0x28,0x22e)]:
            self.key(vk,1);self.assertEqual(self.field(field),1)
            self.key(vk,0);self.assertEqual(self.field(field),0)

    def test_close_neutralizes_held_scroll_arrows_without_changing_other_keys(self):
        for collection in [False,True]:
            self.open_read();self.key(0x26,1);self.key(0x28,1)
            self.assertEqual(self.field(0x22d),1);self.assertEqual(self.field(0x22e),1)
            before=bytes(self.v.uc.mem_read(self.v.obj,0x500))
            self.close(collection)
            after=bytes(self.v.uc.mem_read(self.v.obj,0x500))
            self.assertEqual(after[0x22d:0x22f],b'\0\0')
            self.assertTrue(all(a==b or i in [0x22d,0x22e] for i,(a,b) in enumerate(zip(before,after))))
            self.key(0x26,0);self.key(0x28,0)
            self.assertEqual(self.collect()[0]&0xc0,0)

    def test_original_enabled_mode_e_can_open_two_successive_interactions_after_close(self):
        v=self.v;v.run(0x2eb90,rcx=v.obj,edx=1)
        self.open_read();self.key(0x45,1)
        held,pressed=self.collect();self.assertTrue(held&0x4000);self.assertTrue(pressed&0x4000)
        self.close();self.key(0x45,0);held,pressed=self.collect()
        self.assertFalse(held&0x4000)
        self.key(0x45,1);held,pressed=self.collect()
        self.assertTrue(held&0x4000);self.assertTrue(pressed&0x4000,'Next E interaction must produce a fresh native edge')
        self.key(0x45,0);self.collect();self.key(0x45,1)
        self.assertTrue(self.collect()[1]&0x4000)

if __name__=='__main__':unittest.main(verbosity=2)
