# 本地目录与生成物保留

## 保留

- 源码、译文、补丁配方、字体现有身份及许可、品牌输入。
- `dist/Dementium-II-zh-CN-Setup.exe`及当前安装器ZIP；GitHub附件与此EXE同哈希，仅发布名不同。
- `build/full-zh-CN/`当前输出，`build/text-layout-fix/original/`一个支持版本原版基线。
- `build/toolchain/dotnet/`提取后的SDK，不反复复制或重新下载。
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

清理器拒绝重解析点，核对目标始终位于build内，排除Git文件、两份保留ROM、提取SDK及本轮维护证据；不触碰实际游戏安装、存档、Release、dist或源码。
旧Python预览分发包已退出默认入口，工具仍保留作开发/差分回归；可按需重新生成，不保留过时成品冒充当前Release。
