"""Game 1.0.4 native measurement, document drawing, and scroll consumption."""
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from replay_document_draw import replay

EXE = Path(os.environ.get('DEMENTIUM_26286386_TEST_EXE', ROOT/'build/full-zh-CN/Dementium II.exe'))
ROM = Path(os.environ.get('DEMENTIUM_PREVIEW_ROM', ROOT/'build/full-zh-CN/rom.zar'))


class DocumentDraw26286386Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from native_replay import require_native_fixture
        require_native_fixture(EXE, '26286386')
        if not ROM.is_file():
            raise unittest.SkipTest('requires current localized ROM')

    def draw(self, number, collection=False, events=()):
        result = replay(EXE, ROM, 'EN/EXAMINE.%03d' % number, collection,
                        events, native_profile='26286386')
        self.assertGreater(result['native_measure_calls'], 0)
        self.assertGreater(result['glyph_count'], 0)
        self.assertEqual(result['sentinel_before'], result['sentinel_after'])
        self.assertEqual(result['draw_flag_after'], 0)
        self.assertTrue(all(g['draw_flag'] == 1 for g in result['drawn']))
        return result

    def test_all_postcards_use_real_measurement_and_draw_in_both_views(self):
        for number in [41, 42, 43, 45, 46, 47, 48, 49, 50, 51, 52, 53]:
            for collection in (False, True):
                with self.subTest(number=number, collection=collection):
                    result = self.draw(number, collection)
                    self.assertEqual(result['reader_active'], 0)
                    if not collection:
                        self.assertTrue(all(104 <= g['y'] < 176 for g in result['drawn']))

    def test_short_letters_ignore_scroll_and_preserve_collection_position(self):
        for number, lines in [(92, 4), (93, 2)]:
            with self.subTest(number=number):
                first = self.draw(number, True)
                self.assertEqual(len(first['text'].rstrip('\n').split('\n')), lines)
                self.assertEqual(first['reader_active'], 0)
                self.assertEqual(min(g['y'] for g in first['drawn']), 88)
                for events in [(('wheel', -1),), (('key', 0x11, 1),)]:
                    after = self.draw(number, True, events)
                    self.assertEqual(after['reader_active'], 0)
                    self.assertEqual(after['scroll_line'], 0)
                    self.assertEqual(after['drawn'], first['drawn'])

    def test_long_letters_scroll_through_actual_input_consumers(self):
        for number in [78, 90, 91]:
            with self.subTest(number=number):
                first = self.draw(number, True)
                self.assertEqual(first['reader_active'], 1)
                for events in [(('wheel', -1),), (('key', 0x11, 1),)]:
                    after = self.draw(number, True, events)
                    self.assertGreater(after['scroll_line'], 0)
                    self.assertNotEqual(after['drawn'], first['drawn'])

    def test_field_documents_keep_their_native_reader_path(self):
        for number in [78, 90, 92, 93, 501, 504]:
            with self.subTest(number=number):
                self.assertEqual(self.draw(number)['reader_active'], 1)


if __name__ == '__main__':
    unittest.main()
