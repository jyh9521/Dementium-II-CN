# Issue Lifecycle and Evidence Standard

Actual current and historical issues remain in [KNOWN_ISSUES](KNOWN_ISSUES.md). This specification neither closes nor reopens an issue by itself.

## Independent fields

- Status: `open`, `investigating`, `partially_fixed`, `fix_pending_verification`, `fixed_in_development`, `fixed_in_release`, `deferred`, `wont_fix`.
- Severity: `critical`, `high`, `medium`, `low`, `cosmetic`.
- Attribution: `localization`, `original_game`, `emulator`, `other_mod`, `unknown`.
- Attribution confidence: `verified`, `high_confidence_deduction`, `unverified_hypothesis`.
- Workaround: separate description, not a lifecycle status.
- Affected versions/platforms/locales/scenes: explicit sets, not statuses.

An issue can be open, high severity and emulator-specific at the same time.
Treat corruption and progression blockers as release blockers under [acceptance](ACCEPTANCE.md).
Severity reflects impact, not effort to fix.

## Issue template

```text
Issue ID and title:
Status / severity:
Attribution / confidence / evidence:
Affected game builds, patch versions, locales and environments:
Content/resource IDs and scene:
Reproduction steps and baseline comparison:
Expected / actual result:
Logs/screenshots and tested candidate hash:
Workaround and side effects:
Owner / next action / deferral rationale:
Fix revision / regression case / verification result:
First release containing the verified fix:
```

Use `fix_pending_verification` for a proposed/code fix without a passing regression. Use `fixed_in_development` only after candidate-bound regression verification, and `fixed_in_release` only when that verified fix is shipped in an identified release.
Record untested versions as untested, not supported. Preserve a short history after resolution.

## Coverage prompts

Look for untranslated/wrong-context text, missing glyphs, clipping, wrapping, subtitles, audio references, script progression, saves, regional variants, loader/mod conflicts, installation, performance and memory.
Include packaging-only failures independently of developer builds.
Record actual resolutions, UI scales, emulator backends and settings rather than assuming a defect affects all environments. Include OS/driver/GPU/CPU dependencies when observed, and distinguish suspected causes from verified ones.
For crashes, retain trigger, reproducibility, stack/address when available and unpatched comparison. For binary detections, record the exact file hash, build/source provenance, detection and investigation evidence; call a false positive only when supported. For proxy-loader conflicts, record the colliding DLL/module and whether chaining is verified.
