# 当前技术实现

ZAR1双索引重建、UTF-8提取/回写和BMP字形机制见 [技术报告](docs/TECHNICAL_ANALYSIS.md)。
新增 OPEN/UNLOCK 交互资源后，实际英文文本清单为179资源、676条记录。
英文与正文Fusion12、章节中文ChillBitmap16；图形标签采用受哈希和像素区域约束的重建配方。
5个PC菜单固定字面量仍仅改只读数据槽；新F1菜单另使用受版本/字节守卫的native-menu-pe-v1代码与只读PE数据节改动，安装器可同时恢复EXE与资源。
用户已提供部分中文实机画面；完整实机QA仍待进行。所有新构建/验证均不启动游戏。
下方保留技术证据分类及记录标准。


---

# Technical Notes

This document records technical findings, reverse-engineering results, implementation details, and unresolved technical questions for the localization project.

The purpose is to preserve knowledge so future contributors do not need to rediscover the same behavior from scratch.

---

# 1. Evidence Classification

Important technical claims should be classified as one of:

- Verified
- High-confidence deduction
- Unverified hypothesis

Do not present speculation as established fact.

When possible, include the evidence used to reach a conclusion.

Examples:

```text
Verified:
Changing byte 0x1234 from 0x15 to 0x2B increases the accepted input length.

High-confidence deduction:
Field 0x18 appears to store the string byte length because all observed entries match.

Unverified hypothesis:
Control code $D04 may select a speaker portrait.
```

---

# 2. Supported Game Build

Record the exact analyzed version.

Include when applicable:

```text
Game:
Platform:
Region:
Distribution:
Version:
Executable:
File size:
SHA-256:
```

Any documented address, offset, binary patch, or file structure should be assumed valid only for the tested versions unless otherwise verified.

---

# 3. Text Resource Map

Document every known location that contains user-visible text.

Example:

| Resource | Purpose | Encoding | Editable | Notes |
|---|---|---|---|---|
| UI.DAT | menus | CP932 | yes | fixed slots |
| SCRIPT.BIN | dialogue | custom | yes | offset table |
| GAME.EXE | system text | ASCII | patch | hard-coded |

Include:

- menus
- dialogue
- subtitles
- item names
- descriptions
- tutorials
- names
- system messages
- credits
- hard-coded strings

Do not assume all visible text comes from the same source.

---

# 4. File Format Overview

For each custom format, document:

- filename or extension
- magic
- header structure
- entry count
- pointer tables
- string tables
- length fields
- alignment
- compression
- checksums
- indexes
- unknown fields

Detailed structures should be moved to:

```text
docs/FILE_FORMATS.md
```

Use this file for high-level relationships and implementation notes.

---

# 5. Text Encoding

Document the actual runtime encoding.

Possible cases include:

- ASCII
- UTF-8
- UTF-16
- Shift-JIS / CP932
- GBK / CP936
- CP949
- custom multibyte encoding
- glyph-index encoding
- mixed encoding

Record:

- byte ranges
- lead-byte rules
- trail-byte rules
- terminators
- invalid sequence behavior
- control-code interaction
- fallback behavior

If decoding occurs in executable code, document the relevant function or patch point.

---

# 6. String Storage

Determine how each string is stored.

Possible forms:

- null-terminated
- fixed-slot
- offset + length
- pointer table
- record structure
- compressed block
- script token stream
- executable constant

Document whether the stored length represents:

- bytes
- characters
- code units
- glyphs

Also note whether the length includes:

- null terminator
- control codes
- padding
- headers

---

# 7. Text Extraction

Document how source text is extracted.

Include:

- tool name
- source files
- parsing rules
- output format
- stable IDs
- ordering guarantees
- duplicate handling

If extraction requires heuristics, describe them.

If some strings cannot currently be extracted automatically, list them explicitly.

---

# 8. Text Reinsertion

Document how translated text is written back.

Include:

- target resource
- encoding conversion
- offset recalculation
- length recalculation
- pointer updates
- checksum updates
- archive rebuilding
- fixed-slot handling
- overflow behavior

If reinsertion is not fully reversible, explain the limitation.

---

# 9. Control Codes

Document known control codes.

Example table:

| Code | Meaning | Status |
|---|---|---|
| `$n` | line break | Verified |
| `$D04` | unknown | Unverified |
| `{0}` | format placeholder | Verified |

Record whether control codes:

- consume display width
- affect line count
- change speaker
- change color
- trigger animation
- select portrait
- insert variables

Unknown codes should remain preserved.

---

# 10. Font System

Document the font implementation.

