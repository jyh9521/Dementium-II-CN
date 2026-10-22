"""Independent input boundary audit: native WndProc focus, hook ABI, state bounds."""
import os,struct,sys,unittest
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *
import test_menu_message_path as message_path
from native_replay import Replay
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(os.environ.get('DEMENTIUM_UI_TEST_EXE',os.environ.get('DEMENTIUM_MODIFIED_EXE',str(ROOT/'build/full-zh-CN/Dementium II.exe'))))

class AuditedReplay(Replay):
 def __init__(self,path):
  self.boundaries=[]
  super().__init__(path)
 def boundary(self,u,address,size,user):
  if address not in self.stubs:return
  self.boundaries.append((self.stubs[address],u.reg_read(UC_X86_REG_RSP)&15))
  super().boundary(u,address,size,user)
  # Simulate ABI-permitted clobbers which ordinary API doubles leave intact.
  for k,reg in enumerate([UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9,UC_X86_REG_R10,UC_X86_REG_R11]):u.reg_write(reg,0xc0000000+k)
  for k in range(6):u.reg_write(globals()['UC_X86_REG_XMM'+str(k)],int.from_bytes(bytes([0xc0+k])*16,'little'))
  u.reg_write(UC_X86_REG_EFLAGS,0x202)

class InputBoundaryAuditTests(unittest.TestCase):
 def helper(self):
  class AbiMessages(message_path.MenuMessagePathTests):
   def full_message(self,v,*args,**kwargs):
    # Replay.run's default stack is a mid-function jump site (mod16=0).
    # Actual Win32 WNDPROC and queue FUNCTION entries receive a return address.
    saved=v.stack;v.stack=saved-8
    try:return super().full_message(v,*args,**kwargs)
    finally:v.stack=saved
  return AbiMessages('test_real_startup_enables_queued_button_and_position_input')
 def message_vm(self,base=None):
  h=self.helper()
  if base is None:return h,h.setup()
  original=message_path.Replay
  message_path.Replay=lambda path:Replay(path,image_base=base)
  try:return h,h.setup()
  finally:message_path.Replay=original
 def attach_raw_listener(self,v,clobber=False):
  listener=0x30009000;vtable=0x30009100;callback=0x40008000;events=[]
  v.uc.mem_write(listener,struct.pack('<Q',vtable));v.uc.mem_write(vtable+0x10,struct.pack('<Q',callback))
  v.uc.mem_write(callback,b'\xc3');v.uc.mem_write(v.obj+0x390,struct.pack('<Q',listener))
  v.raw_listener_alignments=[]
  def watch(u,address,size,user):
   if address==callback:
    key=struct.unpack('<I',u.mem_read(u.reg_read(UC_X86_REG_RDX),4))[0]
    state=bytes(u.mem_read(u.reg_read(UC_X86_REG_R8),1))[0]
    events.append((key,state));v.raw_listener_alignments.append(u.reg_read(UC_X86_REG_RSP)&15)
    if clobber:
     for k,reg in enumerate([UC_X86_REG_RAX,UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9,UC_X86_REG_R10,UC_X86_REG_R11]):u.reg_write(reg,0xabc000+k)
     for k in range(6):u.reg_write(globals()['UC_X86_REG_XMM'+str(k)],int.from_bytes(bytes([0xd0+k])*16,'little'))
     u.reg_write(UC_X86_REG_EFLAGS,0x202)
  v.uc.hook_add(UC_HOOK_CODE,watch)
  return events
 def test_focus_message_owner_mode_matrix_releases_all_native_raw_callbacks(self):
  for base in [0x140000000,0x180000000]:
   for message in [8,0x1c]:
    for owner in ['game','reader','menu']:
     for mode in [0,1]:
      with self.subTest(base=hex(base),message=hex(message),owner=owner,mode=mode):
       h,v=self.message_vm(base);v.uc.mem_write(v.obj+0x458,bytes([mode]))
       v.byte(0x4a2f1d,int(owner=='menu'));v.write(0xa68980,struct.pack('<I',int(owner=='reader')))
       if owner=='menu':v.run(0x4fa66,stop=0x4fa6e,rcx=1)
       events=self.attach_raw_listener(v,clobber=True)
       for key in [0x45,0x28,0x70]:h.full_message(v,0x100,wparam=key)
       downs=[key for key,state in events if state]
       self.assertEqual(len(downs),3)
       h.full_message(v,message,wparam=0)
       self.assertEqual(sorted(key for key,state in events if state==0),sorted(downs),'focus loss did not emit native key-up callbacks')
       self.assertTrue(all(v.byte(0xa30d20+key)==0 for key in [0x45,0x28,0x70]))
       self.assertTrue(all(a==8 for a in v.raw_listener_alignments),v.raw_listener_alignments)
       self.assertEqual(bytes(v.uc.mem_read(v.obj+0x22c,1)),b'\0')
       self.assertEqual(bytes(v.uc.mem_read(v.obj+0x22e,1)),b'\0')
 def test_focus_regain_auto_repeat_is_not_a_fresh_syskey_press(self):
  h,v=self.message_vm();v.byte(0x4a2f1d,1);events=self.attach_raw_listener(v)
  h.full_message(v,0x104,x=1,y=0,wparam=0x70)
  h.full_message(v,8);h.full_message(v,7)
  released=len(events)
  h.full_message(v,0x104,x=1,y=0x4000,wparam=0x70)
  self.assertEqual(len(events),released,'held-key OS auto-repeat after focus loss became a new SYSKEY press')
  self.assertEqual(v.byte(0xa30d20+0x70),0)
  h.full_message(v,0x104,x=1,y=0,wparam=0x70)
  self.assertEqual(len(events),released+1)
  self.assertEqual(v.byte(0xa30d20+0x70),1)
  h.full_message(v,0x105,x=1,y=0xc000,wparam=0x70)
  self.assertEqual(events[-1][1],0)
  self.assertEqual(v.byte(0xa30d20+0x70),0)
 def test_focus_gain_notification_keeps_genuinely_held_keys(self):
  h,v=self.message_vm();events=self.attach_raw_listener(v)
  h.full_message(v,0x100,wparam=0x45)
  self.assertEqual(len(events),1)
  h.full_message(v,0x1c,wparam=1)
  self.assertEqual(len(events),1,'WM_ACTIVATEAPP(true) synthesized a release for a focused key')
  self.assertEqual(v.byte(0xa30d20+0x45),1)
 def test_focus_release_hook_abi_survives_native_raw_listener_volatile_clobbers(self):
  h,v=self.message_vm();events=self.attach_raw_listener(v,clobber=True)
  v.uc.mem_write(v.obj+0x458,b'\1');v.uc.mem_write(v.window+0x79,b'\0')
  for key in [0x45,0x28,0x70]:v.byte(0xa30d20+key,1)
  saved=0x2001f800;v.uc.mem_write(saved+0x1e0,struct.pack('<Q',0x12345678))
  expected=dict(rax=0x1234,rcx=0x2345,rdx=0x3456,r8=0x4567,r9=0x5678,r10=0x6789,r11=0x789a,
                rbx=v.window,rbp=saved,rsi=1,r12=0x9abc,r13=8,r14=0,r15=0xabcd)
  xmm={k:int.from_bytes(bytes([0x40+k])*16,'little') for k in range(16)}
  for k,val in xmm.items():v.uc.reg_write(globals()['UC_X86_REG_XMM'+str(k)],val)
  v.run(0x2f3a3e,stop=0x2f3a45,eflags=0x246,**expected)
  self.assertEqual(len(events),3)
  self.assertTrue(all(a==8 for a in v.raw_listener_alignments),v.raw_listener_alignments)
  for k,val in expected.items():self.assertEqual(v.uc.reg_read(globals()['UC_X86_REG_'+k.upper()]),val,k)
  for k,val in xmm.items():self.assertEqual(v.uc.reg_read(globals()['UC_X86_REG_XMM'+str(k)]),val,'xmm'+str(k))
  self.assertEqual(v.uc.reg_read(UC_X86_REG_RDI),0x12345678)
  self.assertEqual(v.uc.reg_read(UC_X86_REG_RSP),v.stack)
  self.assertEqual(v.uc.reg_read(UC_X86_REG_EFLAGS)&0x8d5,0x246&0x8d5)
 def test_f1_refocus_new_press_before_any_intermediate_frame_still_toggles(self):
  import capstone
  h=self.helper();v=h.setup();v.byte(0x4a2f1d,0)
  md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
  ins=next(md.disasm(v.pe.get_data(0x4fa2e,7),v.base+0x4fa2e))
  operand=next(o for o in ins.operands if o.type==capstone.x86.X86_OP_MEM)
  previous_rva=ins.address+ins.size+operand.mem.disp-v.base
  h.full_message(v,0x100,wparam=0x70)
  v.run(0x4fa2e,stop=0x4fa6e,rcx=1,rsi=0)
  self.assertEqual(v.byte(0x4a2f1d),1);self.assertEqual(v.byte(previous_rva),1)
  h.full_message(v,8);h.full_message(v,7)
  h.full_message(v,0x100,wparam=0x70)
  v.run(0x4fa2e,stop=0x4fa6e,rcx=1,rsi=0)
  self.assertEqual(v.byte(0x4a2f1d),0,'focus key-up reset left F1 consumer debounce armed without an intermediate draw frame')
 def test_all_256_native_virtual_keys_complete_down_up_without_stale_latch(self):
  h=self.helper();v=h.setup();v.byte(0x4a2f1d,1)
  for key in range(256):
   h.full_message(v,0x100,wparam=key);h.full_message(v,0x101,wparam=key)
  self.assertEqual(v.read(0xa30d20,256),b'\0'*256)
  self.assertEqual(bytes(v.uc.mem_read(v.obj+0x22c,1)),b'\0')
 def test_focus_loss_releases_native_vk_latches_before_next_press(self):
  h=self.helper();v=h.setup();v.byte(0x4a2f1d,1)
  v.run(0x4fa66,stop=0x4fa6e,rcx=1)
  keys=[0x45,0x57,0x10,0x28,0x70]
  for key in keys:h.full_message(v,0x100,wparam=key)
  h.full_message(v,8) # Actual WM_KILLFOCUS; physical release occurs elsewhere.
  v.run(0x4fa66,stop=0x4fa6e,rcx=1)
  remaining=[hex(key) for key in keys if v.byte(0xa30d20+key)]
  self.assertEqual(remaining,[],f'Win32 repeat-suppression keys survive focus loss: {remaining}')
 def test_refocus_first_new_down_is_not_suppressed_after_lost_keyup(self):
  h=self.helper();v=h.setup();v.byte(0x4a2f1d,1)
  v.run(0x4fa66,stop=0x4fa6e,rcx=1)
  h.full_message(v,0x100,wparam=0x28)
  self.assertEqual(bytes(v.uc.mem_read(v.obj+0x22e,1)),b'\1')
  h.full_message(v,8);v.run(0x4fa66,stop=0x4fa6e,rcx=1)
  self.assertEqual(bytes(v.uc.mem_read(v.obj+0x22e,1)),b'\0')
  h.full_message(v,7);v.run(0x4fa66,stop=0x4fa6e,rcx=1)
  h.full_message(v,0x100,wparam=0x28)
  self.assertEqual(bytes(v.uc.mem_read(v.obj+0x22e,1)),b'\1','new Down after release outside game was suppressed as repeat')
 def test_focus_hook_preserves_saved_values_with_real_abi_volatile_clobbers(self):
  v=AuditedReplay(SOURCE);v.byte(0x4a2f1d,1)
  expected=dict(rax=1,rcx=0x12345,rdx=0x23456,r8=0x34567,r9=0x45678,r10=0x56789,r11=0x67890)
  xmm={k:int.from_bytes(bytes([0x30+k])*16,'little') for k in range(1,6)}
  for k,val in xmm.items():v.uc.reg_write(globals()['UC_X86_REG_XMM'+str(k)],val)
  v.run(0x4fa66,stop=0x4fa6e,eflags=0x246,**expected)
  for k,val in expected.items():self.assertEqual(v.uc.reg_read(globals()['UC_X86_REG_'+k.upper()]),val)
  for k,val in xmm.items():self.assertEqual(v.uc.reg_read(globals()['UC_X86_REG_XMM'+str(k)]),val)
  self.assertEqual(v.uc.reg_read(UC_X86_REG_RSP),v.stack)
  self.assertEqual(v.uc.reg_read(UC_X86_REG_EFLAGS)&0x8d5,0x246&0x8d5)
  self.assertTrue(v.boundaries)
  self.assertTrue(all(alignment==8 for name,alignment in v.boundaries),v.boundaries)
 def test_focus_close_and_lose_paths_keep_api_call_stack_aligned(self):
  for loss in [False,True]:
   with self.subTest(loss=loss):
    v=AuditedReplay(SOURCE);v.byte(0x4a2f1d,1)
    v.run(0x4fa66,stop=0x4fa6e,rcx=1)
    if loss:v.uc.mem_write(v.window+0x79,b'\0')
    else:v.byte(0x4a2f1d,0)
    v.run(0x4fa66,stop=0x4fa6e,rcx=1)
    self.assertTrue(all(alignment==8 for name,alignment in v.boundaries),v.boundaries)
 def test_shared_state_stays_in_separate_zero_fill_and_not_executable(self):
  v=Replay(SOURCE);p=v.pe
  dat=next(s for s in p.sections if s.Name.rstrip(b'\0')==b'.data')
  code=next(s for s in p.sections if s.Name.rstrip(b'\0')==b'.locui')
  self.assertLessEqual(dat.VirtualAddress+dat.SizeOfRawData,0xa68980)
  self.assertLessEqual(0xa68980+0x440,0xa68e80)
  self.assertLess(0xa68e80+3,dat.VirtualAddress+dat.Misc_VirtualSize)
  self.assertEqual(dat.Characteristics&0x20000000,0)
  self.assertEqual(code.Characteristics&0xa0000000,0x20000000)
  self.assertEqual(v.read(0xa68980,0x440),b'\0'*0x440)
 def test_focus_lifecycle_keeps_reader_buffer_and_inter_state_canary(self):
  v=Replay(SOURCE);reader=bytes([0x5a])*0x440;gap=bytes([0x96])*0xc0
  v.write(0xa68980,reader);v.write(0xa68dc0,gap)
  v.byte(0x4a2f1d,1);v.run(0x4fa66,stop=0x4fa6e,rcx=1)
  v.uc.mem_write(v.window+0x79,b'\0');v.run(0x4fa66,stop=0x4fa6e,rcx=1)
  v.uc.mem_write(v.window+0x79,b'\1');v.run(0x4fa66,stop=0x4fa6e,rcx=1)
  v.byte(0x4a2f1d,0);v.run(0x4fa66,stop=0x4fa6e,rcx=1)
  self.assertEqual(v.read(0xa68980,0x440),reader)
  self.assertEqual(v.read(0xa68dc0,0xc0),gap)

if __name__=='__main__':unittest.main()
