# 当前已知问题（2026-10-21）

- 高：中文游戏画面尚未验收，技术闭环尚未完成。
- 高：唯一译文为“新游戏”；其余未译，666 只是已识别文本记录数。
- 高：按钮文本复制容量和自动换行仍待追踪。
- 中：仅扩展主字体，debug08 的实际使用场景待调查。
- 中：图片文字、成就显示、程序常量、字幕时间单位、~INDEX 其他用途待确认。
- 中：存档、场景切换、全流程稳定性尚未进行中文版本验收。
- 版本更新时拒绝未知哈希，需重新调查。
- 本轮未启动游戏、未改 Steam 原件、未安装到真实目录。

下方保留原有问题分类标准。

---

# Known Issues

This document records known user-visible limitations, compatibility problems, incomplete areas, and unresolved defects in the localization project.

Use this file for issues that affect players, testers, or release quality.

Use `docs/PITFALLS.md` for technical traps, failed approaches, and development lessons.

---

# 1. Issue Classification

Classify issues using one of these statuses:

- Open
- Investigating
- Workaround available
- Partially fixed
- Fixed in development
- Fixed in release
- Won't fix
- Upstream issue
- Emulator-specific
- Version-specific

Also classify severity when useful:

- Critical
- High
- Medium
- Low
- Cosmetic

Do not overstate severity.

---

# 2. Issue Entry Template

Use the following template for each known issue.

```markdown
## Short issue title

**Status:** Open  
**Severity:** Medium  
**Affected versions:**  
**Affected platforms:**  
**Affected locales:**  

**Symptoms:**
Describe what the player sees.

**Trigger:**
Describe how to reproduce the issue.

**Expected behavior:**
Describe what should happen.

**Actual behavior:**
Describe what actually happens.

**Workaround:**
Describe any temporary workaround.

**Technical notes:**
Briefly describe the suspected or verified cause.

**Related files:**
List relevant files, resources, tools, or code.

**Tracking:**
Link an issue, commit, or release if available.
```

---

# 3. Player-Visible Text Issues

Record issues such as:

- untranslated strings
- mistranslated strings
- duplicate translations
- missing subtitles
- wrong speaker text
- incorrect names
- inconsistent terminology
- untranslated debug text
- text using the wrong locale

If the issue is only a translation-quality concern and not a technical defect, state that clearly.

---

# 4. Missing Glyphs

Record any characters that:

- render as boxes
- render as question marks
- disappear
- display the wrong glyph
- cause fallback fonts
- crash the renderer

Include:

- affected string
- affected screen
- missing character
- font resource
- locale

Where practical, link to a font-coverage validation issue.

---

# 5. Text Clipping

Record cases where translated text:

- exceeds a button
- clips outside a dialog
- overlaps another element
- extends off-screen
- is truncated
- wraps incorrectly

Include:

- screen
- resolution
- UI scale
- font scale
- affected locale

If the issue only occurs at certain resolutions, state that explicitly.

---

# 6. Line Wrapping

Record incorrect wrapping such as:

- breaks in the middle of protected tokens
- lines that exceed safe width
- excessive empty lines
- broken punctuation placement
- dialogue boxes with too many lines
- subtitles wrapping beyond engine limits

If a workaround requires manual line breaks, document it.

---

# 7. Subtitle Issues

Record:

- missing subtitles
- wrong timing
- subtitles too long
- overlap
- wrong speaker
- wrong scene
- subtitles outside the visible region
- subtitle renderer missing glyphs

For video subtitles, include:

- video filename
- timestamp
- subtitle source file

---

# 8. Audio and Voice Issues

Record localization-related audio problems such as:

- wrong voice clip
- missing voice playback
- mismatched subtitle and voice
- audio event broken by translated identifier
- regional voice assets missing
- alternate-language voice selection failure

Do not list unrelated original-game audio bugs unless the localization interacts with them.

---

