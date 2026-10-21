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
    backup = game / '.dementium-locale' / 'original.zar'
    if current == destination:
        if action == 'install' and (not backup.exists() or filehash(backup) != patch['original_sha256']):
            raise ValueError('Installed archive has no verified recovery backup')
        return 'ALREADY_' + ('INSTALLED' if action == 'install' else 'RESTORED')
    if current != expected:
        raise ValueError('Archive version/hash mismatch; no files changed')
    if action == 'install':
        if backup.exists() and filehash(backup) != current:
            raise ValueError('Existing recovery backup mismatch')
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
    return 'INSTALLED' if action == 'install' else 'RESTORED'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install', 'uninstall'])
    parser.add_argument('--game', required=True, type=Path)
    parser.add_argument('--identity', type=Path, default=Path(__file__).resolve().parent / 'supported-build.json')
    parser.add_argument('--patch', type=Path, default=Path(__file__).resolve().parent / 'patch.json')
    parser.add_argument('--allow-experimental', action='store_true')
    args = parser.parse_args()
    if not args.allow_experimental:
        parser.error('Experimental build: explicit --allow-experimental is required')
    identity = json.loads(args.identity.read_text(encoding='utf-8'))
    patch = json.loads(args.patch.read_text(encoding='utf-8'))
    result = operate(args.game, identity, patch, args.action)
    print(result + ' sha256=' + filehash(args.game / 'rom.zar') + ' game_launch=NEVER')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(2)
