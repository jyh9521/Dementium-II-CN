import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from archive_zip_rollback import create,restore


class ZipRollbackTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.old=self.root/'old.zip';self.new=self.root/'new.zip'
        for path,version in [(self.old,'old'),(self.new,'new')]:
            with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('unchanged.bin',b'unchanged data'*1000)
                archive.writestr(version+'.exe',b'MZ'+version.encode()+b'payload'*2000)
                archive.writestr('metadata.txt',version)
        self.delta=self.root/'rollback.gz';self.out=self.root/'restored.zip'
    def build(self):create(self.new,self.old,self.delta,{'old.exe':'new.exe'})
    def test_exact_zip_headers_contents_and_original_unchanged(self):
        current=self.new.read_bytes();previous=self.old.read_bytes();self.build()
        restore(self.new,self.delta,self.out)
        self.assertEqual(self.out.read_bytes(),previous);self.assertEqual(self.new.read_bytes(),current)
        with zipfile.ZipFile(self.out) as archive:self.assertIsNone(archive.testzip())
    def test_output_is_never_overwritten(self):
        self.build();self.out.write_bytes(b'KEEP')
        with self.assertRaises(FileExistsError):restore(self.new,self.delta,self.out)
        self.assertEqual(self.out.read_bytes(),b'KEEP')
    def test_wrong_source_stops_before_output(self):
        self.build();self.new.write_bytes(self.new.read_bytes()+b'drift')
        with self.assertRaisesRegex(ValueError,'source identity'):restore(self.new,self.delta,self.out)
        self.assertFalse(self.out.exists())
    def test_corrupt_target_hash_has_no_published_output(self):
        self.build();r=json.loads(gzip.decompress(self.delta.read_bytes()));r['target']['sha256']='0'*64
        self.delta.write_bytes(gzip.compress(json.dumps(r).encode()))
        with self.assertRaisesRegex(ValueError,'target identity'):restore(self.new,self.delta,self.out)
        self.assertFalse(self.out.exists())
    def test_invalid_copy_rejects_before_output(self):
        self.build();r=json.loads(gzip.decompress(self.delta.read_bytes()));r['operations'][0]=['copy',-1,100]
        self.delta.write_bytes(gzip.compress(json.dumps(r).encode()))
        with self.assertRaisesRegex(ValueError,'COPY bounds'):restore(self.new,self.delta,self.out)
        self.assertFalse(self.out.exists())
    def test_existing_delta_is_never_overwritten(self):
        self.delta.write_bytes(b'KEEP')
        with self.assertRaises(FileExistsError):self.build()
        self.assertEqual(self.delta.read_bytes(),b'KEEP')


if __name__=='__main__':unittest.main()
