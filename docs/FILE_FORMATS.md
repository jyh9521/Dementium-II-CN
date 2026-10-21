# 已实现格式入口

ZAR1、UTF-8 行表/字幕/文档及 d1-rgba 字体的准确字段和证据见 [TECHNICAL_ANALYSIS.md](TECHNICAL_ANALYSIS.md)。
实现：tools/localize.py；合成测试：tests/test_localize.py。
外层包重定位不等于内部 UI 长度已验证。
下方保留通用记录标准，模板示例不代表本游戏实际结构。

---

# File Formats

This document records reverse-engineered file formats used by the localization project.

Use this file for concrete binary or structured format documentation such as headers, offsets, field sizes, alignment, compression, checksums, string tables, pointer tables, and archive metadata.

High-level implementation notes belong in `TECHNICAL.md`.

---

# 1. Documentation Rules

For every documented format, include as much of the following as known:

- filename or extension
- purpose
- platform
- endianness
- magic
- version
- header size
- entry count
- offsets
- lengths
- alignment
- compression
- checksum behavior
- string encoding
- pointer tables
- filename tables
- secondary manifests
- unknown fields
- parser or builder implementation
- confidence level

Important claims should be classified as:

- Verified
- High-confidence deduction
- Unverified hypothesis

Do not assign meanings to unknown fields without evidence.

---

# 2. Format Entry Template

Use this template when documenting a new format.

```markdown
## FORMAT_NAME

**Purpose:**
Describe what the file stores.

**Platform:**
Describe where it is used.

**Status:**
Verified / High-confidence / Unverified

**Known files:**
- example.ext
- another.ext

**Endianness:**
Little-endian / Big-endian / Mixed / Unknown

**Encoding:**
ASCII / UTF-8 / UTF-16 / CP932 / CP936 / CP949 / Custom / Unknown

**Magic:**
`XX XX XX XX`

**Header size:**
`0x00`

**Alignment:**
4 bytes / 16 bytes / 0x800 bytes / Unknown

**Compression:**
None / algorithm / Unknown

**Structure:**

| Offset | Size | Type | Meaning | Status |
|---|---:|---|---|---|
| 0x00 | 4 | u32 | magic | Verified |
| 0x04 | 4 | u32 | entry count | Verified |

**Entry structure:**

| Offset | Size | Type | Meaning | Status |
|---|---:|---|---|---|
| 0x00 | 4 | u32 | data offset | Verified |
| 0x04 | 4 | u32 | data length | Verified |

**Notes:**
Additional behavior.

**Unknown fields:**
- offset 0x10
- offset 0x14

**Tools:**
- `tools/extract_format.py`
- `tools/build_format.py`
```

---

# 3. Integer Types

Use consistent notation.

Recommended types:

```text
u8
s8
u16
s16
u32
s32
u64
s64
f32
f64
char[n]
bytes[n]
```

If a field uses fixed-point representation, document it explicitly.

Examples:

```text
u16 8.8 fixed-point
s32 16.16 fixed-point
```

---

# 4. Endianness

Always document endianness where binary integer fields are involved.

Possible values:

- little-endian
- big-endian
- mixed-endian
- platform-native
- unknown

Do not infer endianness solely from the platform if the format has not been verified.

---

# 5. Offsets

For every offset, specify what it is relative to.

Possible bases include:

- file start
- current structure start
- current entry start
- data section start
- archive start
- decompressed block start

Example:

```text
string_offset:
u32 little-endian
relative to the beginning of the string table
```

Do not write only "offset" when the base is ambiguous.

---

# 6. Length Fields

Document what each length represents.

Possible meanings:

- byte length
- character count
- code-unit count
- glyph count
- compressed size
- decompressed size
- aligned size
- size including terminator
- size excluding terminator

Example:

```text
text_length:
number of encoded bytes
does not include trailing 0x00
```

This distinction is especially important for multibyte localization.

---

# 7. Alignment

Document alignment rules precisely.

Examples:

```text
entries aligned to 4 bytes
payloads aligned to 0x10 bytes
files aligned to 0x800-byte sectors
```

Record whether padding bytes are:

- zero
- 0xFF
- preserved from original
- ignored
- unknown

Incorrect alignment may break loading even when offsets appear valid.

---

# 8. String Storage

Document how strings are represented.

Possible forms:

- null-terminated
- fixed-width field
- offset + length
- string-table index
- pointer
- inline script token
- compressed string block
- glyph index stream

Record:

