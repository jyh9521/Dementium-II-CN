import hashlib
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from image_preservation import validate_configuration,verify_archive


class Archive:
    def __init__(self,raw=b'original fixture'):self.raw=raw
    def read(self,name):return self.raw


class ImagePreservationTests(unittest.TestCase):
    def setUp(self):
        self.a=Archive()
        self.config={'images':[], 'preserve_original_images':{'TEX/SAMPLE.PNG':{
            'source_sha256':hashlib.sha256(self.a.raw).hexdigest()}}}

    def test_unchanged_source_allowed(self):
        self.assertEqual(validate_configuration(self.a,self.config),1)

    def test_replacement_rejected(self):
        self.config['images']=[{'resource':'TEX/SAMPLE.PNG'}]
        with self.assertRaises(ValueError):validate_configuration(self.a,self.config)

    def test_source_hash_guard(self):
        with self.assertRaises(ValueError):validate_configuration(Archive(b'different'),self.config)

    def test_output_change_rejected(self):
        with self.assertRaises(ValueError):verify_archive(self.a,Archive(b'modified'),self.config)

    def test_output_unchanged(self):
        self.assertEqual(verify_archive(self.a,self.a,self.config)[0]['result'],'BYTE_IDENTICAL')
