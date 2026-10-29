"""Keep installer identity and executable recipe in sync with the source build."""
import json
import gzip
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SupportedBuildTests(unittest.TestCase):
    def test_compatibility_inventory_matches_advertised_builds(self):
        identity = json.loads((ROOT/'assets/supported-build.json').read_text())
        settings = json.loads((ROOT/'locales/zh-CN/installer.json').read_text(encoding='utf-8'))
        compatibility = json.loads((ROOT/'assets/compatibility-payloads.json').read_text())['payloads']
        advertised = settings['supported_builds'].split(' / ')
        self.assertEqual(set(advertised), {identity['buildid'], *[p['buildid'] for p in compatibility]})
        for item in compatibility:
            previous = json.loads((ROOT/'assets/supported-builds'/f"{item['buildid']}.json").read_text())
            self.assertEqual(item['exe_sha256'], previous['exe_sha256'])

    def test_generated_payload_contains_each_native_source_exactly_once(self):
        path = ROOT/'build/installer/resource-patches.gz'
        if not path.is_file():
            self.skipTest('requires generated installer payload')
        payload = json.loads(gzip.decompress(path.read_bytes()))['native_executable']
        variants = [payload, *payload.get('source_variants', [])]
        settings = json.loads((ROOT/'locales/zh-CN/installer.json').read_text(encoding='utf-8'))
        expected = [json.loads((ROOT/'assets/supported-builds'/f'{build}.json').read_text())['exe_sha256']
                    for build in settings['supported_builds'].split(' / ')]
        self.assertCountEqual([p['source_sha256'] for p in variants], expected)
        self.assertTrue(all(p.get('hash_guards') for p in variants))
        self.assertTrue(all('source_variants' not in p for p in variants[1:]))

    def test_executable_recipe_matches_supported_identity(self):
        identity = json.loads((ROOT/'assets/supported-build.json').read_text())
        recipe = json.loads((ROOT/'locales/zh-CN/executable-text.json').read_text(encoding='utf-8'))
        self.assertEqual(recipe['source_size'], identity['exe_size'])
        self.assertEqual(recipe['source_sha256'], identity['exe_sha256'])

    def test_ui_build_label_matches_supported_identity(self):
        identity = json.loads((ROOT/'assets/supported-build.json').read_text())
        settings = json.loads((ROOT/'locales/zh-CN/installer.json').read_text(encoding='utf-8'))
        self.assertEqual(settings['build_label'], '2026 build '+identity['buildid'])
        self.assertEqual(settings['supported_builds'], '26099941 / 26123896 / 26152271 / 26260428')
        window = (ROOT/'installer/MaterialWindow.xaml.cs').read_text(encoding='utf-8')
        self.assertIn('payload.Settings.build_label', window)
        self.assertNotIn('payload.Settings.supported_builds', window)
        self.assertEqual(settings['footer'], '已验证支持 Steam 2026 build '+identity['buildid'])
        self.assertIn('已验证支持', (ROOT/'installer/MaterialWindow.xaml').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
