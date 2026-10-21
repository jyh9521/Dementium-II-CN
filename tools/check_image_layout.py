"""Reject unreviewed scene overlays, omitted Y-axis text and overlapping UI boxes."""
import argparse
import json
from pathlib import Path


def check(config):
    errors=[]
    for r in config['images']:
        name=r['resource']
        if name.startswith('TEX/') and not r.get('art_delta'):
            errors.append(name+': scene-art-is-font-overlay')
        if 'YAXIS' in name and not any('Y Axis' in l['source'] and '纵轴' in l['target'] for l in r['labels']):
            errors.append(name+': untranslated-Y-Axis')
        if 'CONTROLS_' not in name:continue
        labels=r['labels']
        for i,a in enumerate(labels):
            x0,y0,x1,y1=a['box']
            if not (0<=x0<x1<=r['size'][0] and 0<=y0<y1<=r['size'][1]):
                errors.append(name+': outside-texture')
            for b in labels[i+1:]:
                u0,v0,u1,v1=b['box']
                if max(x0,u0)<min(x1,u1) and max(y0,v0)<min(y1,v1):
                    errors.append(name+': overlapping-labels '+a['target']+' / '+b['target'])
    return errors


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('config',type=Path)
    p.add_argument('--output',type=Path);a=p.parse_args()
    config=json.loads(a.config.read_text(encoding='utf-8'));errors=check(config)
    report=dict(images=len(config['images']),violations=errors,result='FAIL' if errors else 'PASS')
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return bool(errors)


if __name__=='__main__':raise SystemExit(main())
