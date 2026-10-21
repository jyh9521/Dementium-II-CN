# 当前构建入口

图形安装器（开发端.NET 10 SDK；品牌输入及设置见docs/GUI_INSTALLER.md）：`python -X utf8 tools/build_installer.py`；发行包：`python -X utf8 tools/package_installer.py`。先构建差分，开发端使用.NET 10 SDK发布自包含WPF单文件，玩家不需要另装.NET/Python。详见[图形安装器](docs/GUI_INSTALLER.md)。

实际版本、已安装字体身份、依赖和完整命令见 [构建说明](docs/BUILD_AND_RELEASE.md)。
Python3.11+，所有输出在 build/、dist/；工具不自动启动游戏，不写入 Steam 原件。
当前完整构建包含179个文本资源、固定PC标签和图形标签，不再以单项实验作为默认输出。
下方保留通用可复现构建标准。


---

# Building

This document defines how to rebuild the localization project from a clean repository checkout plus user-supplied original game files.

The build process should be reproducible, documented, and independent from private local working directories or undocumented manual steps.

---

# 1. Supported Game Version

Document the exact supported game build here.

Include when applicable:

- game title
- platform
- region
- distribution or store version
- executable or ELF filename
- version number
- file size
- SHA-256
- important archive hashes

Example:

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

Binary patches must not silently modify unsupported or unknown versions.

---

# 2. Requirements

List all required tools and dependencies.

Examples:

- Python 3.x
- Visual Studio Build Tools
- CMake
- Ninja
- Pillow
- ffmpeg
- external archive tools
- original game files
- specific redistributable fonts

Do not assume dependencies are already installed.

Where practical, provide exact installation commands or version requirements.

Example:

```bash
python -m pip install -r requirements.txt
```

---

# 3. Original Game Files

Clearly list all original files that the user must provide.

Do not include copyrighted original game files in the repository unless redistribution is explicitly permitted.

Example:

```text
original/
  GAME.EXE
  DATA.PAK
```

Document where each file comes from and how its version is verified.

If the game requires files from multiple regions or releases, document each source separately.

---

# 4. Repository Preparation

A clean build should start from a fresh clone.

Example:

```bash
git clone <repository-url>
cd <repository-directory>
```

Do not require the user to copy undocumented private work directories into the repository.

If local configuration is necessary, provide a documented file such as:

```text
config.local.json
```

and include a safe template such as:

```text
config.example.json
```

Local-only configuration should normally be excluded through `.gitignore`.

---

# 5. Preferred Build Entry Point

The build process should expose one obvious entry point whenever practical.

Examples:

```bash
python build.py --locale <locale>
```

or:

```powershell
./build.ps1 -Locale <locale>
```

or:

```bash
cmake --build build
```

Avoid requiring contributors to manually run a long undocumented sequence of unrelated commands.

---

# 6. Recommended Build Pipeline

Where applicable, the build system should perform the following steps:

1. verify dependencies
2. verify original game files
3. extract source resources
4. import localization data
5. validate translations
6. collect required characters
7. generate fonts or glyph tables
8. patch executable or runtime code
9. rebuild archives or containers
10. verify rebuilt resources
11. assemble final output
12. generate checksums or manifests
13. package release files

Not every project needs every step.

The build pipeline should reflect the actual technical requirements of the game.

---

# 7. Version Verification

Before modifying original files, verify one or more of:

- SHA-256
- file size
- expected version metadata
- expected byte sequences
- archive identifiers

Example behavior:

```text
Expected:
GAME.EXE SHA-256 = ...

Found:
GAME.EXE SHA-256 = ...

Result:
Supported
```

If the version does not match, stop with a clear error message.

Do not silently continue on unknown binaries.

---

# 8. Build Output

Generated files should go into a dedicated output directory.

Preferred directories:

```text
build/
dist/
out/
```

Example:

```text
dist/
  <project-name>-<locale>/
```

Generated files should not be scattered across source directories.

Temporary intermediate files should be placed under a build directory and should normally be excluded from version control.

---

# 9. Validation

Before producing a usable or release build, validation should check as many of the following as applicable:

- unsupported original game version
- missing dependency
- missing input file
- invalid translation encoding
- unsupported characters
- missing glyphs
- placeholder mismatch
- control-code mismatch
- malformed markup
- fixed-slot overflow
- invalid string lengths
- duplicate IDs
- linked-string inconsistencies
- broken archive structure
- invalid offsets
- unexpected file sizes
- missing generated resources
- failed binary patches
- checksum mismatch

If a validation error can cause corruption or crashes, the build must stop.

Warnings may be used for non-fatal issues such as possible UI clipping.

---

# 10. Rebuilding From Scratch

A future developer should ideally be able to:

1. clone the repository
2. obtain the required original game files
3. install documented dependencies
4. place original files in the documented location
5. run the documented build command
6. obtain a functional localization build

The project should not depend on:

- old private build directories
- manually modified intermediate files
- deleted binaries
- undocumented local tools
- chat-only instructions
- one developer's filesystem layout

Any unavoidable manual requirement must be documented explicitly.

---

# 11. Locale Selection

If the project supports multiple locales, the build system should accept the locale as a parameter.

Preferred example:

```bash
python build.py --locale zh-CN
```

Potential future usage:

```bash
python build.py --locale zh-TW
python build.py --locale ja-JP
python build.py --locale ko-KR
```

