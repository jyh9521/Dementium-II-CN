"""Expanded localization acceptance against original/copied assets, no EXE execution."""
import argparse
import io
import json
from pathlib import Path

from localize import TOKEN, Zar, apply_delta, digest, extract, filehash, import_text, validate
from check_runtime_assets import check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['baseline','modified','rollback'])
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--build', type=Path, default=Path('build/zh-CN'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    identity = json.loads((root/'assets/supported-build.json').read_text(encoding='utf-8'))
    original = (args.game/'rom.zar').read_bytes()
    assert digest(original) == identity['rom_sha256']
    assert filehash(args.game/'Dementium II.exe') == identity['exe_sha256']
    source = Zar(original)
    if args.stage == 'baseline':
        rows = extract(source)
        # Actually run the no-translation import and full resource-preserving rebuild.
        assert source.rebuild(import_text(source, rows)) == original
        assert len(rows)==666
        print('BASELINE records=666 archive=BYTE_IDENTICAL sha256='+digest(original)+' result=PASS')
        return
    modified = (args.build/'rom.zar').read_bytes()
    patch = json.loads((args.build/'patch.json').read_text(encoding='utf-8'))
    assert digest(modified) == patch['modified_sha256']
    if args.stage == 'rollback':
        path = args.build/'rollback-test/rom.zar'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(apply_delta(modified,patch,True))
        assert path.read_bytes() == original
        assert filehash(args.build/'rom.zar') == patch['modified_sha256']
        assert next(r for r in extract(Zar(path.read_bytes())) if r['id']=='EN/GAMEMODE.TBL:0002')['source']=='New Game'
        print('ROLLBACK sha256='+filehash(path)+' text=New Game modified_retained=YES result=PASS')
        return
    from PIL import Image
    from font_pipeline import build_mixed
    records = json.loads((args.build/'text.json').read_text(encoding='utf-8'))
    compiled = json.loads((args.build/'runtime-text.json').read_text(encoding='utf-8'))
    profile = json.loads((root/'locales/zh-CN/font-profile.json').read_text(encoding='utf-8'))
    validate(records,extract(source))
    fonts, expected, info = build_mixed(source,records,profile)
    assert compiled == expected
    after = Zar(modified)
    extracted = {r['id']:r['source'] for r in extract(after)}
    assert all(extracted[r['id']]==r['target'] for r in compiled)
    assert all(TOKEN.findall(a['source'])==TOKEN.findall(b['target']) for a,b in zip(records,compiled))
    assert all(after.read(n)==value for n,value in fonts.items())
    assert apply_delta(original,patch)==modified
    _,mismatches,decoded = check(after)
    assert not mismatches and decoded=='PASS'
    before_meta = json.loads(source.read('FONTS/D2FONT_12X15.JSON'))
    meta = json.loads(after.read('FONTS/D2FONT_12X15.JSON'))
    old = Image.open(io.BytesIO(source.read('FONTS/D2FONT_12X15.PNG'))).convert('RGBA')
    atlas = Image.open(io.BytesIO(after.read('FONTS/D2FONT_12X15.PNG'))).convert('RGBA')
    assert atlas.crop((0,0,*old.size)).tobytes()==old.tobytes()
    replaced = set(info['replaced_original_codes'])
    assert all(meta['glyphs'][k]==v for k,v in before_meta['glyphs'].items() if int(k) not in replaced)
    assert all(meta['glyphs'][str(k)] != before_meta['glyphs'][str(k)] for k in replaced)
    # Decode and bounds-check every referenced glyph and every generated glyph.
    for row in compiled:
        assert all(str(ord(c)) in meta['glyphs'] for c in row['target'] if ord(c)>=32)
    for key,glyph in meta['glyphs'].items():
        assert 0<=int(key)<=65535
        assert 0<=glyph['tx']<glyph['tx']+glyph['w']<=atlas.width
        assert 0<=glyph['ty']<glyph['ty']+glyph['h']<=atlas.height
    for name in source.entries:
        if not (name.startswith('EN/') or name in fonts or name=='~INDEX'):
            assert source.read(name)==after.read(name)
    print('MODIFIED records=666 translated=%d glyphs=%d fallback=%d title_rows=5 replaced_latin=%d preserved=%d vfs=PASS reextract=PASS delta=PASS sha256=%s result=PASS' %
          (sum(r['target']!=r['source'] for r in records),info['added_glyphs'],len(info['body_fallback_codes']),len(replaced),info['original_glyphs_preserved'],digest(modified)))


if __name__ == '__main__':
    main()
