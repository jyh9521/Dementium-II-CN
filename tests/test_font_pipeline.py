"""Synthetic layout and font fixtures: no game files or installed fonts required."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from font_pipeline import build_mixed, glyph_width, route_titles, wrap_text
from localize import TOKEN


def metrics():
    result = {'glyphs': {'0': {'logw': 12}}}
    for char in '甲乙丙丁中标题章节第一开始，。！？、（）「」：； ':
        result['glyphs'][str(ord(char))] = {'logw': 2 if char == ' ' else 12}
    for char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.-':
        result['glyphs'][str(ord(char))] = {'logw': 5}
    return result


def visible(text):
    return TOKEN.sub('', text).strip()


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.meta = metrics()
        self.start = '，。！？、）」：；'
        self.end = '（「'

    def wrap(self, text, width=25):
        return wrap_text(text, self.meta, width, self.start, self.end)

    def assert_kinsoku(self, text):
        for line in text.split('\n'):
            ink = visible(line)
            if ink:
                self.assertNotIn(ink[0], self.start, repr(text))
                self.assertNotIn(ink[-1], self.end, repr(text))

    def test_width_counts_glyph_advances_and_interglyph_spacing(self):
        self.assertEqual(glyph_width('', self.meta), 0)
        self.assertEqual(glyph_width('甲', self.meta), 12)
        self.assertEqual(glyph_width('甲乙', self.meta), 25)
        self.assertEqual(glyph_width('ABC', self.meta), 17)
        self.assertEqual(glyph_width('甲A', self.meta), 18)
        self.assertEqual(glyph_width('甲乙', self.meta, spacing=0), 24)

    def test_width_zero_width_protected_controls(self):
        self.assertEqual(glyph_width('\x02甲\x01乙', self.meta), 25)
        self.assertEqual(glyph_width('\x02\x01', self.meta), 0)
        self.assertEqual(glyph_width('甲{0}<tag>%s乙', self.meta), 25)

    def test_variable_width_budget_is_not_reduced_by_trailing_spacing(self):
        self.assertGreaterEqual(glyph_width('$K', self.meta), 24)
        self.assertGreaterEqual(glyph_width('$Keypad,520$', self.meta), 24)

    def test_simple_cjk_wrap_is_bounded_and_lossless(self):
        wrapped = self.wrap('甲乙丙丁')
        self.assertEqual(wrapped, '甲乙\n丙丁')
        self.assertEqual(wrapped.replace('\n', ''), '甲乙丙丁')
        self.assertTrue(all(glyph_width(line, self.meta) <= 25 for line in wrapped.split('\n')))

    def test_final_tail_is_balanced_without_losing_text_or_controls(self):
        source = '甲乙丙丁甲乙丙丁甲'
        result = wrap_text(source, self.meta, 103, self.start, self.end, min_tail_width=39)
        self.assertEqual(result.replace('\n', ''), source)
        self.assertTrue(all(glyph_width(line, self.meta) >= 39 for line in result.splitlines()))
        self.assertTrue(all(glyph_width(line, self.meta) <= 103 for line in result.splitlines()))

    def test_latin_word_is_not_split(self):
        self.assertEqual(self.wrap('甲William乙'), '甲\nWilliam\n乙')
        self.assertIn('9mm', self.wrap('甲9mm乙', 20))

    def test_paragraphs_and_line_endings(self):
        self.assertEqual(self.wrap('甲\r\n\r\n乙\r丙\n'), '甲\n\n乙\n丙\n')

    def test_closing_punctuation_does_not_start_line(self):
        wrapped = self.wrap('甲乙，丙')
        self.assert_kinsoku(wrapped)
        self.assertEqual(wrapped.replace('\n', ''), '甲乙，丙')

    def test_opening_punctuation_does_not_end_line(self):
        wrapped = self.wrap('甲（乙丙')
        self.assert_kinsoku(wrapped)
        self.assertEqual(wrapped.replace('\n', ''), '甲（乙丙')

    def test_consecutive_closing_marks_stay_with_preceding_character(self):
        wrapped = self.wrap('甲乙，，丙')
        self.assert_kinsoku(wrapped)
        self.assertEqual(wrapped.replace('\n', ''), '甲乙，，丙')

    def test_space_before_punctuation_does_not_create_punctuation_line(self):
        wrapped = self.wrap('甲乙 ，丙')
        self.assert_kinsoku(wrapped)
        self.assertFalse(any(not line for line in wrapped.split('\n')))

    def test_wrapped_spaces_do_not_create_new_empty_paragraphs(self):
        for source in ('甲乙     丙', '     甲乙', '甲乙             ', '甲乙\x02\x01     丙'):
            with self.subTest(source=source):
                wrapped = self.wrap(source)
                self.assertTrue(all(visible(line) for line in wrapped.split('\n')), repr(wrapped))
                self.assertEqual(TOKEN.findall(source), TOKEN.findall(wrapped))

    def test_color_controls_do_not_hide_forbidden_line_start(self):
        source = '甲乙\x02，\x01丙'
        wrapped = self.wrap(source)
        self.assert_kinsoku(wrapped)
        self.assertEqual(TOKEN.findall(source), TOKEN.findall(wrapped))

    def test_protected_atoms_and_order_survive_wrapping(self):
        source = '\x02甲$Keypad,520$乙\x01丙$K丁{0}%s<tag>'
        wrapped = self.wrap(source)
        self.assertEqual(TOKEN.findall(source), TOKEN.findall(wrapped))
        self.assertEqual(wrapped.replace('\n', ''), source)

    def test_title_route_only_first_segment_and_preserves_controls(self):
        aliases = {ord('第'): 0xE000, ord('章'): 0xE001}
        source = '\x03第一章|\x02第一章'
        result = route_titles(source, aliases, True)
        self.assertEqual(result, '\x03\ue000一\ue001|\x02第一章')
        self.assertEqual(TOKEN.findall(source), TOKEN.findall(result))
        self.assertEqual(route_titles(source, aliases, False), source)
        self.assertEqual(route_titles('第一章', aliases, True), '\ue000一\ue001')


def tiny_font(path, characters):
    """Generate original rectangle outlines, not a copy of any commercial font."""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    builder = FontBuilder(1000, isTTF=True)
    names = ['.notdef'] + ['u%04X' % code for code in sorted(set(map(ord, characters)))]
    builder.setupGlyphOrder(names)
    builder.setupCharacterMap({ord(c): 'u%04X' % ord(c) for c in characters})
    glyphs = {}
    for name in names:
        pen = TTGlyphPen(None)
        if name != 'u0020':
            pen.moveTo((100, 100))
            pen.lineTo((900, 100))
            pen.lineTo((900, 900))
            pen.lineTo((100, 900))
            pen.closePath()
        glyphs[name] = pen.glyph()
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics({name: (1000, 0) for name in names})
    builder.setupHorizontalHeader(ascent=1000, descent=0)
    builder.setupNameTable({'familyName': 'Synthetic Pipeline Fixture', 'styleName': 'Regular',
                            'uniqueFontIdentifier': 'SyntheticPipelineFixture', 'fullName': 'Synthetic Pipeline Fixture',
                            'psName': 'SyntheticPipelineFixture', 'version': 'Version 1.000'})
    builder.setupOS2(sTypoAscender=1000, sTypoDescender=0, usWinAscent=1000, usWinDescent=0)
    builder.setupPost()
    builder.setupMaxp()
    builder.save(path)


class SyntheticAtlasTests(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.font = Path(self.temp.name) / 'fixture.ttf'
        tiny_font(self.font, 'A一第章节开始甲乙， ')
        self.meta = dict(format='d1-rgba', version=1, cell_width=12, cell_height=15,
                         layout_height=8, layout_top=5, linefeed=13,
                         glyphs={'0': dict(w=1, h=1, logw=1, xo=0, yo=0, tx=0, ty=0),
                                 '65': dict(w=1, h=1, logw=5, xo=-1, yo=3, tx=1, ty=1),
                                 '124': dict(w=1, h=1, logw=1, xo=0, yo=0, tx=2, ty=2)})
        self.original = Image.new('RGBA', (4, 4), (7, 11, 19, 83))
        self.original.putpixel((1, 1), (201, 57, 38, 255))
        buffer = io.BytesIO()
        self.original.save(buffer, format='PNG')
        self.members = {'FONTS/D2FONT_12X15.JSON': json.dumps(self.meta).encode(),
                        'FONTS/D2FONT_12X15.PNG': buffer.getvalue()}
        self.zar = type('MemoryArchive', (), {'read': lambda _, name: self.members[name]})()
        self.profile = dict(fonts={'body': {'pixel_size': 12}, 'title': {'pixel_size': 16}},
                            previews={'body': ['甲乙，'], 'title': ['章节'], 'mixed': ['A甲'], 'interaction': ['开始']},
                            title_resources=['EN/CHAPTERS.TBL'], atlas_width=128, max_atlas_height=256,
                            linefeed=16, document_width=72, review_width=96,
                            forbidden_start='，', forbidden_end='（')
        self.records = [dict(id='EN/CHAPTERS.TBL:0000', resource='EN/CHAPTERS.TBL',
                             source='Chapter|Begin', target='\x03第一章|\x02开始'),
                        dict(id='EN/GUI.TBL:0000', resource='EN/GUI.TBL', source='Start', target='开始')]
        patcher = patch('font_pipeline.resolve_fonts', return_value={'body': self.font, 'title': self.font})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_atlas_preserves_original_glyphs_pixels_and_inputs(self):
        from PIL import Image
        records = copy.deepcopy(self.records)
        profile = copy.deepcopy(self.profile)
        changes, runtime, report = build_mixed(self.zar, self.records, self.profile)
        meta = json.loads(changes['FONTS/D2FONT_12X15.JSON'])
        atlas = Image.open(io.BytesIO(changes['FONTS/D2FONT_12X15.PNG'])).convert('RGBA')
        self.assertEqual(atlas.crop((0, 0, 4, 4)).tobytes(), self.original.tobytes())
        for code, glyph in self.meta['glyphs'].items():
            self.assertEqual(meta['glyphs'][code], glyph)
        self.assertEqual(self.records, records)
        self.assertEqual(self.profile, profile)
        self.assertFalse(report['runtime_verified'])
        self.assertEqual(meta['linefeed'], 16)
        self.assertEqual(runtime[1]['target'], '开始')
        self.assertEqual(TOKEN.findall(runtime[0]['target']), TOKEN.findall(records[0]['target']))

    def test_present_but_empty_existing_glyph_is_rebuilt(self):
        from PIL import Image
        meta = copy.deepcopy(self.meta)
        meta['glyphs'][str(ord('甲'))] = dict(w=1, h=1, logw=12, xo=0, yo=0, tx=3, ty=3)
        self.original.putpixel((3,3), (0,0,0,0))
        buffer = io.BytesIO(); self.original.save(buffer, format='PNG')
        self.members['FONTS/D2FONT_12X15.PNG'] = buffer.getvalue()
        self.members['FONTS/D2FONT_12X15.JSON'] = json.dumps(meta).encode()
        changes, _, report = build_mixed(self.zar, self.records, self.profile)
        self.assertEqual(report['repaired_blank_codes'], [ord('甲')])
        output = json.loads(changes['FONTS/D2FONT_12X15.JSON'])
        glyph = output['glyphs'][str(ord('甲'))]
        atlas = Image.open(io.BytesIO(changes['FONTS/D2FONT_12X15.PNG']))
        self.assertIsNotNone(atlas.crop((glyph['tx'],glyph['ty'],glyph['tx']+glyph['w'],glyph['ty']+glyph['h'])).getchannel('A').getbbox())

    def test_aliases_and_generated_members_are_deterministic(self):
        first, runtime, report = build_mixed(self.zar, self.records, self.profile)
        second, _, again = build_mixed(self.zar, list(reversed(self.records)), self.profile)
        self.assertEqual(first, second)
        self.assertEqual(report['title_aliases'], again['title_aliases'])
        codes = sorted(int(code) for code in report['title_aliases'])
        self.assertEqual([report['title_aliases'][str(c)] for c in codes], list(range(0xE000, 0xE000 + len(codes))))
        aliases = {int(code): mapped for code, mapped in report['title_aliases'].items()}
        self.assertEqual(runtime[0]['target'], route_titles(self.records[0]['target'], aliases, True))
        meta = json.loads(first['FONTS/D2FONT_12X15.JSON'])
        for alias in aliases.values():
            self.assertEqual(meta['glyphs'][str(alias)]['w'], 16)
            self.assertEqual(meta['glyphs'][str(alias)]['h'], 16)
            self.assertEqual(meta['glyphs'][str(alias)]['logw'], 16)

    def test_atlas_budget_is_enforced(self):
        self.profile['max_atlas_height'] = 5
        with self.assertRaisesRegex(ValueError, 'texture budget'):
            build_mixed(self.zar, self.records, self.profile)

    def test_configured_latin_replacement_repoints_original_glyph(self):
        self.profile['replace_existing_ranges'] = [[65, 65]]
        changes, _, report = build_mixed(self.zar, self.records, self.profile)
        meta = json.loads(changes['FONTS/D2FONT_12X15.JSON'])
        self.assertNotEqual(meta['glyphs']['65'], self.meta['glyphs']['65'])
        self.assertEqual(meta['glyphs']['65']['logw'], 12)
        self.assertEqual(meta['glyphs']['124'], self.meta['glyphs']['124'])
        self.assertEqual(report['replaced_original_codes'], [65])
        self.assertEqual(report['original_glyphs_preserved'], 2)

    def test_supplementary_and_private_use_source_rejected(self):
        for char in ('\U00020000', '\ue123'):
            with self.subTest(character=char):
                self.records[1]['target'] = char
                with self.assertRaisesRegex(ValueError, 'supplementary/private-use'):
                    build_mixed(self.zar, self.records, self.profile)

    def test_alias_collision_with_original_glyph_rejected(self):
        meta = copy.deepcopy(self.meta)
        meta['glyphs'][str(0xE000)] = meta['glyphs']['65'].copy()
        self.members['FONTS/D2FONT_12X15.JSON'] = json.dumps(meta).encode()
        with self.assertRaisesRegex(ValueError, 'collides'):
            build_mixed(self.zar, self.records, self.profile)

    def test_missing_required_body_font_glyph_rejected(self):
        self.records[1]['target'] = '无'
        with self.assertRaisesRegex(ValueError, 'font.*(missing|coverage)'):
            build_mixed(self.zar, self.records, self.profile)

    def test_missing_body_glyph_uses_native_title_font_fallback(self):
        title = Path(self.temp.name) / 'title.ttf'
        tiny_font(title, 'A一第章节开始甲乙，无 ')
        self.records[1]['target'] = '无'
        with patch('font_pipeline.resolve_fonts', return_value={'body': self.font, 'title': title}):
            changes, runtime, report = build_mixed(self.zar, self.records, self.profile)
        meta = json.loads(changes['FONTS/D2FONT_12X15.JSON'])
        glyph = meta['glyphs'][str(ord('无'))]
        self.assertEqual((glyph['w'], glyph['h'], glyph['logw']), (16, 16, 16))
        self.assertEqual(runtime[1]['target'], '无')
        self.assertEqual(report['body_fallback_codes'], [ord('无')])
        self.assertEqual(report['body_fallback_native_pixels'], 16)
        self.assertIn(ord('无'), report['coverage']['body']['missing'])
        self.assertNotIn(ord('无'), report['coverage']['title']['missing'])


if __name__ == '__main__':
    unittest.main()
