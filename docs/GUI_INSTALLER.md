# Material Design 自包含差分安装器

## 玩家入口

`dist/Dementium-II-zh-CN-Setup.exe` 是 Windows x64 单文件，内置 .NET 10.0.13 / WPF 和 MaterialDesignThemes 5.3.2。
用户不需要安装 Python、.NET、WebView2，也不在启动时下载运行依赖。
主程序增加内置运行时后体积高于旧版约1.2MB，但仍不包含约579MB的完整游戏归档。
目标系统 Windows 10 1809及以上 / Windows 11；仅当前Windows主机实际执行验证，不宣称所有系统通过。

选择自己的 `rom.zar` → 确认安装。可选检查资源；归档仍按资源内容匹配，程序包含5个菜单词及F1原生菜单改动，因此EXE精确锁定已核对的26099941版本。新增原生代码、中文字体及升级事务见`NATIVE_CHEAT_MENU.md`。
资源级备份为 `.dementium-locale/original-完整SHA256.zar` / `.exe`，resource-state.json记录当前恢复身份；旧版备份不删除。
手工选择路径仍可用，自动检测不写文件、不安装、不启动游戏。

## Steam 自动检测：已验证实现

1. 读取 HKCU/HKLM 的32/64位 `Software\Valve\Steam` 中 SteamPath/InstallPath；检查系统程序目录作为补充。
2. 读取每个Steam根下的 `steamapps/libraryfolders.vdf`，支持现代嵌套path和旧式数字路径字段。
3. 扫描这些库的 `steamapps/appmanifest_5342930.acf`，核对appid。
4. 使用清单中的installdir，而非假定目录必须叫Dementium II；拒绝绝对路径或目录穿越。
5. 只有rom.zar及同目录EXE都存在才填入候选；多份安装在日志列出，可手动选择。
6. 缺失库、损坏清单、访问失败跳过；不进行全盘扫描、不依赖Steam当前运行。

磁盘挂载丢失、注册位置和库配置同时缺失或权限阻止读取时需要浏览选择；不保证每种非标准安装均能检测。
此机正规Steam安装路径已实际只读检测到。包含中文/空格库、旧格式、错误AppID、穿越和文件缺失的合成回归。

## 界面

使用真正的MaterialDesignInXamlToolkit，而不是WinForms仿色按钮。
Material Design 3 主题、统一圆角/表面/字体/输入框、按钮Ripple状态、DialogHost确认动画、240–280ms入场动画。
中央中文LOGO、用户指定图标；不显示EXE选项、额外底部说明和线性进度条。
底部左侧仅版本信息，Steam链接到指定商店；右侧伯翎飞云链接到指定博客。
后台任务更新状态和日志，操作期间禁用路径与按钮、禁止中途关闭；不修改游戏菜单LOGO。

## 源码与构建

- installer/InstallerEngine.cs：哈希、差分、备份、临时文件、双组件事务恢复
- installer/SteamLocator.cs：Steam注册位置和KeyValues清单读取
- installer/MaterialWindow.xaml / .xaml.cs：WPF Material界面与动画
- installer/Installer.csproj / Installer.lock.json：固定工具包和运行时版本
- installer/licenses/：第三方许可，随EXE/ZIP分发

开发端需.NET 10 SDK（本次10.0.402）、Python和现有归档构建依赖；玩家端不需要这些工具。
品牌输入由用户提供，位于忽略目录 `installer/branding/logo.png` 和 `app.ico`，身份记于branding-inputs.json。
图标是用户256×256 PNG原字节包装ICO，LOGO保持原PNG，不重绘、不猜字。
为避免提交原版封面图片，这两个完整品牌资产不进入Git；重新构建须提供相同输入。
设置环境变量DOTNET_EXE指向SDK的dotnet.exe，或使用本地build/toolchain/dotnet/dotnet.exe。

```powershell
python -X utf8 tools/build_locale.py --game "用户原版游戏目录"
python -X utf8 tools/build_installer.py
& $env:DOTNET_EXE build/installer/tests/net10.0-windows10.0.17763.0/InstallerTests.dll build/installer-material-tests
& $env:DOTNET_EXE build/installer/tests/net10.0-windows10.0.17763.0/InstallerTests.dll --real "用户原版游戏目录" "尚不存在的副本目录"
python -X utf8 tools/package_installer.py
python -X utf8 tools/verify_installer.py --game "用户原版游戏目录"
```

项目差分需原版文件参与；41张已确认图片仍由源依赖的像素差分重建，26张受保护原图和游戏英文LOGO保留。
JSON/GZip/ZIP规范化；记录SDK、依赖锁定和输入SHA，不将所有SDK/平台差异下PE同哈希作为承诺。

## 验证与边界

