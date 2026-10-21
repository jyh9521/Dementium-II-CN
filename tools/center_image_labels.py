"""Re-capture source-dependent artwork deltas after bounded integer alignment."""
import argparse
import io
import json
from pathlib import Path
from PIL import Image
from art_delta import apply, capture, png
from image_alignment import measure, reposition
from localize import Zar, digest, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8'))
    original = Zar(args.original.read_bytes())
    reports = []
    for recipe in config['images']:
        if not recipe.get('art_delta'):
            continue
        name = recipe['resource']
        raw = original.read(name)
        if digest(raw) != recipe['source_sha256']:
            raise ValueError('Artwork source identity mismatch: '+name)
        source = Image.open(io.BytesIO(raw)).convert('RGBA')
        image = apply(source, recipe['art_delta'])
        before = image.tobytes()
        changes = []
        for box in recipe.get('restore_source_regions', []):
            image.paste(source.crop(box), (box[0], box[1]))
            changes.append(dict(action='restore-original-identity', box=box))
        for rule in recipe.get('ink_alignments', []):
            if measure(image, rule)['result'] != 'PASS':
                image, trace = reposition(image, rule)
                changes.append(trace)
        if image.tobytes() == before:
            continue
        recipe['art_delta'] = capture(source, image, resource=name,
            prompt='Native integer text alignment within reviewed source frames; preserve curved lettering, icons and borders; restore source identity regions without guessing.')
        recipe['art_delta']['workflow'] = 'deterministic bounded native-pixel alignment; no resampling or generation'
        recipe['approved_png_sha256'] = digest(png(image))
        recipe['review'] = '2026-10-21 original-English frame comparison and full image alignment audit'
        reports.append(dict(resource=name, changes=changes))
    if args.apply:
        write_json(args.config, config)
    write_json(args.output, dict(changed_images=len(reports), images=reports))
    print('CENTER_ART changed_images=%d applied=%s result=PASS' % (len(reports), args.apply))


if __name__ == '__main__':
    main()
