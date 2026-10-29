import copy
import io
import json
from pathlib import Path
import sys
import unittest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_ui_corrections import audit
from build_installer import verify_version

ROOT=Path(__file__).resolve().parents[1]

class UiCorrectionTests(unittest.TestCase):
    def test_panel_frame_override_inside_old_text_box_is_rejected(self):
        name='TEXTURES/OPTIONS/EN/CONTROLS_KEYBOARD_TYPE1.PNG'
        a=Image.new('RGBA',(428,240),(0,0,0,67));a.putpixel((248,70),(136,119,109,67))
        def png(im):
            out=io.BytesIO();im.save(out,format='PNG');return out.getvalue()
        class View:
            def __init__(self,im):self.im=png(im)
            def read(self,_):return self.im
        config={'images':[dict(resource=name,labels=[])]}
        self.assertEqual(audit(View(a),View(a),config)['result'],'PASS')
        b=a.copy();b.putpixel((248,70),(0,0,0,67))
        report=audit(View(a),View(b),config)
        self.assertEqual(report['result'],'FAIL')
        self.assertEqual(report['images'][0]['frame_changed_pixels'],1)

    def test_equal_box_centers_do_not_hide_unequal_visible_gaps(self):
        name='TEXTURES/OPTIONS/EN/CONTROLS_PC_TYPE1.PNG'
        im=Image.new('RGBA',(428,240));labels=[]
        for source,top in [('Equip Last',163),('Cycle Weapons',178),('Flashlight',191)]:
            for y in range(top,top+13):
                for x in range(61,100):im.putpixel((x,y),(255,255,255,255))
            labels.append(dict(source=source,target=source,box=[60,top,110,top+13]))
        class View:
            def read(self,_):
                out=io.BytesIO();im.save(out,format='PNG');return out.getvalue()
        report=audit(View(),View(),{'images':[dict(resource=name,labels=labels)]})
        self.assertEqual(report['result'],'FAIL');self.assertEqual(report['images'][0]['gaps'],[2,0])

    def test_version_matches_explicit_user_requested_113(self):
        self.assertEqual(verify_version(ROOT),'1.1.3')
        policy=json.loads((ROOT/'assets/release-policy.json').read_text(encoding='utf-8'))
        self.assertTrue(policy['version_changes_require_explicit_user_request'])

    def test_keyboard_tiles_do_not_paint_background_or_cross_panel(self):
        config=json.loads((ROOT/'locales/zh-CN/image-text.json').read_text(encoding='utf-8'))
        for r in config['images']:
            if 'CONTROLS_KEYBOARD_' in r['resource']:
                self.assertTrue(r['protected_regions'])
                for l in r['labels']:
                    self.assertTrue(l['keep_background'])
                    self.assertLessEqual(l['box'][2],247)
            if 'THATWASYOURLASTBREATH' in r['resource']:
                self.assertEqual(r['labels'][0]['target'],'你已咽下\n最后一口气')

if __name__=='__main__':unittest.main()
