"""Regression gates for the reported whitespace, long-note and options screenshots."""
import argparse,io,json,re,sys
from pathlib import Path
from PIL import Image
from localize import Zar,extract,TOKEN

def check(path):
 z=Zar(path.read_bytes()); rows=extract(z); meta=json.loads(z.read('FONTS/D2FONT_12X15.JSON')); atlas=Image.open(io.BytesIO(z.read('FONTS/D2FONT_12X15.PNG'))).convert('RGBA')
 texts={r['id']:r['source'] for r in rows}
 missing=set()
 for r in rows:
  for c in TOKEN.sub('',r['source']):
   if c.isspace() or ord(c)<32: continue
   g=meta['glyphs'].get(str(ord(c)))
   if not g or not atlas.crop((g['tx'],g['ty'],g['tx']+g['w'],g['ty']+g['h'])).getchannel('A').getbbox(): missing.add(ord(c))
 note=texts['EN/EXAMINE.504:0000']; tails=[s for s in note.splitlines()[1:] if 0<len(s)<=3]
 dashes=sum('—' in r['source'] for r in rows)
 minimap=(texts['EN/OPTIONSNEW.TBL:0041'],texts['EN/OPTIONSNEW.TBL:0042'])==('半透明','不透明')
 legend=Image.open(io.BytesIO(z.read('TEXTURES/OPTIONS/EN/LEGEND_KEYBOARD_YAXIS.PNG'))).convert('RGBA')
 # Difficulty starts at x=188 in the 428px legend canvas (from supplied 1920px screenshot).
 collision=legend.crop((188,218,207,236)).getchannel('A').getbbox() is not None
 result=not missing and not tails and not dashes and minimap and not collision
 print('TEXT_QA blank_glyphs=%s short_tails=%d em_dash_rows=%d minimap=%s legend_overlap=%s result=%s'%(','.join('U+%04X'%c for c in sorted(missing)) or 'NONE',len(tails),dashes,'PASS' if minimap else 'FAIL',str(collision).upper(),'PASS' if result else 'FAIL'))
 return int(not result)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('archive',type=Path);a=p.parse_args();sys.exit(check(a.archive))
