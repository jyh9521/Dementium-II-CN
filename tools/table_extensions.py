"""Locale-configured append-only table rows for context-specific native references."""


def extension_records(profile):
    records = []
    for spec in profile.get('table_extensions', []):
        for i, text in enumerate(spec['rows'], spec['source_rows']):
            if not text or any(c in text for c in '\r\n\0'):
                raise ValueError('Extension must be one nonempty table row')
            records.append(dict(id=f"{spec['resource']}:{i:04d}", resource=spec['resource'],
                                source=text, target=text, prefix='', context='table row', extension=True))
    return records


def extend_tables(zar, changes, profile):
    result = dict(changes)
    extension_records(profile)  # Validate all rows before writing.
    seen = set()
    for spec in profile.get('table_extensions', []):
        name = spec['resource']
        if name in seen or not name.endswith('.TBL'):
            raise ValueError('Duplicate or non-table extension')
        seen.add(name)
        original = zar.read(name)
        raw = result.get(name, original)
        if len(original.splitlines()) != spec['source_rows'] or len(raw.splitlines()) != spec['source_rows']:
            raise ValueError('Table extension source row count mismatch')
        if not original.endswith(b'\r\n') or not raw.endswith(b'\r\n'):
            raise ValueError('Table extension requires terminal CRLF')
        result[name] = raw + ''.join(text+'\r\n' for text in spec['rows']).encode('utf-8')
    return result
