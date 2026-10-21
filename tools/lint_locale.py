"""Locale-configurable text classification and punctuation checks.

Returns structured diagnostics; this module never rewrites translation data.
The default terminal periods implement the current locale's editorial policy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import unicodedata

from localize import TOKEN


def lint(records, config=None):
    """Return ``[{id, code, message}, ...]`` for editorial violations.

    Optional keys: allowed_text_types, terminal_periods, segment_separator,
    require_preservation_note. Protected tokens never count as punctuation.
    Narrative text may freely use sentence periods. UI text with interior
    natural-language punctuation may keep its terminal period.
    """
    options = {
        'allowed_text_types': ('ui', 'narrative', 'preserved'),
        'terminal_periods': ('。', '.'),
        'segment_separator': '|',
        'require_preservation_note': True,
    }
    options.update(config or {})
    separator = options['segment_separator']
    if not isinstance(separator, str) or not separator:
        raise ValueError('segment_separator must be a nonempty string')
    periods = tuple(options['terminal_periods'])
    if not periods or any(not isinstance(p, str) or len(p) != 1 for p in periods):
        raise ValueError('terminal_periods must contain single characters')
    violations = []

    def add(row, code, message):
        violations.append({'id': row.get('id', '<missing>'), 'code': code, 'message': message})

    for row in records:
        kind = row.get('text_type')
        if kind not in options['allowed_text_types']:
            add(row, 'text-type', 'Missing or unsupported text_type')
            continue
        target = row.get('target')
        if not isinstance(target, str):
            add(row, 'target-type', 'target must be a string')
            continue
        if kind == 'preserved':
            if options['require_preservation_note'] and not str(row.get('notes', '')).strip():
                add(row, 'preservation-note', 'Preserved text requires a reason in notes')
            continue
        if kind != 'ui':
            continue
        # A delimiter inside $Lock,1$ or a markup token is not a display split.
        natural = TOKEN.sub(lambda match: separator if match.group() == separator else '', target)
        for index, segment in enumerate(natural.split(separator)):
            segment = segment.strip()
            if not segment or not segment.endswith(periods):
                continue
            interior = segment[:-1]
            if not any(unicodedata.category(char).startswith('P') for char in interior):
                add(row, 'ui-terminal-period',
                    f'UI segment {index + 1} has no internal punctuation; remove its terminal period')
    return violations


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('records', type=Path)
    parser.add_argument('--config', type=Path)
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding='utf-8')) if args.config else None
    issues = lint(json.loads(args.records.read_text(encoding='utf-8')), config)
    print(json.dumps({'violations': issues, 'count': len(issues)}, ensure_ascii=False, indent=2))
    return int(bool(issues))


if __name__ == '__main__':
    raise SystemExit(main())
