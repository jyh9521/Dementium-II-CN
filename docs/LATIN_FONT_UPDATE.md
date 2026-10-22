# 英文字体调整（2026-10-21）

英文也统一使用两套像素字体之一。本次普通英文、数字、ASCII 标点及 Latin-1 重音字母统一采用已安装的 Fusion Pixel 12px（2026.10.16，Regular）。章节中文仍采用 ChillBitmap 16px。

## 实现

- `font-profile.json` 的 `replace_existing_ranges` 为 U+0020–007E、U+00A0–024F；通用工具按配置执行，不写死语言。
- 实际重定向原图集中的 168 个字形。原始像素保留在图集中，但这 168 个索引不再使用旧字形。另 28 个特殊/兼容字形不变，DEBUG08 不变。
- Å 的上方重音、Ç/ç 的下伸部采用独立高度/偏移，避免按固定15px框裁掉；不对单字墨迹框逐字居中。
- 新增合成回归测试验证替换范围、宽度变化和范围外字符保留。全套58项通过。
- 重建后所有666条文本二次提取、双索引长度、PNG解码、完整差分应用通过。隔离回滚恢复原版字节及 New Game，保留修改后副本。

## 本地产物

- 修改资源：`./build/zh-CN/rom.zar`
- 差分：`./build/zh-CN/patch.json`
- 精确命令、输入、标准输出、退出码：`./build/zh-CN/VERIFICATION.txt`
- 可执行回滚脚本：`./tools/ROLLBACK_LOCALE.sh`
- 中英文实际图集离线预览：`./build/zh-CN/mixed-preview.png`
- 调整前副本：`./build/latin-original-baseline/`

本次没有启动或操作游戏。之前的主菜单截图只验证调整前字体，不作为新版英文的实机验收。游戏标题美术图像未改。本次没有重新生成旧技术实验ZIP，不能用旧ZIP验收新版字体。
