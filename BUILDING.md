# 从源码重建

当前构建入口统一维护于本页，历史红/绿/回滚命令见[专项记录](docs/history/BUILD_REGRESSIONS.md)。

## 输入与依赖

- Windows、Python 3.11+，依赖版本固定于 `requirements.txt`。
- Steam 2026版、AppID 5342930、build 26099941的干净原版目录，SHA-256见 `assets/supported-build.json`。不要将已汉化目录作为原版输入。
- 系统或用户Fonts目录中的 `fusion-pixel-12px-proportional-zh_hans.ttf` 与 `ChillBitmap_16px.ttf`；身份固定于 `locales/zh-CN/font-profile.json`，字体发现不会自动下载或安装字体。
- GUI安装器另需.NET 10 SDK及 `installer/branding/logo.png`、`app.ico`，输入SHA见 `installer/branding-inputs.json`。完整品牌图片不随源码分发，详见[安装器说明](docs/GUI_INSTALLER.md)。

## 完整构建

在仓库根目录执行，将示例路径换成已核对的原版目录：

```powershell
python -m pip install -r requirements.txt
python -X utf8 tools/font_pipeline.py
python -X utf8 tools/build_locale.py --game "D:/Games/Dementium II Original"
```

`build/full-zh-CN/`包含重建的EXE/ROM、稀疏差分、逻辑译文、运行文本与审计报告。构建不修改原版输入与实际Steam安装，不执行游戏。
自动门禁覆盖676条文本、控制码、记录结构、全包图片允许区域、正文补字尺寸/基线、VFS双索引与受守卫的原生补丁。
`capacity_bytes=null`表示容量未知，不表示无限制。

## 测试与安装器

```powershell
$env:DEMENTIUM_MODIFIED_EXE = (Resolve-Path "build/full-zh-CN/Dementium II.exe").Path
$env:DEMENTIUM_UI_TEST_EXE = $env:DEMENTIUM_MODIFIED_EXE
$env:DEMENTIUM_PREVIEW_ROM = (Resolve-Path "build/full-zh-CN/rom.zar").Path
python -X utf8 -m unittest discover -s tests -q

# 按实际SDK路径设置，或使用build/toolchain/dotnet/dotnet.exe默认位置。
$env:DOTNET_EXE = "D:/Tools/dotnet/dotnet.exe"
python -X utf8 tools/build_installer.py
python -X utf8 tools/package_installer.py
python -X utf8 tools/verify_installer.py --game "D:/Games/Dementium II Original"
```

默认安装器为 `dist/Dementium-II-zh-CN-Setup.exe`，ZIP为 `dist/Dementium-II-zh-CN-Installer.zip`。
GitHub v1.0附件名为 `Dementium-II-CN-v1.0.exe`，身份见 `assets/releases/v1.0.json`。
验证脚本显式绑定当前EXE/ROM，检查真实文件副本安装、幂等、升级、恢复、Steam只读检测、自包含界面与隔离回滚，不启动游戏、不改存档。
合成测试不需要游戏资产；完整PE/ROM回放还需本地原版与构建输出。历史专项的小型EXE夹具见[保留策略](docs/BUILD_STORAGE.md)。

## 重现与发布

文本和JSON固定LF，ZIP成员顺序及时间戳固定。`source-inputs.json`与`release-manifest.json`记录输入及生成物身份；资源/差分复现与不同SDK下安装器PE复现分别判断。
版本由 `assets/release-policy.json`约束，当前保持1.0.0；修复不会自动递增版本。
源码不含完整游戏、字体、品牌输入及SDK。当前玩家通关结论属于[已发布产物](docs/STATUS.md)，新改动须按实际范围验证。

## 本地清理

```powershell
powershell -ExecutionPolicy Bypass -File tools/clean_generated.ps1
powershell -ExecutionPolicy Bypass -File tools/clean_generated.ps1 -Apply
```

保留当前输出、一个原版基线、SDK、源码、品牌输入、小型回归夹具及证据；删除重复大副本和编译缓存，详见[BUILD_STORAGE.md](docs/BUILD_STORAGE.md)。
