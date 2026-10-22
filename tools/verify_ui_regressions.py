"""Offline native UI regressions, preservation and isolated release rollback."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import struct

from localize import Zar, make_delta, write_json
from debug_menu import make_patch

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before', type=Path, required=True)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--installer-before', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--test', action='append', help='Native regression test filename; repeat for independent symptoms')
    p.add_argument('--unchanged-rom', action='store_true', help='Require the complete resource archive to remain identical')
    p.add_argument('--allow-reader-code-change', action='store_true', help='Reader code may change; its entry hooks stay protected')
    p.add_argument('--change-summary', help='Explicit description of the changed branches/fields for this run')
    a = p.parse_args()
    a.before, a.build, a.output = a.before.resolve(), a.build.resolve(), a.output.resolve()
    a.output.mkdir(parents=True, exist_ok=True)
    records = []
    tests = a.test or ['test_menu_pointer_dispatch.py', 'test_pause_layout.py']
    if not a.change_summary:
        a.change_summary = ('Selected native regressions: '+', '.join(tests)+
                            '; archive byte identity required='+str(a.unchanged_rom)+
                            '; reader code changes allowed='+str(a.allow_reader_code_change))
    if any(Path(name).name != name or not name.startswith('test_') or not name.endswith('.py') for name in tests):
        raise ValueError('Use local test filenames only')

    def run(stage, command, folder=None, expected=0):
        env = dict(os.environ)
        if folder:
            env.update(DEMENTIUM_UI_TEST_EXE=str(folder/'Dementium II.exe'),
                       DEMENTIUM_MODIFIED_EXE=str(folder/'Dementium II.exe'),
                       DEMENTIUM_PREVIEW_EXE=str(folder/'Dementium II.exe'),
                       DEMENTIUM_PREVIEW_ROM=str(folder/'rom.zar'),
                       DEMENTIUM_RESTART_TEST_EXE=str(folder/'Dementium II.exe'),
                       DEMENTIUM_RESTART_TEST_ROM=str(folder/'rom.zar'),
                       DEMENTIUM_PAUSE_TEST_EXE=str(folder/'Dementium II.exe'),
                       DEMENTIUM_PAUSE_TEST_ROM=str(folder/'rom.zar'))
        result = subprocess.run([str(x) for x in command], cwd=ROOT, env=env,
                                text=True, encoding='utf8', capture_output=True)
        records.append(dict(stage=stage, command=[str(x) for x in command],
                            input=str(folder or a.build), stdout=result.stdout,
                            stderr=result.stderr, exit_status=result.returncode))
        write_json(a.output/'commands.json', records)
        if result.returncode != expected:
            raise RuntimeError(str(records[-1]))

    for stage, folder, expected in [('BASELINE', a.before, 1), ('MODIFIED', a.build, 0)]:
        for name in tests:
            run(stage+'_'+name, [sys.executable, '-X', 'utf8', ROOT/'tests'/name], folder, expected)
        print(stage+' selected_regressions='+('FAIL_REPRODUCED' if expected else 'PASS'), flush=True)

    old, new = Zar((a.before/'rom.zar').read_bytes()), Zar((a.build/'rom.zar').read_bytes())
    changes = [name for name in old.entries if old.read(name) != new.read(name)]
    if a.unchanged_rom:
        assert not changes and (a.before/'rom.zar').read_bytes() == (a.build/'rom.zar').read_bytes(), changes
    else:
        assert set(changes) <= {'TEXTURES/GENERAL/EN/LEGEND_KEYBOARD_BACK.PNG', '~INDEX'}, changes
    assert old.read('TEX/EN/SIGN_02.PNG') == new.read('TEX/EN/SIGN_02.PNG')
    import pefile
    before = pefile.PE(str(a.before/'Dementium II.exe'))
    after = pefile.PE(str(a.build/'Dementium II.exe'))
    protected = [(0x4fa49, 2), (0x1a7d4b, 3), (0x1a7d81, 15), (0x11b4f7, 10)]
    if a.allow_reader_code_change:
        # Enlarging the field reader moves the following collection renderer.
        # Its native entry stays a 5-byte relative jump plus exact NOP padding;
        # validate the destination instead of requiring its old displacement.
        report=json.loads((a.build/'debug-menu-report.json').read_text(encoding='utf8'))['document_reader']
        for image,expected in [(before,None),(after,int(report['entries']['inventory_render'],16))]:
            hook=image.get_data(0x123379,10)
            assert hook[:1]==b'\xe9' and hook[5:]==b'\x90'*5
            target=0x123379+5+struct.unpack('<i',hook[1:5])[0]
            section=next(s for s in image.sections if s.Name.rstrip(b'\0')==b'.locui')
            assert section.VirtualAddress+0x1000<=target<section.VirtualAddress+0x2000
            assert section.Characteristics&0xa0000000==0x20000000
            if expected is not None:assert target==expected
    else:
        protected.append((0x123379,10))
    if not a.allow_reader_code_change:
        protected.append((0xaf2000, 4096))
    if a.unchanged_rom:
        protected.append((0x126da7, 10))
    for rva, count in protected:
        assert before.get_data(rva, count) == after.get_data(rva, count), hex(rva)
    print('PRESERVATION sign=EXACT F1=EXACT reader_hooks=GUARDED fonts=EXACT other_resources=EXACT PASS', flush=True)
    for name, key in [('rom.zar', 'rom'), ('Dementium II.exe', 'exe')]:
        delta = (make_delta if key == 'rom' else make_patch)(
            (a.before/name).read_bytes(), (a.build/name).read_bytes())
        write_json(a.output/(key+'-upgrade.json'), delta)

    installer = ROOT/'dist/Dementium-II-zh-CN-Setup.exe'
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    retained = {str(path): digest(path) for path in [installer, a.build/'rom.zar', a.build/'Dementium II.exe']}
    rollback_py = a.output/'rollback_installer.py'
    rollback_py.write_text('import hashlib,shutil\nfrom pathlib import Path\n'
        + f'source=Path({str(installer)!r}); original=Path({str(a.installer_before.resolve())!r})\n'
        + f'target=Path({str(a.output/"rollback-test/Setup.exe")!r})\n'
        + f'assert hashlib.sha256(source.read_bytes()).hexdigest()=={digest(installer)!r}\n'
        + 'shutil.copy2(source,target);shutil.copy2(original,target)\n'
        + 'assert target.read_bytes()==original.read_bytes()\n'
        + f'assert hashlib.sha256(source.read_bytes()).hexdigest()=={digest(installer)!r}\n'
        + 'print("ROLLBACK_INSTALLER restored=BYTE_IDENTICAL modified_retained=YES PASS")\n', encoding='utf8')
    script = a.output/'ROLLBACK.sh'
    script.write_text('#!/usr/bin/env bash\nset -eu\n'
        + f'python -X utf8 "{(ROOT/"tools/rollback_upgrade.py").as_posix()}" --modified "{a.build.as_posix()}" --patches "{a.output.as_posix()}" --output "{(a.output/"rollback-test").as_posix()}"\n'
        + f'python -X utf8 "{rollback_py.as_posix()}"\n', encoding='utf8', newline='\n')
    script.chmod(0o755)
    run('ROLLBACK', [Path('C:/Program Files/Git/bin/bash.exe') if os.name == 'nt' else '/bin/bash', script])
    for name in ['rom.zar', 'Dementium II.exe']:
        assert (a.output/'rollback-test'/name).read_bytes() == (a.before/name).read_bytes()
    for path, expected in retained.items():
        assert digest(Path(path)) == expected
    for name in tests:
        run('ROLLBACK_RESTORED_BEHAVIOR_'+name,
            [sys.executable, '-X', 'utf8', ROOT/'tests'/name], a.output/'rollback-test', 1)

    diff = subprocess.run(['git', 'diff', '--binary'], cwd=ROOT, capture_output=True, check=True).stdout
    names = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'], cwd=ROOT,
                           capture_output=True, text=True, check=True).stdout.splitlines()
    for name in names:
        result = subprocess.run(['git', 'diff', '--no-index', '--', 'NUL' if os.name == 'nt' else '/dev/null', name],
                                cwd=ROOT, capture_output=True)
        assert result.returncode == 1
        diff += result.stdout
    (a.output/'DIFF_FILE.patch').write_bytes(diff)
    text = ('CHANGED: '+a.change_summary+'\n'
            f'MODIFIED_FILE: {installer}\nDIFF_FILE: {a.output/"DIFF_FILE.patch"}\n'
            f'VERIFICATION: {a.output/"VERIFICATION.txt"}\nROLLBACK_SCRIPT: {script}\n\n')
    for rec in records:
        text += (rec['stage']+'\nCOMMAND: '+subprocess.list2cmdline(rec['command'])+'\nINPUT: '+rec['input']
                 +'\nSTDOUT: '+rec['stdout']+'\nSTDERR: '+rec['stderr']+'\nEXIT_STATUS: '+str(rec['exit_status'])+'\n\n')
    text += ('RESTORED_STATUS: isolated game files and installer byte-identical to prior fixed release; '
             'selected baseline defects reproduced after rollback. F1, sign, reader hooks and fonts retained.\n'
             'GAME_LAUNCH: NEVER\nRUNTIME_ACCEPTANCE: PENDING manual in-game interaction; native replay is offline.\n'
             +'MODIFIED_HASHES: '+json.dumps(retained)+'\n')
    (a.output/'VERIFICATION.txt').write_text(text, encoding='utf8')
    assert installer.read_bytes()[:2] == b'MZ'
    assert (a.output/'DIFF_FILE.patch').read_bytes().startswith(b'diff --git')
    assert 'EXIT_STATUS:' in (a.output/'VERIFICATION.txt').read_text(encoding='utf8')
    assert script.read_text(encoding='utf8').startswith('#!/usr/bin/env bash')
    print('UI_REGRESSION_VERIFY artifacts=REOPENED rollback=EXACT modified_retained=YES PASS')


if __name__ == '__main__':
    main()
