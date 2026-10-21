"""Record failing VFS-length replay and corrected output without game startup."""
import json
from pathlib import Path
import subprocess

from localize import Zar, filehash, write_json


def main():
    root = Path(__file__).resolve().parents[1]
    bad = root / 'build/failures/stb-load/rom.zar'
    good = root / 'build/smoke/rom.zar'
    records = []
    for label, path, expected in [('BASELINE', bad, 1), ('MODIFIED', good, 0)]:
        command = ['python', '-X', 'utf8', str(root / 'tools/check_runtime_assets.py'), str(path)]
        done = subprocess.run(command, cwd=root, text=True, encoding='utf-8', capture_output=True)
        assert done.returncode == expected
        records.append(dict(stage=label, command=subprocess.list2cmdline(command), input=str(path), sha256=filehash(path), stdout=done.stdout.rstrip(), stderr=done.stderr.rstrip(), exit_status=done.returncode))
    old, new = Zar(bad.read_bytes()), Zar(good.read_bytes())
    for name in ['EN/GAMEMODE.TBL', 'FONTS/D2FONT_12X15.JSON', 'FONTS/D2FONT_12X15.PNG']:
        assert old.read(name) == new.read(name)
    write_json(root / 'build/font-fix-verification.json', dict(game_launch='NEVER', payloads_unchanged=True, results=records))
    text = ['VFS font startup fix / offline replay only', 'PNG and JSON payloads unchanged; only secondary directory lengths repaired', 'Game launch: NEVER', '']
    for record in records:
        text += [record['stage'], 'COMMAND: ' + record['command'], 'INPUT: ' + record['input'], 'SHA256: ' + record['sha256'], 'STDOUT: ' + record['stdout'], 'EXIT_STATUS: ' + str(record['exit_status']), '']
    text += ['Rollback and original hashes: see VERIFICATION.txt', 'Game startup and Chinese display: PENDING_USER_RETEST']
    (root / 'build/FONT_FIX_VERIFICATION.txt').write_text('\n'.join(text) + '\n', encoding='utf-8', newline='\n')
    print('FONT_FIX baseline=FAIL_EXPECTED modified=PASS payloads_unchanged=PASS game_launch=NEVER result=PASS')


if __name__ == '__main__':
    main()
