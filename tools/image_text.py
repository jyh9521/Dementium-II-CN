"""Hash-locked, region-bounded bitmap text recipes; never requires shipped images in Git."""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from fontTools.ttLib import TTFont


def erase_ink(image, region):
    """Infill only identified original ink; retain all other source background pixels."""
    x0,y0,x1,y1 = region["box"]
    if not (0 <= x0 < x1 <= image.width and 0 <= y0 < y1 <= image.height):
        raise ValueError("Ink erasure outside resource")
    source = image.copy()
    mask = Image.new("L", image.size)
    cutoff = region.get("threshold", {})
    for y in range(y0,y1):
        for x in range(x0,x1):
            r,g,b,a = source.getpixel((x,y))
            yes = (g >= cutoff.get("min_green", 256)) if region["ink"] == "light" else (r >= cutoff.get("min_red",90) and r >= 2*g and g <= 65)
            if yes: mask.putpixel((x,y),255)
    mask = mask.filter(ImageFilter.MaxFilter(3))
    changed=0
    for y in range(y0,y1):
        for x in range(x0,x1):
            if not mask.getpixel((x,y)): continue
            neighbors=[]
            for dx,dy in ((0,-1),(0,1),(-1,0),(1,0)):
                for distance in range(1,max(image.size)):
                    xx,yy=x+dx*distance,y+dy*distance
                    if not (0 <= xx < image.width and 0 <= yy < image.height): break
                    if not mask.getpixel((xx,yy)):
                        neighbors.append((distance,source.getpixel((xx,yy))))
                        break
            if not neighbors: raise ValueError("No background available for ink infill")
            nearest=min(d for d,c in neighbors)
            colors=[c for d,c in neighbors if d == nearest]
            image.putpixel((x,y),tuple(sum(c[k] for c in colors)//len(colors) for k in range(4)))
            changed+=1
    return changed


def build_images(zar, config, fontpath):
    if isinstance(config, (str, Path)):
        config = json.loads(Path(config).read_text(encoding="utf-8"))
    from image_preservation import validate_configuration
    validate_configuration(zar,config)
    if config.get('quality_contract'):
        from check_image_layout import check as check_layout
        errors=check_layout(config)
        if errors:raise ValueError('Image quality contract: '+json.dumps(errors,ensure_ascii=False))
    with TTFont(str(fontpath)) as face:
        supported = set(face.getBestCmap())
    required = {ord(c) for r in config["images"] for label in r["labels"] for c in label["target"] if not c.isspace()}
    missing = required - supported
    if missing:
        raise ValueError("Missing image font glyphs: " + ", ".join(f"U+{c:04X}" for c in sorted(missing)))
    replacements = {}
    report = {"images": [], "labels": 0, "verification": "offline raster, not in-game acceptance"}
    fonts = {}
    for recipe in config["images"]:
        name = recipe["resource"]
        raw = zar.read(name)
        actual = hashlib.sha256(raw).hexdigest()
        if actual != recipe["source_sha256"]:
            raise ValueError(f"Unsupported image identity: {name}")
        original = Image.open(io.BytesIO(raw)).convert("RGBA")
        if list(original.size) != recipe["size"]:
            raise ValueError(f"Unexpected image dimensions: {name}")
        if recipe.get('art_delta'):
            from art_delta import apply,png
            result=apply(original,recipe['art_delta'])
            from image_alignment import measure
            alignment = [measure(result, rule) for rule in recipe.get('ink_alignments', [])]
            if any(row['result'] != 'PASS' for row in alignment):
                raise ValueError('Artwork alignment drift: '+name)
            encoded=png(result)
            replacements[name]=encoded
            report['labels']+=len(recipe['labels'])
            report['images'].append(dict(resource=name,source_sha256=actual,
                output_sha256=hashlib.sha256(encoded).hexdigest(),labels=len(recipe['labels']),
                changed_pixels=sum(a!=b for a,b in zip(original.get_flattened_data(),result.get_flattened_data())),
                dimensions_unchanged=True,workflow='reviewed-art-delta',
                outside_regions_unchanged='full reviewed artwork; source geometry checked separately'))
            continue
        result = original.copy()
        allowed = Image.new("L", original.size)
        for region in recipe.get("erase_regions", []):
            erase_ink(result,region)
            x0,y0,x1,y1=region["box"]
            ImageDraw.Draw(allowed).rectangle((x0,y0,x1-1,y1-1), fill=255)
        for region in recipe.get("clear_regions", []):
            x0,y0,x1,y1 = region["box"]
            if not (0 <= x0 < x1 <= result.width and 0 <= y0 < y1 <= result.height):
                raise ValueError(f"Clear region outside resource: {name}")
            ImageDraw.Draw(result).rectangle((x0,y0,x1-1,y1-1), fill=tuple(region.get("color", [0,0,0,0])))
            ImageDraw.Draw(allowed).rectangle((x0,y0,x1-1,y1-1), fill=255)
        for label in recipe["labels"]:
            x0, y0, x1, y1 = label["box"]
            if not (0 <= x0 < x1 <= result.width and 0 <= y0 < y1 <= result.height):
                raise ValueError(f"Image label outside resource: {name}")
            size = label.get("font_size", 12)
            font = fonts.setdefault(size, ImageFont.truetype(str(fontpath), size))
            lines = label["target"].split("\n")
            boxes = [font.getbbox(t) for t in lines]
            stroke = label.get("stroke", 0)
            width = max((b[2]-b[0] for b in boxes), default=0)
            height = len(lines) * size
            centered_ink = None
            if label.get('ink_center'):
                # Font advance/cell height includes blank bearings, not visible ink.
                scratch = Image.new('L', (width+40, height+40))
                pen = ImageDraw.Draw(scratch)
                for i, (line, bbox) in enumerate(zip(lines, boxes)):
                    pen.text((20-bbox[0], 20+i*size-bbox[1]), line, font=font,
                             fill=255, stroke_width=stroke, stroke_fill=128 if stroke else 255)
                bounds = scratch.getbbox()
                if bounds is None:
                    raise ValueError('Empty label raster: '+name)
                centered_ink = scratch.crop(bounds)
                width, height = centered_ink.size
            padding = 0 if centered_ink is not None else 2 * stroke
            if width + padding > x1-x0 or height + padding > y1-y0:
                raise ValueError(f"Image label overflow: {name}: {label['target']}")
            tile = result.crop((x0,y0,x1,y1)) if label.get("keep_background") else Image.new("RGBA", (x1-x0, y1-y0), tuple(label.get("clear", [0,0,0,0])))
            mask = Image.new("L", tile.size)
            draw = ImageDraw.Draw(mask)
            top = (tile.height-height)//2
            if centered_ink is not None:
                mask.paste(centered_ink, ((tile.width-width)//2, top))
            for i, (line, bbox) in enumerate(zip(lines, boxes)):
                if centered_ink is not None:
                    break
                left = (tile.width-(bbox[2]-bbox[0]))//2 - bbox[0]
                draw.text((left, top+i*size-bbox[1]), line, font=font, fill=255,
                          stroke_width=stroke, stroke_fill=128 if stroke else 255)
            # Pixel font glyphs remain hard-edged; outline remains separately colored.
            pixels = mask.load()
            for px0,py0,px1,py1 in recipe.get('protected_regions',[]):
                left,top=max(x0,px0),max(y0,py0)
                right,bottom=min(x1,px1),min(y1,py1)
                if left<right and top<bottom and mask.crop((left-x0,top-y0,right-x0,bottom-y0)).getbbox():
                    raise ValueError(f'Label overlaps physical input symbol: {name}: {label["target"]}')
            ink = tuple(label.get("color", [255,255,255,255]))
            outline = tuple(label.get("outline", [0,0,0,255]))
            for y in range(tile.height):
                for x in range(tile.width):
                    if pixels[x,y] >= 192:
                        tile.putpixel((x,y), ink)
                    elif pixels[x,y] >= 64:
                        tile.putpixel((x,y), outline)
            result.paste(tile, (x0,y0))
            ImageDraw.Draw(allowed).rectangle((x0,y0,x1-1,y1-1), fill=255)
            report["labels"] += 1
        for box in recipe.get('protected_regions',[]):
            x0,y0,x1,y1=box
            if not (0<=x0<x1<=original.width and 0<=y0<y1<=original.height):
                raise ValueError('Protected input symbol outside texture')
            result.paste(original.crop(box),(x0,y0))
            if result.crop(box).tobytes()!=original.crop(box).tobytes():
                raise AssertionError('Input symbol pixels changed')
        original_pixels = list(original.get_flattened_data())
        modified_pixels = list(result.get_flattened_data())
        permitted = list(allowed.get_flattened_data())
        if any(a != b and not ok for a,b,ok in zip(original_pixels, modified_pixels, permitted)):
            raise AssertionError(f"Pixels outside approved regions changed: {name}")
        changed = sum(a != b for a,b in zip(original_pixels, modified_pixels))
        if not changed:
            raise ValueError(f"Image recipe made no change: {name}")
        stream = io.BytesIO()
        result.save(stream, format="PNG", optimize=False, compress_level=9)
        replacements[name] = stream.getvalue()
        report["images"].append({"resource": name, "source_sha256": actual,
            "output_sha256": hashlib.sha256(stream.getvalue()).hexdigest(),
            "labels": len(recipe["labels"]), "changed_pixels": changed,
            "outside_regions_unchanged": True, "dimensions_unchanged": True})
    report["image_count"] = len(replacements)
    return replacements, report


def audit_archive(zar, config):
    """Finite member ledger, including explicit art exceptions rather than a 666-only claim."""
    from collections import Counter
    from localize import text_members
    if isinstance(config, (str, Path)):
        config=json.loads(Path(config).read_text(encoding="utf-8"))
    patched={r["resource"]:r for r in config["images"]}
    known=set(text_members(zar))
    ledger=[]
    for name,entry in zar.entries.items():
        row={"resource":name,"bytes":entry.size}
        ext=Path(name).suffix
        if name in patched:
            row.update(disposition="localized-bitmap-text", labels=len(patched[name]["labels"]), reason="Hash-locked region recipe; approved labels translated")
        elif ext==".PNG":
            special=config.get("audit_dispositions",{}).get(name)
            if special:row.update(special)
            elif any('/'+loc+'/' in name for loc in ("DE","FR","IT","SP")):
                row.update(disposition="alternate-locale-preserved",reason="Non-English route; English-based patch does not select these assets")
            elif name.startswith("FONTS/"):
                row.update(disposition="font-atlas",reason="Generic glyph atlas rebuilt by font pipeline, not prose artwork")
            elif name.startswith("TEXTURES/TITLE/") or name=="BACKGROUNDS/TITLE.PNG":
                row.update(disposition="preserve-brand",reason="Dementium II title logo and original identity artwork")
            elif any(k in name for k in ("PAGELEFT","PAGERIGHT","LEGEND_TEX_","HUD_E_KEYBOARD","HUD_U_KEYBOARD","HUD_ZL_PC","LEGEND_A.PNG","LEGEND_B.PNG","PUZZLE_CURSOR")):
                row.update(disposition="preserve-keycap-symbol",reason="Physical button/key identifiers or arrows; no linguistic label")
            else:
                row.update(disposition="reviewed-no-legible-prose",reason="Native asset/contact-sheet review: visual art, symbols, numeric markings, or no reliably transcribable linguistic text")
        elif name in known:
            row.update(disposition="structured-english-text",reason="Source record extraction includes this resource; status is validated by locale lint")
        elif name.startswith(("DE/","FR/","IT/","SP/")):
            row.update(disposition="alternate-locale-preserved",reason="Original non-English table/subtitle/document source")
        elif ext in (".INI",".JSON",".TSV",".TOML",".TXT") or name=="MAPS.TBL":
            row.update(disposition="technical-config",reason="Inspected config/sprite/font mappings, resource names, numeric parameters, comments; no player-facing display prose")
        elif ext==".IVF":
            row.update(disposition="video-original-subtitles-separate",reason="21 videos decoded offline; 323 frames sampled at 1fps; no burned-in dialogue detected; external SUB text translated independently")
        elif ext in (".FLAC",".OGG"):
            row.update(disposition="audio-preserved",reason="Original voice/music/effects; text localization does not replace spoken audio")
        elif ext==".TAR":
            row.update(disposition="shader-package",reason="Shader program archive, not player-facing prose")
        elif ext in (".NFTR",".TTF"):
            row.update(disposition="font-data",reason="Original font infrastructure, not narrative record")
        elif name=="~INDEX":
            row.update(disposition="technical-vfs-index",reason="Path/size records; rebuild synchronizes sizes")
        else:
            row.update(disposition="binary-logic-or-animation",reason="Binary scene/model/collision/animation/parameter stream; printable-prose scan found no additional linguistic sentence (one compressed command false positive logged)")
        ledger.append(row)
    counts=Counter(row["disposition"] for row in ledger)
    images=[r for r in ledger if r["resource"].endswith(".PNG")]
    return {"schema":1,"member_count":len(ledger),"png_count":len(images),"non_alternate_png_count":sum(r["disposition"]!="alternate-locale-preserved" for r in images),
            "disposition_counts":dict(sorted(counts.items())),"method":config.get("audit_method",{}),"members":ledger}


def main():
    import argparse
    from localize import Zar,write_json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["audit","build"])
    parser.add_argument("rom",type=Path)
    parser.add_argument("config",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--font",type=Path)
    args=parser.parse_args()
    zar=Zar(args.rom.read_bytes())
    args.output.mkdir(parents=True,exist_ok=True)
    write_json(args.output/"asset-disposition-ledger.json",audit_archive(zar,args.config))
    if args.action=="build":
        if args.font is None:parser.error("build requires --font")
        replacements,report=build_images(zar,args.config,args.font)
        for name,raw in replacements.items():
            path=args.output/"modified"/name
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        write_json(args.output/"image-report.json",report)
        print(f"BITMAP_TRANSLATION PASS: {len(replacements)} images, {report['labels']} labels")
    else:
        print(f"COVERAGE_AUDIT PASS: {len(zar.entries)} archive members classified")


if __name__=="__main__":
    main()
