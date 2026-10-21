# Dementium II（2026 Steam）简体中文汉化工程

Steam AppID **5342930**，当前分析 build **26091059**，不适用于 2013 HD 版。

## 当前实际状态（2026-10-21）

**已识别文本已建立完整初译，正在全量审校；实机验收单列。**

- 169个英文资源、666条记录，510条中文初译，156条人名/谜题/技术记录保留。
- 正文和英文采用 Fusion Pixel12，章节中文采用 ChillBitmap16。
- 明信片72px文字区重排与离线遮挡回归已实现，66项测试通过。
- 用户已提供中文主菜单与明信片实机截图，修复后明信片仍待实机验收。
- 不自动启动游戏，不修改 Steam 原件，不创建未经授权的正式 Release。

## 入口

- [技术报告](docs/TECHNICAL_ANALYSIS.md)、[进度](docs/PROGRESS.md)。
- [构建与发行](docs/BUILD_AND_RELEASE.md)、[测试清单](docs/TESTING_CHECKLIST.md)。
- [实验包说明](docs/PROBE_README.md)、[安装与恢复](docs/INSTALLATION_GUIDE.md)。
- [文件地图](docs/FILEMAP.md)、[术语](GLOSSARY.md)、[更新日志](CHANGELOG.md)。

Python 3.11+，依赖 requirements.txt；本地实验包位于
`dist/Dementium-II-zh-CN-technical-probe.zip`，仅包含差分、脚本和许可证。
它不是正式汉化补丁。所有命令不含游戏启动功能。

仓库：https://github.com/jyh9521/Dementium-II-CN
