# 当前翻译数据约定

UTF-8译文位于 locales/zh-CN/*.map.json，按原包重新提取合并，不修改原文和控制码。
术语遵守 GLOSSARY.md。666条已识别记录已有初译，正在逐条审校；实机验收单列。
capacity_bytes=null 表示容量未知，不表示无限制。字母谜题保持原规则。

## 用户指定的标点标准（2026-10-21）

- 剧情、对白、字幕、日记和信件等叙事文本：正常在完整句子结尾使用句号。
- 设置、物体说明、交互/操作提示：若为单句且句中没有其他标点，句尾不加句号。
- 上述非叙事文本若句中有逗号、冒号等标点，可以正常保留句号；不强制为标签添句号。
- 问号、感叹号等具有语义的符号按原意保留；不是删除所有句末标点。
- 控制码、变量、键位占位符和技术标记内部的标点不算自然语言标点，不得修改。
- 规则追溯应用于既有译文，后续使用相同规则。数据记录 narrative/ui 类别供自动检查。

下方保留通用标准；本项目规则及用户最新要求优先。

---

# Translating

This document defines the translation workflow, translation data rules, and text-safety requirements for the localization project.

The current project may target any locale. The translation structure should remain reusable for additional locales whenever technically feasible.

---

# 1. Translation Data Location

Preferred layout:

```text
locales/
  <locale>/
```

Examples:

```text
locales/zh-CN/
locales/zh-TW/
locales/ja-JP/
locales/ko-KR/
```

If the game uses multiple resource groups, organize translation files by function.

Example:

```text
locales/<locale>/
  ui.tsv
  dialogue.tsv
  items.tsv
  subtitles.tsv
  system.tsv
  glossary.tsv
```

Do not mix unrelated translation domains into one file unless the game format requires it.

---

# 2. Source Text Preservation

Whenever possible, preserve a stable source mapping.

Preferred fields include:

- stable ID
- source text
- target text
- speaker
- context
- source file
- resource ID
- technical notes
- length limit

Example TSV:

```text
id	source	translation
1001	New Game	
1002	Load Game	
```

Example JSON:

```json
{
  "id": 1001,
  "source": "New Game",
  "translation": ""
}
```

Do not keep only translated text when the original source can be preserved.

Stable source mapping makes future review, retranslation, and additional locales much easier.

---

# 3. Encoding

Document the exact encoding required by each runtime resource.

Possible cases include:

- ASCII
- UTF-8
- UTF-16LE
- UTF-16BE
- Shift-JIS / CP932
- GBK / CP936
- CP949
- custom multibyte encoding
- glyph-index encoding
- mixed encoding

Repository translation files may use UTF-8 for editing even if the game requires another runtime encoding.

The build system should perform conversion where possible.

Do not save runtime files in a different encoding merely because it is more convenient to edit.

---

# 4. Control Codes

Treat systematic non-language tokens as protected until their behavior is fully understood.

Examples:

```text
{0}
{1}
%s
%d
$n
\n
^xx
<tag>
<color>
\0
```

Unknown recurring sequences should also be treated as control codes until proven otherwise.

Do not:

- translate them
- delete them
- normalize them
- reorder them casually
- change punctuation inside them

unless the format explicitly allows it.

---

# 5. Placeholder Validation

Translations must preserve compatible placeholders.

Example:

```text
Source:
HP: %d / %d

Target:
HP：%d / %d
```

Validation should detect:

- missing placeholders
- added placeholders
- incompatible placeholder types
- broken placeholder syntax
- invalid reordering where order matters

If indexed placeholders are supported, reordering may be allowed only when verified.

---

# 6. Line Breaks

Document how the game represents line breaks.

Possible forms:

```text
\n
$n
0x0A
0x0D 0x0A
custom token
automatic wrapping only
```

Do not add manual line breaks unless required by layout or subtitle timing.

If the engine uses automatic wrapping, prefer natural sentence flow.

If the engine does not wrap automatically, document the width or line-length rules.

---

# 7. Whitespace

Whitespace may be meaningful.

Do not automatically trim:

- leading spaces
- trailing spaces
- tabs
- repeated spaces
- full-width spaces

unless the format has been verified to ignore them.

Some games use spaces for:

- alignment
- indentation
- control padding
- timing
- fixed-width UI layout

Preserve unusual whitespace until its purpose is understood.

---

# 8. String Length Limits

For every resource type, determine whether the string is:

- dynamically sized
- null-terminated
- offset-based
- fixed-slot
- fixed-record
- fixed-byte-length
- fixed-character-count
- limited by UI width
- hard-coded in executable data

Document whether limits are measured in:

- bytes
- characters
- code units
- glyphs

Also determine whether the limit includes:

- null terminator
- control codes
- headers
- padding

Validation should reject dangerous overflows.

---

# 9. UI Width Limits

A string may technically fit in the file but still break the UI.

Document known limits for:

- menu entries
- buttons
- dialogue boxes
- subtitles
- inventory names
- item descriptions
- HUD elements
- save-slot labels

Where possible, create automated width checks using actual font metrics.

If exact checks are not possible, provide warnings for suspiciously long strings.

---

# 10. Terminology

Maintain a project glossary.

Recommended location:

```text
locales/<locale>/glossary.tsv
```

Useful terminology categories include:

- character names
- place names
- organizations
- weapons
- items
- skills
- status effects
- monster names
- class names
- system terminology
- recurring UI messages

Terminology should be consistent across all translation files.

---

# 11. Style Guide

Each locale should define its own language style rules when needed.

Possible topics include:

- punctuation
- quotation marks
- ellipsis
- spacing
- capitalization
- name transliteration
- title formatting
- terminology preferences
- full-width vs half-width characters
- numeral style
- unit formatting
- honorific handling
- profanity handling
- subtitle brevity

Project-specific style decisions should be documented instead of remaining only in contributor memory.

---

# 12. Context

Preserve context whenever possible.

Useful fields include:

```text
speaker
scene
resource file
string ID
screen
character limit
notes
```

Context is especially important when the same source string has multiple possible meanings.

A short source string such as:

```text
Back
```

may mean:

- return to previous menu
- body part
- move backward
- rear side

Do not translate ambiguous strings without checking context where context is available.

---

# 13. Speaker Information

For dialogue-heavy games, preserve speaker metadata where possible.

Example:

```text
id	speaker	source	translation
2001	CHAR_A	Where are you going?	
```

Speaker information helps maintain:

- voice consistency
- gendered wording
- honorifics
- personality
- terminology consistency

Do not infer speaker identity when the resource does not support that conclusion.

---

# 14. Non-Translatable Content

Document strings that must remain unchanged.

Examples:

- script commands
- internal identifiers
- file paths
- resource names
- debug tokens
- save identifiers
- network protocol strings
- executable symbols
- format markers
- checksum-related text

Do not translate text solely because it is human-readable.

---

# 15. Linked Strings

Some strings may be linked across multiple resources.

Examples:

```text
item display name
pickup text
inventory name
document title
script identifier
```

or:

```text
base name
prefixed variant
abbreviated variant
```

If linked strings must remain synchronized, document the relationship and validate it automatically where possible.

Do not edit linked copies independently if a single source can drive them.

---

# 16. Duplicate Source Strings

Identical source text does not always mean identical meaning.

Do not automatically merge translations based only on source text.

Prefer stable IDs and context.

Example:

```text
Open
```

could mean:

- open a door
- open a menu
- open status
- start availability

Only merge entries when semantic equivalence is verified.

---

# 17. Empty Strings

Do not assume an empty string is untranslated.

An empty target may intentionally represent:

- hidden text
- removed UI label
- spacing
- engine fallback
- unused entry

If empty strings are meaningful, document that behavior.

Validation should distinguish between:

- intentionally empty
- untranslated
- missing entry

---

# 18. Source-Language Updates

If the source text changes after an upstream update, translation data should preserve enough information to detect stale translations.

Possible approaches include:

- source-text comparison
- source hash
- version field
- extraction timestamp
- resource revision

Do not silently keep old translations against changed source text without review.

---

# 19. Translation Status

If the project is large, support translation status metadata.

Possible states:

```text
untranslated
draft
reviewed
final
needs-context
needs-technical-review
```

The exact status system may vary by project.

Do not overcomplicate small projects with workflow states that provide no practical value.

---

# 20. Translation QA

Automated checks should detect as many of the following as applicable:

- untranslated entries
- empty translations
- source accidentally copied into target
- duplicate IDs
- invalid encoding
- unsupported characters
- missing glyphs
- placeholder mismatch
- control-code mismatch
- malformed markup
- fixed-slot overflow
- suspicious length
- linked-string inconsistency
- missing required entries
- unknown target-only IDs

Warnings and errors should be separated.

Fatal issues should block release builds.

---

# 21. Character Coverage

Before building fonts or release packages, collect all characters used by the target locale.

The project should verify that every required character is supported by the selected font or glyph system.

Recommended pipeline:

```text
translation files
    ↓
collect unique characters
    ↓
normalize only where safe
    ↓
font coverage check
    ↓
report missing glyphs
```

Do not discover missing glyphs only after launching the game.

---

# 22. Unicode Normalization

Do not normalize text automatically unless the runtime format and rendering system are known to tolerate it.

Normalization may change:

- composed characters
- compatibility forms
- full-width forms
- combining marks

If normalization is required, document the exact form:

```text
NFC
NFD
NFKC
NFKD
```

and explain why.

---

# 23. Punctuation Safety

Punctuation can affect parsers.

Be careful with:

- quotes
- backslashes
- angle brackets
- braces
- semicolons
- commas
- colons
- percent signs
- dollar signs
- escape sequences

Do not replace ASCII punctuation with locale-specific punctuation inside machine-readable syntax.

Example:

```text
<color=red>
```

must not be localized as markup.

---

# 24. Subtitle Translation

For subtitle resources, preserve timing independently from text when possible.

Document:

- line count behavior
- timing format
- maximum lines
- line width
- speaker labels
- forced line breaks
- overlapping subtitles

If subtitles are hard-coded into video, maintain editable subtitle source files separately from generated media.

---

# 25. Voice and Audio References

Do not translate identifiers that are used to resolve voice files or audio events unless the mapping system has been verified.

Keep display text separate from audio IDs where possible.

A translated display name should not accidentally break voice playback.

---

# 26. Adding a New Locale

A new locale should ideally be added by creating:

```text
locales/<new-locale>/
```

with its own:

- translation files
- glossary
- style notes
- locale configuration

Generic tools should not require source-code modification merely to recognize a new locale.

If technical changes are required, determine whether the cause is:

1. an original engine limitation
2. a framework limitation

If the framework limitation can reasonably be generalized, prefer generalization.

---

# 27. Locale Configuration

Where useful, store locale-specific runtime settings separately.

Example:

```json
{
  "locale": "zh-CN",
  "encoding": "cp936",
  "font": "Example Font",
  "fallback_locale": "en-US"
}
```

Possible configuration fields include:

- locale code
- encoding
- font
- font size
- fallback
- punctuation policy
- subtitle width
- build options

Do not hard-code these values into generic tooling if configuration is sufficient.

---

# 28. Translation Review

Before release, review translations in-game.

Text-only review cannot detect all issues.

In-game review should check:

- clipping
- overlap
- wrong context
- speaker mismatch
- awkward line breaks
- subtitle timing
- font readability
- missing text
- control-code breakage
- wrong terminology

Screenshots and scene references may be useful for review.

---

# 29. Machine Translation

Machine translation may be used as an assistant, but it should not be treated as authoritative.

If machine-generated text is used:

- preserve source text
- preserve terminology rules
- protect control codes
- run validation
- review important narrative and UI strings
- mark uncertain entries when useful

Do not allow automated translation to modify protected tokens.

---

# 30. Final Translation Standard

A mature translation layer should allow contributors to:

- understand what each string represents
- safely edit target text
- preserve machine-readable syntax
- validate technical constraints
- maintain consistent terminology
- add another locale without reverse-engineering the entire game again

The translation system should be maintainable independently from the original translator's memory.
