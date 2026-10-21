"""Regression gates for native panel frames and actual, not box-based, row gaps."""
import argparse
import io
import json
from pathlib import Path
from PIL import Image
from localize import Zar, write_json

PANELS=[[61,14,250,58],[8,63,250,157],[8,162,250,216]]

def audit(source, target, config):
    issues=[]; details=[]
    for r in config['images']:
        name=r['resource']
        if 'CONTROLS_KEYBOARD_' not in name and not any(s in name for s in ['CONTROLS_PC_','CONTROLS_NX_']):continue
        a=Image.open(io.BytesIO(source.read(name))).convert('RGBA')
        b=Image.open(io.BytesIO(target.read(name))).convert('RGBA')
        row={'resource':name}
        if 'CONTROLS_KEYBOARD_' in name:
            changed=[]
            for x0,y0,x1,y1 in PANELS:
                for y in range(y0,y1):
                    for x in range(x0,x1):
                        if x<x0+2 or x>=x1-3 or y<y0+2 or y>=y1-3:
                            if a.getpixel((x,y))!=b.getpixel((x,y)):changed.append((x,y))
            row['frame_changed_pixels']=len(set(changed))
            if changed:issues.append({'resource':name,'reason':'original panel frame overwritten','pixels':len(set(changed))})
        else:
            # Exact visible ink extents, not label-box centers or font advances.
            # Fixed source-diagram lanes also include the OLD text positions.
            # Deriving ROIs from the new recipe would clip baseline row 2 and
            # incorrectly report its touching third row as a one-pixel gap.
            lanes=([52,108,[(162,176),(176,191),(191,205)]] if 'CONTROLS_PC_' in name
                   else [52,124,[(169,183),(183,198),(198,214)]])
            bounds=[]
            for y0,y1 in lanes[2]:
                x0,x1=lanes[:2];box=b.crop([x0,y0,x1,y1]).getchannel('A').getbbox()
                if box:bounds.append([x0+box[0],y0+box[1],x0+box[2],y0+box[3]])
            gaps=[bounds[i+1][1]-bounds[i][3] for i in range(len(bounds)-1)]
            row.update(visible_bounds=bounds,gaps=gaps)
            if len(gaps)!=2 or len(set(gaps))!=1 or min(gaps)<1:
                issues.append({'resource':name,'reason':'unequal visible line gaps','gaps':gaps})
        details.append(row)
    return dict(result='FAIL' if issues else 'PASS',issues=issues,images=details)

def main():
    p=argparse.ArgumentParser();p.add_argument('--original',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();c=json.loads(Path('locales/zh-CN/image-text.json').read_text(encoding='utf-8'))
    r=audit(Zar(a.original.read_bytes()),Zar(a.archive.read_bytes()),c);write_json(a.output,r)
    print('UI_CORRECTION images=%d issues=%d result=%s'%(len(r['images']),len(r['issues']),r['result']))
    for issue in r['issues']:print(json.dumps(issue,ensure_ascii=False))
    return bool(r['issues'])

if __name__=='__main__':raise SystemExit(main())
