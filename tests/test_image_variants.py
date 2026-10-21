import sys
import unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from match_image_variants import transfer


class VariantToneTests(unittest.TestCase):
    def setUp(self):
        self.a=Image.new('RGBA',(10,8),(18,0,0,255));self.b=self.a.copy()
        self.a.putpixel((4,4),(230,220,220,255))
        self.b.putpixel((4,4),(245,215,220,255))
        self.c=self.a.copy();self.c.putpixel((5,4),(230,220,220,255))

    def test_only_shared_geometry_light_ink_changes(self):
        output, report=transfer(self.a,self.b,self.c,[2,2,8,7])
        self.assertEqual(output.getpixel((5,4)),(245,215,220,255))
        self.assertEqual(output.getchannel('A').tobytes(),self.c.getchannel('A').tobytes())
        self.assertEqual(report['localized_ink_pixels'],2)
        for y in range(8):
            for x in range(10):
                if (x,y) not in ((4,4),(5,4)):
                    self.assertEqual(output.getpixel((x,y)),self.c.getpixel((x,y)))

    def test_reject_changes_outside_original_lettering(self):
        self.b.putpixel((0,0),(1,2,3,255))
        with self.assertRaisesRegex(ValueError,'outside reviewed'):
            transfer(self.a,self.b,self.c,[2,2,8,7])

    def test_reject_alpha_or_shape_differences(self):
        self.b.putpixel((4,4),(245,215,220,0))
        with self.assertRaisesRegex(ValueError,'alpha'):
            transfer(self.a,self.b,self.c,[2,2,8,7])

    def test_tone_transfer_is_deterministic_and_does_not_mutate_inputs(self):
        before=self.c.tobytes()
        a,_=transfer(self.a,self.b,self.c,[2,2,8,7])
        b,_=transfer(self.a,self.b,self.c,[2,2,8,7])
        self.assertEqual(a.tobytes(),b.tobytes())
        self.assertEqual(self.c.tobytes(),before)

    def test_brightness_order_is_preserved(self):
        self.a.putpixel((4,5),(130,120,120,255));self.b.putpixel((4,5),(160,100,110,255))
        self.c.putpixel((4,5),(130,120,120,255))
        a,_=transfer(self.a,self.b,self.c,[2,2,8,7])
        self.assertLess(a.getpixel((4,5))[1],a.getpixel((4,4))[1])


if __name__=='__main__': unittest.main()
