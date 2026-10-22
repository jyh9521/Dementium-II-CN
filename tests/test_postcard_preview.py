"""Regression for field acquisition postcards losing all text while collection works."""
import os
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from replay_document_draw import replay
ROOT=Path(__file__).resolve().parents[1]
EXE=Path(os.environ.get('DEMENTIUM_UI_TEST_EXE') or os.environ.get('DEMENTIUM_PREVIEW_EXE') or os.environ.get('DEMENTIUM_MODIFIED_EXE') or ROOT/'build/full-zh-CN/Dementium II.exe')
ROM=Path(os.environ.get('DEMENTIUM_PREVIEW_ROM',ROOT/'build/full-zh-CN/rom.zar'))

@unittest.skipUnless(EXE.is_file() and ROM.is_file(),'locally supplied built assets required')
class PostcardPreviewDrawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from native_replay import require_native_fixture
        require_native_fixture(EXE)
    def test_field_card_native_setup_reaches_visible_glyph_submissions(self):
        r=replay(EXE,ROM)
        print('FIELD_CARD glyphs=%d flag_at_renderer=%s sentinel_preserved=%s' %
              (r['glyph_count'],[c['flag'] for c in r['renderer_calls']],r['sentinel_before']==r['sentinel_after']))
        self.assertGreater(r['glyph_count'],0,'Field acquisition view must submit postcard text glyphs')
        self.assertTrue(all(c['flag']==1 for c in r['renderer_calls']))
        self.assertEqual(r['sentinel_before'],r['sentinel_after'],'Adjacent source-level name must survive drawing')
        self.assertEqual(r['draw_flag_after'],0)
        self.assertTrue(all(104<=g['y']<176 for g in r['drawn']))

    def test_all_twelve_cards_submit_text_in_both_native_reader_paths(self):
        for resource in [41,42,43,45,46,47,48,49,50,51,52,53]:
            for collection in [False,True]:
                with self.subTest(resource=resource,collection=collection):
                    r=replay(EXE,ROM,'EN/EXAMINE.%03d'%resource,collection)
                    self.assertGreater(r['glyph_count'],0)
                    self.assertEqual(r['sentinel_before'],r['sentinel_after'])
                    self.assertEqual(r['draw_flag_after'],0)
                    self.assertTrue(all(g['draw_flag']==1 for g in r['drawn']))

    def test_native_long_reader_and_illustrated_letter_still_draw(self):
        # This reaches native source width/height calculations and the built
        # reader hook rather than supplying its argument registers directly.
        for resource,collection in [(501,False),(504,False),(78,False),(90,False),(78,True),(90,True)]:
            with self.subTest(resource=resource,collection=collection):
                r=replay(EXE,ROM,'EN/EXAMINE.%03d'%resource,collection)
                self.assertGreater(r['glyph_count'],0)
                self.assertEqual(r['sentinel_before'],r['sentinel_after'])
                self.assertEqual(r['draw_flag_after'],0)

    def test_collection_card_original_draw_path_stays_visible(self):
        r=replay(EXE,ROM,collection=True)
        self.assertGreater(r['glyph_count'],0)
        self.assertEqual(r['sentinel_before'],r['sentinel_after'])
        self.assertEqual(r['draw_flag_after'],0)

if __name__=='__main__':unittest.main(verbosity=2)
