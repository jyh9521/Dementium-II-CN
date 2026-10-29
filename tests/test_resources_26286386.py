"""The official melee-crosshair row is data, not a localization-only extension."""
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from localize import Zar, digest, extract, import_text
from lint_locale import lint
from test_localize import fixture
from test_archive_update import archive
from audit_archive_update import audit


class MeleeCrosshairResourceTests(unittest.TestCase):
    def setUp(self):
        self.inventory = json.loads((ROOT / 'locales/zh-CN/smoke.json').read_text('utf-8'))
        self.maps = {}
        for path in sorted((ROOT / 'locales/zh-CN').glob('*.map.json')):
            data = json.loads(path.read_text('utf-8'))
            self.assertFalse(self.maps.keys() & data.keys())
            self.maps.update(data)
        self.rows = [r for r in self.inventory if r['resource'] == 'EN/OPTIONSNEW.TBL']

    def test_current_inventory_matches_all_translation_ids(self):
        self.assertEqual(len(self.inventory), 678)
        self.assertEqual({r['id'] for r in self.inventory}, set(self.maps))
        self.assertFalse([k for k, v in self.maps.items() if not v['target']])

    def test_official_row_48_is_melee_crosshairs_not_head_bob_value(self):
        self.assertEqual(len(self.rows), 49)
        self.assertEqual([r['line'] for r in self.rows], list(range(49)))
        self.assertEqual(self.rows[-1]['id'], 'EN/OPTIONSNEW.TBL:0048')
        self.assertEqual(self.rows[-1]['source'], 'MELEE CROSSHAIRS')
        self.assertEqual(self.maps[self.rows[-1]['id']]['target'], '近战准星')
        self.assertEqual(self.maps['EN/OPTIONSNEW.TBL:0047']['target'], '行走晃动')
        self.assertEqual(self.maps['EN/OPTIONSNEW.TBL:0041']['target'], '半透明')
        profile = json.loads((ROOT / 'locales/zh-CN/font-profile.json').read_text('utf-8'))
        self.assertFalse([r for r in profile.get('table_extensions', [])
                          if r['resource'] == 'EN/OPTIONSNEW.TBL'])

    def test_label_is_reviewed_ui_and_reuses_existing_corpus_characters(self):
        key = 'EN/OPTIONSNEW.TBL:0048'
        row = dict(self.rows[-1], **self.maps[key])
        self.assertEqual(row['status'], 'text-reviewed')
        self.assertEqual(row['text_type'], 'ui')
        self.assertEqual(lint([row]), [])
        existing = set(''.join(v['target'] for k, v in self.maps.items() if k != key))
        self.assertLessEqual(set(row['target']), existing)

    def test_import_retains_all_49_rows_and_original_record_delimiters(self):
        raw = ('\r\n'.join(r['source'] for r in self.rows) + '\r\n\r\n').encode('utf-8')
        source = Zar(fixture({'EN/OPTIONSNEW.TBL': raw, 'CONFIG/DEFAULTS': b'melee=1\n'}))
        translated = extract(source)
        for row in translated:
            row.update(self.maps[row['id']])
        after = Zar(source.rebuild(import_text(source, translated)))
        expected = ('\r\n'.join(self.maps[r['id']]['target'] for r in self.rows)
                    + '\r\n\r\n').encode('utf-8')
        self.assertEqual(after.read('EN/OPTIONSNEW.TBL'), expected)
        self.assertEqual(after.read('CONFIG/DEFAULTS'), b'melee=1\n')
        self.assertEqual(len(extract(after)), 49)

    def test_new_button_strip_and_other_locales_survive_localization(self):
        button = 'TEXTURES/OPTIONS/BUTTONSTRIP.PNG'
        old = archive({'EN/OPTIONSNEW.TBL': b'HEAD BOB\r\n',
                       'DE/OPTIONSNEW.TBL': b'OLD\r\n', button: b'12 buttons'})
        new = archive({'EN/OPTIONSNEW.TBL': b'HEAD BOB\r\nMELEE CROSSHAIRS\r\n',
                       'DE/OPTIONSNEW.TBL': b'OLD\r\nNEW\r\n', button: b'13 buttons'})
        modified = Zar(new.rebuild({'EN/OPTIONSNEW.TBL': '行走晃动\r\n近战准星\r\n'.encode('utf-8')}))
        result = audit(old, new, modified, ['EN/OPTIONSNEW.TBL'])
        self.assertEqual(result['result'], 'PASS')
        self.assertEqual(modified.read(button), new.read(button))
        self.assertEqual(modified.read('DE/OPTIONSNEW.TBL'), new.read('DE/OPTIONSNEW.TBL'))
        regressed = Zar(modified.rebuild({button: old.read(button)}))
        result = audit(old, new, regressed, ['EN/OPTIONSNEW.TBL'])
        self.assertEqual(result['result'], 'FAIL')
        self.assertIn(button, [r.get('resource') for r in result['issues']])


class BuiltMeleeCrosshairResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        modified = os.environ.get('DEMENTIUM_PREVIEW_ROM')
        if not modified:
            raise unittest.SkipTest('Built archive not explicitly selected')
        original = Path(os.environ.get('DEMENTIUM_CURRENT_ORIGINAL_ROM',
                                       ROOT / 'build/inputs/26286386/rom.zar'))
        cls.original = Zar(original.read_bytes())
        if digest(cls.original.data) != '2b45218a899881aa00fa4ea4ab1fa849d8ff8fe280d4aa510e9042cdf8698aa1':
            raise AssertionError('Build 26286386 original fixture identity mismatch')
        cls.modified = Zar(Path(modified).read_bytes())

    def test_actual_new_option_row_is_translated_without_losing_an_official_row(self):
        rows = [r for r in extract(self.modified) if r['resource'] == 'EN/OPTIONSNEW.TBL']
        self.assertEqual(len(rows), 49)
        self.assertEqual(rows[47]['source'], '行走晃动')
        self.assertEqual(rows[48]['source'], '近战准星')

    def test_actual_updated_buttonstrip_and_foreign_tables_are_byte_identical(self):
        names = ['TEXTURES/OPTIONS/BUTTONSTRIP.PNG']
        names.extend(f'{locale}/OPTIONSNEW.TBL' for locale in ('DE', 'FR', 'IT', 'SP'))
        for name in names:
            with self.subTest(resource=name):
                self.assertEqual(self.modified.read(name), self.original.read(name))
        self.assertEqual(digest(self.modified.read(names[0])),
                         '1e76b30eebcd5ea5f69d7ed82ce55e98b979926345e5c7f873d56832b500072d')


if __name__ == '__main__':
    unittest.main()
