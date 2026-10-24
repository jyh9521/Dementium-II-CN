# 本地目录与生成物保留

## 保留

- 源码、译文、补丁配方、字体现有身份及许可、品牌输入。
- `dist/Dementium-II-zh-CN-Setup.exe`一份现有安装器；发布名别名与安装器ZIP可以按需复制或重新打包，不重新编译安装器。
- `build/full-zh-CN/`当前输出，`build/original/`一份支持版本原版基线。
- `build/archive/font-inputs/`字体输入、安装器品牌图片、已提取旧版兼容稀疏配方。
- SDK、SDK压缩包和编译缓存不归档；恢复构建时另行安装BUILDING.md要求的工具链。
- 小型历史EXE夹具、差分、研究及验证日志。既有专项仍使用reader-input-fix/menu-patched.exe、menu-click-fix/modified.exe等文件。
- 人工审校资料移至 `build/archive/manual-review/`，唯一图片草稿与备注不删除、不提交原始游戏图片。

## 删除与恢复依据

重复完整ROM、旧大安装器、旧大压缩包与已知编译缓存可以删除；不再给每次安装/回滚实验保存一整份游戏。
每个删除文件记录相对路径、长度、SHA-256与重建说明，清单保存在 `build/maintenance/deleted-files-*.json`。
源文件快照及本轮精确证据在 `build/maintenance/release-cleanup/`；历史报告保持当时含义，生成路径不保证永久存在。
重新实验时用保留原件、源码和历史配方生成副本，不为“备份”再次复制已清理的大文件。

```powershell
powershell -ExecutionPolicy Bypass -File tools/clean_generated.ps1
powershell -ExecutionPolicy Bypass -File tools/clean_generated.ps1 -Apply
```

清理器拒绝重解析点，核对目标始终位于build内，排除Git文件、原版/当前构建ROM、归档输入和维护证据；SDK可以重新安装，不保留在项目内。不触碰实际游戏安装、存档、Release、dist或源码。
旧Python预览分发包已退出默认入口，工具仍保留作开发/差分回归；可按需重新生成，不保留过时成品冒充当前Release。

## 2026-10-24 精简归档

保留两份不同用途的ROM：原版重建输入与当前完整汉化输出。其余完整历史ROM先转成以原版为基线的精确稀疏差分并逐一重建校验；原路径、SHA-256和恢复配方见 `build/maintenance/archive-20261024/rom-recovery.json`。

历史验证报告保留原始内容，不承诺报告中的测试副本永久存在。需要历史ROM时使用同目录 `ROLLBACK.sh --relative <清单内原相对路径> --output <新的输出文件>`恢复到独立文件。编译缓存不做逐文件备份，按源码重建。

NAS新增归档不覆盖已有v1.0/v1.1归档。归档内包括Git历史、源码和必要非Git输入、现有安装器、当前构建和关键验证证据，不包含SDK及编译缓存。字体在另一台Windows恢复时需先安装，再按BUILDING.md重建。

安装器保持已发布版本；“行走晃动：轻微”修正已进入源码和本地游戏，但尚未更新现有安装器。归档不改变此状态。
