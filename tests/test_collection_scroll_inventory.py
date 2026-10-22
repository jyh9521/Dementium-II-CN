"""Full native collection resource census, not screenshot-selected examples."""
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from audit_collection_scroll import audit

EXE = Path(os.environ.get('DEMENTIUM_UI_TEST_EXE', ROOT / 'build/full-zh-CN/Dementium II.exe'))
ROM = Path(os.environ.get('DEMENTIUM_PREVIEW_ROM', ROOT / 'build/full-zh-CN/rom.zar'))


@unittest.skipUnless(EXE.is_file() and ROM.is_file(), 'local built PE and archive required')
class CollectionScrollInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from native_replay import require_native_fixture
        require_native_fixture(EXE)
    def test_every_existing_native_collection_text_resource(self):
        report = audit(EXE, ROM)
        self.assertEqual(report['native_id_range'], [41, 99])
        self.assertEqual(report['tested_resource_count'] + len(report['missing_text_ids']), 59)
        self.assertEqual(len({row['identifier'] for row in report['rows']}), report['tested_resource_count'])
        self.assertEqual(report['problems'], [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
