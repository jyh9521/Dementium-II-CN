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
        variant = recipe.get('tone_variant')
        if variant:
            from match_image_variants import transfer
            base_name = variant['base']
            base_source = Image.open(io.BytesIO(original.read(base_name))).convert('RGBA')
            base_target = Image.open(io.BytesIO(modified.read(base_name))).convert('RGBA')
            try:
                expected, variant_report = transfer(base_source, source, base_target, variant['roi'])
                row['tone_variant'] = variant_report
                if expected.tobytes() != target.tobytes():
                    issues.append(dict(resource=name, reason='Paired image geometry or source tone differs'))
            except ValueError as exc:
                issues.append(dict(resource=name, reason='Invalid paired image tones: '+str(exc)))
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
                rule = dict(label=label['target'], roi=label['box'], frame=label['box'], mask='alpha', axes=[1])
                test = measure(target, rule)
                row.setdefault('alignment', []).append(test)
                if test['result'] != 'PASS':
                    issues.append(dict(resource=name, reason='legend-off-center', **test))
                if recipe.get('alignment_review', {}).get('mode') == 'source-icon-gap':
                    pane = recipe['clear_regions'][0]['box']
                    old = source.crop(pane).getchannel('A').getbbox()
                    new = target.crop(pane).getchannel('A').getbbox()
                    if not old or not new or old[0] != new[0]:
                        issues.append(dict(resource=name, reason='Original icon/text gap changed', source_left=None if not old else pane[0]+old[0], target_left=None if not new else pane[0]+new[0]))
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
        if recipe.get('alignment_review', {}).get('mode') == 'source-native-pixel-preservation':
            # Native diagrams are not redrawable art: keys, arrows, connectors,
            # controller geometry, panel borders and alpha stay source-exact.
            regions = [r['box'] for r in recipe.get('clear_regions', [])]
            regions += [l['box'] for l in recipe['labels']]
            outside = sum(source.getpixel((x,y)) != target.getpixel((x,y))
                          for y in range(source.height) for x in range(source.width)
                          if not any(a <= x < c and b <= y < d for a,b,c,d in regions))
            row['outside_text_panes_changed_pixels'] = outside
            if outside:
                issues.append(dict(resource=name, reason='Native source pixels outside text panes changed', count=outside))
            for box in recipe.get('protected_regions', []):
                if source.crop(box).tobytes() != target.crop(box).tobytes():
                    issues.append(dict(resource=name, reason='Native physical input symbol changed', box=box))
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