- encoding
- terminator
- length semantics
- alignment
- duplicate-string behavior
- whether empty strings are allowed

---

# 9. String Tables

If the format uses a string table, document:

- table start
- entry count
- indexing method
- duplicate handling
- encoding
- alignment
- offset base
- whether strings are sorted

Example:

```text
entry.name_offset
→ relative to string_table_start
→ null-terminated CP932
```

---

# 10. Pointer Tables

If pointer-like values exist, determine whether they are:

- file offsets
- virtual addresses
- relative offsets
- indexes
- sector numbers
- runtime pointers

Do not assume an integer that increases monotonically is a file offset without verification.

---

# 11. Record Arrays

For fixed-size record arrays, document:

- record size
- record count
- padding
- field order
- unused slots

Example:

```text
record_size = 0x20
record_count = header.entry_count
```

If the final record differs from the others, note it explicitly.

---

# 12. Variable-Length Records

For variable-length records, document how boundaries are determined.

Possible methods:

- length prefix
- next offset
- terminator
- sentinel value
- block table
- parser state machine

If malformed input causes unsafe reads, document the failure behavior.

---

# 13. Archive Formats

For archives, document at minimum:

- file count
- TOC location
- filename table
- data offsets
- file lengths
- alignment
- compression
- ordering
- checksums
- secondary metadata

Also determine whether the game relies on:

- an external index
- a size manifest
- hash table
- path database
- fixed file ordering

Do not assume rebuilding the primary archive alone is sufficient.

---

# 14. Secondary Metadata

Some formats use metadata outside the main container.

Examples:

- size manifests
- lookup indexes
- filename hashes
- dependency tables
- scene indexes

Document these relationships explicitly.

Example:

```text
DATA.AFS
↔ DATA_INDEX.BIN
```

If both must be updated together, record the dependency in `TECHNICAL.md` as well.

---

# 15. Compression

Document compression behavior.

Include:

- algorithm
- header
- block size
- compression flags
- decompressed size
- recompression requirements
- tool compatibility

If decompression is understood but compression is not, state that clearly.

Do not describe a format as "supported" if only extraction works.

---

# 16. Checksums

Document checksums and hashes.

Possible algorithms include:

- CRC16
- CRC32
- Adler-32
- MD5
- SHA variants
- custom hash
- rolling checksum

Record:

- covered byte range
- stored location
- byte order
- initialization value
- final XOR
- whether padding is included

If the algorithm is unknown, preserve the field and mark it unknown.

---

# 17. Filename Hashes

If filenames are hashed, document:

- normalization
- case handling
- slash direction
- encoding
- hash algorithm
- collision behavior

Example:

```text
input:
lowercase ASCII path with backslashes

algorithm:
FNV-1a 32-bit
```

Do not infer a hash algorithm from a small number of examples.

---

# 18. Compression Flags

If entries use flags, document each verified bit separately.

Example:

| Bit | Meaning | Status |
|---:|---|---|
| 0 | compressed | Verified |
| 1 | encrypted | Unverified |
| 2 | streaming | High-confidence |

Do not assign meanings to unknown bits.

---

# 19. Script Formats

For script-like formats, document:

- opcode size
- argument encoding
- string references
- jump targets
- labels
- control flow
- embedded text
- variable references

Translation tools must distinguish text from executable script logic.

Do not rewrite script tokens as natural-language text.

---

# 20. Font Formats

For font resources, document:

- texture format
- atlas dimensions
- glyph order
- character map
- width table
- metrics
- baseline
- line height
- fallback glyph
- maximum glyph count

If the font system spans multiple files, document the relationship.

---

# 21. Texture Formats

If localization requires editing textures, document:

- dimensions
- pixel format
- palette
- swizzling
- alpha format
- mipmaps
- container header
- alignment

If standard formats are embedded inside custom containers, note both layers.

---

# 22. Subtitle Formats

For subtitle resources, document:

- timing units
- time base
- line structure
- text encoding
- speaker metadata
- style metadata
- line-count limits

If timing is frame-based, document frame rate assumptions.

---

# 23. Video Containers

If localization requires video processing, document:

- container type
- video codec
- audio codec
- subtitle handling
- multiplexing behavior
- alignment
- platform-specific constraints

Do not confuse container format with codec format.

---

# 24. Audio Formats

If text references audio assets, document relevant metadata such as:

- event ID
- filename mapping
- index tables
- sample rate
- codec
- channel count

Do not translate internal audio identifiers unless verified safe.

---

# 25. Save Formats

