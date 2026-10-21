# Windows图形差分安装器

## 玩家入口

`dist/Dementium-II-zh-CN-Setup.exe`是独立Windows x64程序，内嵌压缩的资源差分、EXE字面量差分和界面配置，不包含完整游戏ROM、EXE、DLL或字体，也不要求玩家安装Python。
配套发行包为`dist/Dementium-II-zh-CN-Installer.zip`，包含安装器、说明和许可证。步骤见`INSTALLER_README.txt`。

1. 浏览选择自己的`rom.zar`，先验证，再安装。
2. 同目录有`Dementium II.exe`时默认处理其中5个菜单词，也可取消勾选仅处理独立资源文件。
3. 仅支持`assets/supported-build.json`指定Steam2026构建或当前补丁已安装状态；未知哈希不覆盖。
4. 备份位于目标目录`.dementium-locale/original.zar`和`original.exe`。恢复原版保留备份，不改存档或设置。
5. 写入权限不足时提供用户手动点击的管理员重启入口，不自动提权、启动游戏或修改注册表。

## 内容输入

此次将用户确认的`work/manual-review/图片/在这里精修`中41张PNG按原生尺寸导出为差分，未重新生成、猜写文字或引入已隔离的模糊图片草稿。
26张保护图逐字节保持原版。四张主LOGO/公司名贴图不进入替换列表，继续保留英文原版。
高清工作图不作为私有构建依赖：源依赖RGBA异或差分保存在语言配置中，干净检出可用原版资源重建。
输入图片哈希及工作/原生尺寸记录在`build/installer/approved-image-inputs.json`。
文本仍为520条中文、156条有理由保留，27条语境备注不变。图片确认不等于完整游戏流程验收。

## 构建与源文件

- `installer/InstallerEngine.cs`：流式差分、哈希守卫、备份、双组件提交和恢复。
- `installer/InstallerForm.cs`：文件选择、验证/安装/恢复、日志、进度和权限入口。
- `locales/zh-CN/installer.json`：标题、文件名和项目说明。
- `tools/build_installer.py`、`tools/package_installer.py`：原生构建和白名单打包。

```powershell
python -X utf8 tools/build_locale.py --game "原版游戏目录"
python -X utf8 tools/build_installer.py
./build/installer/InstallerTests.exe ./build/installer-unit-tests
./build/installer/InstallerTests.exe --real "原版游戏目录" "尚不存在的副本测试目录"
python -X utf8 tools/package_installer.py
```

已有PNG需要明确导入时：

```powershell
python -X utf8 tools/import_image_edits.py --original "原版rom.zar" --input "已确认PNG目录" --config locales/zh-CN/image-text.json --apply
```

导入核对输入集合、比例和源哈希，并拒绝保护图替换。不能把未经确认的生成草稿送入此目录。
编译使用Windows .NET Framework v4目录的`csc.exe`，无需下载SDK；玩家使用系统.NET Framework4.8。
JSON/GZip差分和发行ZIP规范化顺序/时间戳；旧编译器可能产生不同PE时间戳/MVID，不宣称安装器跨次编译同哈希。输入、源码、编译器和产物身份另有记录。

## 提交和故障处理

验证只读，不创建备份。安装/恢复重新验证，取得目录独占操作锁后建立经过哈希验证的原版备份。
完整临时结果通过校验后，使用同卷`File.Replace`提交；第二文件提交失败时恢复第一文件提交前状态。
强制终止可能留下原版/汉化混合状态，下一次可在备份验证后继续安装或恢复；不宣称跨文件系统原子事务。
未知文件、损坏备份、缺少可信备份的汉化文件和空间不足均拒绝覆盖。

## 已做验证

23项C#测试覆盖正常/仅ROM安装、幂等恢复、错误版本、损坏备份、混合状态、锁冲突、边界检查和注入失败回滚。
另有117项既有Python测试、真实文件副本的安装/恢复哈希检查，以及192DPI界面离线渲染和标签截断检查。
测试不操作玩家实际安装；截图是安装器自身控件渲染，不是游戏截图，也不代表所有DPI和完整游戏流程验收。
精确命令、输出、退出码和身份保存在`build/installer/VERIFICATION.txt`。
