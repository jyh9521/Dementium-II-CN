"""26123896 native machine-code replay; no game process, Win32 calls are doubles."""
import os,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import native_profile as profiles
from native_replay import Replay
SOURCE=Path(os.environ.get('DEMENTIUM_V11_TEST_EXE',ROOT/'build/previous-26123896/Dementium II.exe'))

def mapped(value):
    token=profiles._ACTIVE.set('26123896')
    try:
        if 0xa68980<=value<0xa68f00:return 0xa6a9c0+value-0xa68980
        if 0x1a7c50<=value<=0x1a87a0:return value+0x640
        if 0x31ad26<=value<=0x31ad9a:return value+0x14e0
        if value in (0x2f5350,):return value+0x14e0
        if value==0x2f3650:return value+0x1450
        if value==0x2deb90:return value+0x640
        if 0xa121a0<=value<=0xa345f0:return value+0x2040
        if 0x4a3450<=value<=0x4a3470:return value+0x2000
        if value==0x433850:return 0x435160
        if value in (0x439d98,0x3bb4d8):return value+0x1000
        if value==0x4c2148:return value+0x2040
        if 0x155400<=value<=0x1558f4:return value+0x640
        if 0x11af80<=value<=0x11af86:return value+0x2f0
        if 0x122a10<=value<=0x122a1b:return value+0x590
        if value in (0x2f010,0x2f020,0x62b75,0x62b8a,0x2f49e,0x63f20,0x68640,0x6cbf0,0x86f60,0x6ef30,0x696c0,0x2f171,0x2f199,0x2eb90,0x2ed10,0x2ed60,0x4fb44,0x4fb52,0x4fc4e,0x4fc7e,0x678e0,0x69d40,0x67c70):return value
        if 0x11b4f7<=value<=0x11b501 or 0x11a7b0<=value<=0x11a7b5:return value+0x2f0
        if 0x121e50<=value<=0x121e55:return value+0x590
        if 0x123379<=value<=0x123383:return value+0x590
        if 0x126da7<=value<=0x126db0:return value+0x630
        if value==0xa136b4:return value+0x2040
        return profiles.rva(value)
    finally:profiles.restore(token)

class BuildReplay(Replay):
    def rva(self,value):return mapped(value)
    def __init__(self,path,image_base=None):super().__init__(path,image_base=image_base,native_profile='26123896')
    def write(self,rva,data):
        if len(data)==8:
            pointer=struct.unpack('<Q',data)[0]
            if self.base<=pointer<self.base+0xb00000:data=struct.pack('<Q',self.base+mapped(pointer-self.base))
        super().write(mapped(rva),data)
    def read(self,rva,size):return super().read(mapped(rva),size)
    def run(self,rva,stop=None,**registers):return super().run(mapped(rva),stop=mapped(stop) if stop is not None else None,**registers)

