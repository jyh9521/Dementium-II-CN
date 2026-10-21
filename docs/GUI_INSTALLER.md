# Material Design 自包含差分安装器

## 玩家入口

`dist/Dementium-II-zh-CN-Setup.exe` 是 Windows x64 单文件，内置 .NET 10.0.13 / WPF 和 MaterialDesignThemes 5.3.2。
用户不需要安装 Python、.NET、WebView2，也不在启动时下载运行依赖。
主程序增加内置运行时后体积高于旧版约1.2MB，但仍不包含约579MB的完整游戏归档。
目标系统 Windows 10 1809及以上 / Windows 11；仅当前Windows主机实际执行验证，不宣称所有系统通过。

选择自己的 `rom.zar` → 验证 → 确认安装。固定同时处理同目录EXE的5个菜单词。
备份路径 `.dementium-locale/original.zar`、`original.exe`，恢复后保留。
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

31项C#测试（23项归档事务+8项Steam定位）、117项既有Python测试，以及真实归档/EXE副本安装和逐字节恢复。
单文件在无有效DOTNET_ROOT、禁用多级运行时查找、无可用HTTP代理的条件下离线渲染。
预览检查Material Ripple模板、入场动画状态变化、可见进度条/复选框移除，含最小窗口与2倍栅格渲染。
这不等同在所有Windows版本、DPI、系统策略上的测试；动态效果遵循WPF/系统渲染条件。
确切命令、输入、stdout、exit与产物SHA记录于build/installer/VERIFICATION.txt。

系统临时目录须可写，单文件启动会解包原生运行库；这不是系统安装依赖。
未知原始哈希、损坏/缺失备份拒绝覆盖；确认前不启动游戏，不写系统配置。
跨文件提交有失败恢复，但不宣称断电下跨文件原子事务；下一次支持检测并恢复混合状态。

参考：[MaterialDesignInXamlToolkit](https://github.com/MaterialDesignInXAML/MaterialDesignInXamlToolkit/tree/v5.3.2)、[.NET单文件自包含发布](https://learn.microsoft.com/en-us/dotnet/core/deploying/single-file/overview)、[.NET Windows平台](https://learn.microsoft.com/en-us/dotnet/core/install/windows)。
