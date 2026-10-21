"""Package the native installer, instructions and licenses without game assets."""
import hashlib
import json
from pathlib import Path
import zipfile


def main():
    root=Path(__file__).resolve().parents[1];out=root/'dist/Dementium-II-zh-CN-Installer.zip'
    files={'Dementium-II-zh-CN-Setup.exe':root/'dist/Dementium-II-zh-CN-Setup.exe',
           '使用说明.txt':root/'docs/INSTALLER_README.txt','LICENSE':root/'LICENSE',
           'LICENSE-translations.md':root/'LICENSE-translations.md',
           'Fusion-Pixel-OFL.txt':root/'assets/fonts/Fusion-Pixel-OFL.txt',
           'ChillBitmap-LICENSE.md':root/'assets/fonts/ChillBitmap-LICENSE.md'}
    files.update({'licenses/'+p.name:p for p in (root/'installer/licenses').glob('*.txt')})
    data={name:(p.read_bytes() if p.suffix=='.exe' else p.read_text(encoding='utf-8').encode('utf-8')) for name,p in files.items()}
    hashes={name:hashlib.sha256(raw).hexdigest() for name,raw in data.items()}
    data['SHA256.json']=(json.dumps(hashes,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,raw in sorted(data.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,21,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.create_system=3;info.external_attr=0o100644<<16
            z.writestr(info,raw,compresslevel=9)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None and set(z.namelist())==set(data)
        for name,expected in hashes.items():assert hashlib.sha256(z.read(name)).hexdigest()==expected
    print('INSTALLER_PACKAGE members=%d bytes=%d sha256=%s result=PASS'%(len(data),out.stat().st_size,hashlib.sha256(out.read_bytes()).hexdigest()))


if __name__=='__main__':main()