@unittest.skipUnless(SOURCE.is_file(),'requires built v1.1 native PE')
class NativeProfileV11Tests(unittest.TestCase):
    def setUp(self):self.v=BuildReplay(SOURCE)
    def press(self,key,value=1):self.v.run(0x1a7c50,rcx=self.v.obj,edx=key,r8=value)
    def field(self,offset):return bytes(self.v.uc.mem_read(self.v.obj+offset,1))[0]
    def frame(self):self.v.run(0x4fa66,stop=0x4fa6e,rax=self.v.byte(0x4a2f1d),rcx=1)
    def test_keyboard_menu_reader_and_native_modes(self):
        v=self.v
        for mode in (0,1):
            v.uc.mem_write(v.obj+0x458,bytes([mode]));v.byte(0x4a2f1d,1)
            for key,offset in [(0xf,0x22d),(0x11,0x22e),(5,0x221),(1,0x222)]:
                self.press(key);self.assertEqual(self.field(offset),1)
                self.press(key,0);self.assertEqual(self.field(offset),0)
        v.byte(0x4a2f1d,0);v.uc.mem_write(v.obj+0x458,b'\0')
        self.press(0xf);self.assertEqual(self.field(0x22d),0)
        v.write(0xa68980,struct.pack('<I',1));self.press(0xf);self.assertEqual(self.field(0x22d),1)
        self.press(0x6d);self.assertEqual(self.field(0x227),0)
    def test_f1_edge_debounce_and_cursor_transition(self):
        states=[]
        for held in (0,1,1,0,1):
            self.press(0x1c,held);self.v.run(0x4fa2e,stop=0x4fa6e,rcx=self.field(0x22c),rsi=0)
            states.append(self.v.byte(0x4a2f1d))
        self.assertEqual(states,[0,1,1,1,0])
        self.assertEqual(sum(c[0]=='SetCursorPos' for c in self.v.calls),1)
    def test_cursor_open_focus_close_and_relocated_image(self):
        for base in (None,0x180000000):
            self.v=BuildReplay(SOURCE,image_base=base);v=self.v
            v.byte(0x4a2f1d,1);self.frame()
            self.assertIn(('SetCursorPos',1060,590,None),v.calls)
            self.assertEqual(bytes(v.uc.mem_read(v.window+0x19,1)),b'\0')
            v.uc.mem_write(v.window+0x79,b'\0');self.frame();self.assertEqual(v.calls[-1][0:2],('ClipCursor',0))
            v.uc.mem_write(v.window+0x79,b'\1');self.frame()
            v.byte(0x4a2f1d,0);self.frame();self.assertEqual(bytes(v.uc.mem_read(v.window+0x19,1)),b'\1')
    def test_wheel_menu_reader_then_original_callback(self):
        v=self.v;v.byte(0x4a2f1d,1);v.run(0x2ee30,rcx=v.obj,edx=1)
        self.assertEqual(struct.unpack('<f',v.uc.mem_read(v.io+0x140,4))[0],1.)
        v.write(0xa68980,struct.pack('<I',1));v.byte(0x4a2f1d,0);v.run(0x2ee30,rcx=v.obj,edx=1)
        self.assertEqual(v.dword(0xa68984),1)
        v.write(0xa68980,b'\0'*4);v.run(0x2ee30,rcx=v.obj,edx=1);self.assertEqual(v.dword(0xa136b4),1)
    def test_field_and_collection_reader_scroll_and_reset(self):
        for collection in (False,True):
            self.v=BuildReplay(SOURCE);v=self.v
            owner=0x30005000;font=0x30007000;node=0x30008000
            v.uc.mem_write(font+0x18,b'\x10');v.uc.mem_write(node+0x68,struct.pack('<Q',font));v.uc.mem_write(node+0x40,struct.pack('<Q',font))
            v.uc.mem_write(owner+0x128,struct.pack('<hh',504,-1));v.uc.mem_write(owner+0x1d0,struct.pack('<I',504))
            text=('Line\n'*19+'Last').encode()+b'\0'
            def render():
                v.uc.mem_write(owner+(0x1e0 if collection else 0x12c),text)
                if collection:v.run(0x123379,stop=0x123383,r14=owner+0x1e0,rsi=node,rdi=20,ecx=160,r8=0)
                else:v.run(0x11b4f7,stop=0x11b501,rdi=owner,r15=node,r12=owner+0x12c,rsi=20,edx=160,r8=86,rax=13)
            render();self.assertEqual(v.dword(0xa68980),1)
            v.write(0xa68984,struct.pack('<i',-1));render();self.assertEqual(v.dword(0xa68990),3)
            v.run(0x121e50 if collection else 0x11a7b0,stop=0x121e55 if collection else 0x11a7b5,rcx=owner)
            self.assertEqual(v.dword(0xa68980),0);self.assertEqual(v.dword(0xa68990),0)
    def test_lost_focus_releases_native_held_key_and_f1_debounce(self):
        from menu_input import native_f1_previous_rva
        v=self.v;stub=0x40000800
        v.stubs[stub]='KEY_UP';v.uc.mem_write(stub,b'\xc3')
        v.write(0xa2ca78,struct.pack('<Q',v.obj));v.write(0xa25e28,struct.pack('<Q',stub))
        held=mapped(0xa30d20)+0x70;v.uc.mem_write(v.base+held,b'\1')
        token=profiles._ACTIVE.set('26123896')
        try:previous=native_f1_previous_rva(SOURCE.read_bytes())
        finally:profiles.restore(token)
        v.uc.mem_write(v.base+previous,b'\1');v.uc.mem_write(v.window+0x79,b'\0')
        v.uc.mem_write(v.obj+0x1e0,struct.pack('<Q',0))
        v.run(0x2f3a3e,stop=0x2f3a45,rbx=v.window,rbp=v.obj,r13=8)
        self.assertEqual(bytes(v.uc.mem_read(v.base+held,1)),b'\0')
        self.assertEqual(bytes(v.uc.mem_read(v.base+previous,1)),b'\0')
        self.assertTrue(any(c[0]=='KEY_UP' and c[1]==0x1c for c in v.calls))
    def test_os_auto_repeat_does_not_create_new_native_press(self):
        v=self.v;held=mapped(0xa30d20)+0x70
        v.run(0x2de833,stop=0x2deb38,rsi=0x40000000,r9=0x70,rbx=0x70)
        self.assertEqual(bytes(v.uc.mem_read(v.base+held,1)),b'\0')
    def test_native_xinput_normalization_and_axis_setter(self):
        from unicorn.x86_const import UC_X86_REG_XMM3,UC_X86_REG_XMM9,UC_X86_REG_XMM12
        v=self.v
        for raw,sign in ((32767,1),(-32768,-1)):
            v.write(0xa314ee,struct.pack('<h',raw))
            v.uc.reg_write(UC_X86_REG_XMM12,struct.unpack('<I',v.read(0x439d98,4))[0])
            v.run(0x31ad35,stop=0x31ad9a,r12=v.base,rdi=0,r13=0)
            bits=v.uc.reg_read(UC_X86_REG_XMM9)&0xffffffff
            value=struct.unpack('<f',struct.pack('<I',bits))[0]
            self.assertEqual(1 if value>0 else -1,sign)
            v.write(0xa2ca78,struct.pack('<Q',v.obj));v.uc.reg_write(UC_X86_REG_XMM3,bits)
            v.run(0x2ed10,rcx=v.obj,edx=0,r8=3)
            self.assertEqual(bytes(v.uc.mem_read(v.obj+0x2cc,4)),struct.pack('<I',bits))
    def test_original_existing_import_slots_are_correct(self):
        actual={i.name:i.address-self.v.base for d in self.v.pe.DIRECTORY_ENTRY_IMPORT for i in d.imports}
        for name,old in [(b'LoadCursorA',0x37d818),(b'SetCursor',0x37d758),(b'ClipCursor',0x37d760),(b'GetClientRect',0x37d748),(b'ClientToScreen',0x37d7b0),(b'SetCursorPos',0x37d6f0)]:self.assertEqual(actual[name],mapped(old))


