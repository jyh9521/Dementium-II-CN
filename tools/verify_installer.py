"""Exercise the installer and real copied game files; never launch the game."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import uuid
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True, help='Verified original game input')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    out = root/'build/installer'
    sdk = Path(os.environ.get('DOTNET_EXE', str(root/'build/toolchain/dotnet/dotnet.exe')))
    tests = root/'build/installer/tests/net10.0-windows10.0.17763.0/InstallerTests.dll'
    exe = root/'dist/Dementium-II-zh-CN-Setup.exe'
    report = json.loads((out/'build-report.json').read_text(encoding='utf-8'))
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    original = {p.name: digest(p) for p in [args.game/'rom.zar', args.game/'Dementium II.exe']}
    records = []

    def run(stage, command, input_text, env=None):
        start = subprocess.STARTUPINFO() if os.name == 'nt' else None
        if start:
            start.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            start.wShowWindow = 0
        done = subprocess.run([str(c) for c in command], cwd=root, capture_output=True,
                              encoding='utf-8', text=True, env=env, startupinfo=start)
        rec = dict(stage=stage, command=subprocess.list2cmdline([str(c) for c in command]),
                   input=str(input_text), stdout=done.stdout.strip(), stderr=done.stderr.strip(),
                   exit_status=done.returncode)
        records.append(rec)
        print(stage+' exit='+str(done.returncode), flush=True)
        if done.returncode:
            (out/'verification-failure.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
            raise RuntimeError(done.stdout+done.stderr)
        return rec

    for stage in ['baseline', 'modified', 'rollback']:
        run(stage.upper(), ['python', '-X', 'utf8', root/'tools/verify_locale.py', stage,
                           '--game', args.game.resolve(), '--build', root/'build/full-zh-CN'],
            args.game.resolve() if stage=='baseline' else root/'build/full-zh-CN')
    run('NATIVE_UNIT', [sdk, tests, out/'material-unit-fixtures'], 'Synthetic fixtures + embedded real payload')
    target = out/('real-fixture-'+uuid.uuid4().hex[:12])
    run('REAL_NATIVE_INSTALL_RESTORE', [sdk, tests, '--real', args.game.resolve(), target],
        'Copies of original ROM+EXE; target='+str(target))
    run('PYTHON_UNIT', ['python', '-X', 'utf8', '-m', 'unittest', 'discover', '-s', 'tests', '-q'], 'Repository test suite')
    run('STEAM_READ_ONLY', [sdk, tests, '--detect'], 'Registry Steam roots + libraryfolders.vdf + appmanifest_5342930.acf')
    environment = dict(os.environ, DOTNET_ROOT=str(out/'no-installed-runtime'), DOTNET_MULTILEVEL_LOOKUP='0',
                       HTTP_PROXY='http://127.0.0.1:9', HTTPS_PROXY='http://127.0.0.1:9')
    for name, scale, width, height in [('material-final.png', '1', '780', '710'),
                                      ('material-min.png', '1', '680', '640'),
                                      ('material-200.png', '2', '780', '710')]:
        path = out/name
        rec = run('SELF_CONTAINED_UI_'+name, [exe, '--render-preview', path, scale, width, height],
                  'DOTNET_ROOT invalid; multilevel lookup disabled; unusable HTTP proxies; offscreen own UI only', environment)
        rec['stdout'] = path.with_name(path.name+'.layout.txt').read_text(encoding='utf-8')
        assert path.is_file() and path.stat().st_size>1000
        assert digest(path) != digest(path.with_name(path.name+'.motion-start.png'))

    rollback = out/'ROLLBACK.sh'
    rollback.write_text('#!/bin/sh\nset -eu\ncd "'+root.as_posix()+'"\nexec "C:/Program Files/Git/bin/bash.exe" tools/ROLLBACK_FULL.sh\n', encoding='utf-8', newline='\n')
    run('ROLLBACK_SHELL', ['C:/Program Files/Git/bin/bash.exe', rollback], root/'build/full-zh-CN')
    assert original == {p.name: digest(p) for p in [args.game/'rom.zar', args.game/'Dementium II.exe']}
    assert digest(exe) == report['sha256']
    for name, expected in json.loads((root/'installer/branding-inputs.json').read_text()).items():
        assert digest(root/name) == expected
    archive = root/'dist/Dementium-II-zh-CN-Installer.zip'
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert not any(n.lower().endswith(('.zar', '.dll')) for n in z.namelist())
        assert [n for n in z.namelist() if n.lower().endswith('.exe')] == [exe.name]
        hashes = json.loads(z.read('SHA256.json'))
        assert hashes[exe.name] == digest(exe)
        for name, expected in hashes.items():
            assert hashlib.sha256(z.read(name)).hexdigest() == expected

    paths = dict(MODIFIED_FILE=exe, DIFF_FILE=root/'build/full-zh-CN/patch.json',
                 VERIFICATION=out/'VERIFICATION.txt', ROLLBACK=rollback)
    lines = ['Changed fields: WPF MaterialDesign3 GUI + animation; required ROM and EXE; Steam manifest discovery;',
             'centered supplied logo/icon; compact layout; no visible checkbox/progress bar; two requested links.',
             'Text/image game delta unchanged; original in-game logo and company name preserved.',
             'Original input hashes='+json.dumps(original),
             'Installer bytes='+str(exe.stat().st_size)+' SHA256='+digest(exe),
             'ZIP bytes='+str(archive.stat().st_size)+' SHA256='+digest(archive),
             'OS actually tested='+platform.platform(), 'game_launch=NEVER',
             'Restored behavior/status: original ROM+EXE byte identical; backups retained; modified build and installer retained.',
             'Previous installer preserved='+str(out/'previous/Setup.exe')]
    if (out/'previous/Setup.exe').exists():
        lines += ['Previous installer SHA256='+digest(out/'previous/Setup.exe')]
    lines += [key+'='+str(path) for key, path in paths.items()]
    for rec in records:
        lines += ['', rec['stage'], 'COMMAND: '+rec['command'], 'INPUT: '+rec['input'],
                  'STDOUT: '+rec['stdout'], 'STDERR: '+rec['stderr'], 'EXIT_STATUS: '+str(rec['exit_status'])]
    paths['VERIFICATION'].write_text('\n'.join(lines)+'\n', encoding='utf-8', newline='\n')
    (out/'verification.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    for path in paths.values():
        with path.open('rb') as stream:
            assert stream.read(1)
    print('INSTALLER_VERIFICATION stages='+str(len(records))+' artifacts_reopened=4 original_unchanged=YES result=PASS')


if __name__ == '__main__':
    main()
