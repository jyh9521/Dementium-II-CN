"""Test the packaged installer on copied real files, without starting any EXE."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

from localize import filehash, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    package = root / 'dist/Dementium-II-zh-CN-technical-probe.zip'
    test = root / 'build/package-test'
    bundle = test / 'bundle'
    target = test / 'game-copy'
    bundle.mkdir(parents=True, exist_ok=True)
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package) as archive:
        for name in archive.namelist():
            if not (bundle / name).resolve().is_relative_to(bundle.resolve()):
                raise ValueError('Invalid package path')
        archive.extractall(bundle)
    identity = json.loads((bundle / 'supported-build.json').read_text(encoding='utf-8'))
    for name, key in [('Dementium II.exe', 'exe'), ('rom.zar', 'rom')]:
        assert filehash(args.game / name) == identity[key + '_sha256']
        shutil.copy2(args.game / name, target / name)
    results = []
    for action in ['install', 'install', 'uninstall', 'uninstall']:
        command = ['python', '-X', 'utf8', str(bundle / 'install_patch.py'), action, '--game', str(target), '--allow-experimental']
        done = subprocess.run(command, cwd=bundle, encoding='utf-8', text=True, capture_output=True)
        results.append(dict(command=subprocess.list2cmdline(command), stdout=done.stdout.rstrip(), stderr=done.stderr.rstrip(), exit_status=done.returncode))
        if done.returncode:
            write_json(test / 'results.json', results)
            raise RuntimeError('Packaged installer test failed')
    assert filehash(target / 'rom.zar') == filehash(args.game / 'rom.zar')
    assert filehash(target / '.dementium-locale/original.zar') == identity['rom_sha256']
    write_json(test / 'results.json', results)
    print('PACKAGE_TEST install=PASS idempotence=PASS uninstall=PASS restore=BYTE_IDENTICAL game_launch=NEVER result=PASS')


if __name__ == '__main__':
    main()
