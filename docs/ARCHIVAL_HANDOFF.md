# 精简归档交接（2026-10-24）

## 状态

- 源码保留“行走晃动：轻微”与小地图“半透明”的独立显示引用。
- 现有v1.1.1安装器不重新编译、不更新发布附件；原文件SHA-256为 `ae11b5dcf964f37482ad71f6756e32b18021a51d126b69166563b0eb244c216a`。
- 实际Steam安装、原件备份与存档不属于本次清理目标。
- NAS旧v1.0/v1.1归档保留，新归档为 `Dementium-II-CN-精简归档-20261024.zip`，附逐文件SHA-256清单及外部整包SHA-256。

## 必要输入与恢复

1. 解压整个 `Dementium-II-CN/` 目录；Git历史、源码、译文、测试及项目文档一并保留。
2. 原版build 26123896位于 `build/original/`；当前完整构建位于 `build/full-zh-CN/`。两个ROM用途不同，不是重复测试副本。
3. `build/archive/font-inputs/`保留匹配哈希的字体文件。恢复到另一台Windows时先安装字体；许可见 `assets/fonts/`。
4. `installer/branding/`保留现有品牌输入；`build/installer/old-v1.0/`与 `build/installer/compatibility-v1.1.1/`保留已提取稀疏配方，旧版原生EXE输入位于 `build/inputs/26099941/`。
5. SDK、SDK压缩包、编译缓存、重复大ROM及重复安装器包装不保留。重建时安装Python依赖和.NET 10 SDK，按BUILDING.md设置 `DOTNET_EXE`，无需归档SDK本体。

历史ROM按 `build/maintenance/archive-20261024/rom-recovery.json` 和 `ROLLBACK.sh`还原到新的独立文件。恢复脚本核对原版及生成物完整SHA-256。合成测试缓存由测试重新生成，编译缓存由SDK重新生成。

本地Steam安装使用的窄修正版与仓库完整重建可能包含不同时间的其他已确认译文；两种历史状态都由精确差分保留，不混淆为同一产物。历史证据日志保留原始内容，已删除的测试路径不表示仍然存在。

## 验证边界

精简验证包括清理前逐文件哈希、保留原件身份、历史ROM差分还原、安装器哈希不变、实际游戏文件不变、核心回归测试、ZIP逐成员SHA-256及源文件一致性。不启动游戏，不将归档完整性视为游戏内验收。
