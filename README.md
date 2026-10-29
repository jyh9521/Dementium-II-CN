# 《病房2》简体中文汉化

Dementium II（2026 Steam版）的简体中文汉化补丁与可重建工具，包含文本、像素字库、图片文字、中文F1菜单及文档阅读体验修正。

## 支持版本与当前状态

当前补丁 **v1.1.4**，适用于 **Steam 2026版（AppID 5342930）**，支持已验证的 **build 26099941、26123896、26152271、26260428、26286386**；
当前重建基线为 **26286386（EXE版本字段仍为1.0.4）**。
**不适用于2013年的《Dementium II HD》，也不承诺通用所有版本。**

新增“近战准星”选项已纳入翻译，保留本次官方选项表和按钮条更新。安装器内部版本、窗口标题、界面页脚与交付文件名统一为1.1.4；此前发布身份原样保留。

行走晃动的“反转”错误已修正为独立的“普通 / 轻微 / 关闭”，不改变实际设置与小地图；见[修正记录](docs/HEAD_BOB_RUNTIME_FIX.md)。

v1.0已有完整通关记录；本次1.0.4适配尚无新版完整通关记录。离线验收与游戏内验收分别记录，见[适配报告](docs/UPDATE_26286386.md)。

## 下载 / 安装

**[发布列表](https://github.com/jyh9521/Dementium-II-CN/releases)**

1. 准备Steam版游戏并退出运行。
2. 运行 `Dementium-II-CN-v1.1.4.exe`，使用自动检测到的游戏路径；未检测到时，手动选择游戏目录中的 `rom.zar`。
3. 安装完成后，从Steam正常启动游戏。
4. 恢复原版时，在同一个安装器中选择恢复。安装期间请保留游戏目录里的 `cn-backup`；完整恢复并校验后，安装器会自动清理该目录。

安装器为Windows x64自包含程序，**无需另装Python或.NET**，不包含游戏本体，不修改游戏存档。支持带可信备份记录的旧汉化升级。详细步骤见[安装与恢复](docs/INSTALLATION_GUIDE.md)。

## 汉化与功能

- 菜单、交互提示、字幕、文档及图片文字；专名、字母谜题、按键标识与不可辨认原画按清单保留。
- 正文与英文采用Fusion Pixel12px，章节中文采用ChillBitmap16px；补字按正文尺寸和基线生成。
- 长文保留原分段，可用上下键、滚轮或右摇杆滚动阅读；短文与明信片保持独立排版。
- F1打开原生中文菜单，支持鼠标、滚轮和键盘操作；包含可取消的持续选项与一次性操作按钮。

原图中不可辨认的微缩字样不作猜译，英文LOGO与公司名保留。更多操作见[使用说明](docs/PLAYER_README.md)。

## 从源码重建

需要匹配的原版游戏、Python 3.11+及按哈希锁定的两套字体；构建图形安装器还需.NET 10 SDK与单独提供的品牌输入。完整输入与命令见[BUILDING.md](BUILDING.md)。

```powershell
python -m pip install -r requirements.txt
python -X utf8 tools/build_locale.py --game "D:/Games/Dementium II Original"
```

输出位于 `build/full-zh-CN/`，安装器与压缩包生成至 `dist/`。构建工具不启动游戏。仓库只保存源码、结构化译文、补丁配方与文档，不提交完整游戏资源。

## 仓库结构与文档

| 路径 | 内容 |
| --- | --- |
| `locales/zh-CN/` | 结构化译文、字体及图片文字配置 |
| `tools/` | 提取、校验、字体、资源重建、差分与打包工具 |
| `installer/` | WPF图形安装器与原生安装/恢复测试 |
| `tests/` | 合成资源测试与可选本地原生指令回放 |
| `assets/` | 游戏版本、发布身份与第三方许可记录 |
| `docs/` | 使用说明、技术调查、验收与历史记录 |
| `build/`、`dist/`、`work/` | 本地生成物与工作资料，Git忽略 |

- [文档索引](docs/README.md) · [发布与验收状态](docs/STATUS.md)
- [构建说明](BUILDING.md) · [技术说明](TECHNICAL.md) · [技术陷阱](docs/PITFALLS.md)
- [翻译规范](TRANSLATING.md) · [术语表](GLOSSARY.md) · [更新日志](CHANGELOG.md)

## 来源与许可

感谢原游戏开发与发行团队，以及Fusion Pixel、ChillBitmap、Pillow、fontTools和MaterialDesignInXamlToolkit等项目的作者与贡献者。

项目自编工具采用MIT，原创译文采用CC BY-SA 4.0；字体及第三方组件各遵循自身许可。游戏原文和商业资源仍归原权利人所有。详见[许可与来源](LICENSING.md)及[制作与致谢](CREDITS.md)。
