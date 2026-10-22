# 历史专项构建与回归命令

本页保存开发阶段的逐轮回归命令。历史大副本会按保留策略清理，当前构建入口见[BUILDING.md](../../BUILDING.md)，发布状态见[STATUS.md](../STATUS.md)。下列路径和测试结论保留其当时含义。

## 全量排版门禁
完整构建现在自动运行 audit_text_layout.py 和 audit_image_alignment.py，生成逐记录、逐图片/标签台账；任何越预算、错误短尾、保护码变化、非预期图片改动或居中漂移均停止构建。数值预算属于离线门禁，9条动态变量仍需实机展开复验。

## 原生菜单构建

完整构建同时生成`native-menu-pe-v1`程序差分与调试字体字符子集，新增依赖capstone==5.0.7；不复用未知程序版本的代码偏移。语言数据位于`locales/zh-CN/debug-menu.json`，字体仍使用已记录哈希/OFL许可的Fusion来源。详见`docs/NATIVE_CHEAT_MENU.md`。

## 固定版本策略

补丁及安装器版本保持1.0.0，仅在明确版本决策后修改；修复或新增功能不自动递增版本。assets/release-policy.json是构建约束，build_installer.py逐项核对AssemblyVersion/FileVersion/InformationalVersion。

## D.R./F1回归

`DEMENTIUM_MODIFIED_EXE`指向实际输出后运行`python -X utf8 -m unittest discover -s tests -q`，包含原生初始化禁用直接输入模式后F1的完整限定链。`verify_debug_menu.py`也调用该回归。SIGN_02的死囚区必须通过横纵墨迹居中及译文保留门禁。

## 原生阅读器和菜单输入构建

新增开发依赖keystone-engine==0.9.2与unicorn==2.1.4，前者生成相对x64代码，后者回放实际PE及模拟Win32边界。build_locale.py经build_menu集成menu_input.py和document_reader.py；.locui为RX代码，状态使用受守卫的新.data零填充尾区，.locmenu仍为只读。

`python -X utf8 tools/verify_reader_input.py --before build/dr-f1-fix/modified --build build/reader-input-fix/modified --output build/reader-input-fix/verification`复现旧输入失败、验证新输入、检查死囚区/F1/明信片/谜题/其他UI与字体保留，并运行真实ROLLBACK.sh恢复独立副本。默认全量unittest及verify_debug_menu.py均包含新回归。

## 菜单输入、暂停图例与备份回归

`tests/test_menu_pointer_dispatch.py` 从原生平台消息入口回放到队列、输入对象及 ImGui 点击/悬停/滚轮消费者；旧版本必须失败，不能只测字段写入。
`tests/test_pause_layout.py` 验证冒号与状态的实际字形边界、返回字间透明列和原生坐标守卫。
`installer/ResourceTests.cs` 验证原文件名备份、旧哈希命名备份迁移、失败重试、部分恢复保留、完整恢复清理整个目录。

```powershell
python -X utf8 tools/verify_ui_regressions.py --before build/reader-input-fix/modified --build build/full-zh-CN --installer-before build/backup-layout-fix/baseline/Dementium-II-zh-CN-Setup.exe --output build/backup-layout-fix/verification
```

`ROLLBACK.sh` 只在另一个测试目录还原上一个汉化版本；安装器“恢复原版”另外执行整文件恢复并校验后删除 `cn-backup`。上述均不自动启动游戏。

### 控件激活、现场文本与再次新游戏回归

```powershell
python -X utf8 tools/verify_ui_regressions.py --before build/menu-postcard-restart-fix/baseline --build build/full-zh-CN --installer-before build/menu-postcard-restart-fix/baseline/Setup.exe --output build/menu-postcard-restart-fix/verification --test test_menu_widget_activation.py --test test_postcard_preview.py --test test_restart_lifecycle.py --unchanged-rom --allow-reader-code-change
```

本轮要求ROM整体字节不变；实际Checkbox/动作队列、现场与收藏字形提交、原关卡配置及调试覆盖选择分别回放。生命周期夹具停止于原生LoadSection入口，证明传入关卡名正确，不等同于完整游戏进程验收。代码回滚到另一目录后，同样测试必须重新复现基线缺陷。

