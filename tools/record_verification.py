"""Record exact offline commands and results; never execute the game."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from localize import filehash, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    stages = []
    for stage in ['baseline', 'modified', 'rollback']:
        command = ['python', '-X', 'utf8', str(root / 'tools/verify.py'), stage, '--game', str(args.game)]
        done = subprocess.run(command, cwd=root, text=True, encoding='utf-8', capture_output=True)
        record = dict(stage=stage.upper(), command=subprocess.list2cmdline(command), input=str(args.game / 'rom.zar') if stage == 'baseline' else str(root / 'build/smoke/rom.zar'), stdout=done.stdout.rstrip(), stderr=done.stderr.rstrip(), exit_status=done.returncode)
        stages.append(record)
        if done.returncode:
            write_json(root / 'build/verification-failure.json', stages)
            raise RuntimeError('Offline verification failed: ' + stage)
    paths = {'MODIFIED_FILE': root / 'build/smoke/rom.zar', 'DIFF_FILE': root / 'build/smoke/patch.json',
             'VERIFICATION': root / 'build/VERIFICATION.txt', 'ROLLBACK': root / 'tools/ROLLBACK.sh'}
    original = json.loads((root / 'build/inventory/game-manifest.json').read_text(encoding='utf-8'))['files']
    assert all(filehash(args.game / f['path']) == f['sha256'] for f in original)
    lines = ['Dementium II offline verification / 2026-10-21',
             'changed field: rom.zar!EN/GAMEMODE.TBL:0002 New Game -> 新游戏; font JSON/PNG append three glyphs; ~INDEX synchronizes three size fields',
             'runtime: NOT_TESTED; game launch: NOT_PERFORMED by this verification',
             'original installation: ALL_8_FILES_HASH_UNCHANGED',
             'restored behavior: extracted menu text New Game; original archive SHA-256 restored; runtime behavior untested', '']
    for name, path in paths.items(): lines.append(name + '=' + str(path))
    for record in stages:
        lines.extend(['', record['stage'], 'COMMAND: ' + record['command'], 'INPUT: ' + record['input'],
                      'STDOUT: ' + record['stdout'], 'STDERR: ' + record['stderr'], 'EXIT_STATUS: ' + str(record['exit_status'])])
    paths['VERIFICATION'].write_text('\n'.join(lines) + '\n', encoding='utf-8')
    write_json(root / 'build/verification.json', stages)
    for name, path in paths.items():
        with path.open('rb') as stream:
            assert stream.read(1), name + ' is empty'
    print('VERIFICATION stages=3 original_files=8 artifacts_reopened=4 result=PASS')


if __name__ == '__main__':
    main()