53项C#测试（31项既有归档/定位 + 22项资源级兼容/恢复）、120项Python测试，以及真实归档/EXE副本安装和逐字节恢复。
单文件在无有效DOTNET_ROOT、禁用多级运行时查找、无可用HTTP代理的条件下离线渲染。
预览检查Material Ripple模板、入场动画状态变化、可见进度条/复选框移除，含最小窗口与2倍栅格渲染。
这不等同在所有Windows版本、DPI、系统策略上的测试；动态效果遵循WPF/系统渲染条件。
确切命令、输入、stdout、exit与产物SHA记录于build/installer/VERIFICATION.txt。

系统临时目录须可写，单文件启动会解包原生运行库；这不是系统安装依赖。
未知原始哈希、损坏/缺失备份拒绝覆盖；确认前不启动游戏，不写系统配置。
跨文件提交有失败恢复，但不宣称断电下跨文件原子事务；下一次支持检测并恢复混合状态。

参考：[MaterialDesignInXamlToolkit](https://github.com/MaterialDesignInXAML/MaterialDesignInXamlToolkit/tree/v5.3.2)、[.NET单文件自包含发布](https://learn.microsoft.com/en-us/dotnet/core/deploying/single-file/overview)、[.NET Windows平台](https://learn.microsoft.com/en-us/dotnet/core/install/windows)。


## 2026-10-21 原版基线更新：26099941

原安装器基于旧Steam build 26091059；用户指定的现有Steam安装清单为26099941，depot 5342931 manifest 2467892649090529485。
新ROM SHA256 97618c6f7935e1214f00c7c35f9f45689d898328f51f1024a054850027657e33，579234304字节。
新EXE SHA256 ea68364b72c7c1ef5b84d24990ddcab6090eedff752736d3ef3c634733351e56，5522944字节。
两归档同为3471成员，文本提取结果完全相同，仅TEX/SETTINGS.TSV第391字节由0x33变为0x31；重新构建保留该新版资源，不套回旧文件。
5个EXE槽重新核对.rdata位置和完整零填充。HI-RES CRT新槽只有12字节，不能沿用旧16字节槽覆盖后面的数字1。
已保留旧基线元数据于assets/supported-builds/26091059.json，旧构建在忽略的build/archive中；该精确差分作为构建参考；后续资源级安装器不把此整包哈希作为玩家版本白名单。
界面版本标签及报错改由locale设置读取，构建时强制与supported-build.json一致，防止再次显示旧build。
验证包含指定实际安装路径的只读Inspect、真实文件副本安装/恢复和新版TSV字节保留；实际安装路径从未执行安装或游戏。


## 原资源级安装模式（1.0.0设计记录）

以下是不包含原生作弊菜单的旧载荷设计。1.1.0保留归档按成员匹配，并对原生菜单EXE使用精确身份、代码字节和追加段校验；新旧载荷分开处理，旧模式不再代表完整包的程序部分。

UI使用ResourceEngine，而非旧Engine的固定整包差分入口。构建参考仍锁定受审计输入，以确保翻译来源和再现性。
运行端不限制build/整包哈希/整文件大小；SHA仅用于被改资源匹配、备份/安装记录完整性和并发修改检测。

- tools/build_resource_payload.py从审定归档构建源依赖的成员内差分，不分发完整归档或完整原版贴图。
- installer/ResourceEngine.cs动态解析当前ZAR名称/TOC；只替换待汉化成员，按实际EOF追加，更新当前~INDEX尺寸，保留不相关更新。
- EXE扫描实际.rdata范围，匹配完整原文/译文及NUL字节槽，要求唯一且范围不重叠；不使用配方中的offset和完整EXE身份。
- 所有待改资源必须是已知原文资源或本补丁输出；实际文本/字体结构变化时报告资源名，不以猜测写入。
- 完整备份按原件实际SHA命名，多版本备份共存；旧版resource-state.json先记录计划输出；1.1.0改为双文件提交成功后再提交记录，异常时恢复文件和旧记录。
- 游戏更新产生新原版且资源仍兼容时，创建新备份。安装后文件被其他程序再次修改时不静默恢复旧文件。
- 可选资源检查；检测到路径后可直接安装。恢复按钮仍要求备份目录存在。

旧Engine/固定差分保留供CLI和精确参考/回归测试，不是新GUI的版本门禁。
旧安装器到资源级版本只有已知安装输出和可信旧备份可以自动接纳，不将无来源的已汉化文件当原件备份。

```powershell
python -X utf8 tools/verify_installer.py --game "已核对的26099941原版目录"
```

此验证分别运行精确参考、资源级当前版、不同全包哈希/EXE偏移的旧版及合成变化，逐字节恢复各自原件，不启动游戏。

1.1.0中文菜单为86项/278字形，F1、输入隔离、生命和弹药经过隔离机器码回放。原版副本真实安装/恢复与71项安装器测试通过；旧版升级失败时同时恢复原文件及记录。真实游戏窗口不由验证脚本自动启动。旧命令的`--older-game`交叉版本EXE测试仅适用于历史纯文字槽载荷，不适用于含原生代码的完整包。
