# Research, Format and Diagnostic Records

Shared recording requirements only; these are not new game findings. Keep actual findings in [TECHNICAL](../TECHNICAL.md), structures in [FILE_FORMATS](FILE_FORMATS.md), and failed approaches in [PITFALLS](PITFALLS.md).

## Resource inventory

| Resource/ID | Visible content | Encoding/format | Dependencies | Scope | Evidence |
|---|---|---|---|---|---|
| Example entry (not a game finding) | Content role | Known format or unknown | Linked resources | included/excluded/undetermined | Evidence locator |

Cover menus, dialogue, subtitles, HUD, items, tutorials, system messages, credits, image text, executable constants and dynamic/fallback text.
Link [coverage accounting](ACCEPTANCE.md) rather than keeping conflicting totals here.

## Finding record

```text
Finding ID and claim:
Confidence: verified / high_confidence_deduction / unverified_hypothesis
Tested input/build:
Method and exact reproduction:
Observed evidence and locator:
Alternative explanations / unknowns:
Implementation and regression-test references:
Affected versions and revalidation trigger:
```

## Engine investigation checklist

| Area | Record actual behavior |
|---|---|
| Encoding | Lead/trail bytes, terminators, invalid sequences, decoder and conversion |
| Extraction | Source map, parser/heuristics, stable IDs, ordering, missed resources |
| Reinsertion | Strategy, pointer/length updates, overflow and unrelated-byte preservation |
| Tokens | Grammar, meaning/confidence, width/timing/portrait/variable effects |
| Rendering | Decoder → token parser → glyph mapping/metrics → layout → draw |
| Font/layout | Maps, metrics, fallback, logical vs physical coordinates, wrapping/clipping |
| Runtime hook | Module/function, ABI, lifecycle, initialization, recursion and threading |
| Archives | TOC, compression, alignment, checksums and secondary manifests |
| Linked data | Mirrored text, filenames, item/script/save/audio identifiers |
| Compatibility | Platform endianness/paths, emulator version/backend, mod/loader conflicts |

Distinguish visible text from internal keys. Investigate save compatibility before translating shared identifiers.
Resource files and secondary manifests must be rebuilt together when the engine depends on both.

## Executable patch record

Target manifest entry; address kind (file offset/RVA/runtime address); expected bytes; replacement/algorithm; purpose; ABI/control-flow assumptions; verification; failure behavior; rollback reference.
Validate instruction boundaries, branch displacements, calling convention and cache/loader behavior when applicable.
Keep each supported variant explicit; unknown builds use no silent offset fallback.

## Tool and upstream inventory

For each tool/component: purpose, source URL, pinned revision/version, reused code/findings, independent verification, license and build/configuration instructions.
Keep undocumented binaries out of the required toolchain.


## Format record template

```text
Format ID, purpose and known files:
Platform/region/version and input hashes:
Confidence and supporting evidence:
Parser / builder / validator / tests:
Magic, version and endianness:
Header, entry count, record sizes:
Sections, offsets and their exact bases:
Integer signedness/width, fixed-point representation:
Lengths: bytes/code units/glyphs; terminator/padding inclusion:
String encoding, null/empty/duplicate representation:
String-table indexing/sorting and archive entry ordering:
Variable-record boundaries, final-record exceptions and bit-level flag meanings:
Compression algorithm/header/flags and recompression constraints:
Alignment and padding-byte preservation:
Checksums: range, stored location, byte order, initialization, final XOR:
Filename hashes: normalization, encoding, slash/case behavior, collisions:
External manifests and linked resources:
Unknown fields and how they are preserved:
Rebuild strategy and allowed differences:
Round-trip comparison and evidence:
Malformed-input behavior and negative fixtures:
Variant differences and unresolved questions:
```

Use tables with offset, size, type, meaning and confidence for headers/entries.
Types may be `u8/s8/u16/s16/u32/s32/u64/s64/f32/f64/bytes[n]`; specify byte order instead of assuming it from the platform.
State whether pointer-like fields are indexes, file offsets, sector numbers, RVA or runtime addresses.
Distinguish absolute offsets from entry-, table-, archive- and decompressed-block-relative offsets.

## Specialized fields

- Scripts: opcode/argument grammar, labels/jumps, variables and display-text boundaries.
- Fonts: atlas, character map, metrics, fallback and maximum glyph count.
- Textures: pixel format, palette, alpha, mipmaps, swizzle and container layers.
- Subtitles: time base, frame rate, cue/style/speaker fields and line constraints.
- Video/audio: container versus codec, muxing, sample rate/channel count, event IDs and asset lookup.
- Saves: identifiers, serialization limits, checksums and version/locale compatibility.
- Executables: section, relocation behavior and address-kind mapping.
- Disc/sector formats: sector size, base, alignment and filesystem relationships.

## Parser and builder requirements

Validate bounds, entry counts, truncated data, integer overflow, overlapping regions where invalid, lengths, offsets and output sizes.
Preserve unknown fields. Reject inputs that would require guessing data boundaries or integrity fields.
Avoid archive path traversal and extraction collisions; enforce a selected output root.
Before translation, run extraction → rebuild without edits → comparison.
Then test a changed string, maximum lengths, duplicates and linked metadata.
Record byte-identical or an explicitly defined structural/runtime equivalence under [acceptance](ACCEPTANCE.md).
Document extraction-only support as extraction-only, not complete rebuild support.
Use invented minimal fixtures for public tests and retain private-input integration procedures separately.


## Lesson template

```text
Lesson ID / affected version and component:
Initial assumption:
Method and exact input:
Observed result and evidence:
Cause and confidence:
Failed approaches and why they failed:
Working solution and side effects:
Detection / regression test:
Related implementation, format and issue records:
```

Preserve meaningful failed research, not every temporary output. Archive evidence with stable references and remove only disposable reproductions.
Do not promote an inferred cause to verified merely because a workaround helped.

## Research prompts, not established game findings

| Area | Common trap to test |
|---|---|
| Binary patches | Wrong address kind/version, instruction boundary, branch displacement or ABI |
| Encoding | Byte length confused with characters/glyphs; normalization or trimming damages syntax |
| Font | Atlas changed without map/metrics; glyph order changes; dynamic/fallback coverage missed |
| UI | Measurement and drawing use different scales; replacement happens after wrapping |
| Archive | TOC updated but secondary size/index/checksum metadata remains stale |
| Linked data | Display name also serves as a save/script/audio/resource key |
| Spreadsheet | IDs lose zeros, dates/formulas auto-convert, tabs/quotes/newlines change |
| Build | Old output masks failure; undeclared PATH/font/tool dependency |
| Runtime hook | Early/late initialization, recursion, threading and proxy-loader conflicts |
| Emulator | Renderer/timing differences mistaken for proven game-format behavior |
| Media | Re-encoding shifts timing or changes platform-compatible muxing |
| Filesystem | Unicode/spaces/long paths, case-only collisions and symlink escapes |
| Git | Shared docs/fixtures ignored; line endings or executable bits lost |
| Release | Package differs from tested developer output; private input/logs accidentally included |

For spreadsheet workflows, specify and test import/export settings; changing CSV to TSV alone does not prevent auto-conversion.
For every consequential fix, add a synthetic regression when feasible and a private/runtime procedure when needed.
