# 文件地图

| 路径 | 内容 |
| --- | --- |
| `locales/zh-CN/*.map.json` | 676条结构化文本及原文/备注 |
| `locales/zh-CN/font-profile.json` | 字体身份、语言规则、正文/标题及阅读器配置 |
| `locales/zh-CN/image-text.json` | 图片源身份、文字允许区、图标与原画保护 |
| `tools/build_locale.py` | 完整资源/EXE构建与审计入口 |
| `tools/` | 容器、字库、原生菜单、阅读输入、差分及打包实现 |
| `installer/` | WPF安装器、Steam定位、资源匹配与恢复事务 |
| `tests/` | 合成、图片、安装器及本地PE回放测试 |
| `assets/supported-build.json`、`assets/supported-builds/` | 当前及历史原版身份 |
| `assets/releases/v1.0.json` | 发布安装器身份 |
| `assets/fonts/`、`installer/licenses/` | 来源及第三方许可 |
| `docs/` | 当前说明、专题证据与历史索引 |
| `build/`、`dist/`、`work/` | 本地生成物和工作资料，Git忽略 |

玩家入口见[README](../README.md)，开发者入口见[BUILDING](../BUILDING.md)。最小实验工具保留作机制回归，不作为玩家安装入口。
本地维护指令、完整游戏、原始图片、字体缓存、SDK、存档及反编译正文不进入Git。
