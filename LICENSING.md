# 当前项目许可记录

项目工具：根 LICENSE（MIT）；原创译文：LICENSE-translations.md（CC BY-SA 4.0）。
字体：Noto Sans CJK SC Regular，notofonts/noto-cjk，提交 f8d157532fbfaeda587e826d4cd5b21a49186f7c，SIL OFL 1.1。
原始 OTF 缓存忽略；来源和许可证保留，发行差分附字体许可证。
游戏 EXE、DLL、完整资源、媒体、存档和反编译正文不作为完整文件分发。
实验包仅含稀疏差分、工具和必要说明；原游戏内容的权利不变。
下方保留原有许可边界标准。

---

# Licensing

This document describes the licensing boundaries of the localization project.

A game localization repository may contain multiple categories of material with different legal and licensing requirements.

Do not assume that one license automatically applies to every file in the repository.

---

# 1. Project-Owned Code and Tools

Original code written specifically for this project should use the license declared in the repository's main `LICENSE` file, unless a file or directory explicitly states otherwise.

Possible choices include:

- MIT
- MPL-2.0
- Apache-2.0
- GPL-compatible licenses where appropriate

The selected license should match the project's technical and upstream constraints.

Do not relicense upstream code incompatibly.

---

# 2. Translation Text

Original translation work may be licensed separately from program code.

A common option for translation data is:

```text
CC BY-SA 4.0
```

This allows reuse for:

- Traditional Chinese versions
- ports
- remasters
- additional platforms
- derivative localization projects

while requiring attribution and share-alike distribution.

If another license is used, document it explicitly.

---

# 3. Source-Language Game Text

Source-language text extracted from the original commercial game remains copyrighted by the original rights holders.

Including original strings in translation tables does not mean this project grants rights to those original strings.

Use original game text only to the extent reasonably necessary for:

- translation
- interoperability
- patch construction
- technical analysis
- context preservation

Do not treat original game text as project-owned material.

---

# 4. Original Game Assets

Unless redistribution is explicitly permitted, do not commit or redistribute complete proprietary game assets such as:

- executables
- ELF files
- DLLs
- full archives
- audio
- video
- textures
- models
- proprietary fonts
- complete original data directories

Users should normally provide their own legally obtained original game files.

---

# 5. Binary Patches and Transformation Data

Transformation data may be distributed when appropriate.

Examples include:

- xdelta patches
- IPS patches
- BPS patches
- byte-diff descriptions
- patch scripts
- build scripts
- binary patch manifests

Prefer distributing transformation data instead of complete modified proprietary binaries.

A patched full executable may still contain substantial copyrighted original code and should be treated accordingly.

---

# 6. Upstream Open-Source Code

Files derived from upstream open-source projects remain subject to their original licenses.

Document all upstream components.

Example:

| Component | Upstream | License |
|---|---|---|
| Runtime patch | project URL | MPL-2.0 |
| Archive library | project URL | MIT |
| Font | project URL | SIL OFL 1.1 |

Do not remove required copyright notices.

Do not relicense upstream code under incompatible terms.

---

# 7. Upstream EULA or Source-Available Code

Some projects expose source code under an EULA, source-available license, SDK agreement, or other non-open-source terms.

Such code may require separate treatment.

Document:

- source
- governing agreement
- redistribution limits
- modification limits
- whether derivative patches may be shared
- whether full modified source may be redistributed

Do not label such code as open source unless the license actually qualifies.

---

# 8. Fonts

Fonts must follow their own licenses.

Common examples include:

- SIL Open Font License 1.1
- Apache License 2.0
- other font-specific licenses

Do not copy proprietary operating-system fonts into the repository merely because they are installed locally.

If the build uses a system font, document that dependency.

Prefer redistributable open fonts when practical.

---

# 9. Third-Party Tools

External tools may have their own licenses and redistribution restrictions.

Document:

- tool name
- source
- version
- license
- whether the tool is bundled
- whether the user must obtain it separately

Do not redistribute third-party binaries without confirming permission.

---

# 10. Reverse-Engineering Notes

Original technical documentation written for this project may use the same license as project documentation or another explicitly declared license.

Examples include:

- format descriptions
- diagrams
- offset tables
- rendering notes
- reverse-engineering summaries
- implementation notes

