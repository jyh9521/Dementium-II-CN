"""Merge reviewed locale maps onto a freshly extracted, version-locked inventory."""
import argparse
from collections import Counter
import json
from pathlib import Path

from localize import Zar, digest, extract, validate, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('locale', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--identity', type=Path, default=Path('assets/supported-build.json'))
    args = parser.parse_args()
    raw = args.archive.read_bytes()
    identity = json.loads(args.identity.read_text(encoding='utf-8'))
    if digest(raw) != identity['rom_sha256']:
        raise ValueError('Unsupported original archive')
    maps = {}
    for path in sorted(args.locale.glob('*.map.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        if maps.keys() & data.keys():
            raise ValueError('Duplicate translation ID between map files')
        maps.update(data)
    rows = extract(Zar(raw))
    if maps.keys() != {r['id'] for r in rows}:
        raise ValueError('Missing/extra translation IDs')
    for row in rows:
        entry = maps[row['id']]
        if not entry['target']:
            raise ValueError('Empty translation: ' + row['id'])
        row.update(entry)
    validate(rows, extract(Zar(raw)))
    from lint_locale import lint
    violations = lint(rows)
    if violations:
        raise ValueError('Locale style violations: ' + json.dumps(violations,ensure_ascii=False))
    write_json(args.output, rows)
    translated = sum(r['source'] != r['target'] for r in rows)
    report = dict(total=len(rows), translated=translated, preserved=len(rows)-translated,
                  untranslated=sum(not r['target'] for r in rows), status_counts=dict(Counter(r['status'] for r in rows)),
                  review=[dict(id=r['id'],source=r['source'],target=r['target'],notes=r.get('notes','')) for r in rows if 'context' in r['status']],
                  text_types=dict(Counter(r['text_type'] for r in rows)), resources=len({r['resource'] for r in rows}),
                  scope='All inventoried source-locale textual resources; executable and image text are audited separately')
    write_json(args.output.with_name('translation-report.json'), report)
    print('LOCALE records=%d translated=%d preserved=%d empty=0 tokens=PASS' % (len(rows),translated,len(rows)-translated))


if __name__ == '__main__':
    main()
