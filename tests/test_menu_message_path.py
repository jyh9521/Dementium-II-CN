"""Diagnostic actual startup + Windows-message frontend + native mouse queue.

Uses shipped callback/vtable pointers, not forced +218/+219 fields. The
registered Win32 WndProc and downstream native producer/queue run as real PE
instructions. OS imports and the initialized TLS window getter are boundary
doubles. Messages are supplied fixtures, not live Windows delivery evidence.
"""
import os,struct,unittest
from pathlib import Path
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
from native_replay import Replay
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(os.environ.get('DEMENTIUM_UI_TEST_EXE',os.environ.get('DEMENTIUM_MODIFIED_EXE',str(ROOT/'build/full-zh-CN/Dementium II.exe'))))

class MenuMessagePathTests(unittest.TestCase):
 def setup(self):
  v=Replay(SOURCE)
  v.uc.mem_write(v.obj,struct.pack('<Q',v.base+0x3bb4d8))
  v.uc.mem_write(v.window,struct.pack('<Q',v.base+0x433850))
  # Actual Input constructor and game-specific startup enable move delivery.
  v.run(0x2f010,stop=0x2f020,rdi=v.obj)
  v.run(0x62b75,stop=0x62b8a)
  # Actual registration installs the down/up/move queue callbacks and raw path.
  v.run(0x1a8060,stop=0x1a80ee,rcx=v.obj)
  v.wndproc_trace=[]
  def getter(u,address,size,user):
   if address==v.base+0x2f39d2:v.wndproc_trace.append(('capture-and-discard',u.reg_read(UC_X86_REG_R13D)))
   if address==v.base+0x2f3a5d:v.wndproc_trace.append(('forward-common-handler',u.reg_read(UC_X86_REG_R13D)))
   if address!=v.base+0x2deb90:return
   sp=u.reg_read(UC_X86_REG_RSP);ret=struct.unpack('<Q',u.mem_read(sp,8))[0]
   u.reg_write(UC_X86_REG_RAX,v.window)
   u.reg_write(UC_X86_REG_RSP,sp+8);u.reg_write(UC_X86_REG_RIP,ret)
  v.uc.hook_add(UC_HOOK_CODE,getter)
  # Full registered WndProc also reaches DefWindowProc at the OS boundary.
  for dll in v.pe.DIRECTORY_ENTRY_IMPORT:
   for imp in dll.imports:
    if imp.name in [b'DefWindowProcA',b'DefWindowProcW',b'GetMessageExtraInfo']:
     stub=0x40002000+len(v.stubs)*16
     v.stubs[stub]=imp.name.decode();v.uc.mem_write(stub,b'\xc3')
     v.uc.mem_write(imp.address,struct.pack('<Q',stub))
  return v
 def message(self,v,message,x=320,y=240,dispatch=True):
  # Native this/hwnd/msg/wparam ABI has lParam in the fifth stack argument.
  v.uc.mem_write(v.stack+0x28,struct.pack('<Q',(x&65535)|((y&65535)<<16)))
  v.run(0x2de7a0,stop=0x2deb38,rcx=v.window,rdx=0x1234,r8=message,r9=0)
  if dispatch:v.run(0x1a86a0,rcx=v.obj)
 def full_message(self,v,message,x=320,y=240,dispatch=True,wparam=0):
  # Actual registered WNDPROC WinAPI ABI, not the downstream this/hwnd ABI.
  v.run(0x2f3650,rcx=0x1234,rdx=message,r8=wparam,r9=(x&65535)|((y&65535)<<16))
  if dispatch:v.run(0x1a86a0,rcx=v.obj)
 def test_registered_wndproc_menu_click_is_not_consumed_to_recapture(self):
  for down,up,offset in [(0x201,0x202,0x231),(0x204,0x205,0x232)]:
   with self.subTest(button=hex(down)):
    v=self.setup();v.byte(0x4a2f1d,1)
    v.run(0x4fa66,stop=0x4fa6e,rcx=1)
    self.full_message(v,0x200)
    self.assertEqual(struct.unpack('<2i',v.uc.mem_read(v.obj+0x340,8)),(320,240))
    self.full_message(v,down)
    self.assertEqual(bytes(v.uc.mem_read(v.obj+offset,1)),b'\1',f'actual WndProc discarded down before queue; capture={bytes(v.uc.mem_read(v.window+0x19,1))!r}; trace={v.wndproc_trace}')
    self.assertEqual(bytes(v.uc.mem_read(v.window+0x19,1)),b'\0','menu click stole capture back from menu ownership')
    self.full_message(v,up)
    self.assertEqual(bytes(v.uc.mem_read(v.obj+offset,1)),b'\0')
 def test_registered_wndproc_menu_keyboard_is_unchanged(self):
  v=self.setup();v.byte(0x4a2f1d,1)
  v.run(0x4fa66,stop=0x4fa6e,rcx=1)
  for key,offset in [(0x28,0x22e),(0x0d,0x221),(0x1b,0x222)]:
   self.full_message(v,0x100,wparam=key)
   self.assertEqual(bytes(v.uc.mem_read(v.obj+offset,1)),b'\1')
   self.full_message(v,0x101,wparam=key)
   self.assertEqual(bytes(v.uc.mem_read(v.obj+offset,1)),b'\0')
  self.assertEqual(bytes(v.uc.mem_read(v.window+0x19,1)),b'\0')
 def test_registered_wndproc_menu_mouse_keeps_original_focus_guards(self):
  for offset in [0x79,0x7a]:
   with self.subTest(focus_field=offset):
    v=self.setup();v.byte(0x4a2f1d,1)
    v.run(0x4fa66,stop=0x4fa6e,rcx=1)
    v.uc.mem_write(v.window+offset,b'\0')
    self.full_message(v,0x201)
    self.assertEqual(bytes(v.uc.mem_read(v.obj+0x231,1)),b'\0')
    self.assertEqual(bytes(v.uc.mem_read(v.window+0x19,1)),b'\0','unfocused menu must not recapture')
 def test_registered_wndproc_closed_game_retains_first_click_capture(self):
  v=self.setup();v.byte(0x4a2f1d,0)
  v.uc.mem_write(v.window+0x19,b'\0');v.uc.mem_write(v.window+0x1a,b'\0')
  self.full_message(v,0x201)
  self.assertEqual(bytes(v.uc.mem_read(v.window+0x19,1)),b'\1')
  self.assertEqual(bytes(v.uc.mem_read(v.obj+0x231,1)),b'\0')
 def test_real_startup_enables_queued_button_and_position_input(self):
  v=self.setup()
  self.assertEqual(bytes(v.uc.mem_read(v.obj+0x218,3)),b'\1\1\1')
  self.assertEqual([struct.unpack('<Q',v.read(a,8))[0]-v.base for a in [0x4a3450,0x4a3458,0x4a3460]],[0x1a7fe0,0x1a7f80,0x1a7fc0])
 def test_supplied_win32_messages_reach_real_queue_and_menu_button_fields(self):
  v=self.setup();v.byte(0x4a2f1d,1)
  v.run(0x4fa66,stop=0x4fa6e,rcx=1)
  self.assertEqual(bytes(v.uc.mem_read(v.window+0x19,1)),b'\0')
  for message,expected in [(0x200,0),(0x201,1),(0x202,0),(0x204,0),(0x205,0)]:
   self.message(v,message)
   self.assertEqual(bytes(v.uc.mem_read(v.obj+0x231,1))[0],expected)
   self.assertEqual(struct.unpack('<2i',v.uc.mem_read(v.obj+0x340,8)),(320,240))
  self.assertEqual(bytes(v.uc.mem_read(v.obj+0x232,1)),b'\0')
 def test_native_queue_coalesces_down_up_before_one_frame_to_released(self):
  v=self.setup();v.byte(0x4a2f1d,1)
  v.run(0x4fa66,stop=0x4fa6e,rcx=1)
  writes=[]
  def watch(u,access,address,size,value,user):
   if address==v.obj+0x231:writes.append(value)
  v.uc.hook_add(UC_HOOK_MEM_WRITE,watch)
  self.message(v,0x201,dispatch=False);self.message(v,0x202,dispatch=False)
  self.assertEqual(v.dword(0xa2ca68)&6,6,'both edges must be pending in the native queue')
  v.run(0x1a86a0,rcx=v.obj)
  self.assertEqual(writes,[1,0],'the native queue delivers both edges before the consumer frame')
  self.assertEqual(bytes(v.uc.mem_read(v.obj+0x231,1)),b'\0')
  self.assertEqual(v.dword(0xa2ca68)&6,0)
 def test_native_raw_registration_does_not_set_legacy_suppression_bits(self):
  v=self.setup()
  self.assertEqual(v.pe.get_data(0x2f1e6b,7),bytes.fromhex('c745a001000200'))
  self.assertEqual(v.pe.get_data(0x2f1e72,7),bytes.fromhex('c745a400200000'))
  flags=int.from_bytes(v.pe.get_data(0x2f1e75,4),'little')
  self.assertEqual(flags&0x30,0)

if __name__=='__main__':unittest.main()
