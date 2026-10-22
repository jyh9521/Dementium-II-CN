from pathlib import Path
import tempfile
import unittest

from localize import write_json
from package_probe import text_payload


class PackagingTests(unittest.TestCase):
    def test_checkout_line_endings_do_not_change_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            path.write_bytes(b'{\r\n  "value": 1\r\n}\r\n')
            self.assertEqual(text_payload(path), b'{\n  "value": 1\n}\n')

    def test_portable_bundle_contains_lazy_stdlib_native_profile(self):
        import json,subprocess,sys,zipfile
        from unittest.mock import patch
        from package_locale import main
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory);build=directory/'build';build.mkdir()
            for name in ('patch.json','exe-patch.json','release-manifest.json'):
                (build/name).write_text('{}\n',encoding='utf-8')
            output=directory/'portable.zip'
            with patch.object(sys,'argv',['package_locale','--build',str(build),'--output',str(output)]):main()
            extracted=directory/'extracted'
            with zipfile.ZipFile(output) as archive:
                self.assertIn('native_profile.py',archive.namelist())
                hashes=json.loads(archive.read('SHA256.json'))
                self.assertIn('native_profile.py',hashes)
                archive.extractall(extracted)
            # Applying sparse deltas imports no build-time native analysis engines.
            script="""import importlib.abc,sys
class BlockEngines(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in ('capstone','pefile','keystone'):raise ModuleNotFoundError(fullname)
sys.meta_path.insert(0,BlockEngines())
sys.path.insert(0,sys.argv[1])
import debug_menu,native_profile
assert 'capstone' not in sys.modules
print('PORTABLE_NATIVE_IMPORT=PASS')
"""
            result=subprocess.run([sys.executable,'-I','-c',script,str(extracted)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('PORTABLE_NATIVE_IMPORT=PASS',result.stdout)

    def test_generated_json_uses_lf_on_all_hosts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'output.json'
            write_json(path, {'value': '中文'})
            self.assertNotIn(b'\r', path.read_bytes())
