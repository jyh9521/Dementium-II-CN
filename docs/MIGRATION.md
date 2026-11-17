# 汉化基准 2.1 迁移记录

日期：2026-11-17 · 仓库：`Dementium-II-CN` · 原分支：`main` · 迁移前提交：`26666a7ea28e7d954efc5387d9f6a065d3876df9`

## 适用范围

本项目原有 BUILDING、TRANSLATING、TECHNICAL、LICENSING、FILE_FORMATS、PITFALLS、KNOWN_ISSUES 七份规范/项目记录，且旧 `.gitignore` 明确排除了 AGENTS.md 与 docs/LOCALIZATION_STANDARD.md，因此纳入本轮旧规范升级。此次把共享规范和任务入口纳入 Git；其他原件、生成物与私有数据的忽略边界保持。

这是后续维护要求的文档迁移，不是新汉化版本或游戏补丁。既有译文、数据结构、程序、测试、构建配置、发布附件、标签、许可及已记录的通关反馈均保持原样；[当前项目记录](STATUS.md)和 [README](../README.md)仍负责当前状态。文档更新不把历史未测试内容改为已通过，也不撤销原有反馈。

## 单一事实来源

| 内容 | 现行入口 |
|---|---|
| 通用工程、输入身份、多语言分层 | [LOCALIZATION_STANDARD](LOCALIZATION_STANDARD.md) |
| 验收、覆盖率和完成声明 | [ACCEPTANCE](ACCEPTANCE.md) |
| 数据语义及翻译工作流 | [DATA_CONTRACT](DATA_CONTRACT.md)、[TRANSLATION_STANDARD](TRANSLATION_STANDARD.md) |
| 项目术语、真实数据入口和编辑方式 | [TRANSLATING](../TRANSLATING.md) |
| 中文句号规则 | [STYLE](../locales/zh-CN/STYLE.md) |
| 构建要求 / 实际命令 | [BUILD_STANDARD](BUILD_STANDARD.md) / [BUILDING](../BUILDING.md) |
| 安装、升级、恢复要求 | [INSTALLATION_STANDARD](INSTALLATION_STANDARD.md) |
| 字体、图像和媒体 | [ASSET_LOCALIZATION](ASSET_LOCALIZATION.md) |
| 研究记录要求 / 已有技术事实 | [RESEARCH_STANDARD](RESEARCH_STANDARD.md) / [TECHNICAL](../TECHNICAL.md)、[FILE_FORMATS](FILE_FORMATS.md)、[PITFALLS](PITFALLS.md) |
| 问题状态要求 / 真实问题 | [ISSUE_STANDARD](ISSUE_STANDARD.md) / [KNOWN_ISSUES](KNOWN_ISSUES.md) |
| README写作、命令与链接验收 | [README_STANDARD](README_STANDARD.md) |
| 组件清单要求 / 真实许可和署名 | [LICENSING_STANDARD](LICENSING_STANDARD.md) / [LICENSING](../LICENSING.md) |

不复制空白模板覆盖技术历史，不用统一占位符替代真实参数，不强制迁移现有数据格式或 locale 名称。新增标准字段通过项目适配器映射；新的检查要求不等同于现有工具已经实现。专属约束和已批准例外继续保留，偏离通用要求时写明原因与证据；中文个人规则以现行 STYLE 为准。

## 句号规则与旧检查器

- 后续文本编辑按 STYLE 的逻辑句和内容角色判断，旧“无其他标点”“多句整段豁免”“按排版行切句”表述不再作为现行规范。
- 旧实现/记录：tests/test_locale_style.py；旧说明允许冒号豁免，需复核逐句判定和故事/对白角色。
- 自动化适配状态：`not_run`。本次未更改或重新验收上述工具；旧结果只证明当时规则，不自动升级为 2.1 合规。后续采用新规则时逐条复核受影响记录并重置相应审校/运行证据，保留旧版记录。
- 待适配前用人工角色/逻辑句复核补足；先加控制码、混合角色、嵌套引号、小数、换行与多句正反例，再启用新自动门禁。旧自动修复只用于原阶段重放，不用于新版批量改译文。
- README解释性正文不套用游戏文本句号规则；其中引用的译文仍按 STYLE，错误/修改前示例须标明。

