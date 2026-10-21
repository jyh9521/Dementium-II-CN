"""Reproducible, locale-neutral ZAR1 investigation and text rebuilding tools."""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import struct
import sys


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def filehash(path: Path) -> str:
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


@dataclass(frozen=True)
class Entry:
    name: str
    offset: int
    size: int
    reserved: int
    toc: int


def index_rows(data):
    """VFS ~INDEX: u64 count, records <u32 size,u32 flags,u64 name offset>."""
    if len(data) < 8:
        raise ValueError('Truncated VFS index header')
    count = struct.unpack_from('<Q', data)[0]
    if count > (len(data) - 8) // 16:
        raise ValueError('Truncated VFS index records')
    base = 8 + count * 16
    seen = set()
    for i in range(count):
        offset = 8 + 16 * i
        size, flags, name_offset = struct.unpack_from('<IIQ', data, offset)
        start = base + name_offset
        if not base <= start < len(data):
            raise ValueError('VFS name outside pool')
        end = data.find(b'\0', start)
        if end < 0:
            raise ValueError('Unterminated VFS name')
        name = data[start:end].decode('ascii')
        if not name.startswith('/') or '..' in name.split('/') or '\\' in name or ':' in name:
            raise ValueError('Invalid VFS name')
        key = name.lstrip('/').upper()
        if key in seen:
            raise ValueError('Duplicate VFS name')
        seen.add(key)
        yield key, size, flags, offset


class Zar:
    def __init__(self, data: bytes):
        self.data = data
        if len(data) < 32 or data[:4] != b'ZAR1':
            raise ValueError('Not a ZAR1 archive')
        _, count, self.header_size, reserved, names, strings, toc, tail = struct.unpack_from('<8I', data)
        if not count or reserved != 0 or tail != 0:
            raise ValueError('Unsupported header variant')
        if not (32 <= names <= strings <= toc <= self.header_size <= len(data)):
            raise ValueError('Invalid header table bounds')
        if count > (strings - names) // 4 or count > (self.header_size - toc) // 24:
            raise ValueError('Truncated index')
        self.entries = {}
        previous = ''
        ranges = []
        for i in range(count):
            name_offset = strings + struct.unpack_from('<I', data, names + 4 * i)[0]
            if not strings <= name_offset < toc:
                raise ValueError('Name offset outside string pool')
            end = data.find(b'\0', name_offset, toc)
            if end < 0:
                raise ValueError('Unterminated name')
            name = data[name_offset:end].decode('ascii')
            if not name or name <= previous or '\\' in name or ':' in name or name.startswith('/') or '..' in PurePosixPath(name).parts:
                raise ValueError('Unsafe, duplicate or unsorted member name')
            offset, size, unknown = struct.unpack_from('<QQQ', data, toc + i * 24)
            if offset < self.header_size or offset % 512 or offset + size > len(data):
                raise ValueError('Member bounds/alignment error: ' + name)
            if unknown != 0:
                raise ValueError('Unrecognized member metadata: ' + name)
            self.entries[name] = Entry(name, offset, size, unknown, toc + i * 24)
            ranges.append((offset, offset + size))
            previous = name
        ranges.sort()
        if any(a[1] > b[0] for a, b in zip(ranges, ranges[1:])):
            raise ValueError('Overlapping members')

    def read(self, name):
        e = self.entries[name]
        return self.data[e.offset:e.offset + e.size]

    def rebuild(self, replacements):
        if set(replacements) - self.entries.keys():
            raise ValueError('Unknown replacement member')
        replacements = dict(replacements)
        if '~INDEX' in self.entries:
            original_index = self.read('~INDEX')
            if replacements.get('~INDEX', original_index) != original_index:
                raise ValueError('VFS index is derived; replace its referenced members instead')
            index = bytearray(original_index)
            for name, size, flags, offset in index_rows(original_index):
                if name in self.entries and flags == 0 and size != self.entries[name].size:
                    raise ValueError('Original VFS/ZAR size mismatch: ' + name)
                if name in replacements and len(replacements[name]) != size:
                    if flags != 0 or len(replacements[name]) >= 0x80000000:
                        raise ValueError('Unsupported VFS size/flags: ' + name)
                    struct.pack_into('<I', index, offset, len(replacements[name]))
            if bytes(index) != original_index:
                replacements['~INDEX'] = bytes(index)
        out = bytearray(self.data)
        for name in sorted(replacements):
            payload = replacements[name]
            if payload == self.read(name):
                continue
            e = self.entries[name]
            out.extend(b'\0' * (-len(out) % 512))
            offset = len(out)
            out.extend(payload)
            struct.pack_into('<QQ', out, e.toc, offset, len(payload))
        result = bytes(out)
        parsed = Zar(result)
        for name in self.entries:
            if parsed.read(name) != replacements.get(name, self.read(name)):
                raise ValueError('Rebuild verification failed: ' + name)
        return result