import test_menu_pointer_dispatch as pointer_tests
class NewPointerDispatchTests(pointer_tests.MenuPointerDispatchTests):
    def setUp(self):
        old_replay,old_source=pointer_tests.Replay,pointer_tests.SOURCE
        pointer_tests.Replay,pointer_tests.SOURCE=BuildReplay,SOURCE
        try:super().setUp()
        finally:pointer_tests.Replay,pointer_tests.SOURCE=old_replay,old_source
class NewRelocatedPointerDispatchTests(NewPointerDispatchTests):image_base=0x180000000

NewPointerDispatchTests.__unittest_skip__=not SOURCE.is_file()
NewRelocatedPointerDispatchTests.__unittest_skip__=not SOURCE.is_file()

import test_reader_gamepad as gamepad_tests
import test_reader_key_lifecycle as key_tests
class BuildKeyReplay(key_tests.KeyReplay,BuildReplay):pass
class NewReaderGamepadTests(gamepad_tests.ReaderGamepadTests):
    def setUp(self):
        import test_reader_transition_audit as transitions
        self.f=transitions.ReaderTransitionAuditTests()
        f=key_tests.ReaderKeyLifecycleTests();v=BuildKeyReplay(SOURCE);v.raw_events=[]
        self.f.f=f;self.f.v=v;self.v=v;f.v=v
        f.owner=0x30005000;f.node=0x30007000;f.font=0x30008000
        v.uc.mem_write(f.font+0x18,b'\x10');v.uc.mem_write(f.node+0x68,struct.pack('<Q',f.font))
        v.uc.mem_write(v.obj,struct.pack('<Q',v.base+mapped(0x3bb4d8)))
        v.write(0xa2ca78,struct.pack('<Q',v.obj));v.write(0x4c2148,struct.pack('<Q',0x30018000))
        listener=0x3000a000;table=0x3000b000;stub=0x40000800
        v.uc.mem_write(v.obj+0x390,struct.pack('<Q',listener));v.uc.mem_write(listener,struct.pack('<Q',table))
        v.uc.mem_write(table+0x10,struct.pack('<Q',stub));v.stubs[stub]='RAWKEY';v.uc.mem_write(stub,b'\xc3')
        v.byte(0xa314f0,1)
