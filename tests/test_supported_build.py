"""Keep installer identity and executable recipe in sync with the source build."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SupportedBuildTests(unittest.TestCase):
    def test_executable_recipe_matches_supported_identity(self):
        identity = json.loads((ROOT/'assets/supported-build.json').read_text())
        recipe = json.loads((ROOT/'locales/zh-CN/executable-text.json').read_text(encoding='utf-8'))
        self.assertEqual(recipe['source_size'], identity['exe_size'])
        self.assertEqual(recipe['source_sha256'], identity['exe_sha256'])

    def test_ui_build_label_matches_supported_identity(self):
        identity = json.loads((ROOT/'assets/supported-build.json').read_text())
        settings = json.loads((ROOT/'locales/zh-CN/installer.json').read_text(encoding='utf-8'))
        self.assertEqual(settings['build_label'], '2026 build '+identity['buildid'])
        self.assertEqual(settings['supported_builds'], '26099941 / 26123896 / 26152271')
        window = (ROOT/'installer/MaterialWindow.xaml.cs').read_text(encoding='utf-8')
        self.assertIn('payload.Settings.build_label', window)
        self.assertNotIn('payload.Settings.supported_builds', window)
        self.assertEqual(settings['footer'], '已验证支持 Steam 2026 build '+identity['buildid'])
        self.assertIn('已验证支持', (ROOT/'installer/MaterialWindow.xaml').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
