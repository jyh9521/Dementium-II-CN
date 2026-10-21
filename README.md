# Dementium II（2026 Steam）简体中文汉化工程

Steam AppID **5342930**，构建参考 build **26099941**（归档按资源匹配，F1原生菜单程序精确匹配该版本），不适用于 2013 HD 版。

## 当前实际状态（2026-10-21）

**本地可识别文本已全部翻译并完成对照审校；全流程实机验收单列。**

- 已审计全部3471个原包成员；179个英文资源、676条记录，520条中文译文，156条专名/谜题/技术数据有理由保留，空译文0。
- 补译此前遗漏的10条开门/门禁卡交互；27条已有完整中文但仍需实机场景确认语境。
- 41张位图187个文字标签及5个PC菜单固定字面量完成配方重建。
- 剧情正常用句号；设置、物体说明和操作提示的无内部标点单句不加句末句号。既有译文已追溯调整。
- 正文和英文采用 Fusion Pixel12，章节中文采用 ChillBitmap16。
- 明信片4行/72px门禁与离线遮挡回归通过；170项Python与71项安装器测试通过，另有实际文件、安装和双组件恢复验证。
- 用户已提供中文主菜单与明信片实机截图，修复后明信片仍待实机验收。
- 不自动启动游戏；安装前保留原版备份，不创建未经授权的正式 Release。

## 入口

- **图形安装器**：本地`dist/Dementium-II-zh-CN-Setup.exe`，自动检测Steam库或选择自己的`rom.zar`，可直接安装；归档按资源匹配，包含F1原生菜单的EXE精确校验版本，支持有可信记录的旧汉化升级；Material Design 3含动画、自包含运行时，不打包完整游戏、不要求另装.NET/Python。详见[安装器说明](docs/GUI_INSTALLER.md)。
- 安装器使用用户确认的41张精修工作图，26张不可辨/未核实图保持原版；英文LOGO和公司名不改。

- [技术报告](docs/TECHNICAL_ANALYSIS.md)、[进度](docs/PROGRESS.md)。
- [构建与发行](docs/BUILD_AND_RELEASE.md)、[测试清单](docs/TESTING_CHECKLIST.md)。
- [玩家说明](docs/PLAYER_README.md)、[安装与恢复](docs/INSTALLATION_GUIDE.md)。
- [全文覆盖与保留依据](docs/TEXT_COVERAGE_AUDIT.md)、[独立文本QA](docs/FINAL_TEXT_QA.md)。
- [文件地图](docs/FILEMAP.md)、[术语](GLOSSARY.md)、[更新日志](CHANGELOG.md)。

Python3.11+，依赖requirements.txt。本地完整副本位于 `build/full-zh-CN/`，由用户手动启动其中EXE。
当前玩家测试包 `dist/Dementium-II-zh-CN-preview.zip` 只含差分、脚本和许可证，不包含完整游戏文件。
不以离线通过冒充通关稳定性验收。“全文”不将调试控制台、平台覆盖层、品牌原画、按键/谜题标识和不可辨微字伪称为已替换中文。
历史重复构建统一存放于忽略的 `build/archive/`，原件、恢复资料和既有验收副本保留。

仓库：https://github.com/jyh9521/Dementium-II-CN

## 原生作弊菜单与图像修复（2026-10-21）

本轮完整构建使用F1开关原生中文作弊菜单。持续作弊可随时取消勾选，原生一次性操作保持按钮语义。详见[使用及验证](docs/NATIVE_CHEAT_MENU.md)、[操作图修复](docs/NATIVE_UI_IMAGE_REPAIR.md)、[死亡图配对色调](docs/IMAGE_VARIANT_TONES.md)。
