# Translation Data Contract

Version 1 is a small reference contract, not a requirement to replace a working PO/TSV/game-specific format.
An adapter may use another representation if it preserves these semantics and validates them.

## Reference JSON

The fields below document the baseline reference schema. This documentation migration does not install its example catalog or validator. The existing project format and actual tools remain defined in [TRANSLATING](../TRANSLATING.md); map equivalent fields rather than renaming existing IDs or converting catalogs merely to match this table.
UTF-8 JSON is used; duplicate object keys are errors. IDs are opaque strings, including leading zeros.

| Root field | Meaning |
|---|---|
| `schema_version` | Integer 1; incompatible changes increment this |
| `locale` | Explicit hyphenated target locale; reference syntax: 2-8 ASCII letters, then optional 1-8 alphanumeric subtags; no underscore/whitespace |
| `source_revision` | Nonempty source extraction/build reference |
| `strings` | Array of entries with unique IDs within the catalog |

| Entry field | Meaning |
|---|---|
| `id` | Stable opaque string; resource-qualified if necessary |
| `resource` | Source resource/locator, not an unstable row number alone |
| `context` | Screen, speaker/scene and meaning information |
| `text_role` | `story`, `dialogue`, `other`, or `unknown` |
| `source` | Exact decoded source text |
| `source_sha256` | SHA-256 of exact source UTF-8 bytes, with no trimming/normalization |
| `target` | String, or JSON null only for untranslated entries |
| `disposition` | `translated`, `intentional_empty`, `keep_source`, `untranslated` |
| `review` | `draft`, `needs_review`, `reviewed`, `in_game_verified` |
| `review_source_sha256` | Source fingerprint reviewed; nullable before review |
| `reason` | Explanation for empty/keep-source/uncertain decisions; string |

The baseline reference validator rejects unknown keys to expose misspellings; this does not describe an automatically installed project check. A project extension must version/document its adapter rather than silently dropping fields.
`context` may be empty in an initial extraction but should be completed before ambiguous text is approved.

## Disposition and review invariants

- `untranslated`: target is null; review is `draft` or `needs_review`.
- `translated`: target is nonempty and not whitespace-only. An unchanged target should normally be `keep_source`.
- `intentional_empty`: target is exactly empty and reason is nonempty; confirm the runtime behavior.
- `keep_source`: target exactly equals source and reason is nonempty.
- `reviewed` and `in_game_verified`: review fingerprint equals current source fingerprint.
- `in_game_verified` additionally requires an external G3 evidence record; the catalog label alone is not proof.
- Release data requires a nonempty catalog, a reviewed disposition and a known text role for every included entry. An empty draft is allowed; report an unused module as not_applicable instead of passing empty release data.

The baseline reference `--release` flag checks data eligibility, not G2-G4 completion or external evidence authenticity; it is not a new CLI entry point in this project.
Do not treat a copied source string, a missing record, null and an intentionally empty target as equivalent.

## Stable IDs and re-extraction

Prefer engine resource IDs with a namespace. If the game lacks IDs, maintain an explicit stable mapping; record how moves/duplicates are reconciled.
Do not derive identity solely from the current translation, source text or row number.
Merge by stable identity, then compare source fingerprints and relevant context/constraints.
Preserve translations as drafts on changes, set `needs_review`, and retain the old review fingerprint for history.
Any context, speaker, token grammar or layout constraint change also invalidates affected review even if source text is unchanged.
Editing a target or changing its applicable language policy resets affected review and runtime evidence. The reference checker verifies source binding, not the authenticity of a review decision; use version control and build-bound evidence for target changes.
New IDs start untranslated. Removed IDs become retired records/history, not silently reassigned IDs.
Ambiguous matches require explicit review. Preserve duplicates with different meanings and document intentional linked groups.
Extraction timestamps are provenance, not a substitute for content fingerprints.

## Serialization and game adapter

Document CSV/TSV quoting, embedded tabs/newlines, BOM, line endings and spreadsheet import/export if those formats are supported.
Keep translation source encoding separate from runtime encoding; conversion is strict and never silently substitutes `?` or drops characters.
An adapter defines byte/code-unit/glyph/pixel limits, terminator inclusion, markup grammar, escapes and placeholder ordering rules.
Validate syntax by the actual grammar rather than one universal regular expression. Preserve literal whitespace unless verified nonsemantic.
Represent plural/gender/select forms and linked resources as explicit extensions when required; do not flatten them into one ambiguous string.
Track cross-catalog ID namespaces in the project validator; the reference validator checks one catalog at a time.

## Language policies

Generic validation dispatches language policy separately from engine logic. The reference implementation applies the [Chinese punctuation rule](../locales/zh-CN/STYLE.md) to primary language `zh` and hyphenated `zh-*` variants, case-insensitively (for example zh-CN, zh-TW, zh-HK and zh-Hans-CN). The locale syntax check is a small profile, not full registry validation; other locale systems require an explicit adapter.
The style is a personal baseline preference, not a property of all Chinese software or another language.
Text role follows meaning, not filename: a subtitle may be dialogue, narration or a system message.
For markup/control-code resources, an adapter must supply verified visible-text spans before punctuation checks. The reference validator operates on plain display text; detected markup-like syntax, ambiguous numeric/ASCII-word terminal dots and unbalanced quotes produce `zh_style_review` findings, not a silent pass. A human/adapter must resolve these with evidence; the reference CLI has no blanket ignore switch. This heuristic is not a game-markup parser.
Split mixed story/dialogue/system records into mapped role-specific spans for review; never mark an entire mixed resource as story merely to exempt its UI text. Independent newline-separated messages need separate spans; display wrapping alone does not start a new sentence.
