"""Explicit offline install/uninstall; this tool never starts the game."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

from localize import apply_delta, digest, filehash


def atomic_write(path, data):
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def backup_path(game, name, old_name):
    current = game / 'cn-backup' / name
    legacy = game / '.dementium-locale' / old_name
    return legacy if not current.exists() and legacy.exists() else current


def remove_backup_folder(game, folder):
    path = game / folder
    if not path.exists():
        return
    if path.resolve().parent != game.resolve() or path.is_symlink() or path.is_junction():
        raise ValueError('Unexpected backup folder path')
    for root, dirs, files in os.walk(path, followlinks=False):
        for name in dirs + files:
            child = Path(root) / name
            if child.is_symlink() or child.is_junction():
                raise ValueError('Backup contains a link; recovery files retained')
    shutil.rmtree(path)


def finish_restore(game, plans):
    # Called only after every selected component is committed and hash-verified.
    # A ROM-only invocation must retain any executable recovery backup.
    for folder, exe in [('cn-backup', 'Dementium II.exe'), ('.dementium-locale', 'original.exe')]:
        if len(plans) == 1 and (game / folder / exe).exists():
            continue
        if all(filehash(p['path']) == p['desired'] for p in plans):
            remove_backup_folder(game, folder)


def operate(game, identity, patch, action):
    game = game.resolve(strict=True)
    exe, archive = game / 'Dementium II.exe', game / 'rom.zar'
    if identity['appid'] != 5342930 or filehash(exe) != identity['exe_sha256'] or exe.stat().st_size != identity['exe_size']:
        raise ValueError('Unsupported executable/AppID')
    if patch['original_sha256'] != identity['rom_sha256'] or patch['original_size'] != identity['rom_size']:
        raise ValueError('Patch identity mismatch')
    current = filehash(archive)
    expected = patch['original_sha256'] if action == 'install' else patch['modified_sha256']
    destination = patch['modified_sha256'] if action == 'install' else patch['original_sha256']
    backup = backup_path(game, 'rom.zar', 'original.zar')
    if current == destination:
        if action == 'install' and (not backup.exists() or filehash(backup) != patch['original_sha256']):
            raise ValueError('Installed archive has no verified recovery backup')
        if action == 'uninstall':
            finish_restore(game, [dict(path=archive, desired=destination)])
        return 'ALREADY_' + ('INSTALLED' if action == 'install' else 'RESTORED')
    if current != expected:
        raise ValueError('Archive version/hash mismatch; no files changed')
    if action == 'install':
        if backup.exists() and filehash(backup) != current:
            raise ValueError('Existing recovery backup mismatch')
        backup = game / 'cn-backup' / 'rom.zar'
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            # Exclusive creation preserves any concurrent operator-created backup.
            with archive.open('rb') as src, backup.open('xb') as dst:
                shutil.copyfileobj(src, dst)
        if filehash(backup) != current:
            raise ValueError('Recovery backup verification failed')
        result = apply_delta(archive.read_bytes(), patch)
    else:
        if not backup.exists() or filehash(backup) != patch['original_sha256']:
            raise ValueError('Recovery backup missing or changed')
        result = apply_delta(archive.read_bytes(), patch, reverse=True)
        if digest(result) != filehash(backup):
            raise ValueError('Rollback does not match recovery backup')
    # Recheck just before replacement; do not overwrite an independently updated file.
    if filehash(archive) != expected:
        raise ValueError('Archive changed during operation')
    atomic_write(archive, result)
    if filehash(archive) != destination:
        raise ValueError('Written archive verification failed')
    if action == 'uninstall':
        finish_restore(game, [dict(path=archive, desired=destination)])
    return 'INSTALLED' if action == 'install' else 'RESTORED'


def operate_bundle(game, identity, patch, executable_patch, action):
    """Install/restore archive and guarded literal data as one recoverable bundle.

    Recognize original/installed states per component, including interrupted
    transactions. Unknown content is rejected before backup or file writes.
    """
    from executable_text import apply_executable_patch
    game = game.resolve(strict=True)
    if identity['appid'] != 5342930:
        raise ValueError('Unsupported AppID')
    if (patch['original_sha256'],patch['original_size']) != (identity['rom_sha256'],identity['rom_size']):
        raise ValueError('Archive patch identity mismatch')
    if (executable_patch['original_sha256'],executable_patch['original_size']) != (identity['exe_sha256'],identity['exe_size']):
        raise ValueError('Executable patch identity mismatch')
    components = [('rom.zar','original.zar',patch,apply_delta),
                  ('Dementium II.exe','original.exe',executable_patch,apply_executable_patch)]
    plans = []
    for name,backup_name,delta,apply in components:
        path = game/name
        before = path.read_bytes()
        current = digest(before)
        if current not in (delta['original_sha256'],delta['modified_sha256']):
            raise ValueError('Unknown component state: '+name)
        desired = delta['modified_sha256'] if action=='install' else delta['original_sha256']
        backup = backup_path(game, name, backup_name)
        if backup.exists() and filehash(backup)!=delta['original_sha256']:
            raise ValueError('Recovery backup mismatch: '+name)
        if current==delta['modified_sha256'] and not backup.exists():
            raise ValueError('Modified component lacks verified backup: '+name)
        after = before if current==desired else apply(before,delta,action=='uninstall')
        if digest(after)!=desired:
            raise ValueError('Component result mismatch: '+name)
        plans.append(dict(path=path,backup=backup,before=before,after=after,current=current,desired=desired))
    if all(p['current']==p['desired'] for p in plans):
        if action == 'uninstall':
            finish_restore(game, plans)
        return 'ALREADY_INSTALLED' if action=='install' else 'ALREADY_RESTORED'
    if action=='install':
        for p in plans:
            if not p['backup'].exists():
                p['backup'].parent.mkdir(parents=True,exist_ok=True)
                with p['backup'].open('xb') as stream:
                    stream.write(p['before'])
                if filehash(p['backup'])!=p['current']:
                    raise ValueError('Backup write mismatch')
    if any(filehash(p['path'])!=p['current'] for p in plans):
        raise ValueError('Component changed during operation')
    written = []
    try:
        for p in plans:
            if p['current']!=p['desired']:
                atomic_write(p['path'],p['after'])
                written.append(p)
            if filehash(p['path'])!=p['desired']:
                raise ValueError('Written component mismatch')
    except Exception:
        # Preserve the prior mixed/original state rather than leave half an install.
        for p in reversed(written):
            atomic_write(p['path'],p['before'])
        raise
    if action == 'uninstall':
        finish_restore(game, plans)
    return 'INSTALLED' if action=='install' else 'RESTORED'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install', 'uninstall'])
    parser.add_argument('--game', required=True, type=Path)
    parser.add_argument('--identity', type=Path, default=Path(__file__).resolve().parent / 'supported-build.json')
    parser.add_argument('--patch', type=Path, default=Path(__file__).resolve().parent / 'patch.json')
    parser.add_argument('--exe-patch', type=Path, default=Path(__file__).resolve().parent / 'exe-patch.json')
    parser.add_argument('--allow-experimental', action='store_true')
    args = parser.parse_args()
    if not args.allow_experimental:
        parser.error('Experimental build: explicit --allow-experimental is required')
    identity = json.loads(args.identity.read_text(encoding='utf-8'))
    patch = json.loads(args.patch.read_text(encoding='utf-8'))
    executable_patch = json.loads(args.exe_patch.read_text(encoding='utf-8')) if args.exe_patch.is_file() else None
    result = operate_bundle(args.game,identity,patch,executable_patch,args.action) if executable_patch else operate(args.game, identity, patch, args.action)
    print(result + ' sha256=' + filehash(args.game / 'rom.zar') +
          (' exe_sha256='+filehash(args.game/'Dementium II.exe') if executable_patch else '') + ' game_launch=NEVER')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(2)
