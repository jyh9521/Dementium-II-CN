# 输入状态转换专项审计（2026-10-22）

## 范围与判据

本轮针对阅读器新增输入路径及 F1 菜单的状态生命周期，不把“所有测试通过”解释成整个游戏不存在缺陷。使用实际生成 PE 的指令回放；不启动游戏、不读写玩家存档。Win32 API、字体元数据等外部边界使用可记录的替身，真实窗口和设备验收仍单列。

必须检查的状态包括：原始直接输入模式开/关、按下/松开跨界面、长文退化为非滚动页面、现场/收藏两种打开和关闭入口、资源/所有者切换、菜单打开/关闭、失焦/恢复。除字段归零，还检查原生动作采集结果，避免 listener 收到松键但游戏逻辑字段仍然按住的误判。

## 已复现：阅读器的非 close 退出路径

基线 `f43a5b9a43b1c42875eddf9b040b8f0a85ef0c6871debc05cd7888445be981b2`。

`test_reader_transition_audit.py` 在实际渲染入口先启用长文滚动，按住 Down，再切到短文、卡片、谜题或短信件。原 `inactive` 分支只清 reader_active，未清借用的 input+22d/e；随后 +458=0 的普通模式会跳过松键字段写入。现场与收藏渲染共八种情况均复现，另外两种 open-reset 入口也复现 Up 残留。原生动作采集可见方向动作残留，不仅是辅助状态未清。

修正原则：在此前 reader_active 非零的退出路径，先清除阅读器借用的上下键，再清共享状态。打开入口与关闭入口遵循同一条规则。原本 inactive 的卡片/普通界面不清游戏箭头，+458、E/WASD/F1、鼠标状态不改。原生绘制标志仍从受守卫的原指令解码，避免再次写入相邻关卡名。

## 已复现：后台关闭菜单重新抢占光标

实际注册 WndProc 的 `WM_ACTIVATEAPP(0)` 会产生 window+79=1、+7a=0。旧代码失焦时正确释放光标，但随后关闭菜单的恢复分支仅检查 +79，错误恢复 +19 捕获请求，重新 ClipCursor 到游戏客户区并隐藏系统光标；原生捕获函数没有补挡该情况。

现在恢复捕获必须同时满足 +79 和 +7a。焦点缺失时不捕获、不隐藏光标；原来未捕获的窗口也不强制捕获。`test_menu_transition_audit.py` 使用注册窗口过程和两种装载地址覆盖这一状态，而不是只手改可见标志。

## 已复现：失焦丢失松键与首次输入被吞

原版和本轮基线的注册 WndProc 均会留下 A30d20 的 Win32 虚拟键去重锁存：按住键失焦、在其他应用松开、恢复焦点后，首次全新按下被当成重复。菜单的逻辑字段清理不能替代这一层；F1 还有独立的原生消费者 previous 字节。

新增受原始七字节指令守卫的 2f3a3e 接缝，在原生 WM_KILLFOCUS 或 WM_ACTIVATEAPP(false) 更新焦点标志之后、消息转发之前，对实际已按键按原生 WM_KEYUP 顺序清 VK、翻译键码、调用原 up callback。现场阅读器、菜单及普通游戏、两种 +458 模式都经原 listener 接收松键，不猜写其内部状态。F1 的 previous 字节从原 4fa2e 读取及 4fa60 写入指令交叉解码，仅释放已按 F1 时清理。

恢复焦点时物理仍按住的键不应成为一次全新按下，因此同时在原 2de833 的 WM_KEYDOWN/WM_SYSKEYDOWN 入口拒绝 lParam bit30=1 的自动重复消息。真实松开后 bit30=0 的新按下保持原流程。未增加轮询、额外导入或可写可执行内存。

全部新增 Win32 接缝保留 flags/寄存器和调用栈约定；按键释放不依赖下一渲染帧，覆盖失焦、恢复、新按下之间没有绘制帧的情况。原版对照记录为 `build/input-state-audit/boundary/original-focus-comparison.json`，这属于原生已有的边界缺陷，而非将其误报为汉化新增回归。

ABI 检查须区别接缝和函数入口：Replay 默认栈适合 RSP%16=0 的跳转接缝，不能直接据此宣称函数调用 ABI 正确。边界测试对注册 WndProc 和队列函数入口使用 RSP%16=8，验证实际上层调用栈、原 up callback 入口对齐，以及 listener 合法破坏 volatile GPR/XMM/flags 后的恢复；普通字段回放不替代此证据。

关闭一个本来没有滚动的页面，也不应无条件清普通游戏方向键；本轮将关闭清理限定为此前确实 active 的阅读器，修复这一相反方向的误清理。

## 扩展矩阵

- `test_input_transition_matrix.py`：全部 256 个 Win32 虚拟键，原始模式 0/1，现场/收藏关闭入口，共 1024 对真实翻译与按下/松开事件。基线在这组普通 close 路径已通过；这不是新发现的缺陷，也不计入修复数量。
- `test_reader_transition_audit.py`：上述退出遗漏，以及资源/owner 变化时滚动、滚轮、重复计时复位；不活动界面不清原生箭头。
- `test_menu_transition_audit.py`：菜单跨模式切换与焦点转换。
- `test_input_boundary_audit.py`：输入边界及原生入口审计。

新检查加入默认 unittest discovery 和 `verify_debug_menu.py`；不以测试总数代替对应场景的证据。

## 尚未建立可达性的边界

退出析构的额外只读扫描确认：注册 input/up callback 的全局没有显式 unregister 清零，因此“指针非空”本身不是存活证明。但唯一直接 DestroyWindow 调用属于启动时的临时 model window，未建立“主 input 已销毁后又进入主窗口焦点处理”的实际执行顺序或复现。间接析构与 OS 退出消息顺序仍未知；没有据此增加猜测性生产补丁，也不将其计为已修复缺陷。原始引用与反编译证据存于 boundary/shutdown-rip-refs.json、shutdown-rea-evidence.json。

首轮全套在边界测试尚未冻结时使用了旧函数入口栈夹具，出现 24 个对齐断言失败；日志保留为 `python-tests-before-abi-fixture.txt`。生产 PE 未为此修改，修正函数入口夹具后重新运行冻结版本全套，最终结果另存 `python-tests.txt`，不把初轮失败隐藏为通过。

## 复现与证据

```powershell
$env:DEMENTIUM_UI_TEST_EXE = './build/input-state-audit/baseline/Dementium II.exe'
python -X utf8 tests/test_reader_transition_audit.py
$env:DEMENTIUM_UI_TEST_EXE = './build/full-zh-CN/Dementium II.exe'
python -X utf8 tests/test_reader_transition_audit.py
```

完整命令、输入文件、原始输出、退出码、独立副本回滚和资源保护结果保存在 `build/input-state-audit/verification/VERIFICATION.txt`。新增实机验收顺序：长文按住方向键切短文/卡片后松开、关闭后再次 E 交互、F1 开关与 Alt-Tab 后各操作一次。离线通过不等于这些真实窗口操作已经验收。
