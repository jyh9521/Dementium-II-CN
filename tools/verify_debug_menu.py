"""Verify actual built native-menu executable/font and emit static glyph preview.

No game startup. Native input replay runs bounded copied instruction snippets in
the test process; glyph preview uses the actual packaged TTF, not a mock font.
"""
import argparse
import io
import json
import mmap
import os
from pathlib import Path
import subprocess
import sys

from debug_menu import build_menu, build_font, config, glyph_text, make_patch
from executable_text import build_executable, apply_executable_patch
from font_pipeline import resolve_fonts
from localize import Zar, digest, write_json


ROOT = Path(__file__).resolve().parents[1]


def read_member(path, name):
    with path.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
        return Zar(data).read(name)


def main():
    from fontTools.ttLib import TTFont
    from PIL import Image, ImageDraw, ImageFont
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True, help='locked original directory')
    parser.add_argument('--build', type=Path, required=True, help='built modified directory')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or args.build / 'debug-menu-verification'
    output.mkdir(parents=True, exist_ok=True)
    recipe = json.loads((ROOT / 'locales/zh-CN/executable-text.json').read_text(encoding='utf8'))
    original = (args.game / 'Dementium II.exe').read_bytes()
    baseline, _ = build_executable(original, recipe)
    expected, report = build_menu(baseline)
    modified_path = args.build / 'Dementium II.exe'
    actual = modified_path.read_bytes()
    if actual != expected:
        raise ValueError('Actual built EXE differs from reproducible native-menu build')
    patch = json.loads((args.build / 'exe-patch.json').read_text(encoding='utf8'))
    if apply_executable_patch(original, patch) != actual:
        raise ValueError('Actual build patch does not reproduce EXE')
    restored = apply_executable_patch(actual, patch, True)
    if restored != original:
        raise ValueError('Actual build rollback differs from exact original EXE')
    if make_patch(original, expected) != patch:
        raise ValueError('Actual build patch manifest is not reproducible')
    profile = json.loads((ROOT / 'locales/zh-CN/font-profile.json').read_text(encoding='utf8'))
    font_path = resolve_fonts(profile)['body']
    with (args.game / 'rom.zar').open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
        expected_font = build_font(Zar(data), font_path)
    packaged_font = read_member(args.build / 'rom.zar', 'TUFFY_BOLD.TTF')
    if packaged_font != expected_font:
        raise ValueError('Actual ROM debug TTF differs from reproducible subset')
    face = TTFont(io.BytesIO(packaged_font))
    required = set(map(ord, glyph_text(config())))
    missing = required - face.getBestCmap().keys()
    if missing:
        raise ValueError('Actual ROM font missing required glyphs: ' + repr(sorted(missing)))
    font = ImageFont.truetype(io.BytesIO(packaged_font), 24)
    for code in required - {32}:
        if font.getmask(chr(code)).getbbox() is None:
            raise ValueError('Actual ROM font contains a blank required glyph: ' + chr(code))
    labels = list(config()['labels'].values())
    rows = (len(labels) + 1) // 2
    column = max(640, max(int(font.getlength(text)) for text in labels) + 48)
    image = Image.new('RGB', (column * 2, rows * 34 + 84), (24, 25, 28))
    draw = ImageDraw.Draw(image)
    draw.text((18, 16), 'Native menu font subset - static proof (not in-game)', font=font, fill=(220, 220, 220))
    for index, text in enumerate(labels):
        x = 18 + (index // rows) * column
        y = 64 + (index % rows) * 34
        draw.text((x, y), text, font=font, fill=(245, 245, 245))
    preview_path = output / 'debug-menu-font-preview.png'
    image.save(preview_path)
    with Image.open(preview_path) as reopened:
        reopened.load()
        if reopened.size != image.size:
            raise ValueError('Preview reopen size differs')
    environment = dict(os.environ, DEMENTIUM_SOURCE_EXE=str((args.game / 'Dementium II.exe').resolve()),
                       DEMENTIUM_SOURCE_ROM=str((args.game / 'rom.zar').resolve()),
                       DEMENTIUM_MODIFIED_EXE=str(modified_path.resolve()))
    commands = []
    for script in ('tests/test_debug_input.py', 'tests/test_debug_menu.py'):
        command = [sys.executable, '-X', 'utf8', str(ROOT / script)]
        result = subprocess.run(command, cwd=ROOT, env=environment, text=True, capture_output=True)
        commands.append(dict(command=command, input=dict(source_exe=environment['DEMENTIUM_SOURCE_EXE'],
                            source_rom=environment['DEMENTIUM_SOURCE_ROM'], modified_exe=str(modified_path.resolve())),
                             stdout=result.stdout, stderr=result.stderr, exit_status=result.returncode))
        if result.returncode:
            print(result.stdout + result.stderr)
            raise ValueError('Native-menu verification tests failed')
    result = dict(schema=1, original_sha256=digest(original), baseline_literal_sha256=digest(baseline),
                  modified_sha256=digest(actual), rollback_sha256=digest(restored),
                  baseline='Native gate requires allow-opening; isolated CPU replay passed',
                  modified='F1 toggle/debounce, menu-visible game input/cursor gates, native health mask and two ammo decrement blocks replayed; PE/ASLR/font checks passed',
                  rollback='Exact original executable bytes/hash and locked gate restored in isolated copy',
                  font_sha256=digest(packaged_font), glyphs=len(required), missing_glyphs=[],
                  labels=len(labels), menu_report=report, commands=commands,
                  preview=str(preview_path.resolve()), game_launch='NEVER',
                  remaining_acceptance='Rendered in-game menu, OS pointer focus and gameplay effects require in-game QA')
    write_json(output / 'verification.json', result)
    reopened = json.loads((output / 'verification.json').read_text(encoding='utf8'))
    assert reopened['modified_sha256'] == digest(actual)
    print('NATIVE_MENU_VERIFY labels=%d glyphs=%d missing=0 input_cpu=PASS health_ammo_cpu=PASS pe_aslr=PASS font=PASS rollback=EXACT game_launch=NEVER result=PASS' %
          (len(labels), len(required)))


if __name__ == '__main__':
    main()
