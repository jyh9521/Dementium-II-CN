"""Keep the previously requested installer startup compatibility in new builds."""
import os
from pathlib import Path
import struct
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class InstallerCetTests(unittest.TestCase):
    def test_project_disables_cet_for_installer_only(self):
        project = ET.parse(ROOT/'installer/Installer.csproj')
        self.assertEqual(project.findtext('.//CETCompat'), 'false')

    def test_published_installer_has_compatibility_flag_off(self):
        path = Path(os.environ.get('DEMENTIUM_INSTALLER_TEST_EXE',
                                   ROOT/'dist/Dementium-II-zh-CN-Setup.exe'))
        if not path.is_file():
            self.skipTest('requires newly built installer')
        import pefile
        pe = pefile.PE(str(path))
        entries = [entry for entry in pe.DIRECTORY_ENTRY_DEBUG if entry.struct.Type == 20]
        self.assertEqual(len(entries), 1)
        entry = entries[0].struct
        self.assertGreaterEqual(entry.SizeOfData, 4)
        flags = struct.unpack_from('<I', path.read_bytes(), entry.PointerToRawData)[0]
        self.assertEqual(flags & 1, 0)


if __name__ == '__main__':
    unittest.main()
