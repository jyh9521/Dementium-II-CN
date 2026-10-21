"""Deterministic full-localization sparse bundle. Never ship complete game assets."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from package_probe import text_payload


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,default=Path('build/full-zh-CN'))
    parser.add_argument('--output',type=Path,default=Path('dist/Dementium-II-zh-CN-preview.zip'))
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    files={
        'patch.json':args.build/'patch.json','exe-patch.json':args.build/'exe-patch.json',
        'release-manifest.json':args.build/'release-manifest.json',
        'localize.py':root/'tools/localize.py','executable_text.py':root/'tools/executable_text.py',
        'install_patch.py':root/'tools/install_patch.py','supported-build.json':root/'assets/supported-build.json',
        'LICENSE':root/'LICENSE','LICENSE-translations.md':root/'LICENSE-translations.md',
        'Fusion-Pixel-OFL.txt':root/'assets/fonts/Fusion-Pixel-OFL.txt',
        'ChillBitmap-LICENSE.md':root/'assets/fonts/ChillBitmap-LICENSE.md',
        'README.md':root/'docs/PLAYER_README.md',
    }
    payloads={name:text_payload(path) for name,path in files.items()}
    hashes={name:hashlib.sha256(data).hexdigest() for name,data in payloads.items()}
    payloads['SHA256.json']=(json.dumps(hashes,indent=2,sort_keys=True)+'\n').encode()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(payloads.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,21,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.create_system=3;info.external_attr=0o100644<<16
            archive.writestr(info,data,compresslevel=9)
    with zipfile.ZipFile(args.output) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist())==set(payloads)
        for name,digest in hashes.items():assert hashlib.sha256(archive.read(name)).hexdigest()==digest
        assert not any(Path(n).suffix.lower() in ('.exe','.dll','.zar','.png','.ttf','.otf') for n in archive.namelist())
    print('FULL_PACKAGE files=%d sha256=%s integrity=PASS' % (len(payloads),hashlib.sha256(args.output.read_bytes()).hexdigest()))


if __name__=='__main__':main()