Generic tooling should not assume one locale unless the game itself requires that limitation.

---

# 12. Dependency Management

Document all project dependencies.

Where practical, include standard dependency files such as:

```text
requirements.txt
pyproject.toml
CMakeLists.txt
vcpkg.json
package.json
```

Pin versions when reproducibility requires it.

If an external proprietary tool is required, document:

- tool name
- required version
- download source
- whether redistribution is allowed
- where the user should install or configure it

Do not bundle third-party tools without confirming redistribution rights.

---

# 13. Fonts

If the build requires external fonts, document:

- font name
- source
- license
- required style or weight
- expected file location
- fallback behavior

Prefer redistributable open fonts when practical.

Do not commit proprietary operating-system fonts merely because they are installed locally.

If the build uses a system font, document that dependency clearly.

---

# 14. Archive and Resource Tools

If the project depends on custom extraction or repacking tools, document whether they are:

- included in this repository
- built from source
- provided by an upstream project
- external dependencies

If a tool is custom, include enough documentation to rebuild or replace it.

Do not make the project depend on an unexplained executable with unknown provenance.

---

# 15. Binary Patching

Binary patching must be deterministic and defensive.

Patch tools should:

1. verify the target version
2. verify expected original bytes
3. patch only intended ranges
4. fail on mismatch
5. verify patched output

Where practical, generate a report such as:

```text
Patched file:
GAME.EXE

Verified version:
SHA-256 ...

Applied patches:
- text decoder
- glyph lookup
- line width calculation
```

Do not rely on undocumented manual hex editing for release builds.

---

# 16. Build Logs

Build output should clearly show:

- detected game version
- selected locale
- validation results
- generated character count
- generated files
- patch status
- archive rebuild status
- final output path

Errors should explain what failed and how the user can fix it.

Avoid vague failures such as:

```text
Build failed.
```

Prefer:

```text
Unsupported executable version.
Expected SHA-256: ...
Found SHA-256: ...
```

---

# 17. Release Build

Document a dedicated release build command when appropriate.

Example:

```bash
python build.py release --locale <locale>
```

A release build may additionally:

- clean previous output
- run strict validation
- build optimized binaries
- generate checksums
- generate manifests
- copy documentation
- assemble installation instructions
- create an archive

The exact process should be reproducible.

---

# 18. GitHub Release Packaging

The source repository should normally contain:

- source code
- translation data
- build scripts
- documentation
- patches
- reproducible assets

GitHub Releases may contain:

- ready-to-use localization packages
- installers
- prebuilt redistributable tools
- large generated files
- optional media subtitle packages

Do not use the repository root as a storage area for release archives.

---

# 19. Clean Build Test

Before a major release, perform a clean build test.

Recommended procedure:

1. create a fresh clone in a new directory
2. do not copy any old build output
3. provide only documented original game files
4. install only documented dependencies
5. run the documented build command
6. compare the result with the expected release output

This test helps detect hidden dependencies on the developer's local environment.

---

# 20. Reproducibility Notes

Perfect byte-for-byte reproducibility may not always be possible.

Possible causes include:

- archive timestamps
- compiler version differences
- non-deterministic compression
- external proprietary tools
- media encoders
- file ordering

If output is not byte-identical, document what level of reproducibility is expected.

Examples:

- byte-identical output
- functionally identical output
- identical translation resources but different archive timestamps

Do not claim deterministic output unless it has been verified.

---

# 21. Troubleshooting

Document known build failures and solutions here or in:

```text
docs/PITFALLS.md
```

Typical issues include:

- incorrect game version
- missing dependencies
- wrong file paths
- encoding failures
- font coverage failures
- archive rebuild errors
- compiler architecture mismatch
- missing external tools
- antivirus interference
- path length problems

Important troubleshooting knowledge should not remain only in chat history.

---

# 22. Project-Specific Build Notes

Use this section for project-specific information that does not belong in the generic sections above.

Examples:

- required regional assets
- special disc extraction steps
- emulator-specific testing requirements
- console image rebuilding
- source-port dependencies
- unusual asset conversion steps

Remove unused template notes when adapting this document to a real project.

---

# 23. Final Build Standard

A mature project should make it possible for another developer to rebuild the localization using:

- a clean repository checkout
- documented dependencies
- documented original game files
- documented build commands

The build process should not depend on the original author's memory or private local environment.

## 全量排版门禁
完整构建现在自动运行 audit_text_layout.py 和 audit_image_alignment.py，生成逐记录、逐图片/标签台账；任何越预算、错误短尾、保护码变化、非预期图片改动或居中漂移均停止构建。数值预算属于离线门禁，9条动态变量仍需实机展开复验。

## 原生菜单构建

完整构建同时生成`native-menu-pe-v1`程序差分与调试字体字符子集，新增依赖capstone==5.0.7；不复用未知程序版本的代码偏移。语言数据位于`locales/zh-CN/debug-menu.json`，字体仍使用已记录哈希/OFL许可的Fusion来源。详见`docs/NATIVE_CHEAT_MENU.md`。

## 用户固定版本策略

补丁及安装器版本保持1.0.0，只有用户明确要求时才修改；修复或新增功能不自动递增版本。assets/release-policy.json是构建约束，build_installer.py逐项核对AssemblyVersion/FileVersion/InformationalVersion。
