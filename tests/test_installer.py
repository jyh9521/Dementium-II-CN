import json
from pathlib import Path
import tempfile
import unittest

from test_localize import fixture
from localize import Zar, digest, make_delta
from install_patch import operate


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.original = fixture()
        self.modified = Zar(self.original).rebuild({'EN/GUI.TBL': b'NEW'})
        self.patch = make_delta(self.original, self.modified)
        self.exe = b'SYNTHETIC EXE FIXTURE - NOT EXECUTABLE'
        (self.root / 'Dementium II.exe').write_bytes(self.exe)
        (self.root / 'rom.zar').write_bytes(self.original)
        self.identity = dict(appid=5342930, exe_sha256=digest(self.exe), exe_size=len(self.exe), rom_sha256=digest(self.original), rom_size=len(self.original))

    def test_install_idempotence_uninstall_and_backup(self):
        self.assertEqual(operate(self.root, self.identity, self.patch, 'install'), 'INSTALLED')
        self.assertEqual((self.root / 'rom.zar').read_bytes(), self.modified)
        self.assertEqual(operate(self.root, self.identity, self.patch, 'install'), 'ALREADY_INSTALLED')
        self.assertEqual(operate(self.root, self.identity, self.patch, 'uninstall'), 'RESTORED')
        self.assertEqual((self.root / 'rom.zar').read_bytes(), self.original)
        self.assertEqual(operate(self.root, self.identity, self.patch, 'uninstall'), 'ALREADY_RESTORED')
        self.assertFalse((self.root / 'cn-backup').exists())

    def test_reject_wrong_game_and_patch(self):
        for field in ['appid', 'exe_sha256', 'rom_sha256']:
            ident = self.identity.copy(); ident[field] = 'wrong'
            with self.subTest(field=field), self.assertRaises(ValueError): operate(self.root, ident, self.patch, 'install')
        self.assertFalse((self.root / 'cn-backup').exists())

    def test_reject_changed_archive_and_backup(self):
        operate(self.root, self.identity, self.patch, 'install')
        (self.root / 'cn-backup/rom.zar').write_bytes(b'WRONG')
        with self.assertRaises(ValueError): operate(self.root, self.identity, self.patch, 'uninstall')
        self.assertEqual((self.root / 'rom.zar').read_bytes(), self.modified)
        (self.root / 'rom.zar').write_bytes(self.modified + b'WRONG')
        with self.assertRaises(ValueError): operate(self.root, self.identity, self.patch, 'install')
