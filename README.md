# Dementium II（2026 Steam）简体中文汉化工程

Steam AppID **5342930**，当前分析 build **26091059**，不适用于 2013 HD 版。

## 当前实际状态（2026-10-21）

**技术实验阶段；中文游戏显示尚未验收，不是完整汉化。**

- x64 原生构建；ZAR1 封包 3,471 个成员。
- 英文 169 个文本资源、666 条记录，577 条不同原文。
- 单项实验：`New Game → 新游戏`，加入三个中文字形。
- 已填写 1/666 个目标字段（约 0.15%）；不代表全游戏覆盖率。
- 全包字节一致往返、二次提取、字体静态校验、隔离回滚及 36 项合成测试通过。
- 本轮仅离线工作，不启动游戏，不改 Steam 原件。
- 全量翻译等待中文显示技术门禁；没有正式 Release。

## 入口

- [技术报告](docs/TECHNICAL_ANALYSIS.md)、[进度](docs/PROGRESS.md)。
- [构建与发行](docs/BUILD_AND_RELEASE.md)、[测试清单](docs/TESTING_CHECKLIST.md)。
- [实验包说明](docs/PROBE_README.md)、[安装与恢复](docs/INSTALLATION_GUIDE.md)。
- [文件地图](docs/FILEMAP.md)、[术语](GLOSSARY.md)、[更新日志](CHANGELOG.md)。

Python 3.11+，依赖 requirements.txt；本地实验包位于
`dist/Dementium-II-zh-CN-technical-probe.zip`，仅包含差分、脚本和许可证。
它不是正式汉化补丁。所有命令不含游戏启动功能。

仓库：https://github.com/jyh9521/Dementium-II-CN
