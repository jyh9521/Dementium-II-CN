"""Reversible two-component install tests, entirely synthetic."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_localize import fixture as archive_fixture
from test_executable_text import fixture as executable_fixture
from localize import Zar, digest, make_delta
from executable_text import build_executable
from install_patch import operate_bundle, atomic_write


class BundleInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.game=Path(self.temp.name)
        self.rom=archive_fixture();self.modified_rom=Zar(self.rom).rebuild({'EN/GUI.TBL':b'UPDATED'})
        self.exe,recipe=executable_fixture();self.modified_exe,self.exe_patch=build_executable(self.exe,recipe)
        self.rom_patch=make_delta(self.rom,self.modified_rom)
        self.identity=dict(appid=5342930,rom_sha256=digest(self.rom),rom_size=len(self.rom),exe_sha256=digest(self.exe),exe_size=len(self.exe))
        self.write_original()

    def write_original(self):
        (self.game/'rom.zar').write_bytes(self.rom)
        (self.game/'Dementium II.exe').write_bytes(self.exe)

    def operate(self,action):
        return operate_bundle(self.game,self.identity,self.rom_patch,self.exe_patch,action)

    def test_install_repeat_restore_repeat(self):
        self.assertEqual(self.operate('install'),'INSTALLED')
        self.assertEqual((self.game/'rom.zar').read_bytes(),self.modified_rom)
        self.assertEqual((self.game/'Dementium II.exe').read_bytes(),self.modified_exe)
        self.assertEqual(self.operate('install'),'ALREADY_INSTALLED')
        self.assertEqual(self.operate('uninstall'),'RESTORED')
        self.assertEqual((self.game/'rom.zar').read_bytes(),self.rom)
        self.assertEqual((self.game/'Dementium II.exe').read_bytes(),self.exe)
        self.assertEqual(self.operate('uninstall'),'ALREADY_RESTORED')

    def test_unknown_executable_rejected_before_any_write(self):
        (self.game/'Dementium II.exe').write_bytes(b'UNKNOWN')
        with self.assertRaises(ValueError):self.operate('install')
        self.assertEqual((self.game/'rom.zar').read_bytes(),self.rom)
        self.assertFalse((self.game/'cn-backup').exists())

    def test_unknown_archive_rejected_before_any_write(self):
        (self.game/'rom.zar').write_bytes(b'UNKNOWN')
        with self.assertRaises(ValueError):self.operate('install')
        self.assertEqual((self.game/'Dementium II.exe').read_bytes(),self.exe)

    def test_tampered_backup_rejected(self):
        self.operate('install')
        (self.game/'cn-backup/Dementium II.exe').write_bytes(b'UNKNOWN')
        with self.assertRaises(ValueError):self.operate('uninstall')
        self.assertEqual((self.game/'rom.zar').read_bytes(),self.modified_rom)

    def test_modified_without_backup_rejected(self):
        (self.game/'Dementium II.exe').write_bytes(self.modified_exe)
        with self.assertRaises(ValueError):self.operate('install')
        self.assertFalse((self.game/'cn-backup').exists())

    def test_interrupted_mixed_state_can_be_completed(self):
        self.operate('install')
        (self.game/'Dementium II.exe').write_bytes(self.exe)
        self.assertEqual(self.operate('install'),'INSTALLED')
        self.assertEqual((self.game/'Dementium II.exe').read_bytes(),self.modified_exe)
        (self.game/'rom.zar').write_bytes(self.rom)
        self.assertEqual(self.operate('uninstall'),'RESTORED')
        self.assertEqual((self.game/'Dementium II.exe').read_bytes(),self.exe)

    def test_second_component_write_failure_restores_first(self):
        def fail_exe(path,data):
            if path.name=='Dementium II.exe':raise OSError('synthetic write failure')
            atomic_write(path,data)
        with patch('install_patch.atomic_write',side_effect=fail_exe):
            with self.assertRaises(OSError):self.operate('install')
        self.assertEqual((self.game/'rom.zar').read_bytes(),self.rom)
        self.assertEqual((self.game/'Dementium II.exe').read_bytes(),self.exe)


if __name__=='__main__':unittest.main()
