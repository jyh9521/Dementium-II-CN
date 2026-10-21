"""Import explicitly approved manual-review PNGs as source-dependent artwork deltas."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from PIL import Image
from art_delta import capture
from localize import Zar
from image_preservation import validate_configuration


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original',type=Path,required=True)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--apply',action='store_true')
    a=p.parse_args();config=json.loads(a.config.read_text(encoding='utf-8'))
    zar=Zar(a.original.read_bytes());validate_configuration(zar,config)
    expected={r['resource'] for r in config['images']}
    actual={f.relative_to(a.input).as_posix() for f in a.input.rglob('*') if f.is_file() and f.suffix.lower()=='.png'}
    if actual!=expected:raise ValueError('Missing/extra approved PNG paths: '+str(actual^expected))
    rows=[]
    for recipe in config['images']:
        name=recipe['resource'];raw=zar.read(name)
        if hashlib.sha256(raw).hexdigest()!=recipe['source_sha256']:raise ValueError('Original image identity mismatch: '+name)
        original=Image.open(io.BytesIO(raw)).convert('RGBA');edited_path=a.input/name
        edited=Image.open(edited_path).convert('RGBA')
        if abs((edited.width/edited.height)/(original.width/original.height)-1)>.015:raise ValueError('Artwork aspect ratio changed: '+name)
        source_hash=hashlib.sha256(edited_path.read_bytes()).hexdigest()
        resized=edited.resize(original.size,Image.Resampling.LANCZOS)
        recipe['art_delta']=capture(original,resized,resource=name,prompt='User approved the manual-review image set. Exact PNG import and native-size export only; no image generation or added text.')
        recipe['art_delta']['workflow']='user-approved PNG import; native-size export; no generation'
        recipe['approved_png_sha256']=source_hash
        recipe['approved_working_size']=list(edited.size)
        recipe['review']='User confirmed 图片没问题，文本暂时先这样 before requesting the installer'
        if 'YAXIS' in name:recipe['labels']=[dict(source='Y Axis',target='纵轴反转',box=[155,218,207,236])]
        rows.append(dict(resource=name,input_sha256=source_hash,working_size=list(edited.size),native_size=list(original.size)))
    if a.apply:a.config.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    out=Path('build/installer/approved-image-inputs.json');out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('APPROVED_IMAGE_IMPORT images=%d protected_originals=%d applied=%s result=PASS'%(len(rows),len(config.get('preserve_original_images',{})),a.apply))


if __name__=='__main__':main()
