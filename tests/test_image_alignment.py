"""Native-frame alignment fixtures contain no game art or font data."""
import copy
import io
import sys
from pathlib import Path
import unittest
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from image_alignment import measure, reposition
from image_text import build_images
import test_image_text as fixtures


class NativeAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.image = Image.new('RGBA', (48, 28), (25, 45, 65, 255))
        ImageDraw.Draw(self.image).rectangle((14, 8, 23, 17), fill=(230, 220, 200, 255))
        self.rule = dict(label='fixture', roi=[8, 3, 40, 25], frame=[8, 3, 40, 25], axes=[0,1])

    def test_off_center_goes_red_then_green_without_resampling(self):
        self.assertEqual(measure(self.image,self.rule)['result'], 'FAIL')
        moved, trace = reposition(self.image,self.rule)
        self.assertEqual(trace['shift'], [5,1])
        self.assertEqual(measure(moved,self.rule)['result'], 'PASS')
        self.assertEqual(moved.crop((19,9,29,19)).tobytes(),self.image.crop((14,8,24,18)).tobytes())

    def test_pixels_outside_roi_and_input_are_unchanged(self):
        before = self.image.tobytes()
        moved, _ = reposition(self.image,self.rule)
        for y in range(self.image.height):
            for x in range(self.image.width):
                if not (8<=x<40 and 3<=y<25):
                    self.assertEqual(moved.getpixel((x,y)),self.image.getpixel((x,y)))
        self.assertEqual(self.image.tobytes(),before)

    def test_alignment_is_idempotent(self):
        first, _ = reposition(self.image,self.rule)
        second, _ = reposition(first,self.rule)
        self.assertEqual(first.tobytes(),second.tobytes())

    def test_unreviewed_large_move_or_clipping_is_rejected(self):
        rule=copy.deepcopy(self.rule);rule['max_shift']=1
        with self.assertRaisesRegex(ValueError,'margin'):
            reposition(self.image,rule)
        rule=copy.deepcopy(self.rule);rule['frame']=[32,3,48,25]
        with self.assertRaises(ValueError):
            reposition(self.image,rule)

    def test_source_curve_keeps_vertical_baseline(self):
        self.rule['axes']=[0]
        moved, trace=reposition(self.image,self.rule)
        self.assertEqual(trace['shift'][1],0)
        self.assertEqual(measure(moved,self.rule)['ink_bounds'][1:4:2],[8,18])


class InkBearingTests(unittest.TestCase):
    setUp = fixtures.ImageTextTests.setUp
    def test_actual_ink_center_ignores_advance_bearings_and_preserves_icon(self):
        self.config['images'][0]['labels'][0]['ink_center']=True
        changes,_=build_images(self.zar,self.config,self.font)
        result=Image.open(io.BytesIO(next(iter(changes.values())))).convert('RGBA')
        tile=result.crop((20,10,44,26))
        bounds=tile.getchannel('A').getbbox()
        self.assertLessEqual(abs((bounds[0]+bounds[2])/2-12),.5)
        self.assertLessEqual(abs((bounds[1]+bounds[3])/2-8),.5)
        self.assertEqual(result.getpixel((2,2)),(255,0,0,255))


if __name__=='__main__':
    unittest.main()
