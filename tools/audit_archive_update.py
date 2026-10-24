"""Audit an updated source archive without reverting unlocalized game resources."""
import argparse
from pathlib import Path

from localize import Zar, digest, write_json


def compare(previous, current):
    """Describe member changes, including empty members and removed names."""
    rows = []
    for name in sorted(previous.entries.keys() | current.entries.keys()):
        old = previous.read(name) if name in previous.entries else None
        new = current.read(name) if name in current.entries else None
        if old == new:
            continue
        rows.append(dict(resource=name,
                         old_size=None if old is None else len(old),
                         new_size=None if new is None else len(new),
                         old_sha256=None if old is None else digest(old),
                         new_sha256=None if new is None else digest(new)))
    return rows


def audit(previous, current, modified, allowed):
    """Only explicitly approved localization members may differ from new source.

    The derived VFS index may change sizes, but its complete name set and every
    non-localization member remain checked against the updated archive.
    """
    allowed = set(allowed)
    issues = []
    missing = sorted(current.entries.keys() - modified.entries.keys())
    extra = sorted(modified.entries.keys() - current.entries.keys())
    if missing:
        issues.append(dict(reason='Missing updated members', resources=missing))
    if extra:
        issues.append(dict(reason='Unexpected members', resources=extra))
    changed = []
    preserved = 0
    for name in sorted(current.entries.keys() & modified.entries.keys()):
        if current.read(name) == modified.read(name):
            preserved += 1
        else:
            changed.append(name)
            if name not in allowed and name != '~INDEX':
                issues.append(dict(reason='Updated source member was reverted or changed',
                                   resource=name))
    from localize import index_rows
    import struct
    expected_index = bytearray(current.read('~INDEX'))
    for name, size, flags, offset in index_rows(bytes(expected_index)):
        if flags == 0 and name in modified.entries:
            if name in allowed:
                struct.pack_into('<I', expected_index, offset, modified.entries[name].size)
            elif size != modified.entries[name].size:
                issues.append(dict(reason='VFS/ZAR size mismatch', resource=name))
    if '~INDEX' in modified.entries and modified.read('~INDEX') != expected_index:
        issues.append(dict(reason='Unexpected derived VFS index change'))
    return dict(result='FAIL' if issues else 'PASS', issues=issues,
                source_changes=compare(previous, current),
                current_members=len(current.entries), preserved_members=preserved,
                localization_changed_members=changed,
                source_sha256=digest(current.data), modified_sha256=digest(modified.data))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--current', type=Path, required=True)
    parser.add_argument('--modified', type=Path, required=True)
    parser.add_argument('--approved-report', type=Path, required=True,
                        help='Prior audited build-report.json listing localization members')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    import json
    approved = json.loads(args.approved_report.read_text(encoding='utf-8'))['changed_resources']
    result = audit(Zar(args.previous.read_bytes()), Zar(args.current.read_bytes()),
                   Zar(args.modified.read_bytes()), approved)
    write_json(args.output, result)
    print('ARCHIVE_UPDATE source_changes=%d preserved=%d localized=%d issues=%d result=%s' %
          (len(result['source_changes']), result['preserved_members'],
           len(result['localization_changed_members']), len(result['issues']), result['result']))
    return bool(result['issues'])


if __name__ == '__main__':
    raise SystemExit(main())
