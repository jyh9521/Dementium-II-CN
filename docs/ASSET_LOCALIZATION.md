# Fonts, Artwork and Media Localization

These modules supplement the [data contract](DATA_CONTRACT.md) and [acceptance gates](ACCEPTANCE.md). Select only the modules the game uses.

## 1. Font and dynamic-character coverage

Required coverage is the union of:

- translated display text, verified control-code expansions and formatted UI values;
- intentionally retained originals and all reachable fallback text;
- numerals, signs, units, runtime substitutions and supported player-input characters;
- text loaded from compatible saves, optional resources and supported locale switching.

Record static versus dynamic character sources. For an open input space, define supported ranges, fallback/rejection behavior and tests instead of claiming exhaustive coverage from a static corpus.
Collect glyph requirements from parsed display text, not raw markup syntax alone.
Verify decoding, character map, glyph generation, metrics, measurement, wrapping and rendering together.
Record font file/hash/license, weight/size, rasterizer/version/options, atlas layout, glyph-map order, baseline and line height. Include advance widths, side bearings, kerning, proportional/fixed-width behavior and measurement/rendering scales.
Preserve stable custom glyph IDs across updates when saves or resources depend on them; otherwise document and test a migration.
Test fallback selection, combining sequences and missing-glyph behavior. Enable script-specific shaping, bidirectional layout and grapheme-aware operations only where required, with representative fixtures.
Chinese line breaking and the personal sentence-ending rule are separate concerns; apply [the locale style](../locales/zh-CN/STYLE.md) to visible text.

### Font acceptance

Check required characters before packaging, then observe actual runtime glyphs, spacing, clipping and readability at supported scales.
Include long strings, punctuation, fallback text, dynamic counters and supported player/save names.
Measure atlas/memory/performance costs against project-specific thresholds. Static coverage is not proof of correct shaping or rendering.

## 2. Image text and texture replacements

Inventory each image-text region by stable asset ID, source hash, text meaning/role and target locale.
Preserve editable layers, vector/text sources or a reproducible generation recipe; record fonts and dependencies.
When original artwork is required, generate outputs locally from documented inputs rather than depending on an unexplained edited bitmap.

The design brief records:

- lettering family/weight, outline, shadow, texture and decorative treatment;
- text position, alignment, scale, perspective and relationship to surrounding art;
- background reconstruction and preservation of non-text content;
- native and HD replacement relationships, naming/hash lookup and scaling strategy;
- approved deviations when exact style matching harms readability.

The technical recipe records dimensions, pixel/palette format, alpha, color space, mipmaps, compression, swizzle and container metadata.
Verify all changed mip levels and alpha edges; a correct preview PNG does not prove correct game-texture output.
AI-generated artwork is an editable candidate, not automatically approved typography. Review spelling, glyph forms and non-text changes explicitly.

### Image acceptance

Keep source/target side-by-side comparisons at native scale and a game screenshot of the final candidate.
Review fidelity to the brief, spelling, legibility, placement, transparency, seams and unchanged surrounding art.
Track asset/region coverage separately from string coverage. OCR can help discover text but does not prove complete coverage.

## 3. Subtitles, video and audio references

Keep editable text, timing and style independent from generated video wherever feasible.
Record cue IDs, frame/time base, frame rate, duration, speaker, text role, maximum lines, safe region and project reading-speed limits.
Observe actual playback for onset/offset, overlaps, clipping and audio synchronization, including after remuxing/re-encoding.
Record codec/container, encoder/version/options, bitrate, dimensions, audio sample rate/channel layout and platform constraints; verify duration/frame count and A/V sync.
Preserve audio/event IDs unless their mapping is verified. A display-name change must not break voice lookup.
Narrative subtitles and dialogue retain their applicable language style; system-message subtitles are still `other` text.

## 4. Evidence record

For each module: source hash, editable source/recipe, tool versions, output hash, affected IDs, comparison evidence, runtime configuration, reviewer and gate result.
Use [licensing](../LICENSING.md) for source/output redistribution decisions; keep restricted comparison media outside public release packages.
