# Translation Workflow Standard

Use [the data contract](DATA_CONTRACT.md) for fields and states, and [acceptance](ACCEPTANCE.md) for completion claims.
Language-specific decisions live under `locales/<locale>/`; the included [Chinese style](../locales/zh-CN/STYLE.md) is a personal policy, not generic engine behavior.

Actual catalogs, terminology and project constraints remain in [TRANSLATING](../TRANSLATING.md). This workflow does not replace them.

## Translator workflow

1. Confirm the source revision and resource ID. Inspect scene, speaker and UI context where available.
2. Classify `text_role` by content: story, dialogue or other. Leave uncertain classification `unknown` pending review.
3. Consult the locale glossary and style guide; preserve characterization, intent, ambiguity and register.
4. Translate only display text. Preserve protected commands, placeholders, identifiers and meaningful whitespace.
5. Set an explicit disposition for deliberately empty or unchanged text, with reason.
6. Run contract and game-adapter checks; resolve errors and review warnings.
7. Have the text reviewed against the current source and context; record its source fingerprint.
8. Inspect the actual game presentation and link runtime evidence separately.

An automated or machine-translated draft must remain a draft until reviewed. Record unresolved meaning instead of inventing a speaker or interpretation.
Review all included content before a complete-scope claim, not just prominent narrative strings.
Resolve technical limits by an approved wording/layout/engine solution. Removing meaning, hiding text or marking entries excluded merely to improve validation or coverage is not an accepted translation fix.

## Locale package

Keep translations, glossary, style and locale configuration together. Define:

- terminology, name transliteration, character voice and treatment of honorifics/profanity;
- punctuation, quotation marks, numerals, spacing, units and line-breaking conventions;
- required font/style, runtime encoding adapter, fallback policy and subtitle limits;
- handling of proper names, player-generated text and intentionally retained originals.

The glossary should identify concept/context, preferred translation, forbidden variants and source of the decision.
Do not merge identical source words when their contexts differ. Keep verified mirrored strings synchronized from one source.
Adding a locale should normally add data/configuration, not rewrite generic tools.

## Technical review checklist

- Token multiplicity, type, syntax and allowed reordering match the engine grammar.
- Escapes, tags, line breaks and null terminators remain valid.
- Encoded length includes the correct terminator/header/padding rules.
- Actual font metrics satisfy layout limits; byte fit alone is insufficient.
- Required static, fallback and dynamic glyphs are covered under [asset rules](ASSET_LOCALIZATION.md).
- UI text, save identifiers, voice events, script keys and network strings are distinguished.
- Source/context changes invalidate review and affected runtime tests.

Normalization is an explicit project decision with a verified form and rationale; never normalize machine syntax blindly.
Use natural wrapping when supported. Manual breaks require verified layout/timing needs and locale rules.
For subtitles, text and timing remain independently editable. For images, preserve editable artwork and comparison evidence.

## Review result

Record string IDs, source revision, reviewer, terminology/context decisions and remaining questions.
Report translation, review and runtime coverage independently. A successful catalog lint is not a linguistic or game-display approval.