def text_members(zar, source='EN'):
    for name in zar.entries:
        if name.startswith(source.upper() + '/') and (name.endswith(('.TBL', '.SUB')) or '/EXAMINE.' in name):
            yield name


def extract(zar, source='EN'):
    records = []
    for name in text_members(zar, source):
        raw = zar.read(name)
        bom = 3 if raw.startswith(b'\xef\xbb\xbf') else 0
        raw[bom:].decode('utf-8', errors='strict')
        offset = bom
        pieces = [raw[bom:]] if '/EXAMINE.' in name else raw[bom:].splitlines(keepends=True)
        # bytes.splitlines only recognizes CR/LF; control bytes 01/02/03 remain content.
        for line, piece in enumerate(pieces):
            end = b'' if '/EXAMINE.' in name else (b'\r\n' if piece.endswith(b'\r\n') else b'\n' if piece.endswith(b'\n') else b'\r' if piece.endswith(b'\r') else b'')
            body = piece[:-len(end)] if end else piece
            prefix = b''
            if name.endswith('.SUB') and body:
                match = re.match(rb'\{\d+\}\{\d+\}', body)
                if match is None:
                    raise ValueError('Unrecognized subtitle syntax: ' + name)
                prefix = match.group()
                body = body[len(prefix):]
            if body.strip():
                text = body.decode('utf-8')
                records.append({'id': f'{name}:{line:04d}', 'source': text, 'target': '',
                                'source_file': 'rom.zar', 'resource': name, 'line': line,
                                'offset': offset + len(prefix), 'archive_offset': zar.entries[name].offset + offset + len(prefix),
                                'source_bytes': len(body), 'resource_sha256': digest(raw),
                                'context': 'subtitle' if name.endswith('.SUB') else 'document' if '/EXAMINE.' in name else 'table row',
                                'prefix': prefix.decode('ascii'), 'capacity_bytes': None,
                                'duplicate_group': digest(body)[:16], 'status': 'untranslated'})
            offset += len(piece)
    return records


TOKEN = re.compile(r'\$[A-Za-z][^$\r\n]*\$|\$[A-Z]|%[-+0 #]*\d*(?:\.\d+)?[sdifuxX]|\{[^{}]*\}|<[^<>]*>|[\x01-\x08\x0b\x0c\x0e-\x1f]|\|')


