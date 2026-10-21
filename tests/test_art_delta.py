import copy
import sys
from pathlib import Path
import unittest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from art_delta import capture,apply


class ArtDeltaTests(unittest.TestCase):
    def setUp(self):
        self.a=Image.new('RGBA',(12,8),(20,40,60,0))
        self.b=self.a.copy();self.b.putpixel((5,3),(200,180,120,255))
        self.patch=capture(self.a,self.b,resource='sample',prompt='synthetic fixture')

    def test_exact_reconstruction(self):
        self.assertEqual(apply(self.a,self.patch).tobytes(),self.b.tobytes())

    def test_original_not_modified(self):
        before=self.a.tobytes();apply(self.a,self.patch)
        self.assertEqual(before,self.a.tobytes())

    def test_wrong_source_rejected(self):
        self.a.putpixel((0,0),(1,2,3,4))
        with self.assertRaises(ValueError):apply(self.a,self.patch)

    def test_wrong_result_rejected(self):
        bad=copy.deepcopy(self.patch);bad['output_pixels_sha256']='0'*64
        with self.assertRaises(ValueError):apply(self.a,bad)

    def test_dimensions_rejected(self):
        with self.assertRaises(ValueError):capture(self.a,self.b.resize((3,3)),resource='sample',prompt='test')

    def test_truncated_payload_rejected(self):
        bad=copy.deepcopy(self.patch);bad['xor']=bad['xor'][:4]
        with self.assertRaises(ValueError):apply(self.a,bad)
