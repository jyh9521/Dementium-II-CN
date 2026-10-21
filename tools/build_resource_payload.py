"""Build source-dependent member deltas, independent of container offsets at install."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
from localize import Zar, apply_delta, digest


def make_payload(build, recipe):
    modified = (build/'rom.zar').read_bytes()
    manifest = json.loads((build/'patch.json').read_text())
    original = apply_delta(modified, manifest, True)
    source, target = Zar(original), Zar(modified)
    members = []
    for name in source.entries:
        a, b = source.read(name), target.read(name)
        if a == b or name == '~INDEX':
            continue
        runs = []
        i = 0
        while i < min(len(a), len(b)):
            if a[i] == b[i]:
                i += 1
                continue
            start = i
            while i < min(len(a), len(b)) and a[i] != b[i]:
                i += 1
            runs.append(dict(offset=start, old=a[start:i].hex(), new=b[start:i].hex()))
        members.append(dict(name=name, source_size=len(a), target_size=len(b),
                            source_sha256=digest(a), target_sha256=digest(b), runs=runs,
                            tail=base64.b64encode(b[min(len(a), len(b)):]).decode()))
    config = json.loads(recipe.read_text(encoding='utf-8'))
    return dict(schema=1, members=members,
                literals=[dict(source=e['source'], target=e['target'], capacity=e['slot_size']) for e in config['entries']])


def write_payload(build, recipe, output):
    data = make_payload(build, recipe)
    raw = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if len(raw) > 64*1024*1024:
        raise ValueError('Resource payload too large')
    output.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    return hashlib.sha256(raw).hexdigest()