def validate(records, originals):
    expected = {r['id']: r for r in originals}
    seen = set()
    for row in records:
        key = row['id']
        if key in seen or key not in expected:
            raise ValueError('Duplicate/unknown ID: ' + key)
        seen.add(key)
        original = expected[key]
        for field in ('source', 'resource', 'line', 'offset', 'archive_offset', 'source_bytes', 'resource_sha256', 'prefix', 'context', 'source_file'):
            if row[field] != original[field]:
                raise ValueError('Stale source/location: ' + key)
        target = row['target']
        if not target:
            continue
        target.encode('utf-8', errors='strict')
        if '\0' in target or '\ufeff' in target:
            raise ValueError('Illegal character: ' + key)
        if not '/EXAMINE.' in row['resource'] and ('\n' in target or '\r' in target):
            raise ValueError('Table/subtitle row count change: ' + key)
        if TOKEN.findall(row['source']) != TOKEN.findall(target):
            raise ValueError('Protected token mismatch: ' + key)
        if '/ALPHA' in row['resource'] and target != row['source']:
            raise ValueError('Puzzle strings need separate logic/texture investigation: ' + key)
    if seen != expected.keys():
        raise ValueError('Missing source records')


def import_text(zar, records, source='EN'):
    validate(records, extract(zar, source))
    changes = {}
    for row in records:
        if row['target'] and row['target'] != row['source']:
            changes.setdefault(row['resource'], []).append(row)
    result = {}
    for name, rows in changes.items():
        raw = zar.read(name)
        for row in sorted(rows, key=lambda r: r['offset'], reverse=True):
            start = row['offset']
            raw = raw[:start] + row['target'].encode('utf-8') + raw[start + row['source_bytes']:]
        result[name] = raw
    return result