## 本轮验证与后续验收

本轮只验证文档迁移：新规范可追溯、入口和本地链接有效、旧规则冲突已更新或明确标为历史、非文档与正式许可文件未变、差分可在隔离副本恢复。新规范中的 G0-G4 是后续相关修改/发布的验收要求，本次没有运行游戏测试、安装器、资源重建或重新发布附件。旧文档命令和历史输出保留，不把它们写成本轮执行结果。

保留实际构建限制和未解决问题。新增检查/适配须另行实现并用项目输入验证；文件名为 STYLE 或 ACCEPTANCE 本身不是实现/通过证据。共享参考校验器、示例 catalog 和 synthetic 测试未安装到本仓库，文档里的参考模型不应直接当作现成命令调用。

## 来源指纹

以下是本次读取的汉化基准 2.1 源文档 SHA-256。共享规则按职责迁入项目；模板占位与假想命令未复制，正式许可未替换。

| 基准源文件 | SHA-256 |
|---|---|
| `AGENTS.md` | `df23644a0e05a03cf75637fd18bf10c0f40cabf04e20b2ca0e6fcaa99e0378ac` |
| `BUILDING.md` | `1275df2ec0f6ffeb6cea61daa80fe029936e506215817a2c4b5c49d54761d394` |
| `TRANSLATING.md` | `238a1499b008465a38508ef204a05c451741c3b3288e981e04a79b81eea254fa` |
| `TECHNICAL.md` | `115ff100e97c0a9280cd0beb369050c1c82624e11c2ef63e7d6fdd7a30c8b1b6` |
| `LICENSING.md` | `3baa7ac2a9d51fb0c0db7b6b09c63eeb1c860adfd9cc853948a2c8411e272aef` |
| `locales/zh-CN/STYLE.md` | `aaaf61479b726b38e2fbb8f03b1f44b236e34c1804f101bf75951b2c1eb12ca6` |
| `docs/LOCALIZATION_STANDARD.md` | `e9364c20605fc72191265e9d23e2bc13762a2847277ebc65b86dba30b5cf44e7` |
| `docs/ACCEPTANCE.md` | `68d1e7da63be7074b34ad4b4d7dd8f5c5aa9ea43f0c55be4e5beaca9da0b524b` |
| `docs/DATA_CONTRACT.md` | `f24ed1579c346330e0a6e16bfc41273bfd15801e94322de0df2b1a515d48c339` |
| `docs/INSTALLATION_STANDARD.md` | `90299ea6f0d89ce792b6c224ef8c2a1ffcab699c0d3da293f05a0a6cf20b02e5` |
| `docs/ASSET_LOCALIZATION.md` | `bb37be474398f8ac6f41370d745ced4167902d7700c867bcfc1dcd864b080138` |
| `docs/README_STANDARD.md` | `13f08811aa5148dc8c419af9c8932eeadbf005d1b71e108b9a32a7793f8aa63d` |
| `docs/FILE_FORMATS.md` | `44ee525a41821f6a523a983c90bf44026336265ac4983b7d5c822ace08ec705c` |
| `docs/PITFALLS.md` | `3b995fa73cc2d1705b4b535c6c2fbf8c8db06a6a8a58ea4164cb54edd06773ae` |
| `docs/KNOWN_ISSUES.md` | `abc45e1b86946e3680c48757f958e16d7c835463e9d4ab6a764de88a31a6435b` |
| `docs/MIGRATION.md` | `1009093f2399edb417896a3b0b2c361289bad7f1e99f7567497c52f2040bfadd` |
