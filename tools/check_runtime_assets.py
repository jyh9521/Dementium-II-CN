"""Offline replay of VFS-declared lengths and image decode, never game startup."""
import argparse
import io
from pathlib import Path
import sys

from localize import Zar, index_rows


def check(zar):
    from PIL import Image
    rows = list(index_rows(zar.read('~INDEX')))
    mismatches = []
    for name, size, flags, offset in rows:
        if name in zar.entries and flags == 0 and size != zar.entries[name].size:
            mismatches.append((name, size, zar.entries[name].size))
    font = 'FONTS/D2FONT_12X15.PNG'
    size = next(size for name, size, _, _ in rows if name == font)
    try:
        image = Image.open(io.BytesIO(zar.read(font)[:size]))
        image.load()
        decoded = 'PASS'
    except (OSError, ValueError) as exc:
        decoded = 'FAIL(' + str(exc) + ')'
    return rows, mismatches, decoded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    rows, mismatches, decoded = check(Zar(args.archive.read_bytes()))
    for name, declared, actual in mismatches:
        print(f'VFS_MISMATCH {name} declared={declared} actual={actual}')
    result = not mismatches and decoded == 'PASS'
    print(f'VFS_REPLAY entries={len(rows)} mismatches={len(mismatches)} font_decode={decoded} game_launch=NEVER result=' + ('PASS' if result else 'FAIL'))
    return 0 if result else 1


if __name__ == '__main__':
    sys.exit(main())
