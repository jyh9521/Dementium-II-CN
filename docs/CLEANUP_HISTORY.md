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