Document factual discoveries without unnecessarily embedding copyrighted game content.

---

# 11. Generated Files

Generated output inherits licensing constraints from its inputs.

A generated file is not automatically freely redistributable merely because a project tool created it.

Examples:

- rebuilt archives may contain original copyrighted game assets
- patched executables still contain original executable code
- subtitled videos remain derivative works of original videos
- generated font atlases may include glyphs from third-party fonts

Treat generated files according to their actual contents.

---

# 12. Repository Source vs Release Artifacts

The Git repository should preferably contain:

- original project code
- scripts
- translation data
- patch definitions
- documentation
- legally redistributable assets

GitHub Releases may contain:

- ready-to-use patch packages
- installers
- redistributable prebuilt tools
- large generated artifacts
- optional subtitle packs

Release packaging does not override copyright or license restrictions.

---

# 13. Game-Derived Resources

Be cautious with files derived directly from original game assets.

Examples:

- edited textures
- modified videos
- rebuilt archives
- extracted fonts
- modified executable sections

If redistribution status is uncertain, prefer generating them locally from user-supplied originals.

Do not assume that changing an asset makes it freely redistributable.

---

# 14. Translation Licenses and Original Text

Translation files may contain both:

- original game text
- project-created target-language text

These two parts may have different legal status.

Where practical, document that:

- source-language text remains property of the original rights holders
- target-language translation is licensed by the translation contributors under the project's chosen translation license

A translation license does not grant rights over the original game text.

---

# 15. Contributor Licensing

If the project accepts contributions, make licensing expectations clear.

Contributors should understand that their contributions may be distributed under the licenses declared for the relevant part of the project.

If code and translation text use different licenses, document that distinction clearly.

---

# 16. Attribution

Preserve attribution for:

- upstream developers
- reverse-engineering researchers
- translation contributors
- font authors
- external tool authors
- original game developers and publishers

Recommended locations include:

```text
README.md
LICENSING.md
NOTICE.md
```

Do not remove legally required notices from upstream components.

---

# 17. Recommended License Split

A common project structure may use:

```text
LICENSE
```

for project-owned code and tools,

and:

```text
LICENSE-translations.md
```

for original translation work.

Example:

```text
Code and tools:
MIT

Original translation text:
CC BY-SA 4.0

Fonts:
their own licenses

Upstream code:
its original license

Game text and assets:
copyright remains with original rights holders
```

This is only a recommended pattern.

Actual licensing must follow the real upstream and project constraints.

---

# 18. Directory-Specific Licensing

Where different directories use different terms, document them explicitly.

Example:

```text
src/
  MIT

tools/
  MIT

locales/
  CC BY-SA 4.0 for original translation text

patches/upstream-engine/
  governed by upstream license or EULA

assets/fonts/
  governed by each font's license
```

Do not rely on contributors guessing which license applies.

---

# 19. License Files

Common files may include:

```text
LICENSE
LICENSE-translations.md
LICENSING.md
NOTICE.md
```

Their roles should be:

- `LICENSE` — formal license for project-owned code
- `LICENSE-translations.md` — formal license for original translation work
- `LICENSING.md` — explanation of licensing boundaries
- `NOTICE.md` — attribution and third-party notices where useful

Not every project needs all four, but the distinction should remain clear.

---

# 20. Uncertain Licensing Status

If the licensing status of a file or upstream component is uncertain:

- do not guess
- do not silently mark it as redistributable
- document the uncertainty
- avoid redistribution until clarified

Prefer omission over accidental unauthorized redistribution.

---

# 21. Project-Specific Licensing Notes

Use this section to record the actual licensing arrangement for the specific project.

Template:

```text
Project-owned code:
[license]

Project-owned translation:
[license]

Upstream project:
[name / URL / license]

Fonts:
[name / license]

Third-party tools:
[name / license]

Game source text:
copyright retained by original rights holders

Game assets:
not redistributed unless explicitly permitted
```

Replace this section with project-specific information when adapting the template.

---

# 22. Final Licensing Standard

A mature localization project should make it clear:

- what the project authors own
- what contributors may reuse
- what requires attribution
- what must remain under an upstream license
- what must not be redistributed
- what must be generated locally from original game files

If the licensing boundary is not obvious, document it explicitly.
