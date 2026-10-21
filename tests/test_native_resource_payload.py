import base64
import copy
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from build_resource_payload import native_executable_payload
from localize import digest


class NativeExecutablePayloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.build=Path(self.tmp.name)
        self.original=b'MZ SYNTHETIC ORIGINAL EXE'
        self.modified=self.original[:3]+b'X'+self.original[4:]+b'APPENDED SECTION'
        (self.build/'Dementium II.exe').write_bytes(self.modified)
        self.identity=dict(exe_size=len(self.original),exe_sha256=digest(self.original))
        self.patch=dict(format='native-menu-pe-v1',original_size=len(self.original),modified_size=len(self.modified),
            original_sha256=digest(self.original),modified_sha256=digest(self.modified),
            runs=[dict(offset=3,old=self.original[3:4].hex(),new='58')],
            append=base64.b64encode(b'APPENDED SECTION').decode())

    def test_carries_complete_sparse_native_payload(self):
        p=native_executable_payload(self.build,self.patch,self.identity)
        self.assertEqual(p['name'],'Dementium II.exe')
        self.assertEqual(p['runs'],self.patch['runs'])
        self.assertEqual(p['tail'],self.patch['append'])
        self.assertEqual(p['target_sha256'],digest(self.modified))

    def test_unknown_executable_identity_rejected(self):
        self.identity['exe_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'supported executable'):
            native_executable_payload(self.build,self.patch,self.identity)

    def test_wrong_target_file_rejected(self):
        (self.build/'Dementium II.exe').write_bytes(self.modified+b'?')
        with self.assertRaisesRegex(ValueError,'output mismatch'):
            native_executable_payload(self.build,self.patch,self.identity)

    def test_bad_native_byte_guard_rejected(self):
        self.patch['runs'][0]['new']='ff'
        with self.assertRaisesRegex(ValueError,'byte guard'):
            native_executable_payload(self.build,self.patch,self.identity)

    def test_overlapping_native_runs_rejected(self):
        self.patch['runs']*=2
        with self.assertRaisesRegex(ValueError,'byte guard'):
            native_executable_payload(self.build,self.patch,self.identity)

    def test_wrong_original_guard_rejected(self):
        self.patch['runs'][0]['old']='ff'
        with self.assertRaisesRegex(ValueError,'reverse identity'):
            native_executable_payload(self.build,self.patch,self.identity)

    def test_wrong_appended_section_rejected(self):
        self.patch['append']=base64.b64encode(b'UNKNOWN SECTION').decode()
        with self.assertRaisesRegex(ValueError,'appended section'):
            native_executable_payload(self.build,self.patch,self.identity)


if __name__=='__main__':unittest.main()
