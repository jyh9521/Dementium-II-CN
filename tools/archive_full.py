"""Pack a self-contained, explicitly selected local engineering archive.

The archive contains committed source, a complete Git bundle, one original
baseline, sparse recovery recipes and selected local evidence. Game binaries
are local archival inputs, not files to add to the source repository. Only the
standard library is required to verify/extract or restore source deltas; Git is
required only for packaging and optional history restoration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import zipfile

from archive_increment import (ROOT_NAME, ZIP_TIME, canonical, identity, no_links,
                               relative_path, restore_sources, within)

KIND = 'standalone-engineering-archive'
MANIFEST = 'ARCHIVE_MANIFEST.json'
HASHES = 'SHA256.json'
README = 'ARCHIVE_README.txt'
BUNDLE = 'source-history.bundle'
ROLES = {'input', 'evidence', 'recipe', 'installer', 'native-fixture', 'baseline-input'}
CACHE_PARTS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'toolchain',
               '.pytest_cache', '.mypy_cache', '.ruff_cache', 'obj', 'bin'}
RESERVED = re.compile(r'^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?$', re.I)
HEX = re.compile(r'^[0-9a-f]{64}$')
COMMIT = re.compile(r'^(?:[0-9a-f]{40}|[0-9a-f]{64})$')


def safe_path(value):
    path = relative_path(value)
    if any(p.endswith(('.', ' ')) or RESERVED.fullmatch(p) for p in path.parts):
        raise ValueError('Unsafe Windows archive path')
    return path


def permitted(value, role, baseline, installer):
    path = safe_path(value)
    if any(p.lower() in CACHE_PARTS for p in path.parts):
        raise ValueError('Excluded archive cache or Git directory: ' + value)
    if path.suffix.lower() in {'.pyc', '.pyo', '.pdb', '.zip', '.7z', '.rar'}:
        raise ValueError('Excluded derived or nested archive: ' + value)
    if role not in ROLES | {'source', 'history'}:
        raise ValueError('Unknown archive role: ' + str(role))
    if role == 'history' and value != BUNDLE:
        raise ValueError('Unexpected history bundle path')
    if role == 'installer' and value != installer:
        raise ValueError('Only the selected installer may be archived')
    if role == 'baseline-input' and not path.is_relative_to(safe_path(baseline)):
        raise ValueError('Original input is outside the selected baseline')
    if path.suffix.lower() == '.zar' and role != 'baseline-input':
        raise ValueError('Complete ROM copies must use the one selected baseline')
    if path.suffix.lower() in {'.exe', '.dll'} and role not in {'baseline-input', 'native-fixture', 'installer'}:
        raise ValueError('Binary input requires an explicit archival role')


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)


def clean_source(root):
    if git(root, 'status', '--porcelain', '--untracked-files=no').strip():
        raise ValueError('Commit source changes before making a standalone archive')


def checked_identity(value):
    if (not isinstance(value, dict) or type(value.get('bytes')) is not int
            or value['bytes'] < 0 or not HEX.fullmatch(str(value.get('sha256', '')))):
        raise ValueError('Invalid archived file identity')
    return {'bytes': value['bytes'], 'sha256': value['sha256']}


def validate_plan(plan):
    if plan.get('schema') != 1 or not isinstance(plan.get('files'), list):
        raise ValueError('Unknown standalone archive plan')
    baseline = plan.get('baseline_directory', 'build/original')
    safe_path(baseline)
    installer = plan.get('installer')
    if installer is not None:
        safe_path(installer)
    rows, names = [], set()
    for row in plan['files']:
        name, role = row['path'], row['role']
        if role not in ROLES:
            raise ValueError('Explicit file must use a local-input role')
        permitted(name, role, baseline, installer)
        if name.casefold() in names or name == BUNDLE:
            raise ValueError('Duplicate explicit archive path')
        names.add(name.casefold())
        rows.append(dict(path=name, role=role))
    if installer and not any(r == dict(path=installer, role='installer') for r in rows):
        raise ValueError('Selected installer is missing from the explicit plan')
    manifests = plan.get('source_manifests', [])
    if not isinstance(manifests, list) or len(set(manifests)) != len(manifests):
        raise ValueError('Invalid source manifest selection')
    for name in manifests:
        safe_path(name)
    if sum(r['path'].lower().endswith('.zar') for r in rows) > 1:
        raise ValueError('Only one complete original ROM baseline belongs in the archive')
    return baseline, installer, rows, manifests


def check_delta_dependencies(manifests, rows, read):
    """Every sparse source recipe must refer only to included archive members."""
    by_name = {r['path']: r for r in rows}
    for name in manifests:
        if name not in by_name:
            raise ValueError('Source manifest is not included: ' + name)
        data = json.loads(read(name))
        if data.get('schema') != 1 or data.get('format') != 'source-copy-add-v1' or not data.get('files'):
            raise ValueError('Unknown or empty archived source manifest')
        for row in data['files']:
            source = str(safe_path(row['source_path']))
            delta = str(safe_path(str(safe_path(name).parent / safe_path(row['delta']))))
            if source not in by_name or delta not in by_name:
                raise ValueError('Source delta depends on a missing archive input')
            if checked_identity(by_name[source]) != row['source'] or checked_identity(by_name[delta]) != row['delta_identity']:
                raise ValueError('Archived source-delta dependency identity mismatch')


def zip_info(name):
    info = zipfile.ZipInfo(name, date_time=ZIP_TIME)
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | (0o755 if name.endswith('.sh') else 0o644)) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def remove_staging(path, parent, prefix):
    """Restrict recursive cleanup to the exact generated sibling staging path."""
    path, parent = no_links(path).resolve(), no_links(parent).resolve()
    if path.parent != parent or not path.name.startswith(prefix):
        raise ValueError('Staging cleanup escaped its selected parent')
    if path.exists():
        shutil.rmtree(path)


def package_full(root, plan, output):
    root, output = no_links(root).resolve(strict=True), no_links(output)
    if output.exists():
        raise FileExistsError('Archive output already exists')
    baseline, installer, extras, manifests = validate_plan(plan)
    clean_source(root)
    commit = git(root, 'rev-parse', 'HEAD').decode().strip()
    branch = git(root, 'symbolic-ref', '--quiet', '--short', 'HEAD').decode().strip()
    try:
        origin = git(root, 'remote', 'get-url', 'origin').decode().strip()
    except subprocess.CalledProcessError:
        origin = None
    source = [n.decode('utf-8') for n in git(root, 'ls-files', '-z').split(b'\0') if n]
    rows, paths, names = [], {}, set()
    for entry in [*(dict(path=p, role='source') for p in source), *extras]:
        name, role = entry['path'], entry['role']
        permitted(name, role, baseline, installer)
        if name.casefold() in names:
            raise ValueError('Duplicate source/explicit archive path: ' + name)
        names.add(name.casefold())
        path = within(root, name)
        if not path.is_file():
            raise ValueError('Archive input is not a regular file: ' + name)
        rows.append(dict(path=name, role=role, **identity(path)))
        paths[name] = path
    check_delta_dependencies(manifests, rows, lambda n: paths[n].read_bytes())
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.full-archive-', dir=output.parent))
    try:
        bundle = staging/BUNDLE
        git(root, 'bundle', 'create', str(bundle), '--all')
        check_bundle_header(bundle)
        git(root, 'bundle', 'verify', str(bundle))
        rows.append(dict(path=BUNDLE, role='history', **identity(bundle)))
        paths[BUNDLE] = bundle
        rows.sort(key=lambda r: r['path'])
        manifest = dict(schema=1, kind=KIND, root_name=ROOT_NAME, source_commit=commit,
                        source_branch=branch, source_origin=origin, standalone=True,
                        baseline_directory=baseline, installer=installer,
                        source_manifests=manifests, files=rows)
        readme = ('Standalone local engineering archive. No older archive is required.\n'
                  '1. Verify/extract with tools/archive_full.py.\n'
                  '2. Restore Git history with restore-git, if needed.\n'
                  '3. Restore current original inputs with restore-sources and an included manifest.\n'
                  '4. See docs/ARCHIVE_FULL_20261030.md and BUILDING.md for reconstruction.\n'
                  'One original ROM baseline is retained; other versions use exact source deltas.\n'
                  'SDKs/caches and duplicate complete ROMs are excluded.\n').encode()
        hashes = {ROOT_NAME+'/'+r['path']: r['sha256'] for r in rows}
        envelope = {MANIFEST: canonical(manifest), README: readme}
        hashes.update({n: hashlib.sha256(raw).hexdigest() for n, raw in envelope.items()})
        envelope[HASHES] = canonical(hashes)
        temporary = staging/'archive.zip'
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for name in sorted([*envelope, *(ROOT_NAME+'/'+n for n in paths)]):
                if name in envelope:
                    archive.writestr(zip_info(name), envelope[name])
                    continue
                relative = name[len(ROOT_NAME)+1:]
                h, size = hashlib.sha256(), 0
                with paths[relative].open('rb') as src, archive.open(zip_info(name), 'w', force_zip64=True) as dst:
                    for chunk in iter(lambda: src.read(1024*1024), b''):
                        h.update(chunk); size += len(chunk); dst.write(chunk)
                if dict(bytes=size, sha256=h.hexdigest()) != checked_identity(next(r for r in rows if r['path'] == relative)):
                    raise ValueError('Archive input changed during packaging: ' + relative)
        clean_source(root)
        if git(root, 'rev-parse', 'HEAD').decode().strip() != commit:
            raise ValueError('Source commit changed during packaging')
        result = verify_full(temporary)
        if output.exists():
            raise FileExistsError('Archive output appeared during packaging')
        temporary.rename(output)
        return dict(**result, path=str(output), **identity(output))
    finally:
        remove_staging(staging, output.parent, '.full-archive-')


def check_bundle_header(path):
    with Path(path).open('rb') as stream:
        if stream.readline().rstrip() not in (b'# v2 git bundle', b'# v3 git bundle'):
            raise ValueError('Invalid Git bundle header')
        while line := stream.readline():
            if line == b'\n':
                return
            if line.startswith(b'-'):
                raise ValueError('History bundle requires another repository')
        raise ValueError('Incomplete Git bundle header')


def verify_full(path):
    with zipfile.ZipFile(no_links(path)) as archive:
        infos = archive.infolist()
        names, folded = set(), set()
        for info in infos:
            safe_path(info.filename)
            if info.filename in names or info.filename.casefold() in folded:
                raise ValueError('Duplicate or case-colliding ZIP member')
            names.add(info.filename); folded.add(info.filename.casefold())
            if info.is_dir() or stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG):
                raise ValueError('Archive members must be regular files')
            if info.filename.endswith('.sh') and (info.external_attr >> 16) & 0o111 != 0o111:
                raise ValueError('Shell script is missing executable mode')
        for name in names:
            if any(str(parent).casefold() in folded for parent in safe_path(name).parents if str(parent) != '.'):
                raise ValueError('ZIP file/directory collision')
        hashes = json.loads(archive.read(HASHES))
        if set(hashes) | {HASHES} != names:
            raise ValueError('ZIP member set differs from checksum manifest')
        observed = {}
        for name, expected in hashes.items():
            if not HEX.fullmatch(str(expected)):
                raise ValueError('Invalid member checksum')
            with archive.open(name) as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != expected:
                raise ValueError('ZIP member identity mismatch: ' + name)
            observed[name] = dict(bytes=archive.getinfo(name).file_size, sha256=actual)
        manifest = json.loads(archive.read(MANIFEST))
        if (manifest.get('schema') != 1 or manifest.get('kind') != KIND
                or manifest.get('root_name') != ROOT_NAME or manifest.get('standalone') is not True):
            raise ValueError('Unknown standalone archive manifest')
        if not COMMIT.fullmatch(str(manifest.get('source_commit', ''))):
            raise ValueError('Invalid source commit identity')
        rows, selected = manifest['files'], set()
        for row in rows:
            relative = row['path']
            permitted(relative, row['role'], manifest['baseline_directory'], manifest.get('installer'))
            name = ROOT_NAME+'/'+relative
            if name in selected or observed.get(name) != checked_identity(row):
                raise ValueError('Standalone manifest identity mismatch')
            selected.add(name)
        if selected | {MANIFEST, HASHES, README} != names:
            raise ValueError('Unexpected standalone archive member')
        if sum(r['path'].lower().endswith('.zar') for r in rows) > 1:
            raise ValueError('Archive repeats a complete original ROM baseline')
        history = [r for r in rows if r['role'] == 'history']
        if len(history) != 1 or history[0]['path'] != BUNDLE:
            raise ValueError('Standalone archive needs exactly one full history bundle')
        raw_header = archive.read(ROOT_NAME+'/'+BUNDLE).split(b'\n\n', 1)[0].splitlines()
        if not raw_header or raw_header[0] not in (b'# v2 git bundle', b'# v3 git bundle') or any(l.startswith(b'-') for l in raw_header):
            raise ValueError('History bundle is not self-contained')
        check_delta_dependencies(manifest.get('source_manifests', []), rows,
                                 lambda n: archive.read(ROOT_NAME+'/'+n))
    return dict(result='PASS', members=len(names), files=len(rows), source_commit=manifest['source_commit'],
                standalone=True, original_roms=sum(r['path'].lower().endswith('.zar') for r in rows))


def extract_full(archive_path, output):
    archive_path, output = no_links(archive_path), no_links(output)
    if output.exists():
        raise FileExistsError('Extraction output must be a new directory')
    result = verify_full(archive_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.full-extract-', dir=output.parent))
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for info in archive.infolist():
                path = within(staging, info.filename)
                path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, path.open('xb') as dst:
                    shutil.copyfileobj(src, dst, 1024*1024)
                os.chmod(path, 0o755 if path.suffix == '.sh' else 0o644)
            hashes = json.loads((staging/HASHES).read_bytes())
            for name, expected in hashes.items():
                if identity(within(staging, name))['sha256'] != expected:
                    raise ValueError('Extracted file readback mismatch')
        if output.exists():
            raise FileExistsError('Extraction output appeared during verification')
        staging.rename(output)
    finally:
        remove_staging(staging, output.parent, '.full-extract-')
    return dict(**result, output=str(output))


def restore_git(repository):
    repository = no_links(repository).resolve(strict=True)
    if (repository/'.git').exists():
        raise FileExistsError('Git history restoration requires an absent .git directory')
    manifest = json.loads((repository.parent/MANIFEST).read_bytes())
    if manifest.get('kind') != KIND or repository.name != manifest.get('root_name'):
        raise ValueError('Repository does not match its standalone archive manifest')
    if not COMMIT.fullmatch(str(manifest.get('source_commit', ''))):
        raise ValueError('Invalid source commit identity')
    bundle = within(repository, BUNDLE)
    row = next(r for r in manifest['files'] if r['role'] == 'history')
    if identity(bundle) != checked_identity(row):
        raise ValueError('History bundle identity mismatch')
    check_bundle_header(bundle)
    staging = Path(tempfile.mkdtemp(prefix='.full-history-', dir=repository.parent))
    try:
        target = staging/'git'
        subprocess.run(['git', 'clone', '--mirror', str(bundle), str(target)], check=True, capture_output=True)
        command = ['git', '--git-dir='+str(target)]
        subprocess.run([*command, 'cat-file', '-e', manifest['source_commit']+'^{commit}'], check=True)
        subprocess.run([*command, 'config', 'core.bare', 'false'], check=True)
        subprocess.run([*command, 'config', '--unset-all', 'remote.origin.mirror'], check=True)
        subprocess.run([*command, 'config', 'remote.origin.fetch', '+refs/heads/*:refs/remotes/origin/*'], check=True)
        if manifest.get('source_origin'):
            subprocess.run([*command, 'config', 'remote.origin.url', manifest['source_origin']], check=True)
        branch = manifest['source_branch']
        subprocess.run(['git', 'check-ref-format', '--branch', branch], check=True, capture_output=True)
        subprocess.run([*command, 'symbolic-ref', 'HEAD', 'refs/heads/'+branch], check=True)
        target.rename(repository/'.git')
        git(repository, 'reset', '--mixed', manifest['source_commit'])
        clean_source(repository)
        commit = git(repository, 'rev-parse', 'HEAD').decode().strip()
        if commit != manifest['source_commit']:
            raise ValueError('Restored Git commit differs from archive')
        return dict(result='PASS', source_commit=commit, source_branch=branch, tracked_source_clean=True)
    finally:
        remove_staging(staging, repository.parent, '.full-history-')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    pack = sub.add_parser('pack')
    pack.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    pack.add_argument('--plan', type=Path, required=True)
    pack.add_argument('--output', type=Path, required=True)
    verify = sub.add_parser('verify'); verify.add_argument('--archive', type=Path, required=True)
    extract = sub.add_parser('extract')
    extract.add_argument('--archive', type=Path, required=True)
    extract.add_argument('--output', type=Path, required=True)
    history = sub.add_parser('restore-git'); history.add_argument('--repository', type=Path, required=True)
    sources = sub.add_parser('restore-sources')
    sources.add_argument('--repository', type=Path, required=True)
    sources.add_argument('--manifest', required=True, help='repository-relative included source manifest')
    sources.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'pack':
        result = package_full(args.root, json.loads(args.plan.read_text('utf-8-sig')), args.output)
    elif args.command == 'verify': result = verify_full(args.archive)
    elif args.command == 'extract': result = extract_full(args.archive, args.output)
    elif args.command == 'restore-git': result = restore_git(args.repository)
    else:
        result = restore_sources(args.repository, within(args.repository, str(safe_path(args.manifest))), args.output)
    print('FULL_ARCHIVE_'+args.command.upper().replace('-', '_')+' '+json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