def build_font(zar, records, fontpath):
    from PIL import Image, ImageDraw, ImageFont
    from fontTools.ttLib import TTFont
    required = sorted({ord(c) for row in records if row['target'] for c in row['target'] if ord(c) >= 32 and c != '\ufeff'})
    name = 'FONTS/D2FONT_12X15'
    meta = json.loads(zar.read(name + '.JSON'))
    missing = [c for c in required if str(c) not in meta['glyphs']]
    if not missing:
        return {}, {'added_glyphs': 0}
    cmap = TTFont(fontpath).getBestCmap()
    unsupported = [c for c in missing if c not in cmap or c > 65535]
    if unsupported:
        raise ValueError('Font coverage missing: ' + repr(unsupported))
    old = Image.open(io.BytesIO(zar.read(name + '.PNG'))).convert('RGBA')
    cols = old.width // 14
    height = old.height + ((len(missing) + cols - 1) // cols) * 17 + 2
    if height > 4096:
        raise ValueError('Font atlas exceeds conservative 4096px budget')
    atlas = Image.new('RGBA', (old.width, height))
    atlas.paste(old, (0, 0))
    font = ImageFont.truetype(str(fontpath), 12)
    for i, c in enumerate(missing):
        x, y = (i % cols) * 14 + 1, old.height + (i // cols) * 17 + 1
        glyph = Image.new('RGBA', (12, 15))
        gd = ImageDraw.Draw(glyph)
        bounds = font.getbbox(chr(c))
        if bounds[2] > 12 or bounds[0] < 0 or bounds[3] - bounds[1] > 14:
            raise ValueError('Glyph does not fit the experimental cell: U+%04X' % c)
        gd.text((0, 1 - bounds[1]), chr(c), font=font, fill=(255, 255, 255, 255))
        atlas.paste(glyph, (x, y))
        meta['glyphs'][str(c)] = {'w': 12, 'h': 15, 'logw': 12, 'xo': 0, 'yo': 0, 'tx': x, 'ty': y}
    buf = io.BytesIO()
    atlas.save(buf, format='PNG', optimize=False)
    return {name + '.JSON': (json.dumps(meta, ensure_ascii=False, indent=2) + '\n').encode(), name + '.PNG': buf.getvalue()}, {
        'added_glyphs': len(missing), 'atlas_size': [atlas.width, atlas.height], 'font_sha256': filehash(fontpath),
        'codepoints': missing, 'runtime_verified': False}


def make_delta(original, modified):
    if len(modified) < len(original):
        raise ValueError('Delta requires append-preserving rebuild')
    runs = []
    i = 0
    while i < len(original):
        if original[i:i + 65536] == modified[i:i + 65536]:
            i += 65536
            continue
        if original[i] == modified[i]:
            i += 1
            continue
        start = i
        while i < len(original) and original[i] != modified[i]:
            i += 1
        runs.append({'offset': start, 'old': original[start:i].hex(), 'new': modified[start:i].hex()})
    return {'format': 'zar-sparse-delta-v1', 'original_size': len(original), 'modified_size': len(modified),
            'original_sha256': digest(original), 'modified_sha256': digest(modified), 'runs': runs,
            'append': base64.b64encode(modified[len(original):]).decode('ascii')}


def apply_delta(data, patch, reverse=False):
    if patch['format'] != 'zar-sparse-delta-v1':
        raise ValueError('Unsupported delta format')
    tag = 'modified' if reverse else 'original'
    if len(data) != patch[tag + '_size'] or digest(data) != patch[tag + '_sha256']:
        raise ValueError('Version/hash mismatch')
    out = bytearray(data)
    for run in patch['runs']:
        a, b = bytes.fromhex(run['old']), bytes.fromhex(run['new'])
        if reverse:
            a, b = b, a
        o = run['offset']
        if len(a) != len(b) or o < 0 or o + len(a) > patch['original_size'] or out[o:o + len(a)] != a:
            raise ValueError('Invalid delta run')
        out[o:o + len(a)] = b
    if reverse:
        del out[patch['original_size']:]
    else:
        out.extend(base64.b64decode(patch['append'], validate=True))
    result = bytes(out)
    tag = 'original' if reverse else 'modified'
    if len(result) != patch[tag + '_size'] or digest(result) != patch[tag + '_sha256']:
        raise ValueError('Delta result hash mismatch')
    Zar(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('scan'); p.add_argument('game', type=Path); p.add_argument('output', type=Path)
    p = sub.add_parser('extract'); p.add_argument('archive', type=Path); p.add_argument('output', type=Path); p.add_argument('--source', default='EN')
    p = sub.add_parser('build'); p.add_argument('archive', type=Path); p.add_argument('translation', type=Path); p.add_argument('output', type=Path); p.add_argument('--font', type=Path); p.add_argument('--profile', type=Path); p.add_argument('--identity', type=Path, required=True)
    p = sub.add_parser('patch'); p.add_argument('input', type=Path); p.add_argument('delta', type=Path); p.add_argument('output', type=Path); p.add_argument('--reverse', action='store_true')
    args = parser.parse_args()
    if args.command == 'scan':
        import pefile
        manifest = []
        for path in sorted(args.game.rglob('*')):
            if not path.is_file():
                continue
            raw = path.read_bytes()
            item = {'path': path.relative_to(args.game).as_posix(), 'size': len(raw), 'sha256': digest(raw), 'magic_hex': raw[:32].hex()}
            if raw.startswith(b'MZ'):
                pe = pefile.PE(data=raw)
                item['pe'] = {'machine': hex(pe.FILE_HEADER.Machine), 'timestamp': pe.FILE_HEADER.TimeDateStamp,
                              'linker': [pe.OPTIONAL_HEADER.MajorLinkerVersion, pe.OPTIONAL_HEADER.MinorLinkerVersion],
                              'sections': [s.Name.rstrip(b'\0').decode() for s in pe.sections],
                              'imports': {d.dll.decode(): [x.name.decode() if x.name else x.ordinal for x in d.imports] for d in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', [])}}
                candidates = []
                for pattern, encoding in [(rb'[ -~]{5,}', 'ascii'), (rb'(?:[ -~]\x00){5,}', 'utf-16le')]:
                    for m in re.finditer(pattern, raw):
                        candidates.append({'offset': m.start(), 'encoding': encoding, 'text': m.group().decode(encoding), 'classification': 'candidate-not-approved'})
                write_json(args.output / (path.name + '.strings.json'), candidates)
            manifest.append(item)
        archive = Zar((args.game / 'rom.zar').read_bytes())
        entries = [dict(name=e.name, offset=e.offset, size=e.size, reserved=e.reserved, sha256=digest(archive.read(e.name)), magic_hex=archive.read(e.name)[:16].hex()) for e in archive.entries.values()]
        write_json(args.output / 'game-manifest.json', {'appid': 5342930, 'files': manifest})
        write_json(args.output / 'archive-manifest.json', entries)
        print(f'SCAN files={len(manifest)} archive_members={len(entries)}')
    elif args.command == 'extract':
        records = extract(Zar(args.archive.read_bytes()), args.source)
        write_json(args.output, records)
        print(f'EXTRACT records={len(records)} resources={len({r["resource"] for r in records})} duplicates={len(records)-len({r["source"] for r in records})}')
    elif args.command == 'build':
        data = args.archive.read_bytes()
        identity = json.loads(args.identity.read_text(encoding='utf-8'))
        if digest(data) != identity['rom_sha256'] or len(data) != identity['rom_size']:
            raise ValueError('Unsupported original archive')
        zar = Zar(data)
        records = json.loads(args.translation.read_text(encoding='utf-8'))
        validate(records, extract(zar))
        logical_records = records
        if args.font and args.profile:
            raise ValueError('Use --font or --profile, not both')
        mixed_fonts = {}
        if args.profile:
            from font_pipeline import build_mixed
            profile = json.loads(args.profile.read_text(encoding='utf-8'))
            mixed_fonts, records, mixed_info = build_mixed(zar, records, profile)
        changes = import_text(zar, records)
        info = {'added_glyphs': 0}
        if args.profile:
            changes.update(mixed_fonts)
            info = mixed_info
        elif args.font:
            fonts, info = build_font(zar, records, args.font)
            changes.update(fonts)
        else:
            supported = json.loads(zar.read('FONTS/D2FONT_12X15.JSON'))['glyphs']
            if any(str(ord(c)) not in supported for row in records for c in row['target'] if ord(c) >= 32):
                raise ValueError('Missing glyphs; supply --font')
        out = zar.rebuild(changes)
        again = {r['id']: r for r in extract(Zar(out))}
        for row in records:
            if again[row['id']]['source'] != (row['target'] or row['source']):
                raise ValueError('Text re-extraction mismatch: ' + row['id'])
        args.output.mkdir(parents=True, exist_ok=True)
        target = args.output / 'rom.zar'
        if target.resolve() == args.archive.resolve():
            raise ValueError('Output must not be the original')
        # Incremental builds avoid rewriting identical archive output.
        if not target.exists() or filehash(target) != digest(out):
            target.write_bytes(out)
        write_json(args.output / 'patch.json', make_delta(data, out))
        if args.profile:
            from font_pipeline import render_previews
            render_previews(Zar(out), args.output, profile, info)
            write_json(args.output / 'runtime-text.json', records)
            write_json(args.output / 'font-report.json', info)
        parsed_output = Zar(out)
        actual_changes = [name for name in zar.entries if zar.read(name) != parsed_output.read(name)]
        count = sum(bool(r['target']) and r['target'] != r['source'] for r in logical_records)
        write_json(args.output / 'build-report.json', {'changed_resources': actual_changes, 'translated': count, 'total': len(records), 'font': info, 'original_sha256': digest(data), 'modified_sha256': digest(out), 'runtime_verified': False})
        print(f'BUILD translated={count} total={len(records)} changed_resources={len(actual_changes)} added_glyphs={info["added_glyphs"]} reextract=PASS')
    elif args.command == 'patch':
        if args.input.resolve() == args.output.resolve():
            raise ValueError('Use a separate output path')
        result = apply_delta(args.input.read_bytes(), json.loads(args.delta.read_text(encoding='utf-8')), args.reverse)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(result)
        print(('ROLLBACK' if args.reverse else 'PATCH') + ' sha256=' + digest(result) + ' result=PASS')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, UnicodeError, struct.error) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(2)
