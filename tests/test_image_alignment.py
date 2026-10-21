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

    def test_left_ink_anchor_retains_original_key_gap(self):
        label=self.config['images'][0]['labels'][0]
        label.update(ink_center=True,ink_align='left')
        out,_=build_images(self.zar,self.config,self.font)
        im=Image.open(io.BytesIO(next(iter(out.values()))))
        self.assertEqual(im.crop(label['box']).getchannel('A').getbbox()[0],0)

    def test_native_tracking_compacts_without_resampling_strokes(self):
        label=self.config['images'][0]['labels'][0]
        label.update(target='中中',ink_center=True,ink_align='left')
        wide,_=build_images(self.zar,self.config,self.font)
        label['letter_spacing']=-1
        narrow,_=build_images(self.zar,self.config,self.font)
        a=Image.open(io.BytesIO(next(iter(wide.values())))).crop(label['box']).getchannel('A')
        b=Image.open(io.BytesIO(next(iter(narrow.values())))).crop(label['box']).getchannel('A')
        self.assertEqual(a.getbbox()[2]-b.getbbox()[2],1)
        self.assertEqual(sum(a.get_flattened_data()),sum(b.get_flattened_data()))

    def test_native_diagram_audit_rejects_opaque_background_regression(self):
        from audit_image_alignment import audit
        label=self.config['images'][0]['labels'][0]
        self.config['images'][0]['alignment_review']={'mode':'source-native-pixel-preservation'}
        output,_=build_images(self.zar,self.config,self.font)
        name=self.config['images'][0]['resource']
        class View:
            entries={name:None}
            def __init__(self,raw):self.raw=raw
            def read(self,_):return self.raw
        modified=output[name]
        self.assertEqual(audit(View(self.raw),View(modified),self.config)['result'],'PASS')
        im=Image.open(io.BytesIO(modified)).convert('RGBA');im.putpixel((0,0),(0,0,0,255))
        stream=io.BytesIO();im.save(stream,format='PNG')
        report=audit(View(self.raw),View(stream.getvalue()),self.config)
        self.assertEqual(report['result'],'FAIL')
        self.assertTrue(any('outside text panes' in r['reason'] for r in report['issues']))

    def test_repository_control_recipes_preserve_original_diagrams(self):
        import json
        config=json.loads((Path(__file__).resolve().parents[1]/'locales/zh-CN/image-text.json').read_text('utf8'))
        controls=[r for r in config['images'] if 'CONTROLS_' in r['resource']]
        self.assertEqual(len(controls),12)
        for recipe in controls:
            self.assertNotIn('art_delta',recipe)
            self.assertEqual(recipe['alignment_review']['mode'],'source-native-pixel-preservation')
            for label in recipe['labels']:
                if label['source']=='Jump':self.assertEqual(label['target'],'跳跃')
        for recipe in config['images']:
            if 'YAXIS' in recipe['resource']:
                self.assertTrue(recipe['labels'][0]['target'].endswith(':'))
                self.assertLess(recipe['labels'][0]['box'][2],188)


if __name__=='__main__':
    unittest.main()
