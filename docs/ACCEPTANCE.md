# Acceptance and Completion Claims

This is the authority for new test results and completion statements. Existing dated results retain their original scope under [migration rules](MIGRATION.md); document adoption alone neither reruns nor upgrades them.

## 1. States and evidence

Each test has one state: `pass`, `fail`, `not_run`, `blocked`, or `not_applicable`.
`blocked` names the missing input or environment. `not_applicable` explains why the feature is absent and identifies the reviewer.
Neither state counts as a pass. A test that ran unsuccessfully is `fail`, not `blocked`.
An exception records owner, reason, affected scope, expiry/retest condition and release impact.
Unknown input identity, data corruption, progression blockers and required failed checks block a supported release.

Minimum record:

| Field | Required content |
|---|---|
| Identity | Case ID, gate, locale, content/resource IDs |
| Inputs | Original-input manifest hash; source revision |
| Candidate | Commit or source-tree digest; payload/package SHA-256 |
| Environment | OS, tool versions; emulator/hardware, renderer and settings when relevant |
| Procedure | Exact command and input or reproducible scene/save/navigation steps |
| Expected | Observable expected result, thresholds set before the run |
| Actual | Literal output/exit status or observed runtime result |
| Evidence | Log, report, screenshot/video with scene/timestamp; evidence hash where practical |
| Decision | State, tester/reviewer, date, issue/deviation reference |

Use `not_applicable` for command exit status in a manual test, not a fabricated zero.
Evidence MUST bind to the candidate, not merely to a similarly named build.
Preserve shareable reports; store restricted screenshots/saves locally with a reproducible locator and access notes.
Rerun affected cases after a change; unchanged evidence can be carried forward only with a documented dependency analysis.

## 2. Verification gates

| Gate | Minimum pass conditions | Permitted claim |
|---|---|---|
| G0 Input | Supported clean-input manifest matches; unsupported or unrecognized inputs rejected without writes | Inputs verified |
| G1 Data | Contract, source freshness, required entries, encoding, tokens, lengths and terminology checks pass | Data validation passed |
| G2 Resource | No-edit round trip at declared equivalence; changed data reads back correctly; unrelated data preserved | Resources validated offline |
| G3 Runtime | Candidate boots; relevant text/layout/scenes, saves and transitions pass on named environments | Listed scenarios verified in-game |
| G4 Distribution | Final downloaded/extracted package installs, upgrades, recovers and uninstalls; manifest matches tested payload | Listed release package verified |

Gates are cumulative for a supported release, but records stay separate. A count of thousands of unit assertions is not runtime coverage.
If byte identity is not achievable, define a canonical structural comparison, enumerate allowed differences and test runtime behavior. “Functionally equivalent” needs a reproducible test, not visual inspection of archive contents alone.
G1 must include game-specific token/encoding checks in addition to any adopted reference validator. Compare expected IDs against the source inventory to detect missing entries and unknown target-only IDs; a self-consistent partial catalog is not full coverage.

## 3. Minimum matrix

- G0 (clean build): supported manifest including listed donor sets; wrong region/version; one changed byte; missing file; unlisted mixed discs; already-patched input. G4 separately tests recognized installed states for repeat/repair/upgrade.
- G1: missing/duplicate ID; stale source review; null versus intentional empty; token count/type/order; encoding failure; byte-length boundaries including terminators.
- G2: zero edits; one edit; multiple edits; shared strings; unknown bytes; offset/alignment/checksum consistency; truncated and malformed input.
- G3: cold boot; menus; dialogue and branching; long/multiline text; combat/HUD; loading and scene transitions; subtitles; old/new save reload; relevant long-session and memory behavior.
- G4: clean install; repeated install; supported upgrade; conflict; interrupted installation; insufficient space; uninstall; restore verification.

Select representative contexts and critical paths from the resource inventory, not from convenience alone.
Record each advertised game build, locale and runtime configuration. Hardware evidence and emulator evidence remain distinct.
Set numeric memory/performance/duration limits from project measurements; do not invent universal thresholds.
Classify a failure as original-game/emulator behavior only after a baseline comparison or label the attribution uncertain.

## 4. Coverage accounting

Maintain a versioned inventory covering text tables, executable constants, scripts, image text, video subtitles, dynamic/fallback text and remaining unknown sources.
Each unit has a stable ID, type, location, scope (`included`, `excluded`, `undetermined`), exclusion reason, review state and runtime evidence reference.
Choose units per content type: strings for catalogs, assets/regions for images, cues or scenes for video. Report different units separately.

For a frozen included inventory of N units:

- Translation coverage = units with an intentional translated/empty/keep-source disposition / N.
- Review coverage = units reviewed against the current source / N.
- Runtime coverage = units observed on the candidate, including verified generated variants / N.

Show counts with percentages; `N = 0` is `not_applicable`, not 100%.
List excluded and undetermined counts alongside the denominator. A runtime sample covers only the sampled units.
Keep-source and intentionally empty decisions need reasons and review; they are not missing translations.
Residual-source-language searches are heuristics with false positives and missed image/dynamic text. They do not establish whole-game coverage.

## 5. Release decision

| Label | Required evidence |
|---|---|
| Research / prototype | Actual gate states and limitations; no claim of general playability |
| Test release | G0-G2 for changed resources, named G3 smoke cases, applicable installer checks; remaining gaps disclosed |
| Supported release | All required G0-G4 cases pass; critical/high-impact defects resolved; accepted lower-impact issues listed |
| Complete for declared scope | Supported release plus 100% translation and review coverage of included units; full declared runtime plan completed, with observed-unit coverage stated separately; exclusions and unknown discovery limits stated |

The test-release label does not permit known corruption or known progression-blocking behavior to be described as usable.
A completed sampled runtime plan is not 100% observed-unit coverage. A claim that every included unit was verified in-game requires runtime coverage of 100%; otherwise publish the exact sample/plan scope.
For this baseline or a standalone tool without game inputs/runtime, report document/tool verification separately; G0-G4 game results are not applicable until a game integration exists.
“Complete for declared scope” is not proof that undiscovered resources do not exist. Reserve a whole-game claim for a defensible full inventory and coverage record.
Fixing a known issue requires a regression result and a tested candidate, not just a code change.

## 6. Completion report template

```text
Candidate/source revision:
Package/payload SHA-256:
Supported inputs and runtime environments:
Changed resources and locales:
G0 / G1 / G2 / G3 / G4: state + evidence reference
Translation / review / runtime: numerator / denominator by content type
Excluded and undetermined inventory:
Open issues and accepted deviations:
Install/upgrade/recovery/uninstall result:
Exact completion claim justified by this evidence:
```
