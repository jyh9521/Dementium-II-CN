# Paired texture variants: shared geometry and source tone

## Verified (2026-10-21)

The supported original `TEXTURES/HUD/THATWASYOURLASTBREATH.PNG` and
`THATWASYOURLASTBREATH2.PNG` are both 428×240. Their alpha channels are
identical. All 4,171 differing RGB pixels lie within `[93,109,334,138]`,
the lower English lettering and its tone/shadow. The upper line, ornaments,
background, dimensions and positions do not change between these originals.

The previous localized variants were separate art imports. They differed at
53,585 pixels outside the first image's lower light-lettering mask; therefore
they did not preserve this variant relationship.

## Repair

The approved first localized image supplies a common base, including its glyph
positions, upper line, ornaments and background. The second image is rebuilt
from that exact base. Only lower light-ink pixels within `[80,106,350,150]`
receive a tone change; alpha and every other pixel remain byte-identical.

`tools/match_image_variants.py` takes lower-lettering palette samples at matching
positions which contain light ink in both originals. It orders those samples
by luminance and applies their quantiles to the common localized lettering.
The output uses colors from the second original, not invented colors. It does
not regenerate, resize, shift, or independently draw the second image.

The luminance ramp is intentional. A nearest-RGB mapping between the paired
originals produces speckled localized strokes: the original second texture
changes bevel/shadow detail, so similar source RGB values do not uniquely
identify the intended destination tone. Luminance ordering retains the
localized stroke's shading order while matching the second original's palette.

```powershell
python -X utf8 tools/match_image_variants.py `
  --original build/text-layout-fix/original/rom.zar `
  --config locales/zh-CN/image-text.json `
  --source-resource TEXTURES/HUD/THATWASYOURLASTBREATH.PNG `
  --variant-resource TEXTURES/HUD/THATWASYOURLASTBREATH2.PNG `
  --roi 80 106 350 150 --output build/death-image-fix/final
python -X utf8 -m unittest discover -s tests -p test_image_variants.py -v
```

The command writes a one-resource `recipe-patch.json`, not the whole shared
locale configuration. Merge its sole resource entry into `image-text.json`.
The patch remains source-hash-locked through the ordinary image delta pipeline.
Full proprietary textures are local ignored inspection artifacts only.

Offline result: zero differences outside the selected lower ink, identical
alpha, 2,230 selected pixels, and the second variant's 41-color source palette.
The existing numeric centering gate passes (x error +0.5 px). The contact sheet
was inspected at native size. This is raster QA, not a game-render acceptance.
