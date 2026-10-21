"""Create an explicitly experimental, deterministic sparse-patch package."""
import hashlib
import json
from pathlib import Path
import zipfile

from localize import write_json


def text_payload(path):
    # All allowlisted members are UTF-8 text. Normalize host checkout line endings.
    return path.read_text(encoding='utf-8').encode('utf-8')


def main():
    root = Path(__file__).resolve().parents[1]
    files = {
        'patch.json': root / 'build/smoke/patch.json',
        'localize.py': root / 'tools/localize.py',
        'install_patch.py': root / 'tools/install_patch.py',
        'supported-build.json': root / 'assets/supported-build.json',
        'LICENSE': root / 'LICENSE',
        'LICENSE-translations.md': root / 'LICENSE-translations.md',
        'FONT-OFL.txt': root / 'assets/fonts/OFL.txt',
        'README.md': root / 'docs/PROBE_README.md',
    }
    payloads = {name: text_payload(path) for name, path in files.items()}
    manifest = {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()}
    destination = root / 'dist/Dementium-II-zh-CN-technical-probe.zip'
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        payloads['SHA256.json'] = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
        for name, data in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 21, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(files) | {'SHA256.json'}
        for name, expected in manifest.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected
        # The allowlist deliberately excludes every full executable/archive/font.
        assert not any(Path(n).suffix.lower() in ['.exe', '.dll', '.zar', '.otf', '.ttf'] for n in archive.namelist())
    print('PACKAGE files=' + str(len(files) + 1) + ' integrity=PASS sha256=' + hashlib.sha256(destination.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
