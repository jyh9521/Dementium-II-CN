"""Build source-dependent member deltas, independent of container offsets at install."""
import base64
import copy
import gzip
import hashlib
import json
import struct
from pathlib import Path
from localize import Zar, apply_delta, digest


def native_hash_guards(source, target):
    """Bind every address-bearing PE byte, without distributing original code.

    The only unguarded original section is .rsrc (icons/version metadata).
    Unknown builds can differ there, but not in code, globals, relocations,
    imports, unwind data, layout or any patch byte. Guards cover the original
    ranges only; the appended localization sections are checked separately.
    """
    from executable_text import _rdata
    _rdata(source)
    pe = struct.unpack_from('<I', source, 60)[0]
    count, optional = struct.unpack_from('<H', source, pe+6)[0], struct.unpack_from('<H', source, pe+20)[0]
    table = pe+24+optional
    header_size = struct.unpack_from('<I', source, pe+24+60)[0]
    ranges = [(0, header_size)]
    for i in range(count):
        pos=table+40*i
        name=source[pos:pos+8].rstrip(b'\0')
        size, offset=struct.unpack_from('<II',source,pos+16)
        if size and name != b'.rsrc': ranges.append((offset,size))
    guards=[]
    for offset,size in ranges:
        if offset+size>len(source): raise ValueError('Native guard exceeds original image')
        guards.append(dict(offset=offset,length=size,sha256=digest(source[offset:offset+size]),
                           target_sha256=digest(target[offset:offset+size])))
    return guards


def _variants(patch):
    """Flatten imported historical bundles; the installer selects one level."""
    yield patch
    for variant in patch.get('source_variants', []):
        yield from _variants(variant)


def _merge_variants(current, previous):
    seen = {current['source_sha256']}
    variants = []
    # Keep the newest recipe for each preimage. Historical bundles may already
    # carry older versions also listed independently in the compatibility index.
    for patch in [*current.get('source_variants', []), previous]:
        for variant in _variants(patch):
            identity = variant['source_sha256']
            if identity in seen:
                continue
            seen.add(identity)
            item = copy.deepcopy(variant)
            item.pop('source_variants', None)
            variants.append(item)
    if variants:
        current['source_variants'] = variants


def add_compatibility(payload, previous):
    """Merge independently validated sparse source recipes, never game files."""
    if previous.get('schema') != 1: raise ValueError('Unsupported compatibility payload')
    old = {m['name']: m for m in previous['members']}
    for member in payload['members']:
        prior = old.pop(member['name'], None)
        if prior:
            _merge_variants(member, prior)
    # A resource no longer needing modification must not become mandatory on
    # the new build. A stale old-only recipe requires an explicit migration.
    if old: raise ValueError('Unmapped legacy resources: '+', '.join(sorted(old)))
    native = previous['native_executable']
    if native['source_sha256'] == payload['native_executable']['source_sha256']:
        raise ValueError('Compatibility source duplicates current executable')
    _merge_variants(payload['native_executable'], native)
    return payload


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


def make_payload(build, recipe, include_native=True):
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
    if include_native and executable_patch.exists():
        patch=json.loads(executable_patch.read_text(encoding='utf-8'))
        if patch.get('format')=='native-menu-pe-v1':
            identity=json.loads((Path(__file__).resolve().parents[1]/'assets/supported-build.json').read_text(encoding='utf-8'))
            payload['native_executable']=native_executable_payload(build,patch,identity)
            original_exe=bytearray((build/'Dementium II.exe').read_bytes()[:patch['original_size']])
            for run in patch['runs']:
                old=bytes.fromhex(run['old']);original_exe[run['offset']:run['offset']+len(old)]=old
            payload['native_executable']['hash_guards']=native_hash_guards(bytes(original_exe),(build/'Dementium II.exe').read_bytes())
            compatibility=Path(__file__).resolve().parents[1]/'assets/compatibility-payloads.json'
            if compatibility.exists():
                for item in json.loads(compatibility.read_text(encoding='utf-8'))['payloads']:
                    path=Path(__file__).resolve().parents[1]/item['path']
                    raw=path.read_bytes()
                    if digest(raw)!=item['sha256']: raise ValueError('Compatibility payload identity mismatch')
                    previous=json.loads(gzip.decompress(raw))
                    if previous['native_executable']['source_sha256']!=item['exe_sha256']:
                        raise ValueError('Compatibility executable source mismatch')
                    add_compatibility(payload,previous)
    return payload


def write_payload(build, recipe, output):
    data = make_payload(build, recipe)
    raw = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if len(raw) > 64*1024*1024:
        raise ValueError('Resource payload too large')
    output.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    return hashlib.sha256(raw).hexdigest()
