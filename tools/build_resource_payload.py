"""Build source-dependent member deltas, independent of container offsets at install."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
from localize import Zar, apply_delta, digest


def native_executable_payload(build, patch, identity):
    """An executable-code payload is exact-version locked, unlike member deltas."""
    if patch.get('format')!='native-menu-pe-v1':
        raise ValueError('Unsupported native executable patch')
    if (patch['original_size'],patch['original_sha256']) != (identity['exe_size'],identity['exe_sha256']):
        raise ValueError('Native menu source differs from supported executable identity')
    data=(build/'Dementium II.exe').read_bytes()
    if len(data)!=patch['modified_size'] or digest(data)!=patch['modified_sha256']:
        raise ValueError('Native menu executable output mismatch')
    tail=base64.b64decode(patch['append'],validate=True)
    if data[patch['original_size']:]!=tail:
        raise ValueError('Native menu appended section mismatch')
    restored=bytearray(data[:patch['original_size']]);end=0
    for run in patch['runs']:
        old,new=bytes.fromhex(run['old']),bytes.fromhex(run['new']);offset=run['offset']
        if not old or len(old)!=len(new) or offset<end or offset>len(restored)-len(old) or restored[offset:offset+len(old)]!=new:
            raise ValueError('Native menu byte guard mismatch')
        restored[offset:offset+len(old)]=old;end=offset+len(old)
    if len(restored)!=patch['original_size'] or digest(restored)!=patch['original_sha256']:
        raise ValueError('Native menu reverse identity mismatch')
    return dict(name='Dementium II.exe',source_size=patch['original_size'],target_size=patch['modified_size'],
        source_sha256=patch['original_sha256'],target_sha256=patch['modified_sha256'],
        runs=patch['runs'],tail=patch['append'])


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
    payload = dict(schema=1, members=members,
                   literals=[dict(source=e['source'], target=e['target'], capacity=e['slot_size']) for e in config['entries']])
    executable_patch = build/'exe-patch.json'
    if executable_patch.exists():
        patch=json.loads(executable_patch.read_text(encoding='utf-8'))
        if patch.get('format')=='native-menu-pe-v1':
            identity=json.loads((Path(__file__).resolve().parents[1]/'assets/supported-build.json').read_text(encoding='utf-8'))
            payload['native_executable']=native_executable_payload(build,patch,identity)
    return payload


def write_payload(build, recipe, output):
    data = make_payload(build, recipe)
    raw = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if len(raw) > 64*1024*1024:
        raise ValueError('Resource payload too large')
    output.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    return hashlib.sha256(raw).hexdigest()
