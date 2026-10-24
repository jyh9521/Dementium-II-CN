"""Context-specific rows retain the shared source table's existing indices."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from table_extensions import extend_tables, extension_records


class TableExtensionTests(unittest.TestCase):
    def setUp(self):
        self.profile = {'table_extensions': [{'resource': 'EN/A.TBL', 'source_rows': 2, 'rows': ['轻微']}]}
        self.zar = type('Archive', (), {'read': lambda _, name: b'ON\r\nSUBTLE\r\n'})()

    def test_append_preserves_existing_rows_and_changes_input(self):
        changes = {'EN/A.TBL': '开\r\n半透明\r\n'.encode()}
        result = extend_tables(self.zar, changes, self.profile)
        self.assertEqual(result['EN/A.TBL'], '开\r\n半透明\r\n轻微\r\n'.encode())
        self.assertEqual(changes['EN/A.TBL'], '开\r\n半透明\r\n'.encode())
        self.assertEqual(extension_records(self.profile)[0]['id'], 'EN/A.TBL:0002')

    def test_stale_count_and_invalid_row_rejected(self):
        self.profile['table_extensions'][0]['source_rows'] = 3
        with self.assertRaises(ValueError): extend_tables(self.zar, {}, self.profile)
        self.profile['table_extensions'][0]['rows'] = ['a\nb']
        with self.assertRaises(ValueError): extend_tables(self.zar, {}, self.profile)

    def test_empty_profile_is_noop(self):
        self.assertEqual(extend_tables(self.zar, {'x': b'y'}, {}), {'x': b'y'})


class OptionContextReplayTests(unittest.TestCase):
    def test_both_option_contexts_in_actual_built_getter(self):
        import os
        exe = os.environ.get('DEMENTIUM_MODIFIED_EXE')
        rom = os.environ.get('DEMENTIUM_PREVIEW_ROM')
        if not exe or not rom:
            self.skipTest('Built executable and archive not selected')
        from verify_option_context import labels
        self.assertEqual(labels(Path(exe).read_bytes(), Path(rom).read_bytes()),
                         {'head_bob': ['普通', '轻微', '关闭'], 'minimap': ['关', '半透明', '不透明']})


if __name__ == '__main__': unittest.main()
