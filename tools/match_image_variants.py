"""Keep translated variant geometry identical; transfer a verified source tone ramp.

The input pair must differ only in the reviewed lower lettering region.  The
first localized image supplies every position and pixel outside its light ink;
the second original supplies the color palette, sampled at corresponding source
pixels. No source art, resizing, OCR, or generated glyphs are required.
"""
from collections import Counter
from PIL import ImageChops


def light_ink(pixel, threshold=38):
    r, g, b, a = pixel
    return a > 128 and g >= threshold and r <= 2*g+20 and b >= 25


def transfer(source, variant, localized, roi, *, threshold=38):
    if source.mode != 'RGBA' or variant.mode != 'RGBA' or localized.mode != 'RGBA':
        raise ValueError('Variant inputs must be RGBA')
    if source.size != variant.size or source.size != localized.size:
        raise ValueError('Variant dimensions differ')
    if source.getchannel('A').tobytes() != variant.getchannel('A').tobytes():
        raise ValueError('Original variants differ in alpha')
    difference = ImageChops.difference(source.convert('RGB'), variant.convert('RGB')).getbbox()
    if difference is None:
        raise ValueError('Original variants have no tone difference')
    x0, y0, x1, y1 = roi
    if not (0 <= x0 < x1 <= source.width and 0 <= y0 < y1 <= source.height):
        raise ValueError('Variant ROI outside texture')
    if not (x0 <= difference[0] < difference[2] <= x1 and y0 <= difference[1] < difference[3] <= y1):
        raise ValueError('Original variant changes outside reviewed lettering')
    source_tones = []
    changed_source = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            a, b = source.getpixel((x,y)), variant.getpixel((x,y))
            changed_source += a != b
            if light_ink(a, threshold) and light_ink(b, threshold):
                source_tones.append(b[:3])
    if not source_tones:
        raise ValueError('No source lettering palette')
    # The original second variant changes local bevel/shadow tones as well as
    # color, so RGB nearest-neighbor correspondence creates speckled letters.
    # A luminance-ordered quantile ramp retains each localized glyph's smooth
    # shading while matching the second original's exact palette distribution.
    luminance=lambda c: 2126*c[0]+7152*c[1]+722*c[2]
    source_tones.sort(key=lambda c:(luminance(c),c))
    output, affected, shades = localized.copy(), [], Counter()
    for y in range(y0, y1):
        for x in range(x0, x1):
            pixel = localized.getpixel((x,y))
            if not light_ink(pixel, threshold):
                continue
            affected.append((x,y))
            shades[pixel[:3]]+=1
    if not affected:
        raise ValueError('No localized lettering')
    cache, cumulative = {}, 0
    for rgb,count in sorted(shades.items(),key=lambda item:(luminance(item[0]),item[0])):
        rank=min(len(source_tones)-1, int((cumulative+count/2)*len(source_tones)/len(affected)))
        cache[rgb]=source_tones[rank]
        cumulative+=count
    for p in affected:
        pixel=localized.getpixel(p)
        output.putpixel(p,(*cache[pixel[:3]],pixel[3]))
    # Selection comes from the common first image, never the varying second
    # brightness. Original dark red shadows can legitimately cross a threshold.
    return output, dict(source_difference_box=list(difference), source_changed_pixels=changed_source,
        source_palette_colors=len(set(source_tones)), localized_ink_pixels=len(affected), roi=list(roi),
        geometry='identical', outside_selected_ink='byte-identical', alpha='byte-identical',
        method='paired-source lower-ink palette; luminance-ordered quantiles; no resampling')


def main():
    import argparse
    import copy
    import io
    import json
    from pathlib import Path
    from PIL import Image
    from localize import Zar, digest, write_json
    from art_delta import apply, capture, png
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original',type=Path,required=True)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--source-resource',required=True)
    parser.add_argument('--variant-resource',required=True)
    parser.add_argument('--roi',type=int,nargs=4,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    config=json.loads(args.config.read_text(encoding='utf-8'))
    recipes={r['resource']:r for r in config['images']}
    first_recipe, second_recipe=recipes[args.source_resource],copy.deepcopy(recipes[args.variant_resource])
    zar=Zar(args.original.read_bytes())
    source_raw,variant_raw=zar.read(args.source_resource),zar.read(args.variant_resource)
    if digest(source_raw)!=first_recipe['source_sha256'] or digest(variant_raw)!=second_recipe['source_sha256']:
        raise ValueError('Variant source identity mismatch')
    source=Image.open(io.BytesIO(source_raw)).convert('RGBA')
    variant=Image.open(io.BytesIO(variant_raw)).convert('RGBA')
    common=apply(source,first_recipe['art_delta'])
    result, report=transfer(source,variant,common,args.roi)
    second_recipe['art_delta']=capture(variant,result,resource=args.variant_resource,
        prompt='Share first localized geometry; transfer original second lower-lettering palette in luminance order',regions=[args.roi])
    second_recipe['art_delta']['workflow']='deterministic paired-source lower-ink tone transfer; no resampling; common geometry and background'
    second_recipe['approved_png_sha256']=digest(png(result))
    second_recipe['approved_working_size']=list(result.size)
    second_recipe['ink_alignments']=copy.deepcopy(first_recipe.get('ink_alignments',[]))
    second_recipe['alignment_review']=dict(mode='shared-variant-geometry',
        basis='First localized variant byte-identical outside lower light ink; original second palette luminance distribution',tone_transfer=report)
    args.output.mkdir(parents=True,exist_ok=True)
    write_json(args.output/'recipe-patch.json',dict(images=[second_recipe]))
    write_json(args.output/'verification.json',report)
    common.save(args.output/'localized-first.png');result.save(args.output/'localized-second.png')
    sheet=Image.new('RGBA',(source.width*2,source.height*2),(44,44,44,255))
    for im,xy in ((source,(0,0)),(common,(source.width,0)),(variant,(0,source.height)),(result,source.size)):
        sheet.paste(im,xy)
    sheet.save(args.output/'comparison.png')
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))


if __name__=='__main__':main()
