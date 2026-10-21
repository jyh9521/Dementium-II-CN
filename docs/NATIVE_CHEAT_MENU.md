# 原生作弊菜单（2026-10-21）

## 使用

安装本轮完整包后，按 **F1** 打开或关闭原生菜单，鼠标操作复选框和按钮；也可用原生方向/确认输入导航。菜单关闭后，无敌、无限弹药等已勾选状态继续生效，再次打开可取消。

菜单完整保留：无限生命、无限弹药、恢复生命、全部/单件武器、全部/单件物品、清除敌人、角色死亡、任务目标、完成任务、章节跳转、区域载入、界面/武器/小地图隐藏、成就重置，以及原生环境、雾效、光照、声音和同步设置。中文数据共86项，调试字体包含278个所需字符。

复选框是持续开关；获得物品、杀敌、跳关、重置成就等原生按钮执行一次操作，不是可撤销的开关。原生菜单把有些按钮限定为游玩中执行：标题画面可以打开菜单，但没有玩家/关卡时仍保留原生可用性检查。无限弹药原生逻辑是“不扣除已有弹药”，零弹药时需先取得武器/弹药。

## 已验证的实现

- 输入翻译器 `FUN_1402dd940`：Win32 `VK_F1=0x70` 转为内部键码`0x1c`；原快捷键V转为`0x7e`。
- `0x1401a7d4b`：`83 fa 7e` → `83 fa 1c`，只改变调试菜单的内部键码比较。
- `0x14004fa49`：`75 04` → `eb 04`，绕过隐藏解锁条件，保留按下沿、长按去抖、开关状态和窗口关闭行为。
- 原生可见状态`0x1404a2f1d`仍控制鼠标捕获分支及游戏操作屏蔽。隔离CPU回放验证这些实际机器码片段；没有注入轮询线程或新增窗口钩子。
- 原生无敌/无限弹药仍使用游戏对象`+0x40a4`的`0x200/0x400`。回调、武器逻辑、任务操作和存档逻辑保持原实现。
- `.locmenu`为新增的只读、不可执行PE节。53个原生调试字符串/字形范围RIP引用重定向；35个物品/武器及7个区域组名称指针沿用已有DIR64重定位，兼容ASLR。
- 原调试字体`TUFFY_BOLD.TTF`仅由原生调试初始化载入。本轮使用已锁定Fusion字体的确定性字符子集替代，并同时扩充原ASCII字形范围；不是仅换字体后遗漏字符范围。
- 所有地址是已锁定版本的首选VA，不是可跨版本复用的固定运行时地址。

## 构建与验证

`tools/debug_menu.py`保留通用PE/字体实现，`locales/zh-CN/debug-menu.json`单独保留语言数据。`build_locale.py`先执行原有五处只读文字替换，再启用菜单；原版EXE和ROM身份仍先验证。`exe-patch.json`使用`native-menu-pe-v1`，与原先只允许`.rdata`的`fixed-slot-utf8-v1`分开，不放宽旧格式约束。

安装器的`native_executable`载荷验证EXE完整哈希、尺寸、每个旧字节、结果及追加数据。未知EXE不套用代码修改；选择仅资源时仍沿用资源级汉化。安装器保留完整原版备份及事务恢复；有可验证安装记录的旧汉化可以从原版备份直接升级，失败时同时恢复旧文件与旧记录。回滚恢复程序/资源，不追溯修改玩家之后保存的游戏进度。

```powershell
python -X utf8 tools/build_locale.py --game build/text-layout-fix/original --output build/menu-controls-fix/modified
$env:DEMENTIUM_MODIFIED_EXE=(Resolve-Path 'build/menu-controls-fix/modified/Dementium II.exe').Path
python -X utf8 -m unittest discover -s tests -q
python -X utf8 tools/verify_locale.py modified --game build/text-layout-fix/original --build build/menu-controls-fix/modified
python -X utf8 tools/rollback_locale.py build/menu-controls-fix/modified build/menu-controls-fix/rollback-test
```

这是离线机器码回放、PE/资源及栅格验证。真实渲染中的鼠标位置、不同分辨率、手柄焦点和每种武器/死亡场景仍需游戏内验收；本轮不擅自启动游戏，不读写玩家存档。

## 复用研究

原生环境编辑器证据`ev_3c05d4b4ef740ab16e633763e15a34868006896be713ef290a90840635a64a51`，`FUN_14004e660`；原有菜单/初始化/弹药/生命证据见`CHEAT_MENU_FEASIBILITY.md`和本地`build/cheat-analysis/`。原始机器码不进入Git；脚本在用户提供的已校验EXE上取出限定片段测试。
