import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class SignDrRegressionTests(unittest.TestCase):
    def test_dr_translation_and_center_gate_survive_rebuild(self):
        c=json.loads((ROOT/'locales/zh-CN/image-text.json').read_text('utf8'))
        r=next(r for r in c['images'] if r['resource']=='TEX/EN/SIGN_02.PNG')
        label=next(l for l in r['labels'] if l['source']=='D.R.')
        self.assertEqual(label['target'],'死囚区')
        box=label['box']
        for restore in r.get('restore_source_regions',[]):
            self.assertFalse(max(box[0],restore[0])<min(box[2],restore[2]) and max(box[1],restore[1])<min(box[3],restore[3]))
        rule=next(a for a in r['ink_alignments'] if a['label']=='死囚区')
        self.assertEqual(rule['axes'],[0,1]);self.assertLessEqual(rule['tolerance'],.5)
if __name__=='__main__':unittest.main()
