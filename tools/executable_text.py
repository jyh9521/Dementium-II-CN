"""Version-locked, reversible UTF-8 literal replacement in PE .rdata only.

Does not execute the input, relocate code, alter PE structures, or grow files.
Recipes describe independently audited NUL-padded slots, never inferred capacity.
"""
import hashlib
import struct


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _rdata(data):
    try:
        if data[:2] != b'MZ':
            raise ValueError('Not a DOS/PE image')
        pe = struct.unpack_from('<I', data, 60)[0]
        if data[pe:pe+4] != b'PE\0\0':
            raise ValueError('Missing PE signature')
        count = struct.unpack_from('<H', data, pe+6)[0]
        optional = struct.unpack_from('<H', data, pe+20)[0]
        base = pe+24+optional
        found = []
        for i in range(count):
            pos = base+40*i
            name = data[pos:pos+8].rstrip(b'\0')
            size, offset = struct.unpack_from('<II', data, pos+16)
            flags = struct.unpack_from('<I', data, pos+36)[0]
            if offset+size > len(data):
                raise ValueError('Section exceeds image')
            if name == b'.rdata':
                if flags & 0x20000000 or flags & 0x80000000:
                    raise ValueError('Refuse writable/executable .rdata')
                found.append((offset, offset+size))
        if len(found) != 1:
            raise ValueError('Expected exactly one .rdata section')
        return found[0]
    except (struct.error, IndexError) as exc:
        raise ValueError('Truncated PE structure') from exc


def _ranges(data, changes):
    lo, hi = _rdata(data)
    end = lo
    for change in sorted(changes, key=lambda x: x['offset']):
        offset = change['offset']
        old, new = bytes.fromhex(change['old']), bytes.fromhex(change['new'])
        if not old or len(old) != len(new):
            raise ValueError('Patch run must retain nonzero byte length')
        if not isinstance(offset, int) or offset < end or offset+len(old) > hi:
            raise ValueError('Overlapping or non-.rdata patch run')
        end = offset+len(old)
        yield offset, old, new


def build_executable(data, recipe):
    """Return modified bytes and JSON-serializable exact-byte patch manifest."""
    if recipe.get('schema') != 1 or recipe.get('encoding') != 'utf-8':
        raise ValueError('Unsupported executable text recipe')
    if len(data) != recipe['source_size'] or _sha(data) != recipe['source_sha256']:
        raise ValueError('Unsupported executable identity')
    changes = []
    for entry in sorted(recipe['entries'], key=lambda item: item['offset']):
        offset, capacity = entry['offset'], entry['slot_size']
        source = entry['source'].encode('utf-8')
        target = entry['target'].encode('utf-8')
        if b'\0' in source or b'\0' in target or not target:
            raise ValueError('Literal must be nonempty and NUL-free')
        if capacity < len(source)+1 or capacity < len(target)+1:
            raise ValueError('UTF-8 literal exceeds audited NUL-padded slot')
        old = source + b'\0' * (capacity-len(source))
        new = target + b'\0' * (capacity-len(target))
        if data[offset:offset+capacity] != old:
            raise ValueError('Literal/source zero-padding guard mismatch')
        changes.append(dict(id=entry['id'], offset=offset, old=old.hex(), new=new.hex()))
    out = bytearray(data)
    for offset, old, new in _ranges(data, changes):
        out[offset:offset+len(old)] = new
    modified = bytes(out)
    patch = dict(schema=1, format='fixed-slot-utf8-v1',
                 original_size=len(data), modified_size=len(modified),
                 original_sha256=_sha(data), modified_sha256=_sha(modified), runs=changes)
    return modified, patch


def apply_executable_patch(data, patch, reverse=False):
    """Apply only to the exact recorded before/after identity; reject all drift."""
    if patch.get('schema') != 1 or patch.get('format') != 'fixed-slot-utf8-v1':
        raise ValueError('Unsupported executable patch manifest')
    before = patch['modified_sha256'] if reverse else patch['original_sha256']
    after = patch['original_sha256'] if reverse else patch['modified_sha256']
    if patch['original_size'] != patch['modified_size']:
        raise ValueError('Executable patch must retain file size')
    if len(data) != patch['original_size'] or _sha(data) != before:
        raise ValueError('Executable patch input hash/size mismatch')
    out = bytearray(data)
    for offset, old, new in _ranges(data, patch['runs']):
        expected, replacement = (new, old) if reverse else (old, new)
        if data[offset:offset+len(expected)] != expected:
            raise ValueError('Executable patch byte guard mismatch')
        out[offset:offset+len(expected)] = replacement
    out = bytes(out)
    if _sha(out) != after:
        raise ValueError('Executable patch output hash mismatch')
    return out
