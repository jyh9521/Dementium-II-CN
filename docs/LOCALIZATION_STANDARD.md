# Localization Engineering Standard

Revision 2.1, adopted for this existing project on 2026-11-17. This document owns cross-project principles. Specialized documents own their detailed rules.
Read [migration and applicability](MIGRATION.md) before treating an existing implementation or historical release as conforming to these requirements.

## 1. Requirement levels and applicability

- **MUST**: required for the relevant operation or acceptance claim.
- **SHOULD**: default; an exception records reason, risk, reviewer and evidence.
- **MAY**: optional technique, not a mandatory feature.

Apply only relevant modules. An unused runtime hook can be `not_applicable`; an untested hook is `not_run`, not `not_applicable`.
Project-specific requirements may be stronger. A deviation must be explicit and must not silently retain a claim whose prerequisites it bypasses.
Template examples describe invented data, not verified facts about a game.

## 2. Rule ownership

| Rule family | Single source of truth |
|---|---|
| Cross-project principles and input identity | This document |
| Completion, evidence and release gates | [ACCEPTANCE](ACCEPTANCE.md) |
| Translation representation and merge semantics | [DATA_CONTRACT](DATA_CONTRACT.md) |
| Translator operations | [TRANSLATION_STANDARD](TRANSLATION_STANDARD.md); project facts in [TRANSLATING](../TRANSLATING.md) |
| Language style | `locales/<locale>/STYLE.md` |
| Build requirements and reproducibility | [BUILD_STANDARD](BUILD_STANDARD.md); actual commands in [BUILDING](../BUILDING.md) |
| Installation and recovery | [INSTALLATION_STANDARD](INSTALLATION_STANDARD.md) |
| Rendering, artwork and media | [ASSET_LOCALIZATION](ASSET_LOCALIZATION.md) |
| Research and format requirements | [RESEARCH_STANDARD](RESEARCH_STANDARD.md); facts in [TECHNICAL](../TECHNICAL.md), [FILE_FORMATS](FILE_FORMATS.md) |
| Issue lifecycle and diagnostics | [ISSUE_STANDARD](ISSUE_STANDARD.md); actual inventory in [KNOWN_ISSUES](KNOWN_ISSUES.md) |
| README claims and structure | [README_STANDARD](README_STANDARD.md) |
| Component inventory requirements | [LICENSING_STANDARD](LICENSING_STANDARD.md); governing terms and notices in [LICENSING](../LICENSING.md) |

Other documents link to these rules and record project-specific values instead of repeating the rules.

## 3. Reusable engineering

1. Separate generic tools, engine adapters and language data. Pass locale selection as configuration.
2. Use `locales/<locale>/`; avoid language-specific names and constants in generic code unless the engine requires them.
3. Adding a locale should normally add data/configuration. Distinguish engine constraints from avoidable framework constraints.
4. Preserve reusable extractors, builders, validators, font generation and technical records.
5. Use a clean checkout plus documented inputs and dependencies to rebuild. Record unavoidable manual steps and their verification.
6. Preserve stable source identifiers, context and protected syntax. Display text must be distinguished from script, save, audio and resource identifiers.
7. Keep original inputs immutable; modify working copies and validate outputs.
8. Keep build output separate from authored sources. Track shared specifications and synthetic fixtures.
9. Preserve upstream attribution and meaningful failed research; move durable findings out of chat-only history.
10. Generalize at reasonable cost. Do not invent unused abstractions merely to match this layout.

For forks, keep useful upstream history compatible where practical. Change behavior and its owning documentation together; use regression and evidence records to detect drift.

## 4. Supported input identity

Every release MUST have an input manifest: relative path, byte length, SHA-256, game/platform/region/build and role.
Include every original file consumed by the build, not just the executable. Distinguish discs, regional donor files and optional DLC.
The default acceptance rule is a supported manifest with exact file hashes. Size, filename, magic or a version string alone is not proof of identity.
For a clean source build, reject unknown/missing inputs, unlisted mixed-version sets and already-modified originals before writing. Explicitly listed regional donor files are not an unlisted mix.
Installation is a separate state machine: a recognized installed state may be a valid input for a verified repeat install, repair or upgrade under [installation rules](INSTALLATION_STANDARD.md). Reject unrecognized modifications, not every previously installed patch.
For every executable patch, verify expected original bytes at each patch site before writing, including the exact-hash path; record expected output bytes/ranges and reject overlapping or unexpected changes.

If exact identity varies legitimately, define a separate versioned adapter profile with:

- a documented reason and a bounded set of supported variants;
- multiple discriminating structural checks and hashes of relevant regions;
- verified expected bytes at every executable patch site;
- positive and negative fixtures and explicit failure behavior;
- tests for each advertised variant and a manifest recording the actual inputs.

An approximate scan or a lone signature is not a release-ready substitute for this profile.
After a binary patch, verify the intended changed ranges and output structure; unexpected differences fail validation.

## 5. Lifecycle

| Stage | Required exit evidence |
|---|---|
| Reconnaissance | Supported-input record; resource inventory; unknowns identified |
| Minimal proof of concept | Small representative text set extracted, rebuilt and observed in-game |
| Toolchain | Automated validation; no-edit round trip; negative fixtures; reproducible commands |
| Translation | Source-bound data; terminology; protected tokens; reviewed context |
| QA | Applicable acceptance gates and regression cases on the candidate build |
| Release | Packaged artifact tested independently, checksummed and accompanied by accurate limitations |

Bulk translation follows the proof of concept. A prototype may be shared as experimental with its actual verification level.
Offline checks do not replace runtime evidence. Full completion is defined only by [acceptance](ACCEPTANCE.md).

## 6. Evidence and technical knowledge

Classify findings as `verified`, `high_confidence_deduction` or `unverified_hypothesis`.
A verified finding identifies the tested input/build, method, observations and evidence location; confidence is separate from execution status.
Keep unknown fields and failed approaches visible. Preserve opaque bytes unless a verified transformation requires changing them.
Addresses must identify file offset, RVA or runtime address and the version to which they apply.

## 7. Repository and delivery boundaries

Use explicit directories for original inputs, generated payloads and public synthetic fixtures.
Before committing or packaging, inspect the actual file list; ignore patterns are convenience rules, not a content audit.
Do not publish complete proprietary inputs without explicit redistribution permission. Prefer reproducible transformations, patch data and licensed source assets.
An output produced by a tool retains the relevant input constraints; use [LICENSING](../LICENSING.md) for the inventory.
