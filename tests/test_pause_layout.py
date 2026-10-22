"""Actual native pause coordinates plus rasterized label/glyph gap regressions."""
import io,json,os,sys,unittest
from pathlib import Path
import pefile
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from localize import Zar
from image_text import build_images
from font_pipeline import resolve_fonts

class PauseLayoutTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.exe=Path(os.environ.get('DEMENTIUM_PAUSE_TEST_EXE',str(ROOT/'build/full-zh-CN/Dementium II.exe')))
  cls.archive=Path(os.environ.get('DEMENTIUM_PAUSE_TEST_ROM',str(ROOT/'build/full-zh-CN/rom.zar')))
  from native_replay import require_native_fixture
  require_native_fixture(cls.exe)
  if not cls.archive.is_file():raise unittest.SkipTest('requires local native archive fixture')
  cls.pe=pefile.PE(str(cls.exe));cls.z=Zar(cls.archive.read_bytes())
 def test_native_value_immediately_follows_colon_and_shares_ink_top(self):
  p=self.pe;code=p.__data__
  self.assertEqual(p.get_data(0x126da7,1),b'\xba');self.assertEqual(p.get_data(0x126dac,1),b'\xb9')
  y=int.from_bytes(p.get_data(0x126da8,4),'little')-24
  x=int.from_bytes(p.get_data(0x126dad,4),'little')-86
  label=Image.open(io.BytesIO(self.z.read('TEXTURES/OPTIONS/EN/LEGEND_KEYBOARD_YAXIS.PNG'))).convert('RGBA')
  labelbox=label.crop((155,218,193,236)).getchannel('A').getbbox()
  label_right=155+labelbox[2]-154;label_top=218+labelbox[1]-24
  meta=json.loads(self.z.read('FONTS/D2FONT_12X15.JSON'))
  atlas=Image.open(io.BytesIO(self.z.read('FONTS/D2FONT_12X15.PNG'))).convert('RGBA')
  glyph=meta['glyphs'][str(ord('普'))]
  bounds=atlas.crop((glyph['tx'],glyph['ty'],glyph['tx']+glyph['w'],glyph['ty']+glyph['h'])).getchannel('A').getbbox()
  self.assertIn(x+bounds[0]-label_right,range(2,5),'status is too far from colon')
  self.assertEqual(y+bounds[1],label_top,'status and label ink tops differ')
 def test_keyboard_back_glyphs_have_a_transparent_column(self):
  im=Image.open(io.BytesIO(self.z.read('TEXTURES/GENERAL/EN/LEGEND_KEYBOARD_BACK.PNG'))).convert('RGBA')
  self.assertTrue(any(im.crop((x,0,x+1,16)).getchannel('A').getbbox() is None for x in range(35,39)),'return glyphs touch')
  source=Zar((ROOT/'build/text-layout-fix/original/rom.zar').read_bytes())
  orig=Image.open(io.BytesIO(source.read('TEXTURES/GENERAL/EN/LEGEND_KEYBOARD_BACK.PNG'))).convert('RGBA')
  self.assertEqual(im.crop((0,0,24,20)).tobytes(),orig.crop((0,0,24,20)).tobytes())
  self.assertIsNone(im.crop((24,0,25,20)).getchannel('A').getbbox(),'Esc touches text')
 def test_pause_patch_source_guards_and_only_two_immediates(self):
  from pause_layout import patch_pause_layout
  data=(ROOT/'build/text-layout-fix/original/Dementium II.exe').read_bytes()
  changed,report=patch_pause_layout(data)
  self.assertEqual(len(data),len(changed));self.assertEqual(sum(a!=b for a,b in zip(data,changed)),2)
  with self.assertRaisesRegex(ValueError,'guard'):patch_pause_layout(changed)

if __name__=='__main__':unittest.main()
