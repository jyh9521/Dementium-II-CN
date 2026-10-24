"""Record baseline/localized/isolated rollback evidence for a verified build."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from localize import Zar, extract, filehash


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    game, build, out = (p.resolve() for p in (args.game, args.build, args.evidence))
    out.mkdir(parents=True, exist_ok=True)
    identity = json.loads((root/'assets/supported-build.json').read_text('utf-8'))
    original = {name: filehash(game/name) for name in ('rom.zar', 'Dementium II.exe')}
    modified = {name: filehash(build/name) for name in original}
    assert original == {'rom.zar': identity['rom_sha256'], 'Dementium II.exe': identity['exe_sha256']}
    rollback = out/'ROLLBACK.sh'
    rollback.write_text('#!/bin/sh\nset -eu\nexec python -X utf8 "'+
        (root/'tools/rollback_locale.py').as_posix()+'" "'+build.as_posix()+
        '" "'+(out/'rollback-copy').as_posix()+'"\n', encoding='utf-8', newline='\n')
    os.chmod(rollback, 0o755)
    stages = [
        ('BASELINE', [sys.executable, '-X', 'utf8', root/'tools/verify_locale.py', 'baseline', '--game', game, '--build', build], game),
        ('MODIFIED', [sys.executable, '-X', 'utf8', root/'tools/verify_locale.py', 'modified', '--game', game, '--build', build], build),
        ('ROLLBACK', ['C:/Program Files/Git/bin/bash.exe', rollback], build),
        ('OPTION_CONTEXT', [sys.executable, '-X', 'utf8', root/'tools/verify_option_context.py', build], build),
    ]
    records = []
    for stage, command, input_path in stages:
        command = [str(c) for c in command]
        done = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding='utf-8')
        record = dict(stage=stage, command=subprocess.list2cmdline(command), input=str(input_path),
                      stdout=done.stdout.rstrip(), stderr=done.stderr.rstrip(), exit_status=done.returncode)
        records.append(record)
        (out/'verification.json').write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(stage+' exit='+str(done.returncode), flush=True)
        if done.returncode:
            raise RuntimeError(done.stdout+done.stderr)
    restored = {name: filehash(out/'rollback-copy'/name) for name in original}
    assert restored == original
    restored_rows = extract(Zar((out/'rollback-copy/rom.zar').read_bytes()))
    assert next(r for r in restored_rows if r['id'] == 'EN/GAMEMODE.TBL:0002')['source'] == 'New Game'
    assert modified == {name: filehash(build/name) for name in original}
    assert original == {name: filehash(game/name) for name in original}
    paths = dict(MODIFIED_FILE=build/'rom.zar', DIFF_FILE=build/'patch.json',
                 VERIFICATION=out/'VERIFICATION.txt', ROLLBACK=rollback)
    lines = ['Changed fields: supported build '+identity['buildid']+'; guarded native address profile; localized EN/font/image members; ~INDEX sizes; head-bob display index 41 -> 48.',
             'Preserved: updated maps/config and all unlocalized members; original installed files and save data.',
             'Restored behavior/status: original EXE/ROM byte-identical in rollback-copy; original New Game text; modified output retained; game_launch=NEVER.',
             *[key+'='+str(path) for key, path in paths.items()],
             'ORIGINAL_HASHES='+json.dumps(original, sort_keys=True),
             'MODIFIED_HASHES='+json.dumps(modified, sort_keys=True)]
    for record in records:
        lines.extend(['', record['stage'], 'COMMAND: '+record['command'], 'INPUT: '+record['input'],
                      'STDOUT: '+record['stdout'], 'STDERR: '+record['stderr'], 'EXIT_STATUS: '+str(record['exit_status'])])
    paths['VERIFICATION'].write_text('\n'.join(lines)+'\n', encoding='utf-8', newline='\n')
    for path in paths.values():
        with path.open('rb') as stream:
            assert stream.read(1)
    print('BUILD_UPDATE stages=4 original_unchanged=YES modified_retained=YES artifacts_reopened=4 result=PASS')


if __name__ == '__main__':
    main()
