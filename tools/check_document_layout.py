"""Offline replay of the verified 256x72 bottom-aligned examination text pane.

This produces a diagnostic, never a purported in-game screenshot. The pane
geometry comes from FUN_14011a6f0 and the centered 256x192 reference UI.
"""
import argparse
import io
import json
from pathlib import Path
import re

from localize import TOKEN, Zar, extract, write_json
from font_pipeline import glyph_width


def replay(archive, resource='EN/EXAMINE.041'):
    from PIL import Image, ImageChops, ImageDraw
    zar = Zar(archive.read_bytes())
    text = next(r['source'] for r in extract(zar) if r['resource']==resource)
    meta = json.loads(zar.read('FONTS/D2FONT_12X15.JSON'))
    atlas = Image.open(io.BytesIO(zar.read('FONTS/D2FONT_12X15.PNG'))).convert('RGBA')
    background = Image.open(io.BytesIO(zar.read('BACKGROUNDS/EXAMINE041.PNG'))).convert('RGBA')
    # Ignore transparent or black padding when bounding the illustration.
    red,green,blue,alpha = background.split()
    light = ImageChops.lighter(ImageChops.lighter(red,green),blue).point(lambda p:255 if p>48 else 0)
    light = ImageChops.multiply(light,alpha.point(lambda p:255 if p>128 else 0))
    picture = light.getbbox()
    assert picture is not None
    offset_x,offset_y = (background.width-256)//2, (background.height-192)//2
    pane_top, pane_bottom = offset_y+104,offset_y+176
    lines = text.replace('\r\n','\n').replace('\r','\n').split('\n')
    origin_y = pane_bottom - len(lines)*meta['linefeed']
    ink = Image.new('RGBA', background.size)
    for index,line in enumerate(lines):
        if '$' in line:
            raise ValueError('Replay requires resolved variables')
        x = offset_x + ((256-glyph_width(line,meta))>>1)
        y = origin_y + index*meta['linefeed']
        for char in TOKEN.sub('',line):
            glyph = meta['glyphs'][str(ord(char))]
            region = atlas.crop((glyph['tx'],glyph['ty'],glyph['tx']+glyph['w'],glyph['ty']+glyph['h']))
            ink.alpha_composite(region,(x+glyph['xo'],y+glyph['yo']))
            x += glyph['logw']+1
    bounds = ink.getchannel('A').getbbox()
    assert bounds is not None
    overlap = bounds[0]<picture[2] and picture[0]<bounds[2] and bounds[1]<picture[3] and picture[1]<bounds[3]
    within = pane_top<=bounds[1] and bounds[3]<=pane_bottom
    result = dict(resource=resource,measured_lines=len(lines),picture_bounds=list(picture),text_ink_bounds=list(bounds),
                  pane=[offset_x,pane_top,offset_x+256,pane_bottom],overlap=overlap,within_pane=within,
                  clearance=bounds[1]-picture[3],runtime_verified=False)
    preview = Image.new('RGBA',(background.width,background.height+20),(18,18,18,255))
    preview.alpha_composite(background)
    shadow = Image.new('RGBA',ink.size,(0,0,0,255));shadow.putalpha(ink.getchannel('A'))
    preview.alpha_composite(shadow,(1,1));preview.alpha_composite(ink)
    ImageDraw.Draw(preview).text((6,background.height+3),'OFFLINE LAYOUT REPLAY - NOT A GAME SCREENSHOT',fill='white')
    return result,preview


def main():
    from PIL import Image
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result,preview=replay(args.archive)
    args.output.mkdir(parents=True,exist_ok=True)
    write_json(args.output/'layout.json',result)
    preview.resize((preview.width*3,preview.height*3),Image.Resampling.NEAREST).save(args.output/'layout-preview.png')
    passed=not result['overlap'] and result['within_pane']
    print('POSTCARD lines=%d overlap=%s within_pane=%s clearance=%dpx game_launch=NEVER result=%s' %
          (result['measured_lines'],str(result['overlap']).upper(),str(result['within_pane']).upper(),result['clearance'],'PASS' if passed else 'FAIL'))
    return 0 if passed else 1


if __name__=='__main__':
    raise SystemExit(main())
