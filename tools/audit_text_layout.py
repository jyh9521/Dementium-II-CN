"""Audit every localized resource row and document line against editable data.

This is an offline engineering budget, not a measurement of every runtime pane.
Table/SUB separators and timing prefixes are immutable; short authored headings,
poetry and puzzle rows are not mistaken for generated orphaned wrap fragments.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re

from localize import TOKEN, Zar, extract, write_json
from font_pipeline import glyph_width


def audit(zar, logical, profile):
    from table_extensions import extension_records
    logical = [*logical, *extension_records(profile)]
    actual = {r['id']: r for r in extract(zar)}
    meta = json.loads(zar.read('FONTS/D2FONT_12X15.JSON'))
    ledger, issues = [], []
    for row in logical:
        key = row['id']
        if key not in actual:
            issues.append(dict(id=key, code='missing-record'))
            continue
        entry = actual[key]
        text = entry['source']
        if row.get('extension') and text != row['target']:
            issues.append(dict(id=key, code='extension-text-mismatch'))
        document = '/EXAMINE.' in row['resource']
        kind = ('postcard' if row['resource'] in profile.get('document_layouts', {}) else
                'document' if document else 'subtitle' if row['resource'].endswith('.SUB') else
                'interaction' if row['context'] == 'interaction' else 'table')
        rule = {**profile.get('document_defaults', {}), **(profile.get('document_layouts', {}).get(row['resource']) or profile.get('prose_layouts', {}).get(row['resource']) or {})}
        width = rule.get('width', profile['document_width']) if document else profile['review_width']
        tail_limit = rule.get('min_tail_width', 0)
        lines = re.split(r'[|\r\n]', text.replace('\r\n', '\n').replace('\r', '\n'))
        authored = {TOKEN.sub('', s).strip() for s in re.split(r'[|\r\n]', row['target'])}
        problems = []
        if TOKEN.findall(text) != TOKEN.findall(row['source']):
            problems.append(dict(code='protected-token-sequence'))
        if entry['prefix'] != row['prefix']:
            problems.append(dict(code='subtitle-timing-prefix'))
        if not document and row['context'] != 'interaction' and ('\r' in text or '\n' in text):
            problems.append(dict(code='physical-record-break'))
        for index, line in enumerate(lines):
            pixels = glyph_width(line, meta)
            natural = TOKEN.sub('', line).strip()
            if pixels > width:
                problems.append(dict(code='width', line=index+1, pixels=pixels, limit=width))
            if document and 0 < pixels < tail_limit and natural and natural not in authored:
                problems.append(dict(code='generated-short-tail', line=index+1, pixels=pixels, text=natural))
            if document and line.count('\x02') != line.count('\x01'):
                # Only flag a wrap-introduced split, not intentionally authored spans.
                if not any(line == source for source in row['target'].splitlines()):
                    problems.append(dict(code='split-emphasis', line=index+1))
            if document and index and natural and natural[0] in profile['forbidden_start'] and natural not in authored:
                # An authored ellipsis at paragraph start remains intentional.
                if not (natural.startswith('…') and any(s.lstrip().startswith('…') for s in row['target'].splitlines())):
                    problems.append(dict(code='line-start-punctuation', line=index+1, text=natural))
            if document and natural and natural[-1] in profile['forbidden_end'] and natural not in authored:
                problems.append(dict(code='line-end-punctuation', line=index+1, text=natural))
        if kind == 'postcard':
            rule = profile['document_layouts'][row['resource']]
            height = len(lines)*meta['linefeed']
            if len(lines)>rule['max_visible_lines'] or height>rule['pane_height']:
                problems.append(dict(code='postcard-pane', lines=len(lines), height=height))
        variables = [s for s in TOKEN.findall(text) if s.startswith('$')]
        item = dict(id=key, kind=kind, physical_segments=len(lines), max_width=max(glyph_width(s, meta) for s in lines),
                    width_budget=width, tokens_preserved=TOKEN.findall(text)==TOKEN.findall(row['source']),
                    authored_short_segments=[s for s in lines if document and 0<glyph_width(s,meta)<tail_limit and TOKEN.sub('',s).strip() in authored],
                    variable_expansion='RUNTIME_PENDING' if variables else None, variables=variables, issues=problems)
        ledger.append(item)
        issues.extend(dict(id=key, **p) for p in problems)
    extras = sorted(actual.keys()-{r['id'] for r in logical})
    issues.extend(dict(id=k, code='extra-record') for k in extras)
    return dict(records=len(ledger), resources=len({r['resource'] for r in logical}),
                kinds=dict(Counter(r['kind'] for r in ledger)), issue_count=len(issues),
                affected_rows=len({r['id'] for r in issues}), issues=issues, ledger=ledger,
                variable_rows=sum(bool(r['variables']) for r in ledger), runtime_verified=False,
                geometry='Locale-configured conservative offline budgets; variable width estimate=24px',
                result='FAIL' if issues else 'PASS')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--logical',type=Path,required=True)
    parser.add_argument('--profile',type=Path,default=Path('locales/zh-CN/font-profile.json'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=audit(Zar(args.archive.read_bytes()),json.loads(args.logical.read_text(encoding='utf-8')),
                 json.loads(args.profile.read_text(encoding='utf-8')))
    write_json(args.output,report)
    print('FULL_TEXT_LAYOUT records=%d resources=%d issues=%d affected_rows=%d variable_rows=%d runtime=UNTESTED result=%s' %
          (report['records'],report['resources'],report['issue_count'],report['affected_rows'],report['variable_rows'],report['result']))
    return int(bool(report['issue_count']))


if __name__=='__main__':raise SystemExit(main())