### 注册窗口过程与阅读器键盘释放

```powershell
python -X utf8 tools/verify_ui_regressions.py --before build/mouse-document-input-fix/baseline --build build/full-zh-CN --installer-before build/mouse-document-input-fix/baseline/Setup.exe --output build/mouse-document-input-fix/verification --test test_reader_key_lifecycle.py --test test_menu_message_path.py --test test_menu_full_frame.py --unchanged-rom --allow-reader-code-change
```

`test_menu_full_frame.py`从实际注册WndProc到完整ImGui帧测试长按与两次点击；`test_reader_key_lifecycle.py`检查打开/关闭阅读器后的E松开及动作边沿。纯common-handler内层测试通过不能取代注册入口可达性。`tools/observe_runtime_input.py`是可选的只读、仅前台游戏字段观察辅助，等待手动启动游戏；本次等待期间没有运行中游戏，因此没有采到实时输入，不将该等待记作实机通过。

### 输入状态转换专项审计

默认 unittest 与 verify_debug_menu 包含 `test_reader_transition_audit.py`、`test_menu_transition_audit.py`、`test_input_boundary_audit.py`、`test_input_transition_matrix.py`。专项 red/green/rollback：

```powershell
python -X utf8 tools/verify_ui_regressions.py --before build/input-state-audit/baseline --build build/full-zh-CN --installer-before build/input-state-audit/baseline/Setup.exe --output build/input-state-audit/verification --test test_reader_transition_audit.py --test test_menu_transition_audit.py --test test_input_boundary_audit.py --unchanged-rom --allow-reader-code-change
```

256VK普通关闭矩阵本来就通过，不列为基线失败的修复测试。完整范围、原版对照与实机边界见docs/INPUT_STATE_AUDIT.md；版本保持1.0.0。

### 库存短信溢出回归

默认unittest及verify_debug_menu包括tests/test_short_letter_scroll.py：实际EXAMINE.092/093的测量/绘制与wheel/Down重绘须保持不活动、scroll_line=0且字形坐标不变；078/090/091仍滚动，段落空行保留且终点不含尾部空白。使用build/short-letter-scroll-fix/baseline和build/full-zh-CN运行verify_ui_regressions.py --test test_short_letter_scroll.py --unchanged-rom --allow-reader-code-change进行红/绿/隔离回滚。

`test_collection_scroll_inventory.py`已同时加入默认unittest发现和verify_debug_menu门禁，另按原生41..99范围对当前所有实际库存EXAMINE资源逐项回放，不只抽查5封信。缺失正文的编号必须列明且不计为通过。可独立运行tools/audit_collection_scroll.py生成逐项报告，范围与实机边界见docs/COLLECTION_SCROLL_AUDIT.md。

### 右摇杆文档滚动

默认unittest与verify_debug_menu包括`tests/test_reader_gamepad.py`，实际PE原生axis3 setter接入现有阅读器，每格3行；本地红/绿/隔离回滚使用`verify_ui_regressions.py --before build/right-stick-scroll/baseline --build build/full-zh-CN --installer-before build/right-stick-scroll/baseline/Setup.exe --output build/right-stick-scroll/verification --test test_reader_gamepad.py --unchanged-rom --allow-reader-code-change`。仅重建EXE及安装器，ROM保持整文件字节一致。技术说明见docs/DOCUMENT_READER_SCROLL.md，版本保持1.0.0。

### 正文补字门禁（2026-10-22）

完整构建自动执行tools/audit_body_fallback.py，检查所有正文缺字的实际字形PNG、12px规格及共同基线；保留16px章节标题。输出body-fallback-audit.json/png；合成回归位于test_font_pipeline.py。红/绿/隔离回滚及安装器证据见build/fallback-font-fix/VERIFICATION.txt，版本保持1.0.0。

安装器验证脚本显式绑定DEMENTIUM_MODIFIED_EXE、DEMENTIUM_UI_TEST_EXE及DEMENTIUM_PREVIEW_ROM到本次full-zh-CN输出，避免历史reader-input-fix夹具污染全套回归；不修改原生输入实现。
