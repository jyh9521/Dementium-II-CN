"""Audit every fallback against body-size raster and shared typographic baseline."""
import argparse, io, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from font_pipeline import resolve_fonts
from localize import Zar, write_json

ROOT = Path(__file__).resolve().parents[1]

def audit(archive, report, logical, output, legacy=False):
    profile = json.loads((ROOT/'locales/zh-CN/font-profile.json').read_text('utf8'))
    info = json.loads(report.read_text('utf8'))
    records = json.loads(logical.read_text('utf8'))
    paths = resolve_fonts(profile)
    with TTFont(paths['body']) as font:
        coverage = set(font.getBestCmap())
    required = {ord(c) for r in records for c in (r['target'] or r['source']) if ord(c)>=0x3000}
    required |= {ord(c) for group in profile['previews'].values() for t in group for c in t if ord(c)>=0x3000}
    required |= {ord(c) for t in profile.get('extra_texts', []) for c in t if ord(c)>=0x3000}
    codes = sorted(set(info['body_fallback_codes']))
    assert set(codes) == required-coverage, 'Fallback inventory differs from independently scanned required CJK'
    size = profile['fonts']['body']['pixel_size']
    body = ImageFont.truetype(str(paths['body']),size)
    fallback = ImageFont.truetype(str(paths['title']),size)
    shift = body.getmetrics()[0]-fallback.getmetrics()[0]
    z = Zar(archive.read_bytes())
    meta = json.loads(z.read('FONTS/D2FONT_12X15.JSON'))
    atlas = Image.open(io.BytesIO(z.read('FONTS/D2FONT_12X15.PNG'))).convert('RGBA')
    inventory=[]; issues=[]
    for code in codes:
        c=chr(code); g=meta['glyphs'][str(code)]
        actual=atlas.crop((g['tx'],g['ty'],g['tx']+g['w'],g['ty']+g['h'])).getchannel('A')
        expected=Image.new('L',(size,15))
        ImageDraw.Draw(expected).text((0,shift),c,font=fallback,fill=255)
        expected=expected.point(lambda a:255 if a>=128 else 0)
        normalized=(g['w'],g['h'],g['logw'],g['yo'],g['xo'])==(size,15,round(fallback.getlength(c)),0,0) and actual.tobytes()==expected.tobytes()
        if legacy:
            old=Image.new('L',(16,16))
            ImageDraw.Draw(old).text((0,0),c,font=ImageFont.truetype(str(paths['title']),16),fill=255)
            old=old.point(lambda a:255 if a>=128 else 0)
            valid=(g['w'],g['h'],g['logw'],g['yo'])==(16,16,16,-2) and actual.tobytes()==old.tobytes()
        else:
            valid=normalized and expected.getbbox() is not None
        if not valid:issues.append(c)
        inventory.append(dict(character=c,code='U+%04X'%code,metrics=g,normalized=normalized,ink_bbox=actual.getbbox(),source_ascent=fallback.getmetrics()[0],body_ascent=body.getmetrics()[0],raster_shift=shift,records=[r['id'] for r in records if c in (r['target'] or r['source'])]))
    output.parent.mkdir(parents=True,exist_ok=True)
    write_json(output,dict(fallbacks=inventory,required_cjk=len(required),fallback_count=len(codes),issues=issues,legacy=legacy,game_launch='NEVER'))
    # Actual atlas crops, not substitutes from system fonts.
    samples=['她力量强大，却永远饥肠辘辘，','尽量减少肘部、骶部及臀部的压疮。']
    canvas=Image.new('RGBA',(360,76),(24,24,24,255))
    for row,text in enumerate(samples):
        x=8
        for c in text:
            g=meta['glyphs'].get(str(ord(c)))
            if not g:continue
            im=atlas.crop((g['tx'],g['ty'],g['tx']+g['w'],g['ty']+g['h']))
            canvas.alpha_composite(im,(x+g['xo'],8+row*30+g['yo']));x+=g['logw']+1
    canvas.resize((1080,228),Image.Resampling.NEAREST).save(output.with_suffix('.png'))
    assert not issues, 'Fallback size/baseline/pixel mismatch: '+repr(issues)
    line='BODY_FALLBACK count=%d chars=%s size=%s baseline=%s inventory=PASS raster=PASS result=PASS'%(len(codes),','.join(chr(c) for c in codes),'16' if legacy else str(size),'yo=-2' if legacy else 'body')
    print(line)
    return line

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True);p.add_argument('--report',type=Path,required=True)
    p.add_argument('--logical',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--legacy',action='store_true');a=p.parse_args()
    audit(a.archive,a.report,a.logical,a.output,a.legacy)
if __name__=='__main__':main()