If localization touches save-related data, document:

- text fields
- identifiers
- checksums
- version fields
- string encoding

Visible names may also be logic identifiers.

Do not modify save structures without understanding compatibility impact.

---

# 26. Executable Data Tables

If strings or font tables are embedded in executables, document:

- file offset
- RVA
- virtual address
- section name
- record size
- relocation behavior

Clearly distinguish:

```text
file offset
RVA
runtime virtual address
```

Do not mix these concepts.

---

# 27. Sector-Based Formats

Console formats may use sector-relative addressing.

Document:

- sector size
- base sector
- offset calculation
- padding
- filesystem relationship

Examples:

```text
sector size = 0x800
byte_offset = sector_index * 0x800
```

Verify rather than assume.

---

# 28. Platform Notes

Record platform-specific format behavior.

Examples:

- PS2 DMA alignment
- little-endian MIPS data
- Xbox sector alignment
- PC filesystem paths
- console disc image constraints

Keep platform assumptions separate from format facts.

---

# 29. Unknown Fields

Unknown fields should remain visible in documentation.

Example:

| Offset | Size | Meaning |
|---|---:|---|
| 0x10 | 4 | unknown |

Do not delete unknown fields from diagrams just because the current tooling preserves them.

Preserving unknown bytes may be necessary for safe rebuilding.

---

# 30. Rebuild Strategy

For each format, state whether the project uses:

- in-place patching
- full rebuild
- append-and-repoint
- block replacement
- archive reconstruction
- runtime override

Document why the chosen strategy is safe.

---

# 31. Round-Trip Testing

Where possible, test:

```text
original file
→ extract
→ rebuild without modification
→ compare
```

Possible outcomes:

- byte-identical
- structurally equivalent
- functionally equivalent
- not yet reproducible

Document the expected level.

A non-byte-identical rebuild may still be valid if differences are understood.

---

# 32. Sample Data

Use minimal samples where legally and practically appropriate.

Prefer:

- synthetic examples
- short byte sequences
- structure diagrams
- tiny excerpts

Avoid embedding substantial copyrighted game content.

---

# 33. Parser Safety

Custom parsers should validate:

- file size
- header bounds
- entry count sanity
- offsets within file
- lengths within bounds
- integer overflow
- truncated data
- malformed records

Do not trust game files blindly.

---

# 34. Builder Safety

Custom builders should validate:

- encoded string lengths
- alignment
- offset range
- checksum generation
- required metadata
- entry count
- output size

Fail clearly rather than generating ambiguous broken files.

---

# 35. Version Differences

If format behavior differs between game versions or regions, document each variant separately.

Example:

```text
US version:
record size = 0x20

JP version:
record size = 0x24
```

Do not merge incompatible variants into one undocumented assumption.

---

# 36. Tool Mapping

For each documented format, list the tools that operate on it.

Example:

```text
Format:
SCRIPT.BIN

Extractor:
tools/extract_script.py

Builder:
tools/build_script.py

Validator:
tools/validate_script.py
```

This makes technical documentation directly actionable.

---

# 37. Open Questions

Keep unresolved format questions visible.

Example:

```text
- Unknown meaning of header field 0x18.
- Entry flag bit 2 may control streaming.
- Final 4 bytes may be a checksum.
```

Do not erase unanswered questions when the current implementation works.

---

# 38. Project-Specific Formats

Add actual game-specific format documentation below this line.

Remove unused template examples when adapting the file to a real project.

---

# 39. Final File Format Standard

A mature format document should allow another developer to understand:

- how the file is structured
- which fields are verified
- how text is stored
- how offsets and lengths work
- how alignment works
- which metadata must be updated
- how to extract and rebuild the file
- which parts remain unknown

The goal is to preserve enough knowledge that future localization work does not require repeating the same binary-format reverse engineering.

## native-menu-pe-v1（2026-10-21）

独立于fixed-slot-utf8-v1的精确版本PE差分：original_size、modified_size、original_sha256、modified_sha256、排序不重叠的runs（offset/old/new等长十六进制）与append（base64追加字节）。原版/修改版完整身份、每段期望字节、追加尺寸和结果哈希全部验证后才写出；反向应用截回original_size。新增.locmenu只读不可执行节，用RIP相对引用及已有DIR64重定位的表指针引用UTF-8数据。不放宽旧只读文字槽格式的范围约束，不把它作为跨版本固定偏移补丁。语言文本在locales/<locale>/debug-menu.json，通用实现见tools/debug_menu.py。
