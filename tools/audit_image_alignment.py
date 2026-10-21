"""Compare every PNG against original, plus reviewed text-frame alignment gates."""
import argparse
import io
import json
from pathlib import Path
from PIL import Image
from localize import Zar, digest, write_json
from image_alignment import measure


def audit(original, modified, config):
    recipes = {row['resource']: row for row in config['images']}
    members, labels, issues = [], [], []
    for name in sorted(original.entries):
        if not name.endswith('.PNG'):
            continue
        a, b = original.read(name), modified.read(name)
        source = Image.open(io.BytesIO(a)).convert('RGBA')
        target = Image.open(io.BytesIO(b)).convert('RGBA')
        status = 'BYTE_IDENTICAL' if a == b else 'FONT_ATLAS' if name.startswith('FONTS/') else 'LOCALIZED_REVIEWED' if name in recipes else 'UNEXPECTED_CHANGE'
        row = dict(resource=name, source_sha256=digest(a), target_sha256=digest(b),
                   source_size=list(source.size), target_size=list(target.size), status=status)
        members.append(row)
        if (source.size != target.size and status != 'FONT_ATLAS') or status == 'UNEXPECTED_CHANGE':
            issues.append(dict(resource=name, reason='Unexpected pixel/dimension change'))
        if name not in recipes:
            continue
        recipe = recipes[name]
        review = recipe.get('alignment_review')
        if not review:
            issues.append(dict(resource=name, reason='Missing original-layout review'))
        for index, label in enumerate(recipe['labels']):
            labels.append(dict(resource=name, label_index=index, source=label['source'], target=label['target'], review=review))
        for rule in recipe.get('ink_alignments', []):
            test = measure(target, rule)
            row.setdefault('alignment', []).append(test)
            if test['result'] != 'PASS':
                issues.append(dict(resource=name, reason='off-center', **test))
        if '/GENERAL/' in name:
            for box in recipe.get('protected_regions', []):
                if target.crop(box).tobytes() != source.crop(box).tobytes():
                    issues.append(dict(resource=name, reason='Original physical icon changed'))
            for label in recipe['labels']:
                rule = dict(label=label['target'], roi=label['box'], frame=label['box'], mask='alpha')
                test = measure(target, rule)
                row.setdefault('alignment', []).append(test)
                if test['result'] != 'PASS':
                    issues.append(dict(resource=name, reason='legend-off-center', **test))
            for clear in recipe.get('clear_regions', []):
                box, label_box = clear['box'], recipe['labels'][0]['box']
                for y in range(box[1], box[3]):
                    for x in range(box[0], box[2]):
                        if not (label_box[0] <= x < label_box[2] and label_box[1] <= y < label_box[3]) and target.getpixel((x,y))[3]:
                            issues.append(dict(resource=name, reason='Residual old English outside label pane'))
                            break
                    else:
                        continue
                    break
        for box in recipe.get('restore_source_regions', []):
            if target.crop(box).tobytes() != source.crop(box).tobytes():
                issues.append(dict(resource=name, reason='Original identity region not restored', box=box))
    return dict(png_count=len(members), localized_images=len(recipes), label_count=len(labels),
                numeric_alignment_checks=sum(len(row.get('alignment', [])) for row in members),
                issues=issues, issue_count=len(issues), result='FAIL' if issues else 'PASS',
                runtime_verified=False, members=members, labels=labels)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=Path('locales/zh-CN/image-text.json'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit(Zar(args.original.read_bytes()), Zar(args.archive.read_bytes()),
                   json.loads(args.config.read_text(encoding='utf-8')))
    write_json(args.output, report)
    print('IMAGE_LAYOUT png=%d localized=%d labels=%d alignment_checks=%d issues=%d result=%s' %
          (report['png_count'], report['localized_images'], report['label_count'],
           report['numeric_alignment_checks'], report['issue_count'], report['result']))
    return int(bool(report['issues']))


if __name__ == '__main__':
    raise SystemExit(main())