Investigate:

- font file format
- texture format
- atlas layout
- glyph order
- character map
- glyph dimensions
- advance width
- kerning
- baseline
- line height
- fallback
- missing-glyph behavior
- proportional vs fixed-width behavior

If the font system uses multiple files, document their relationship.

Example:

```text
font texture
+ glyph map
+ width table
+ renderer logic
```

Do not assume one component is sufficient.

---

# 11. Glyph Mapping

Document how characters map to glyphs.

Possible methods:

- direct byte index
- code page lookup
- Unicode table
- custom character table
- two-byte lookup
- hash table
- executable mapping function

Record:

- input code
- lookup process
- glyph index
- fallback behavior

If custom mappings are introduced by the localization, document the format.

---

# 12. Font Metrics

Document how text width is calculated.

Possible data includes:

- advance width
- left bearing
- right bearing
- kerning
- fixed cell width
- scaling factor

Record whether width is stored as:

- integer pixels
- fixed-point value
- normalized value
- texture-relative value

Incorrect metrics can cause:

- clipping
- overlap
- wrong alignment
- broken wrapping
- oversized dialogs

---

# 13. Text Rendering Pipeline

Describe the rendering pipeline as far as known.

Example:

```text
resource string
→ decoder
→ control-code parser
→ glyph lookup
→ metrics lookup
→ layout
→ vertex generation
→ renderer
```

If the localization hooks or replaces part of this pipeline, document exactly where.

Include:

- function names if known
- module names
- vtable entries
- RVA or file offsets where useful
- calling convention
- input/output expectations

Only record addresses for verified game versions.

---

# 14. UI Layout

Document text-layout constraints.

Examples:

- fixed-width boxes
- hard-coded pixel widths
- menu row height
- subtitle region
- maximum lines
- logical resolution
- physical resolution scaling
- alignment rules
- clipping regions

Note any mismatch between:

- logical coordinates
- actual resolution
- font pixel size
- renderer scale

---

# 15. Binary Patches

For every executable patch, document:

- target file
- supported hash/version
- offset or RVA
- original bytes
- replacement bytes
- purpose
- validation rule
- failure behavior

Example:

```text
Target:
GAME.EXE

Offset:
0x00123456

Original:
15 00 00 00

Replacement:
2B 00 00 00

Purpose:
Increase maximum text input length.
```

Patch tools must verify expected original bytes before writing.

---

# 16. Runtime Hooks

If the project uses runtime hooking, document:

- proxy DLL strategy
- import redirection
- function hook
- vtable hook
- trampoline
- patch location
- loader behavior

Record:

- target function
- reason for hook
- expected call flow
- thread-safety concerns
- initialization order
- compatibility risks

---

# 17. Archive Formats

Document all relevant archive/container formats.

Examples:

- AFS
- POD
- VPP
- RES
- PAK
- custom container

Record:

- header
- file table
- offsets
- lengths
- alignment
- compression
- checksums
- filename table
- manifests
- secondary metadata

Do not assume archive TOC data is the only metadata the engine uses.

---

# 18. Secondary Manifests

Some games store duplicated file-size or index data outside the primary archive table.

Document any such files.

Examples:

- size manifests
- file indexes
- path tables
- hash tables
- lookup databases

Failure to update secondary metadata may cause:

- truncated reads
- out-of-bounds reads
- missing resources
- crashes

---

# 19. Linked Resources

Document resources that must be updated together.

Examples:

```text
item name
pickup message
inventory name
document title
scene reference
```

or:

```text
base character name
prefixed character name
abbreviated character name
```

If changing one without another breaks logic, record the dependency explicitly.

---

# 20. Hard-Coded Strings

Maintain a list of known hard-coded strings.

Possible locations:

- EXE
- ELF
- DLL
- scripts
- compiled UI data
- resource metadata
- shader constants

Document:

- location
- encoding
- length limit
- patch method
- whether resizing is safe

Hard-coded strings should not be assumed to participate in the normal translation pipeline.

---

# 21. Save Data and Identifiers

Determine whether visible strings are also used as internal identifiers.

Do not translate identifiers that affect:

- save loading
- quest state
- inventory keys
- script references
- network protocol
- resource lookup

Document cases where display text and logic identifiers share storage.

---

# 22. Script Logic Risks

Some text resources may contain executable script data or branching identifiers.

Document:

- commands
- labels
- jump targets
- variable names
- condition tokens
- function names

Do not translate script logic tokens.

If source text and logic are mixed in one file, extraction tools should separate them safely.

---

# 23. Compression

