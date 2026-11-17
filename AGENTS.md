# Dementium-II-CN 维护入口

本仓库按可复用、多语言本地化工程维护。先读 [README](README.md) 和 [规范迁移记录](docs/MIGRATION.md)，确认当前版本、事实来源与本次任务。

## 按任务读取

| 任务 | 必读 |
|---|---|
| 工程/新语言/输入身份 | [主规范](docs/LOCALIZATION_STANDARD.md) |
| 翻译/回填/校对 | [项目翻译说明](TRANSLATING.md)、[工作流](docs/TRANSLATION_STANDARD.md)、[数据合同](docs/DATA_CONTRACT.md)、[中文风格](locales/zh-CN/STYLE.md) |
| 字体/图片/字幕 | [资源规范](docs/ASSET_LOCALIZATION.md)及项目对应研究记录 |
| 格式/补丁/运行时 | [技术事实](TECHNICAL.md)、[格式](docs/FILE_FORMATS.md)、[研究规范](docs/RESEARCH_STANDARD.md)、[陷阱](docs/PITFALLS.md) |
| 构建/安装/恢复 | [实际构建](BUILDING.md)、[构建规范](docs/BUILD_STANDARD.md)、[安装规范](docs/INSTALLATION_STANDARD.md) |
| 验收/发布/问题修复 | [验收](docs/ACCEPTANCE.md)、[问题生命周期](docs/ISSUE_STANDARD.md)、[当前问题](docs/KNOWN_ISSUES.md)、[许可](LICENSING.md) |
| README/其他文档 | [README规范与可复用提示词](docs/README_STANDARD.md)、受影响文档的事实来源 |

## 执行与完成

1. 核对当前检出、既有未提交改动、实际输入与既有工具；按本次任务选择相关模块，不重做历史成果。
2. 保留原件与可运行基线；先建立可复现的小范围验证，再修改独立副本。
3. 通用工具、游戏适配与 locale 数据分离；保留稳定 ID、源绑定、未知字段和已有术语。
4. 跑相关检查并记录命令、输入、字面结果、退出状态、候选身份与隔离恢复；离线成功不等同于游戏内验收。
5. 同步维护单一规则来源与项目事实；报告实际验证层级、改动范围、未解决项及恢复方式。

项目专属约束与已批准例外优先于通用默认；冲突显式记录，不以旧阶段规则静默覆盖现行中文风格。规范迁移本身不改变已发布内容、许可或历史验收。启动游戏、安装、打包或发布仅按当前任务与项目约定执行。提交前检查实际文件清单，保留既有改动；完整原版、存档、私有构建输入及缓存留在本地。
