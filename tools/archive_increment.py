"""Create verified source deltas and incremental archives without complete games.

All archive input paths are repository-relative. Restoration always creates a
new directory; the existing archival baseline is never changed or overlaid.
Only the Python standard library is needed for restoration and ZIP validation.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tempfile
import zipfile
import zlib


FORMAT = 'source-copy-add-v1'
ROOT_NAME = 'Dementium-II-CN'
ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':')) + '\n').encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(path):
    with Path(path).open('rb') as stream:
        result = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(bytes=Path(path).stat().st_size, sha256=result)


def no_links(path):
    """Reject symbolic links and Windows directory junctions before resolution."""
    path = Path(os.path.abspath(path))
    for item in [path, *path.parents]:
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Linked archive path: ' + str(item))
    return path


def relative_path(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value or '\0' in value:
        raise ValueError('Unsafe relative archive path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ('', '.', '..') for p in value.split('/')):
        raise ValueError('Unsafe relative archive path')
    return path


def within(root, relative):
    root = no_links(root)
    path = no_links(root.joinpath(*relative_path(relative).parts))
    if not path.is_relative_to(root):
        raise ValueError('Archive path escapes its root')
    return path


def _append_copy(ops, offset, length):
    if not length:
        return
    if ops and ops[-1][0] == 'copy' and ops[-1][1] + ops[-1][2] == offset:
        ops[-1][2] += length
    else:
        ops.append(['copy', offset, length])


def _append_add(ops, raw):
    if raw:
        ops.append(['add', base64.b64encode(raw).decode('ascii')])


def binary_ops(source, target, block=32):
    """Bounded rsync-style matching, including arbitrary shifted code blocks.

    Adler32 is only an index; exact bytes are compared before every COPY. The
    final recipe also binds both complete input and output with SHA-256.
    """
    index = {}
    for offset in range(0, len(source) - block + 1, block):
        key = zlib.adler32(source[offset:offset + block])
        bucket = index.setdefault(key, [])
        if len(bucket) < 8:
            bucket.append(offset)
    ops, position, pending = [], 0, 0
    while position <= len(target) - block:
        window = target[position:position + block]
        candidates = index.get(zlib.adler32(window), ())
        found = next((offset for offset in candidates
                      if source[offset:offset + block] == window), None)
        if found is None:
            position += 1
            continue
        _append_add(ops, target[pending:position])
        length = block
        while (found + length + block <= len(source) and position + length + block <= len(target)
               and source[found + length:found + length + block] == target[position + length:position + length + block]):
            length += block
        while (found + length < len(source) and position + length < len(target)
               and source[found + length] == target[position + length]):
            length += 1
        _append_copy(ops, found, length)
        position += length
        pending = position
    _append_add(ops, target[pending:])
    return ops


def zar_ops(source, target):
    """Copy unchanged members even after rename/reorder; retain every gap byte."""
    from localize import Zar
    old, new = Zar(source), Zar(target)
    by_content = {}
    for entry in old.entries.values():
        raw = old.read(entry.name)
        by_content.setdefault((len(raw), digest(raw)), entry.offset)
    ops, cursor = [], 0
    for entry in sorted(new.entries.values(), key=lambda item: item.offset):
        if not entry.size:
            continue
        if entry.offset < cursor:
            raise ValueError('Overlapping target archive members')
        _append_add(ops, target[cursor:entry.offset])
        raw = new.read(entry.name)
        offset = by_content.get((len(raw), digest(raw)))
        if offset is not None and source[offset:offset + len(raw)] == raw:
            _append_copy(ops, offset, len(raw))
        else:
            _append_add(ops, raw)
        cursor = entry.offset + entry.size
    _append_add(ops, target[cursor:])
    return ops


def make_delta(source, target, kind='binary'):
    ops = zar_ops(source, target) if kind == 'zar' else binary_ops(source, target)
    copied = sum(op[2] for op in ops if op[0] == 'copy')
    return dict(format=FORMAT, kind=kind, source=dict(bytes=len(source), sha256=digest(source)),
                target=dict(bytes=len(target), sha256=digest(target)), operations=ops,
                copied_bytes=copied, literal_bytes=len(target) - copied)


def _validate_recipe(recipe, source):
    if recipe.get('format') != FORMAT:
        raise ValueError('Unknown source delta format')
    if recipe.get('source') != dict(bytes=len(source), sha256=digest(source)):
        raise ValueError('Source delta baseline identity mismatch')
    target = recipe.get('target', {})
    if (type(target.get('bytes')) is not int or target['bytes'] < 0
            or not isinstance(target.get('sha256'), str) or len(target['sha256']) != 64):
        raise ValueError('Invalid source delta target')
    total = 0
    for op in recipe.get('operations', []):
        if not isinstance(op, list) or not op:
            raise ValueError('Invalid source delta operation')
        if op[0] == 'copy' and len(op) == 3:
            offset, length = op[1:]
            if (type(offset) is not int or type(length) is not int or offset < 0 or length <= 0
                    or offset > len(source) - length):
                raise ValueError('Source delta COPY bounds')
            total += length
        elif op[0] == 'add' and len(op) == 2:
            raw = base64.b64decode(op[1], validate=True)
            if not raw:
                raise ValueError('Empty source delta ADD')
            total += len(raw)
        else:
            raise ValueError('Unknown source delta operation')
        if total > target['bytes']:
            raise ValueError('Source delta exceeds target bounds')
    if total != target['bytes']:
        raise ValueError('Source delta target size mismatch')


def apply_delta(source, recipe):
    _validate_recipe(recipe, source)
    pieces = (source[op[1]:op[1] + op[2]] if op[0] == 'copy'
              else base64.b64decode(op[1], validate=True) for op in recipe['operations'])
    target = b''.join(pieces)
    if digest(target) != recipe['target']['sha256']:
        raise ValueError('Source delta target identity mismatch')
    return target


def create_source_deltas(base, current, output, pairs):
    """pairs contains source-relative path, target-relative path, output filename."""
    base, current, output = (no_links(p) for p in (base, current, output))
    if output.exists():
        raise FileExistsError('Delta output directory already exists')
    if output.is_relative_to(base):
        raise ValueError('Delta output must be outside the archival baseline')
    plans, names = [], set()
    for source_rel, target_rel, filename in pairs:
        relative_path(filename)
        if '/' in filename or filename in names:
            raise ValueError('Source delta output names must be distinct filenames')
        names.add(filename)
        source_path, target_path = within(base, source_rel), within(current, target_rel)
        source, target = source_path.read_bytes(), target_path.read_bytes()
        kind = 'zar' if target[:4] == b'ZAR1' else 'binary'
        recipe = make_delta(source, target, kind)
        if recipe['target']['bytes'] and not recipe['copied_bytes']:
            raise ValueError('Source delta would contain a complete target file')
        if apply_delta(source, recipe) != target:
            raise ValueError('Source delta round trip differs')
        raw = gzip.compress(canonical(recipe), compresslevel=9, mtime=0)
        plans.append((filename + '.delta.gz', raw, dict(source_path=source_rel,
                      output_path=filename, source=recipe['source'], target=recipe['target'],
                      copied_bytes=recipe['copied_bytes'], literal_bytes=recipe['literal_bytes'])))
    output.mkdir(parents=True)
    files = []
    for name, raw, row in plans:
        (output/name).write_bytes(raw)
        row.update(delta=name, delta_identity=identity(output/name))
        files.append(row)
    manifest = dict(schema=1, format=FORMAT, files=files,
                    restore='archive_increment.py restore --base OLD_ARCHIVE_REPOSITORY --manifest source-deltas/manifest.json --output NEW_DIRECTORY')
    (output/'manifest.json').write_bytes(canonical(manifest))
    return manifest


def restore_sources(base, manifest_path, output):
    """Validate every input first, then atomically publish a fresh output folder."""
    base, manifest_path, output = (no_links(p) for p in (base, manifest_path, output))
    if output.exists():
        raise FileExistsError('Restoration output must be a new directory')
    if output.is_relative_to(base) or base.is_relative_to(output):
        raise ValueError('Restoration output overlaps the archival baseline')
    manifest = json.loads(manifest_path.read_text('utf-8'))
    if manifest.get('schema') != 1 or manifest.get('format') != FORMAT:
        raise ValueError('Unknown source manifest')
    if not isinstance(manifest.get('files'), list) or not manifest['files']:
        raise ValueError('Source manifest must contain at least one file')
    plans, names = [], set()
    for row in manifest['files']:
        source = within(base, row['source_path'])
        delta = within(manifest_path.parent, row['delta'])
        relative_path(row['output_path'])
        if '/' in row['output_path'] or row['output_path'] in names:
            raise ValueError('Duplicate or nested restoration output')
        names.add(row['output_path'])
        if identity(source) != row['source'] or identity(delta) != row['delta_identity']:
            raise ValueError('Restoration input identity mismatch')
        recipe = json.loads(gzip.decompress(delta.read_bytes()))
        if recipe.get('source') != row['source'] or recipe.get('target') != row['target']:
            raise ValueError('Manifest and source delta disagree')
        # Complete operation and resulting-byte checks precede filesystem writes.
        restored = apply_delta(source.read_bytes(), recipe)
        plans.append((row, restored))
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.source-restore-', dir=output.parent))
    try:
        for row, restored in plans:
            path = staging/row['output_path']
            path.write_bytes(restored)
            if identity(path) != row['target']:
                raise ValueError('Restored file readback mismatch')
            if identity(within(base, row['source_path'])) != row['source']:
                raise ValueError('Archival baseline changed during restoration')
        # Recheck after preflight, and never replace an existing output directory.
        if output.exists():
            raise FileExistsError('Restoration output appeared during validation')
        staging.rename(output)
    finally:
        if staging.exists():
            checked = no_links(staging).resolve()
            if checked.parent != no_links(output.parent).resolve() or not checked.name.startswith('.source-restore-'):
                raise ValueError('Temporary restoration cleanup escaped its parent')
            shutil.rmtree(staging)
    return {row['output_path']: row['target'] for row, _ in plans}


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)


def tracked(root):
    return {p.decode('utf-8') for p in git(root, 'ls-files', '-z').split(b'\0') if p}


def _permitted(relative, installer):
    path = relative_path(relative)
    lowered = relative.lower()
    if (any(part.lower() in ('.git', '__pycache__', '.venv', 'node_modules', 'toolchain') for part in path.parts)
            or path.suffix.lower() in ('.zar', '.dll', '.pyc', '.pdb', '.zip', '.7z')
            or path.suffix.lower() == '.exe' and relative != installer):
        raise ValueError('Excluded full game, dependency, cache or duplicate package: ' + relative)


def package_increment(root, base, output, includes=(), installer=None, bundle=False, allow_dirty=False):
    root, base, output = (no_links(p) for p in (root, base, output))
    if output.exists():
        raise FileExistsError('Incremental archive already exists')
    if output.is_relative_to(base):
        raise ValueError('Archive output overlaps baseline')
    base_commit = git(base, 'rev-parse', 'HEAD').decode().strip()
    current_commit = git(root, 'rev-parse', 'HEAD').decode().strip()
    git(root, 'merge-base', '--is-ancestor', base_commit, current_commit)
    dirty = git(root, 'status', '--porcelain', '--untracked-files=normal').decode('utf-8')
    if dirty and not allow_dirty:
        raise ValueError('Commit source changes before creating the final archive')
    current_tracked, old_tracked = tracked(root), tracked(base)
    selected = current_tracked | set(includes) | ({installer} if installer else set())
    rows, data = [], {}
    for relative in sorted(selected):
        _permitted(relative, installer)
        path = within(root, relative)
        if not path.is_file():
            raise ValueError('Selected archive input is not a file: ' + relative)
        old_path = within(base, relative)
        old = identity(old_path) if old_path.is_file() else None
        raw = path.read_bytes()
        new = dict(bytes=len(raw), sha256=digest(raw))
        if old == new:
            continue
        member = ROOT_NAME + '/' + relative
        data[member] = raw
        rows.append(dict(path=member, previous=old, current=new,
                         origin='tracked-source' if relative in current_tracked else 'explicit-input'))
    deleted = []
    for relative in sorted(old_tracked - current_tracked):
        old_path = within(base, relative)
        deleted.append(dict(path=ROOT_NAME + '/' + relative,
                            previous=identity(old_path) if old_path.is_file() else None))
    if bundle:
        with tempfile.TemporaryDirectory(prefix='incremental-git-') as tmp:
            bundle_path = Path(tmp)/'source-history.bundle'
            git(root, 'bundle', 'create', str(bundle_path), base_commit + '..HEAD')
            git(base, 'bundle', 'verify', str(bundle_path))
            raw = bundle_path.read_bytes()
        member = ROOT_NAME + '/source-history.bundle'
        data[member] = raw
        rows.append(dict(path=member, previous=None,
                         current=dict(bytes=len(raw), sha256=digest(raw)), origin='incremental-git-history'))
    manifest = dict(schema=1, kind='incremental-archive', baseline_commit=base_commit,
                    current_commit=current_commit, source_dirty=bool(dirty), files=rows,
                    deleted_tracked_paths=deleted, baseline_changed=False,
                    complete_game_files=False, contains_dependencies=False, installer=installer)
    data['INCREMENT_MANIFEST.json'] = canonical(manifest)
    data['INCREMENT_README.txt'] = (
        '增量归档：仅保存相对清单所列旧归档的新增或变更文件。\n'
        '旧归档保持不变；本 ZIP 不是独立完整源码副本。\n'
        '恢复工程：复制旧归档到新目录，再覆盖本包 Dementium-II-CN 内的文件。\n'
        '删除的已跟踪路径列于 INCREMENT_MANIFEST.json，仅作清单，不自动删除。\n'
        '若含 source-history.bundle，可在恢复工程执行 git fetch ./source-history.bundle HEAD:refs/heads/archive-20261029。\n'
        '新版原版输入按 source-deltas/manifest.json 从旧原版差分恢复到另一新目录。\n'
        '恢复命令：python -B tools/archive_increment.py restore --base "旧归档内工程目录" '
        '--manifest "本包中的 source-deltas/manifest.json" --output "新的原版目录"\n'
        '校验 ZIP：python -B tools/archive_increment.py verify --archive "本增量包.zip"\n'
        '安装器独立使用；新源文件、差分、证据与提交由 INCREMENT_MANIFEST.json 绑定。\n'
    ).encode('utf-8')
    # Manifest and instructions are envelope members; bind them in a compact sidecar.
    data['SHA256.json'] = canonical({name: digest(raw) for name, raw in sorted(data.items())})
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, raw in sorted(data.items()):
                info = zipfile.ZipInfo(name, date_time=ZIP_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (0o100755 if name.endswith('.sh') else 0o100644) << 16
                archive.writestr(info, raw, compresslevel=9)
        result = verify_increment(output)
    except Exception:
        if output.exists():
            output.unlink()
        raise
    return dict(**result, path=str(output), **identity(output))


def verify_increment(path):
    with zipfile.ZipFile(no_links(path)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP member')
        for name in names:
            relative_path(name)
            info = archive.getinfo(name)
            if stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK:
                raise ValueError('Linked ZIP member')
        hashes = json.loads(archive.read('SHA256.json'))
        if set(names) != set(hashes) | {'SHA256.json'}:
            raise ValueError('ZIP member set differs from checksum manifest')
        for name, expected in hashes.items():
            if digest(archive.read(name)) != expected:
                raise ValueError('ZIP member identity mismatch: ' + name)
        manifest = json.loads(archive.read('INCREMENT_MANIFEST.json'))
        if manifest.get('schema') != 1 or manifest.get('kind') != 'incremental-archive':
            raise ValueError('Unknown incremental archive manifest')
        members = set()
        for row in manifest['files']:
            name = row['path']
            if name in members:
                raise ValueError('Duplicate incremental manifest path')
            if not name.startswith(ROOT_NAME + '/'):
                raise ValueError('Incremental file is outside its repository prefix')
            _permitted(name[len(ROOT_NAME) + 1:], manifest.get('installer'))
            members.add(name)
            raw = archive.read(name)
            if dict(bytes=len(raw), sha256=digest(raw)) != row['current']:
                raise ValueError('Incremental manifest identity mismatch')
            if row.get('previous') == row['current']:
                raise ValueError('Unchanged file included in incremental archive')
        if set(names) != members | {'INCREMENT_MANIFEST.json', 'INCREMENT_README.txt', 'SHA256.json'}:
            raise ValueError('Unexpected archive envelope member')
    return dict(result='PASS', members=len(names), changed_files=len(members),
                baseline_commit=manifest['baseline_commit'], current_commit=manifest['current_commit'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    delta = sub.add_parser('delta')
    delta.add_argument('--base', type=Path, required=True)
    delta.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    delta.add_argument('--output', type=Path, required=True)
    delta.add_argument('--file', action='append', required=True,
                       help='repository-relative source and target path; restored basename is retained')
    restore = sub.add_parser('restore')
    restore.add_argument('--base', type=Path, required=True)
    restore.add_argument('--manifest', type=Path, required=True)
    restore.add_argument('--output', type=Path, required=True)
    package = sub.add_parser('pack')
    package.add_argument('--base', type=Path, required=True)
    package.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    package.add_argument('--output', type=Path, required=True)
    package.add_argument('--include', action='append', default=[])
    package.add_argument('--installer')
    package.add_argument('--bundle', action='store_true')
    package.add_argument('--allow-dirty', action='store_true')
    verify = sub.add_parser('verify')
    verify.add_argument('--archive', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'delta':
        result = create_source_deltas(args.base, args.root, args.output,
            [(p, p, PurePosixPath(p).name) for p in args.file])
        print('SOURCE_DELTAS files=%d copied_bytes=%d literal_bytes=%d result=PASS' %
              (len(result['files']), sum(r['copied_bytes'] for r in result['files']),
               sum(r['literal_bytes'] for r in result['files'])))
    elif args.command == 'restore':
        result = restore_sources(args.base, args.manifest, args.output)
        print('SOURCE_RESTORE ' + json.dumps(result, sort_keys=True) + ' baseline_unchanged=YES result=PASS')
    elif args.command == 'pack':
        result = package_increment(args.root, args.base, args.output, args.include,
                                   args.installer, args.bundle, args.allow_dirty)
        print('INCREMENT_PACKAGE ' + json.dumps(result, sort_keys=True))
    else:
        print('INCREMENT_VERIFY ' + json.dumps(verify_increment(args.archive), sort_keys=True))


if __name__ == '__main__':
    main()
