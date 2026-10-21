"""Fetch pinned, redistributable font data from its official source; no executables."""
from pathlib import Path
import urllib.request
from localize import digest

COMMIT = 'f8d157532fbfaeda587e826d4cd5b21a49186f7c'
FILES = {
    'Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf': ('NotoSansCJKsc-Regular.otf', '2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b'),
}


def main():
    root = Path(__file__).resolve().parents[1] / 'assets/fonts'
    root.mkdir(parents=True, exist_ok=True)
    for remote, (name, sha) in FILES.items():
        output = root / name
        if output.exists() and digest(output.read_bytes()) == sha:
            print('FONT cached sha256=' + sha)
            continue
        url = f'https://raw.githubusercontent.com/notofonts/noto-cjk/{COMMIT}/{remote}'
        data = urllib.request.urlopen(url, timeout=120).read()
        if digest(data) != sha:
            raise ValueError('Font download hash mismatch')
        output.write_bytes(data)
        print('FONT downloaded sha256=' + sha)


if __name__ == '__main__':
    main()
