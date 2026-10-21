"""Synthetic regression for a bounded document pane below an item picture."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from font_pipeline import build_mixed, glyph_width
from localize import TOKEN
from test_font_pipeline import tiny_font


def native_first_visible_y(text, linefeed=16, pane_height=72, line_spacing=0):
    """Replay FUN_14011a6f0 bottom alignment, relative to pane origin y104."""
    lines = text.split('\n')
    origin = pane_height + line_spacing - (linefeed + line_spacing) * len(lines)
    first_ink = next((i for i, line in enumerate(lines) if TOKEN.sub('', line).strip()), len(lines))
    return origin + first_ink * (linefeed + line_spacing)


class PostcardLayoutTests(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        font = Path(self.temp.name) / 'fixture.ttf'
        tiny_font(font, ''.join(chr(c) for c in range(32, 127)) + '甲乙丙丁——，。')
        meta = dict(format='d1-rgba', version=1, cell_width=12, cell_height=15,
                    layout_height=8, layout_top=5, linefeed=13,
                    glyphs={'0': dict(w=1, h=1, logw=1, xo=0, yo=0, tx=0, ty=0)})
        buffer = io.BytesIO()
        Image.new('RGBA', (4, 4), (11, 17, 23, 255)).save(buffer, format='PNG')
        members = {'FONTS/D2FONT_12X15.JSON': json.dumps(meta).encode(),
                   'FONTS/D2FONT_12X15.PNG': buffer.getvalue()}
        self.archive = type('MemoryArchive', (), {'read': lambda _, name: members[name]})()
        self.profile = dict(fonts={'body': {'pixel_size': 12}, 'title': {'pixel_size': 16}},
                            previews={'body': ['甲乙'], 'title': [], 'mixed': [], 'interaction': []},
                            title_resources=[], atlas_width=128, max_atlas_height=512,
                            linefeed=16, document_width=72, review_width=96,
                            forbidden_start='，。', forbidden_end='（',
                            document_layouts={'EN/EXAMINE.041': dict(
                                leading_lines=0, max_visible_lines=4, reflow=True,
                                pane_height=72, line_spacing=0,
                                soft_joiner='', preserve_line_prefixes=['——'], width=228)})
        patcher = patch('font_pipeline.resolve_fonts', return_value={'body': font, 'title': font})
        patcher.start()
        self.addCleanup(patcher.stop)

    def build(self, text, resource='EN/EXAMINE.041'):
        records = [dict(id=resource + ':0000', resource=resource, source=text, target=text)]
        before = copy.deepcopy(records)
        changes, runtime, report = build_mixed(self.archive, records, self.profile)
        self.assertEqual(records, before, 'Compilation must not mutate editable translation data')
        return runtime[0]['target'], json.loads(changes['FONTS/D2FONT_12X15.JSON'])

    def test_reflow_fits_bottom_anchored_pane_without_blank_padding(self):
        logical = '甲乙丙丁' * 4 + '\n\n' + '甲乙丙丁' * 3 + '\n——甲乙'
        compiled, meta = self.build(logical)
        self.assertFalse(compiled.startswith('\n'), repr(compiled))
        lines = compiled.split('\n')
        self.assertTrue(all(lines), repr(compiled))
        self.assertLessEqual(len(lines), 4)
        self.assertTrue(all(glyph_width(line, meta) <= 228 for line in lines))
        self.assertEqual(compiled.replace('\n', ''), logical.replace('\n', ''))

    def test_signature_stays_on_separate_line_after_soft_reflow(self):
        compiled, _ = self.build('甲乙\n丙丁\n\n——甲乙')
        self.assertEqual(compiled, '甲乙丙丁\n——甲乙')

    def test_protected_control_and_variable_sequence_remains_exact(self):
        logical = '\x02甲乙\n\n丙$K丁\x01\n——甲乙'
        compiled, _ = self.build(logical)
        self.assertFalse(compiled.startswith('\n'), repr(compiled))
        self.assertEqual(TOKEN.findall(compiled), TOKEN.findall(logical))
        self.assertEqual(compiled.replace('\n', ''), logical.replace('\n', ''))

    def test_overflow_is_rejected_instead_of_truncating_document(self):
        with self.assertRaisesRegex(ValueError, r'(?i)(line|overflow|budget|layout)'):
            self.build('甲乙丙丁' * 30)

    def test_native_bottom_anchor_seven_lines_overlap_but_four_lines_fit(self):
        old = '\n'.join(['甲乙'] * 7)
        fixed = '\n'.join(['甲乙'] * 4)
        self.assertEqual(native_first_visible_y(old), -40)
        self.assertEqual(native_first_visible_y(fixed), 8)
        self.assertLess(native_first_visible_y(old), 0)
        self.assertGreaterEqual(native_first_visible_y(fixed), 0)
        # Leading blanks increase both measured height and first-ink offset equally.
        self.assertEqual(native_first_visible_y('\n\n' + fixed), 8)

    def test_native_height_budget_rejects_trailing_blank_measured_line(self):
        rule = self.profile['document_layouts']['EN/EXAMINE.041']
        rule.update(reflow=False, max_visible_lines=8)
        logical = '\n'.join(['甲乙'] * 4) + '\n'
        self.assertEqual(native_first_visible_y(logical), -8)
        with self.assertRaisesRegex(ValueError, r'(?i)(height|pane|budget|layout)'):
            self.build(logical)

    def test_height_budget_uses_configured_linefeed_not_visible_line_limit(self):
        rule = self.profile['document_layouts']['EN/EXAMINE.041']
        rule.update(reflow=False, pane_height=47)
        with self.assertRaisesRegex(ValueError, r'(?i)(height|pane|budget|layout)'):
            self.build('甲乙\n丙丁\n甲乙')

    def test_unconfigured_documents_keep_existing_paragraph_behavior(self):
        compiled, _ = self.build('甲乙\n\n丙丁', resource='EN/EXAMINE.042')
        self.assertEqual(compiled, '甲乙\n\n丙丁')


if __name__ == '__main__':
    unittest.main()
