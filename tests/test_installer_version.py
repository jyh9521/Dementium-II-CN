"""The requested release version must agree with all visible installer labels."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from build_installer import verify_version


class InstallerVersionTests(unittest.TestCase):
    def fixture(self, root):
        for name in ['assets/release-policy.json', 'installer/AssemblyInfo.cs',
                     'installer/MaterialWindow.xaml', 'installer/MaterialWindow.xaml.cs']:
            out = root/name
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, out)

    def test_current_source_and_delivery_identity_are_114(self):
        self.assertEqual(verify_version(ROOT), '1.1.4')
        policy = json.loads((ROOT/'assets/release-policy.json').read_text())
        self.assertEqual(policy['current_release'], 'v1.1.4')

    def test_stale_window_title_stops_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root)
            path = root/'installer/MaterialWindow.xaml'
            path.write_text(path.read_text('utf-8').replace('v1.1.4', 'v1.1.3'), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'window title'):
                verify_version(root)

    def test_stale_footer_stops_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root)
            path = root/'installer/MaterialWindow.xaml.cs'
            path.write_text(path.read_text('utf-8').replace('v1.1.4', 'v1.1.3'), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'build footer'):
                verify_version(root)

    def test_stale_assembly_stops_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root)
            path = root/'installer/AssemblyInfo.cs'
            path.write_text(path.read_text('utf-8').replace('1.1.4', '1.1.3'), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'AssemblyVersion'):
                verify_version(root)


if __name__ == '__main__': unittest.main()
