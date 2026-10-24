"""Synthetic update preservation: no proprietary resources required."""
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from audit_archive_update import audit, compare
from localize import Zar
from test_localize import fixture


def archive(members):
    names = sorted(members)
    pool = bytearray()
    records = bytearray()
    for name in names:
        records += struct.pack('<IIQ', len(members[name]), 0, len(pool))
        pool += ('/' + name).encode() + b'\0'
    return Zar(fixture(dict(members, **{'~INDEX': struct.pack('<Q', len(names)) + records + pool})))


class ArchiveUpdateTests(unittest.TestCase):
    def setUp(self):
        self.old = archive({'EN/GUI.TBL': b'Hello', 'MAP/OLD.PNG': b'old map',
                            'TIMING.TOML': b'hz=30'})
        self.new = archive({'EN/GUI.TBL': b'Hello', 'MAP/NEW.PNG': b'new map',
                            'TIMING.TOML': b'hz=60'})

    def test_localization_keeps_new_map_and_timing(self):
        modified = Zar(self.new.rebuild({'EN/GUI.TBL': '你好'.encode()}))
        report = audit(self.old, self.new, modified, ['EN/GUI.TBL'])
        self.assertEqual(report['result'], 'PASS')
        self.assertEqual(modified.read('MAP/NEW.PNG'), b'new map')
        self.assertEqual(modified.read('TIMING.TOML'), b'hz=60')

    def test_old_localized_archive_is_rejected(self):
        modified = Zar(self.old.rebuild({'EN/GUI.TBL': '你好'.encode()}))
        report = audit(self.old, self.new, modified, ['EN/GUI.TBL'])
        self.assertEqual(report['result'], 'FAIL')
        self.assertIn('Missing updated members', [r['reason'] for r in report['issues']])
        self.assertIn('Updated source member was reverted or changed',
                      [r['reason'] for r in report['issues']])

    def test_map_reversion_rejected(self):
        modified = Zar(self.new.rebuild({'MAP/NEW.PNG': b'old map'}))
        report = audit(self.old, self.new, modified, ['EN/GUI.TBL'])
        self.assertEqual(report['result'], 'FAIL')

    def test_empty_and_absent_member_differ(self):
        changed = compare(archive({'EMPTY': b''}), archive({'EMPTY': b'', 'NEW': b''}))
        self.assertEqual(changed[0]['old_size'], None)
        self.assertEqual(changed[0]['new_size'], 0)
        self.assertIsNotNone(changed[0]['new_sha256'])

    def test_index_unrelated_bytes_rejected(self):
        raw = bytearray(self.new.data)
        raw[self.new.entries['~INDEX'].offset + 12] = 1  # first flags
        report = audit(self.old, self.new, Zar(bytes(raw)), ['EN/GUI.TBL'])
        self.assertEqual(report['result'], 'FAIL')
        self.assertIn('Unexpected derived VFS index change', [r['reason'] for r in report['issues']])


if __name__ == '__main__':
    unittest.main()
