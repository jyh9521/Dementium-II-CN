# 许可与来源

## 项目代码与译文

- 自编工具、安装器及项目文档：MIT，见[LICENSE](LICENSE)。
- 原创中文译文：CC BY-SA 4.0，见[LICENSE-translations.md](LICENSE-translations.md)。
- 原文列、游戏文本、商标、LOGO和商业美术仍归原权利人所有，不因源码公开而获得上述授权。

## 字体

正文/英文使用TakWolf的Fusion Pixel Font（2026.10.16），章节使用ChillBitmap16px（1.000，Warren2060及原版权贡献者）；正文少量缺字使用ChillBitmap face按12px生成并统一基线。
字体身份记录于 `locales/zh-CN/font-profile.json`，版权与OFL全文保留在：

- [Fusion Pixel OFL](assets/fonts/Fusion-Pixel-OFL.txt)
- [ChillBitmap许可](assets/fonts/ChillBitmap-LICENSE.md)

旧Noto CJK仅供历史最小实验，来源固定于 `assets/fonts/source.json`及[OFL.txt](assets/fonts/OFL.txt)，当前全文构建不使用。完整TTF/OTF缓存不提交。

## 安装器与依赖

MaterialDesignInXamlToolkit、.NET/WindowsDesktop和XamlBehaviors等许可保存在[installer/licenses](installer/licenses/)，随安装器分发。Python构建依赖固定于 `requirements.txt`，分别遵循各自许可。
品牌图片作为独立构建输入提供，Git仅保存身份记录，不分发完整品牌输入。

## 源码与发布物

Git保存结构化译文、工具、源依赖补丁配方、版本身份、测试与技术记录。
Release安装器只带差分、必要的项目运行组件与许可，不包含游戏本体、完整ROM、原版游戏EXE、存档或反编译正文。
构建和安装需要合法持有的原版游戏，构建得到的完整资源仅留本地，不上传为源码或独立资源包。
制作与技术来源见[CREDITS.md](CREDITS.md)。
