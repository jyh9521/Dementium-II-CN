# Pause-control legend corrections (2026-10-22)

## Verified offline

- The keyboard return texture is `TEXTURES/GENERAL/EN/LEGEND_KEYBOARD_BACK.PNG`.
  Negative tracking (`letter_spacing=-1`) merged the two 11px-wide glyph inks.
  Native 12px font strokes now use their normal 12px advance, preserving a
  transparent column between characters. The label begins at x25 rather than
  x26 to fit its 23px visible width in the original 48px texture. The original
  Esc icon remains byte-identical in x0..23 and x24 stays transparent.
  Other controller/return textures are unchanged.
- Native pause draw `FUN_140126a40` places the Y-axis bitmap at (-154,-24).
  The localized label has visible texture bounds (155,221)..(181,232).
  `FUN_140120370` subtracts (86,24) from text coordinates; the actual localized
  font atlas has 11px-high ink beginning 3px down for both 普 and 通.
- Guarded local immediates in `tools/pause_layout.py` change only this status
  draw from (125,220) to (116,218). The visible status therefore starts at
  (30,197), three blank pixels after the colon and at the same ink top.
  Baseline has a twelve-pixel gap and a two-pixel downward offset. These
  constants are not global font/layout parameters. Menu input, reader scroll,
  text content, sign artwork, and all other settings draws are untouched.

## Reproduce

Build normally using `tools/build_locale.py`. Set `DEMENTIUM_PAUSE_TEST_EXE`
and `DEMENTIUM_PAUSE_TEST_ROM` to the resulting EXE and archive, then run:

```powershell
python -X utf8 -m unittest discover -s tests -p test_pause_layout.py -v
```

The same command against `build/reader-input-fix/modified` fails the two reported
symptom checks. Tests read the actual PE immediates and archive raster glyphs,
not source constants or text-box centers. `build/pause-layout-fix/compare.png`
is a nearest-neighbor offline reconstruction of those exact local pixels,
not an in-game screenshot. Actual pause-screen acceptance remains manual.