NewReaderGamepadTests.__unittest_skip__=not SOURCE.is_file()

import test_pause_layout as pause_tests
class NewPauseLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from native_replay import require_native_fixture
        require_native_fixture(SOURCE,'26123896')
    def test_native_immediates_match_real_label_and_status_glyph_ink(self):
        import pefile
        from localize import Zar
        archive=Path(os.environ.get('DEMENTIUM_PAUSE_TEST_ROM',ROOT/'build/full-zh-CN/rom.zar'))
        if not archive.is_file():self.skipTest('requires built v1.1 archive')
        raw=pefile.PE(str(SOURCE))
        class ProfilePE:
            __data__=raw.__data__
            def get_data(self,rva,size):return raw.get_data(mapped(rva),size)
        self.pe=ProfilePE();self.z=Zar(archive.read_bytes())
        pause_tests.PauseLayoutTests.test_native_value_immediately_follows_colon_and_shares_ink_top(self)

from functools import partial
from replay_document_draw import replay as native_document_replay
import test_short_letter_scroll as short_tests
import test_postcard_preview as postcard_tests
class NewShortLetterRenderTests(short_tests.ShortLetterScrollTests):
    @classmethod
    def setUpClass(cls):
        from native_replay import require_native_fixture
        require_native_fixture(SOURCE,'26123896')
    def setUp(self):
        self.previous=(short_tests.replay,short_tests.Replay,short_tests.EXE)
        short_tests.replay=partial(native_document_replay,native_profile='26123896')
        short_tests.Replay=BuildReplay;short_tests.EXE=SOURCE
    def tearDown(self):short_tests.replay,short_tests.Replay,short_tests.EXE=self.previous
class NewPostcardRenderTests(postcard_tests.PostcardPreviewDrawTests):
    def test_new_renderer_boundary_is_nonempty_and_draw_enabled(self):
        result=native_document_replay(SOURCE,postcard_tests.ROM,native_profile='26123896')
        self.assertTrue(result['renderer_calls'],'do not accept vacuous draw-flag checks')
        self.assertTrue(all(call['flag']==1 for call in result['renderer_calls']))
    @classmethod
    def setUpClass(cls):
        from native_replay import require_native_fixture
        require_native_fixture(SOURCE,'26123896')
    def setUp(self):
        self.previous=(postcard_tests.replay,postcard_tests.EXE)
        postcard_tests.replay=partial(native_document_replay,native_profile='26123896');postcard_tests.EXE=SOURCE
    def tearDown(self):postcard_tests.replay,postcard_tests.EXE=self.previous
NewPostcardRenderTests.__unittest_skip__=not SOURCE.is_file()

import native_imgui_replay as imgui_replay
import test_menu_full_frame as frame_tests
class BuildImGuiReplay(imgui_replay.ImGuiReplay,BuildReplay):pass
class NewCompleteNativeMenuFrameTests(frame_tests.CompleteNativeMenuFrameTests):
    def setUp(self):
        old_replay,old_source=frame_tests.ImGuiReplay,frame_tests.SOURCE
        frame_tests.ImGuiReplay,frame_tests.SOURCE=BuildImGuiReplay,SOURCE
        try:super().setUp()
        finally:frame_tests.ImGuiReplay,frame_tests.SOURCE=old_replay,old_source
NewCompleteNativeMenuFrameTests.__unittest_skip__=not SOURCE.is_file()
class NewRelocatedCompleteNativeMenuFrameTests(NewCompleteNativeMenuFrameTests):image_base=0x180000000

if __name__=='__main__':unittest.main(verbosity=2)