# 9. Font Rendering Issues

Record:

- inconsistent glyph sizes
- bad baseline
- incorrect spacing
- kerning errors
- blurry font
- font scale mismatch
- incorrect punctuation width
- full-width/half-width alignment problems
- fallback font appearing unexpectedly

Include screenshots or scene references when useful.

---

# 10. Resolution and Scaling Issues

Record problems that depend on:

- 4:3
- 16:9
- ultrawide
- 720p
- 1080p
- 1440p
- 4K
- DPI scaling
- emulator internal resolution

Do not assume a rendering defect affects all resolutions.

---

# 11. Menu Issues

Record:

- clipped menu items
- wrong selection labels
- misaligned text
- untranslated options
- broken hotkeys
- overlapping descriptions
- menu navigation issues caused by translated text

State whether the issue affects usability or is purely cosmetic.

---

# 12. HUD Issues

Record:

- clipped HUD labels
- missing counters
- overlap with icons
- wrong alignment
- text too large
- font scaling errors
- localization text causing performance issues

If a HUD issue only occurs in one renderer or resolution, document that condition.

---

# 13. Inventory and Item Issues

Record:

- item names missing
- wrong item descriptions
- pickup text mismatch
- linked names inconsistent
- inventory sorting affected
- item references broken
- text overflows item panels

If an item name is used internally as an identifier, document the risk.

---

# 14. Dialogue Issues

Record:

- missing lines
- wrong speaker
- wrong branch text
- duplicate dialogue
- skipped dialogue
- broken control codes
- dialogue box overflow
- progression blocked by modified text

Include chapter, scene, or event identifiers where possible.

---

# 15. Script and Progression Issues

Localization changes can sometimes affect game logic.

Record cases such as:

- quest does not advance
- event does not trigger
- item cannot be obtained
- scene fails to load
- script branches incorrectly
- save state becomes inconsistent

Treat progression-blocking issues as high severity.

---

# 16. Save Compatibility Issues

Record:

- old saves no longer load
- saves created with localization fail on unpatched game
- translated identifiers affect save data
- different locale builds are incompatible
- save labels display incorrectly

State clearly whether:

- old saves are supported
- new saves are compatible across versions
- clean-start testing is required

---

# 17. Version Compatibility

Record unsupported or partially supported game builds.

Example:

```text
Supported:
Steam 1.2.3

Not tested:
GOG release

Unsupported:
Retail 1.0
```

Do not describe untested versions as supported.

---

# 18. Region Compatibility

Record region-specific behavior.

Examples:

- US build supported
- JP build requires different executable patch
- KR build has different font table
- EU build uses another archive layout

Do not assume two regions with similar files are identical.

---

# 19. Mod Compatibility

Record known conflicts with:

- graphics mods
- source ports
- modernizer patches
- loaders
- proxy DLLs
- reshade
- script mods
- texture packs
- audio mods

Explain the conflict mechanism if known.

Example:

```text
Both projects use dinput8.dll as a proxy loader.
They cannot be installed together without chaining.
```

---

# 20. Runtime Loader Conflicts

If the localization uses a proxy DLL or injected runtime, document conflicts involving:

- `dinput8.dll`
- `winmm.dll`
- `version.dll`
- `dxgi.dll`
- `d3d9.dll`
- `dsound.dll`

State whether chaining is supported.

---

# 21. Antivirus and Security Software

If generated binaries are sometimes flagged, document:

- affected file
- detection type
- whether the file is built locally
- source availability
- checksum
- known false-positive behavior

Do not claim a detection is a false positive without evidence.

---

# 22. Emulator-Specific Issues

Record issues that occur only in an emulator.

Include:

- emulator name
- version
- renderer
- settings
- internal resolution
- whether the issue reproduces elsewhere

Examples:

- PCSX2 texture corruption
- timing-sensitive subtitle issue
- renderer-specific blending problem

