"""Offline acceptance evidence. No subprocess or game-launch code is used."""
import argparse
from collections import Counter
import io
import json
from pathlib import Path
import sys

from localize import Zar, apply_delta, digest, extract, filehash, import_text, validate, write_json
from check_runtime_assets import check as check_vfs


def baseline(game, project):
    identity = json.loads((project / 'assets/supported-build.json').read_text(encoding='utf-8'))
    data = (game / 'rom.zar').read_bytes()
    assert digest(data) == identity['rom_sha256']
    assert filehash(game / 'Dementium II.exe') == identity['exe_sha256']
    zar = Zar(data)
    _, mismatches, decoded = check_vfs(zar)
    assert not mismatches and decoded == 'PASS'
    rows = extract(zar)
    # Reconstruct every extracted byte span, including identity replacements.
    replacements = {}
    for name in {r['resource'] for r in rows}:
        raw = zar.read(name)
        for row in sorted((r for r in rows if r['resource'] == name), key=lambda r: r['offset'], reverse=True):
            o = row['offset']; raw = raw[:o] + row['source'].encode('utf-8') + raw[o + row['source_bytes']:]
        assert raw == zar.read(name)
        replacements[name] = raw
    assert zar.rebuild(replacements) == data
    for language in ['EN', 'DE', 'FR', 'IT', 'SP']:
        extracted = extract(zar, language)
        validate(extracted, extracted)
    return f'BASELINE members={len(zar.entries)} records={len(rows)} resources={len(replacements)} roundtrip=BYTE_IDENTICAL result=PASS'


def modified(game, project):
    from PIL import Image
    src = Zar((game / 'rom.zar').read_bytes())
    built = project / 'build/smoke'
    out = Zar((built / 'rom.zar').read_bytes())
    patch = json.loads((built / 'patch.json').read_text(encoding='utf-8'))
    assert apply_delta(src.data, patch) == out.data
    rows = json.loads((project / 'locales/zh-CN/smoke.json').read_text(encoding='utf-8'))
    actual = {r['id']: r for r in extract(out)}
    for row in rows:
        assert actual[row['id']]['source'] == (row['target'] or row['source'])
    changed = [n for n in src.entries if src.read(n) != out.read(n)]
    assert changed == ['EN/GAMEMODE.TBL', 'FONTS/D2FONT_12X15.JSON', 'FONTS/D2FONT_12X15.PNG', '~INDEX']
    _, mismatches, decoded = check_vfs(out)
    assert not mismatches and decoded == 'PASS'
    assert len(out.entries) == len(src.entries)
    old_meta = json.loads(src.read('FONTS/D2FONT_12X15.JSON'))
    new_meta = json.loads(out.read('FONTS/D2FONT_12X15.JSON'))
    for key, value in old_meta['glyphs'].items():
        assert new_meta['glyphs'][key] == value
    old = Image.open(io.BytesIO(src.read('FONTS/D2FONT_12X15.PNG'))).convert('RGBA')
    new = Image.open(io.BytesIO(out.read('FONTS/D2FONT_12X15.PNG'))).convert('RGBA')
    assert new.crop((0, 0, old.width, old.height)).tobytes() == old.tobytes()
    for row in rows:
        for c in row['target']:
            if ord(c) < 32: continue
            glyph = new_meta['glyphs'][str(ord(c))]
            x, y, w, h = (glyph[k] for k in ['tx', 'ty', 'w', 'h'])
            assert 0 <= x < x + w <= new.width and 0 <= y < y + h <= new.height
            if c not in ' \t':
                assert new.crop((x, y, x + w, y + h)).getchannel('A').getbbox()
    preview = Image.new('RGBA', (120, 25), (24, 24, 24, 255))
    x = 3
    for c in '新游戏':
        g = new_meta['glyphs'][str(ord(c))]
        part = new.crop((g['tx'], g['ty'], g['tx'] + g['w'], g['ty'] + g['h']))
        preview.alpha_composite(part, (x, 4)); x += g['logw'] + 1
    preview.resize((720, 150), Image.Resampling.NEAREST).save(built / 'font-preview.png')
    return 'MODIFIED changed=4 text=New Game -> 新游戏 glyphs=3 delta=PASS reextract=PASS vfs=PASS runtime=NOT_TESTED result=PASS'


def rollback(game, project):
    built = project / 'build/smoke'
    patch = json.loads((built / 'patch.json').read_text(encoding='utf-8'))
    modified = (built / 'rom.zar').read_bytes()
    restored = apply_delta(modified, patch, reverse=True)
    dest = project / 'build/rollback/rom.zar'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(restored)
    assert filehash(dest) == filehash(game / 'rom.zar')
    assert filehash(built / 'rom.zar') == patch['modified_sha256']
    text = next(r['source'] for r in extract(Zar(dest.read_bytes())) if r['id'] == 'EN/GAMEMODE.TBL:0002')
    assert text == 'New Game'
    return 'ROLLBACK sha256=' + digest(restored) + ' text=New Game original_status=RESTORED modified_copy=RETAINED result=PASS'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['baseline', 'modified', 'rollback'])
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(globals()[args.stage](args.game, args.project))


if __name__ == '__main__':
    main()