Document compression used by localization-relevant resources.

Record:

- algorithm
- header
- decompression tool
- recompression requirements
- alignment
- size limits

If exact recompression is not possible, document acceptable differences.

---

# 24. Checksums and Hashes

Document integrity checks such as:

- CRC32
- MD5
- SHA variants
- custom checksums
- hash tables

Record:

- what data is covered
- where the checksum is stored
- how it is recalculated
- whether the engine verifies it

---

# 25. File Alignment

Document alignment requirements.

Examples:

```text
4-byte
16-byte
2048-byte sector
0x800-byte block
```

Incorrect alignment can break resource loading even if offsets appear correct.

---

# 26. Platform-Specific Notes

Record platform-specific behavior.

Possible platforms:

- Windows
- Linux
- PS2
- PS3
- PSP
- Xbox
- Switch
- other consoles

Examples:

- endianness
- executable format
- filesystem case sensitivity
- sector layout
- emulator behavior
- platform font APIs

Do not assume behavior from one platform applies to another.

---

# 27. Emulator and Runtime Testing

If emulators or compatibility layers are used, record:

- emulator name
- tested version
- renderer/backend
- known compatibility differences
- debugging features used

Examples:

- PCSX2
- RPCS3
- Wine
- Proton

Do not confuse emulator-specific bugs with game-engine bugs without verification.

---

# 28. Known Failures

Record reproducible technical failures.

Examples:

- crash on long translated string
- missing glyph
- archive read failure
- font metrics corruption
- save incompatibility
- broken subtitle timing
- invalid pointer table
- unsupported game build

Detailed troubleshooting history should go in:

```text
docs/PITFALLS.md
```

---

# 29. Failed Approaches

Preserve meaningful failed experiments.

For each failed approach, record:

- goal
- method
- observed result
- why it failed
- whether the conclusion is verified

Example:

```text
Attempt:
Replace only the font texture.

Result:
Characters displayed, but layout was incorrect.

Conclusion:
The game uses a separate width table.
```

Failed research may save future contributors significant time.

---

# 30. Open Questions

Maintain unresolved technical questions.

Example:

```text
- Unknown meaning of field 0x18 in SCRIPT.BIN.
- Control code $D04 may be speaker-related.
- Width table may use fixed-point values.
```

Do not remove unresolved questions simply because the current patch works.

---

# 31. Upstream Research

Record external technical work used by the project.

Include:

- project name
- author
- URL
- commit/tag/release
- reused components
- independently verified findings
- license

Do not present upstream discoveries as original work.

---

# 32. Tool Inventory

Maintain a list of technical tools used by the project.

Example:

| Tool | Purpose | Source |
|---|---|---|
| extractor | text extraction | project |
| packer | archive rebuild | upstream |
| font builder | glyph atlas | project |
| disassembler | binary analysis | external |

Document proprietary dependencies separately.

---

# 33. Test Cases

Maintain minimal technical test cases where practical.

Useful cases include:

- ASCII-only string
- multibyte string
- punctuation
- long string
- line break
- placeholder
- control code
- unsupported character
- fixed-slot boundary
- archive replacement

These help detect regressions.

---

# 34. Regression Testing

When technical changes affect rendering, archives, encoding, or patching, retest previously working cases.

At minimum, verify:

- game boots
- menus render
- dialogue renders
- saves load
- scene transitions work
- patched resources load
- no new missing glyphs
- no new validation errors

---

# 35. Documentation Update Rule

When a verified technical discovery changes, update this document or the relevant specialized document in the same change whenever practical.

Do not leave obsolete technical claims in documentation.

---

# 36. Final Technical Standard

A mature technical implementation should allow future contributors to understand:

- where text lives
- how it is encoded
- how it is rendered
- how fonts work
- how archives are rebuilt
- how binaries are patched
- which resources are linked
- which assumptions are verified
- which questions remain unresolved

The goal is to preserve enough technical knowledge that future localization work can build on the project rather than repeat the same reverse engineering.

## 原生菜单与原像素UI修复

新增只读非执行`.locmenu`节，现有RIP引用与有DIR64重定位的表指针指向该节；保留ASLR、原生回调和存档实现。仅F1键码与隐藏菜单门禁分支为逻辑修改。详见`docs/NATIVE_CHEAT_MENU.md`。操作图不再整图重绘，原按键/箭头/连线/透明度采用源像素保护；配对死亡图以共同几何基底及原版色阶构建，见`docs/NATIVE_UI_IMAGE_REPAIR.md`及`docs/IMAGE_VARIANT_TONES.md`。