Do not present emulator-specific behavior as a confirmed original-hardware issue.

---

# 23. Hardware-Specific Issues

Record issues that depend on:

- GPU vendor
- driver version
- CPU architecture
- controller type
- display refresh rate
- operating system

Only list hardware-specific causes when verified or clearly labeled as suspected.

---

# 24. Operating System Issues

Record differences between:

- Windows versions
- Linux
- Wine
- Proton
- compatibility layers

Examples:

- path encoding
- missing runtime libraries
- case sensitivity
- font availability
- fullscreen behavior

---

# 25. Installation Issues

Record common installation failures.

Examples:

- patch installed to wrong directory
- original version mismatch
- missing required file
- read-only game directory
- launcher restores modified files
- Steam validation overwrites patch
- antivirus removes runtime component

Provide the simplest reliable workaround.

---

# 26. Uninstallation Issues

Document whether the localization can be removed cleanly.

Record:

- files added
- files replaced
- backups created
- files generated at runtime
- settings changed

If uninstall requires restoring original files, state that clearly.

---

# 27. Performance Issues

Record localization-related performance problems such as:

- frame-rate drops caused by text rendering
- excessive runtime glyph generation
- slow archive lookup
- expensive text replacement
- repeated font rasterization
- excessive logging

Include measurable data when possible.

Avoid vague statements like "performance seems worse."

---

# 28. Memory Issues

Record:

- memory leaks
- oversized font atlases
- buffer exhaustion
- increased heap usage
- large translation tables
- runtime cache growth

If an issue only appears after long sessions, document approximate duration and trigger conditions.

---

# 29. Crash Issues

For crashes, record:

- exact trigger
- game version
- locale
- affected file
- stack trace if available
- crash address if available
- reproducibility

Do not write only "sometimes crashes."

State whether the crash is:

- deterministic
- intermittent
- version-specific
- emulator-specific
- unresolved

---

# 30. Data Corruption Issues

Treat potential corruption as critical.

Examples:

- save corruption
- malformed archive
- invalid executable patch
- broken resource index
- overwritten original files
- corrupted configuration

Document backup and recovery instructions.

---

# 31. Build-to-Release Differences

Record cases where:

- development build works
- packaged release fails
- files are missing from release
- release paths differ
- compression changes behavior
- installer changes encoding

Release packaging should be tested independently from local development output.

---

# 32. Known Cosmetic Issues

Cosmetic problems may include:

- minor spacing
- inconsistent punctuation width
- imperfect alignment
- slightly blurry glyphs
- low-priority untranslated decorative text

Classify them as cosmetic rather than presenting them as functional defects.

---

# 33. Deferred Issues

If an issue is intentionally postponed, explain why.

Possible reasons:

- low impact
- requires large engine rewrite
- upstream dependency
- insufficient research
- no known safe fix
- affects only unsupported version

Do not silently abandon known problems.

---

# 34. Fixed Issues

When an issue is fixed, keep a short historical record when useful.

Example:

```text
Status: Fixed in v1.2

Cause:
Font width table used byte count instead of glyph count.

Fix:
Updated layout calculation and added regression test.
```

This helps explain old bug reports and prevents regressions.

---

# 35. Reporting New Issues

When possible, ask testers to provide:

- game version
- platform
- locale
- localization version
- scene or level
- exact text
- screenshot
- logs
- reproduction steps
- whether the issue occurs without the localization

This information greatly improves debugging quality.

---

# 36. Project-Specific Known Issues

Add actual project-specific issues below this line.

Remove unused template sections when adapting this file to a real project.

---

# 37. Final Known-Issue Standard

A useful known-issues document should let players and maintainers understand:

- what is currently broken
- who is affected
- how severe it is
- how to reproduce it
- whether a workaround exists
- whether a fix is planned
- whether the issue belongs to the localization, the original game, an emulator, or another mod

Known limitations should be documented clearly rather than hidden.
