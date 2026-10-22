# 本地目录整理（2026-10-21）

- 初始检查源码、构建与Git状态，将既有字库和明信片成果提交推送为c5e644a。
- 历史重复构建baseline、clean-checkout、fixed-smoke、latin-original-baseline、package-test、probes、rollback、rollback-shell、runtime已移入忽略的build/archive。
- 归档使用已验证工作区内的明确源/目标路径；不移动Steam原件、存档、证据或当前验收副本。
- 冗余空占位.gitkeep已移除，源码只保留实际工具、翻译、测试和文档。
- 当前默认全文入口为build/full-zh-CN，当前包为dist/Dementium-II-zh-CN-preview.zip。
- 旧最小实验、原中文副本和明信片修复版按可回滚依据保留。
- 历史资料为可恢复归档，不声称已物理删除或释放同等磁盘空间。移动清单位于build/cleanup-archive.json。
- 不提交build、dist、游戏二进制/PNG、字体缓存、AGENTS.md或内部LOCALIZATION_STANDARD.md。
- 完成后把旧technical-probe.zip与空src目录移至build/archive/final-cleanup；dist仅保留当前全文差分包，最终移动明细为build/final-cleanup.json。

## 2026-10-22 发布后整理

- 已发布附件与本地验证安装器同SHA-256，保持v1.0标签、原附件及安装器1.0.0版本。
- 删除809个重复生成文件，共8,712,987,477字节（约8.1GiB），包括旧ROM副本、旧大安装包及编译缓存；完整ROM只保留当前输出与一个原版基线。
- 当前安装器EXE/ZIP、提取SDK、品牌输入、译文、源码、小型EXE夹具及原始证据保留，逐项核对哈希。
- 人工审校资料归档至build/archive/manual-review，未删除唯一审校资料；移除过时Python预览分发ZIP，开发工具仍在。
- 删除未填写的通用文档模板，保留真实项目知识及历史回归；README改为安装入口，验收状态统一到STATUS.md。
- 本轮删除清单记录各文件SHA-256与重建依据，保存在忽略的build/maintenance；源码快照可在隔离目录逐字节恢复。

当前保留策略见[BUILD_STORAGE.md](BUILD_STORAGE.md)。以上实际删除与此前仅移动归档的整理分开计量。
