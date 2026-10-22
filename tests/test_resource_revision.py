"""Revision-aware translation inventory and appended option preservation."""
import json
from pathlib import Path
import unittest
from test_localize import fixture
from localize import Zar, extract, import_text

ROOT = Path(__file__).resolve().parents[1]


class ResourceRevisionTests(unittest.TestCase):
    def test_current_inventory_has_reviewed_head_bob_option(self):
        inventory = json.loads((ROOT/'locales/zh-CN/smoke.json').read_text(encoding='utf-8'))
        maps = {}
        for path in (ROOT/'locales/zh-CN').glob('*.map.json'):
            maps.update(json.loads(path.read_text(encoding='utf-8')))
        self.assertEqual({r['id'] for r in inventory}, set(maps))
        row = next(r for r in inventory if r['id'] == 'EN/OPTIONSNEW.TBL:0047')
        self.assertEqual(row['source'], 'HEAD BOB')
        self.assertEqual(maps[row['id']]['target'], '行走晃动')

    def test_appended_setting_keeps_record_order_and_line_endings(self):
        raw = b'Inverted\r\nNormal\r\nHEAD BOB\r\n\r\n'
        source = Zar(fixture({'EN/OPTIONSNEW.TBL': raw, 'CONFIG/DEFAULTS': b'head_bob=1\n'}))
        rows = extract(source)
        for row, target in zip(rows, ['反转', '正常', '行走晃动']):
            row['target'] = target
        after = Zar(source.rebuild(import_text(source, rows)))
        self.assertEqual(after.read('EN/OPTIONSNEW.TBL'), '反转\r\n正常\r\n行走晃动\r\n\r\n'.encode('utf-8'))
        self.assertEqual(after.read('CONFIG/DEFAULTS'), b'head_bob=1\n')
        self.assertEqual([r['line'] for r in extract(after)], [0, 1, 2])


if __name__ == '__main__':
    unittest.main()
