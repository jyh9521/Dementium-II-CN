"""Real letter resources through native measure, draw and input consumers."""
import os,sys,unittest,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from replay_document_draw import replay
from native_replay import Replay
EXE=Path(os.environ.get('DEMENTIUM_UI_TEST_EXE',ROOT/'build/full-zh-CN/Dementium II.exe'))
ROM=Path(os.environ.get('DEMENTIUM_PREVIEW_ROM',ROOT/'build/full-zh-CN/rom.zar'))

class ShortLetterScrollTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from native_replay import require_native_fixture
        require_native_fixture(EXE)
    def test_four_and_two_visible_lines_do_not_scroll_over_trailing_padding(self):
        for resource,visible in [('EN/EXAMINE.092',4),('EN/EXAMINE.093',2)]:
            with self.subTest(resource=resource):
                first=replay(EXE,ROM,resource,collection=True)
                self.assertEqual(len(first['text'].rstrip('\n').split('\n')),visible)
                self.assertEqual(first['reader_active'],0,'Trailing blank padding must not enable scrolling')
                self.assertEqual(min(g['y'] for g in first['drawn']),88,'Do not move fitting letters into the picture')
                for events in [(('wheel',-1),),(('key',0x11,1),)]:
                    after=replay(EXE,ROM,resource,collection=True,events=events)
                    self.assertEqual(after['reader_active'],0)
                    self.assertEqual(after['scroll_line'],0)
                    self.assertEqual(after['drawn'],first['drawn'])
                self.assertEqual(first['sentinel_before'],first['sentinel_after'])
    def test_actual_long_letters_still_scroll_and_keep_every_visible_character(self):
        for resource in ['EN/EXAMINE.078','EN/EXAMINE.090','EN/EXAMINE.091']:
            with self.subTest(resource=resource):
                first=replay(EXE,ROM,resource,collection=True)
                after=replay(EXE,ROM,resource,collection=True,events=(('wheel',-1),))
                self.assertEqual(first['reader_active'],1)
                self.assertGreater(after['scroll_line'],0)
                self.assertNotEqual(after['drawn'],first['drawn'])
    def test_field_letters_remain_on_their_existing_path(self):
        for resource in ['EN/EXAMINE.092','EN/EXAMINE.093']:
            r=replay(EXE,ROM,resource,collection=False)
            self.assertEqual(r['reader_active'],1,'This correction is collection-only')
    def test_padding_does_not_collapse_internal_blank_lines_or_add_blank_tail_scroll(self):
        for text,active,last in [('甲\n\n乙\n\n',0,0),('甲\n\n\n\n乙\n\n',1,1)]:
            with self.subTest(text=text):
                v=Replay(EXE);owner=0x30005000;node=0x30007000;font=0x30008000
                source=text.encode()+b'\0'
                v.uc.mem_write(owner+0x1d0,struct.pack('<I',93));v.uc.mem_write(owner+0x1e0,source)
                v.uc.mem_write(node+0x40,struct.pack('<Q',font));v.uc.mem_write(font+0x18,b'\x10')
                def frame():
                    v.run(0x123379,stop=0x123383,r14=owner+0x1e0,rsi=node,rdi=len(text.split('\n')),ecx=len(text.split('\n'))*16,r8=0)
                frame();self.assertEqual(v.dword(0xa68980),active)
                v.run(0x2ee30,rcx=v.obj,edx=(-100)&0xffffffff);frame()
                self.assertEqual(v.dword(0xa68990),last)
                self.assertEqual(bytes(v.uc.mem_read(owner+0x1e0,len(source))),source)

if __name__=='__main__':unittest.main(verbosity=2)
