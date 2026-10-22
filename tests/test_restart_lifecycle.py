"""Actual PE reader -> native close -> next StartSection selection replay.

The external strncpy boundary copies real emulated bytes. Game resource loading
stops at its native entry: this reproduces the corrupt section argument, not a
claim of whole-engine/OS crash execution. No game process or saves are touched.
"""
import os,re,struct,sys,unittest
from pathlib import Path
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from localize import Zar
from native_replay import Replay

OVERRIDE=0x4c2200
FLAG=0x4c21ff

class RestartReplay:
 def __init__(self,path):
  self.r=Replay(path)
  self.world=0x30008000;self.owner=0x30004000;self.node=0x30005000;self.font=0x30006000;self.config=0x30007000
  self.writes=[];self.copy_calls=[]
  r=self.r
  r.uc.mem_write(self.font+0x18,b'\x10')
  r.uc.mem_write(self.node+0x68,struct.pack('<Q',self.font))
  self.strncpy=0x40001000;r.uc.mem_write(self.strncpy,b'\xc3')
  # Both original native calls use this existing MSVCRT strncpy import.
  r.write(0x37dd58,struct.pack('<Q',self.strncpy))
  r.uc.hook_add(UC_HOOK_CODE,self.copy_boundary)
  r.uc.hook_add(UC_HOOK_MEM_WRITE,self.watch)
 def watch(self,u,access,address,size,value,user):
  if address in [self.r.base+FLAG,self.r.base+OVERRIDE]:
   self.writes.append((hex(u.reg_read(UC_X86_REG_RIP)-self.r.base),hex(address-self.r.base),value))
 def copy_boundary(self,u,address,size,user):
  if address!=self.strncpy:return
  dst=u.reg_read(UC_X86_REG_RCX);src=u.reg_read(UC_X86_REG_RDX);count=u.reg_read(UC_X86_REG_R8)
  raw=bytes(u.mem_read(src,count));raw=raw.split(b'\0',1)[0][:count];u.mem_write(dst,raw.ljust(count,b'\0'))
  self.copy_calls.append((dst,src,count,raw))
  u.reg_write(UC_X86_REG_RAX,dst)
  rsp=u.reg_read(UC_X86_REG_RSP);ret=struct.unpack('<Q',u.mem_read(rsp,8))[0]
  u.reg_write(UC_X86_REG_RSP,rsp+8);u.reg_write(UC_X86_REG_RIP,ret)
 def read_cstring(self,address,size=8):return bytes(self.r.uc.mem_read(address,size)).split(b'\0',1)[0]
 def field_document_then_close(self,resource=504,lines=20):
  r=self.r;r.uc.mem_write(self.owner+0x128,struct.pack('<hh',resource,-1))
  r.uc.mem_write(self.owner+0x12c,('\n'.join('line%d'%i for i in range(lines))).encode()+b'\0')
  r.run(0x11b4f7,stop=0x11b501,rdi=self.owner,r12=self.owner+0x12c,r15=self.node,rsi=lines,rdx=lines*8,r8=86,rax=24)
  flag_during=r.byte(FLAG)
  # Original end-of-draw clear (11b52f) clears the actual renderer flag, not
  # the adjacent debug section override. Then execute actual patched close.
  r.run(0x11b52f,stop=0x11b536,rsi=0)
  r.run(0x11af80,stop=0x11af86,rcx=self.owner)
  return flag_during
 def next_start_section(self,configured=b'p0_000'):
  r=self.r;r.uc.mem_write(self.config,configured+b'\0')
  r.uc.mem_write(self.world+0x4080,b'XXXXXXXX')
  # Replay original config-result selection, strncpy, override test/copy and
  # consumption; RAX is the real config/village.ini StartSection result.
  r.run(0xaccf9,stop=0xacd54,rsi=self.world,rax=self.config,r15=0)
  selected=self.read_cstring(self.world+0x4080)
  used_override=bool(r.uc.reg_read(UC_X86_REG_R15)&255)
  # Continue through the original normal or override LoadSection call site,
  # stopping exactly at LoadSection entry with the native RCX argument.
  r.run(0xace50 if used_override else 0xace6a,stop=0x15ccf0,rdi=self.world+0x4080,rbx=0x30010000)
  argument=self.read_cstring(r.uc.reg_read(UC_X86_REG_RCX))
  return selected,argument,used_override

class RestartLifecycleTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.path=Path(os.environ.get('DEMENTIUM_RESTART_TEST_EXE',os.environ.get('DEMENTIUM_UI_TEST_EXE',os.environ.get('DEMENTIUM_MODIFIED_EXE',str(ROOT/'build/full-zh-CN/Dementium II.exe')))))
  cls.rom=Path(os.environ.get('DEMENTIUM_RESTART_TEST_ROM',str(ROOT/'build/full-zh-CN/rom.zar')))
 def test_field_reader_close_next_newgame_keeps_configured_start_section(self):
  z=Zar(self.rom.read_bytes());ini=z.read('CONFIG/VILLAGE.INI').decode('utf-8')
  starts=dict((int(a),b.encode()) for a,b in re.findall(r'^StartSection(\d+)\s*=\s*(\S+)',ini,re.M))
  for chapter in [0,1,2,3,4]:
   with self.subTest(chapter=chapter):
    x=RestartReplay(self.path);x.field_document_then_close()
    selected,argument,override=x.next_start_section(starts[chapter])
    self.assertEqual(argument,starts[chapter],f'LoadSection received {argument!r}; writes={x.writes}')
    self.assertEqual(selected,starts[chapter]);self.assertFalse(override)
 def test_adjacent_renderer_flag_and_section_override_are_distinct(self):
  x=RestartReplay(self.path);flag=x.field_document_then_close()
  self.assertEqual(flag,1,'displaced renderer flag was not set')
  self.assertEqual(x.r.byte(FLAG),0,'native end-of-draw did not clear renderer flag')
  self.assertEqual(x.r.byte(OVERRIDE),0,'reader corrupted the restart section override')
  self.assertEqual(x.r.dword(0xa68980),0,'native close did not reset reader state')
 def test_legitimate_debug_section_override_survives_reader(self):
  x=RestartReplay(self.path);x.r.write(OVERRIDE,b'v0_000\0\0')
  x.field_document_then_close(resource=41,lines=2)
  self.assertEqual(x.read_cstring(x.r.base+OVERRIDE),b'v0_000')
  self.assertEqual(x.next_start_section(),(b'v0_000',b'v0_000',True))
  self.assertEqual(x.r.byte(OVERRIDE),0,'native LoadStartLevel must consume override')
 def test_three_reader_restart_cycles_keep_section_names(self):
  x=RestartReplay(self.path)
  for section in [b'p0_000',b'v0_000',b'i0_04B']:
   x.field_document_then_close(lines=2)
   self.assertEqual(x.next_start_section(section),(section,section,False))

if __name__=='__main__':unittest.main()
