# 全文与图片文字覆盖审计（2026-10-21）

## 结论与证据层级

**已验证**：原包有 3471 个成员，而旧提取器的 169 个英语成员、666 条记录不是全文边界。
本次发现并纳入 `EN/OPEN.*` 九个成员和 `EN/UNLOCK.000`，结构化英语成员变为 **179 个、676 条记录**。
另有 **41 张位图、187 个物理文字标签**，以及 5 个原生程序显示常量。记录数、图片标签数不是唯一语句数。

位图的确定性配方位于 `locales/zh-CN/image-text.json`，工具位于 `tools/image_text.py`。
配方只保存原图 SHA-256、区域、原词、译文、颜色及处理参数；Git 不包含原游戏 PNG。
原生常量由独立的 `tools/executable_text.py` 管线处理。

**离线检查**：全部 988 张 PNG 中，152 张是 DE/FR/IT/SP 的替代语言路径；其余 **836 张**已以 9 张接触表检查。
文字状候选另以原生像素的整数倍放大检查。逐成员处置台账为
`build/audit/asset-disposition-ledger.json`，覆盖全部 3471 个成员，而非只列已翻译文件。
`reviewed-no-legible-prose` 表示此轮资源目视检查未发现可可靠转录的语言句子，不等于对所有游戏场景的实机穷举证明。

## 此前遗漏的 10 个英语资源

| 资源 | 原文类别 |
|---|---|
| `EN/OPEN.000`、`.009` | It's locked. |
| `EN/OPEN.001` | keycard 插槽提示，含颜色控制码 |
| `EN/OPEN.002` | 电梯不工作 |
| `EN/OPEN.004`、`.008`、`.011` | 上锁、需要 key，含颜色控制码 |
| `EN/OPEN.005` | 骷髅锁、需要 key，含颜色控制码 |
| `EN/OPEN.010` | 奇怪的锁、有 three 个插槽，含颜色控制码 |
| `EN/UNLOCK.000` | keycard 开门，含 UTF-8 BOM、颜色码、尾空格 |

这些是资源中的实际显示句子，不是内部标识符；应进入统一提取/回填、字体覆盖、标点和控制码校验。

## 已接入的位图文本

| 资源组 | 张数 | 处理 |
|---|---:|---|
| `TEXTURES/GENERAL/EN/LEGEND_*` | 16 | 返回、确认、装备、按下；保留 Esc/SPC/手柄按钮图形 |
| `TEXTURES/OPTIONS/EN/CONTROLS_*` | 12 | 键盘、PC、NX、PS4 三种布局中的所有自然语言操作标签 |
| `TEXTURES/OPTIONS/EN/LEGEND_*_YAXIS.PNG` | 4 | Flip → 反转；保留 Y/按钮图形 |
| `TEXTURES/HUD/THATWASYOURLASTBREATH*.PNG` | 2 | 你已呼出最后一口气 |
| `TEX/EN/SIGN_01..03.PNG` | 3 | 西侧牢区、楼层、办公室、商店、东北翼 |
| `TEX/EN/SIGNS010/012/013.PNG` | 3 | 杂货店、禁止入内、废品回收、进出口有限公司、旅馆、佩尔夫等 |
| `TEX/SIGNS011.PNG` | 1 | 圣詹姆斯病区 |
| 合计 | **41** | **187 个物理标签**，包含多平台重复标签 |

大字 Pelf 已按术语表译为“佩尔夫”，不是以“专名”为由漏译地点。
商号中的人名/姓氏、Dementium 品牌、按键字母、数字保留原有身份或符号；`D.R.` 按术语规范译作“死囚区”，不再恢复英文。
`TEXTURES/OPTIONS/EN/PAGERIGHT_PCMOUSE.PNG` 只有 X 键帽与箭头，没有应翻译的词。

### 位图不变量

- 原图 SHA-256 不符即停止；尺寸与原图完全相同。
- 中文字形先查 TTF cmap；缺字报错，不输出方框占位符。
- Fusion Pixel 原生 12px 用于普通标签；24px 只用于原生 12px 的整数倍大字。
- 每个标签按实际字体墨迹宽度、行数校验边界；越界即失败，不悄悄裁字或缩小。
- 所有批准矩形之外，每个 RGBA 像素必须保持一致；原生按键图标列不重绘。
- 键盘标签背景取原图空白采样 `(0,0,0,67)`，保留半透明面板，不引入不透明黑条；旧标签整行区域先擦除；PS4 仅擦除文字列；PC/NX 旧字外缘纳入区域，避免残留英语笔画。
- 死亡画面不再用纯色矩形覆盖红色纹理：只在批准范围识别旧红字/白字墨迹，并按最近的非墨迹原背景像素确定性回填；其他背景保留。
- 操作图中的短标签无句末句号，遵循最新标点标准。

这些是资源级离线证明，不是控制器切换、所有分辨率和所有场景的实机验收。

## 明确保留的图片内容

台账对候选逐个记录理由，不把所有 PNG 当成“已汉化”。

- 游戏品牌/原始书籍身份：Dementium 标识；道具书 `BOOKS01` 的 INFERNO 书名；`BOOKS05` 的 Dementium 标题。
- 原作产品、商号/人名艺术标志：弹药包装、汽水广告、城镇商号姓氏；通用业务词已在有可读英文的路牌中翻译。
- 字母/符号谜题：`TEX/BLOCKS01.PNG`、`SPRITES/SPR-ALPHABET.PNG`、视力表字母、按钮字母、数字房号和符号，不改变谜题/按键身份。
- 原生纹理微字不可可靠转录：`BIBLE`、`BOOKS04`、`BOXES_01`、`BROCHURE`、`BULLETIN`、`MEMO01`、`NOTES01`、`PAGE01`、`PAPER002`、`PAPER_01`、`PIC_02`、`PLETTER`、`HEALTH01`、`P_HLTH01/02`、`PILLS`、`TOETAG01`、`WBOARD01` 等。
  已放大检查，原纹理只有极低分辨率笔画或装饰微印，不编造替换句子。可阅读的物品说明、便条、信件文本走对应 EN 资源，另行汉化。

保留清单不宣称图片中的所有装饰微字都已变成中文；它明确区分可读显示文本、身份艺术、谜题符号和不可可靠转录的原图微字。

## 其他资源与程序常量

- `MAPS.TBL` 实际内容为 p00/b00/v00/m00/l00：地图资源键，不是地图显示名。
- `SPISETTINGS.INI` 的 PS_L01..PS_L37 是成就协议 ID，没有本地成就名称或说明；修改 ID 会破坏 Steam 对应关系。
  Steam 平台成就名称/描述属于发行方平台元数据，不是本地资源记录；本补丁不宣称改写 Steam 平台覆盖层。
- 301 个 INI、字体/精灵 JSON、TEX/SETTINGS.TSV、GAME_SPILLER.TOML 已检查为内部参数、资源名或开发注释，不翻译技术键。
- 二进制 SCN/MSH/COL/ANM/DAT/BIN 做了连续可打印英语句段筛查，只得到一个场景压缩/命令碎片（`I0_02D.SCN:26514`, `kupP Lock'ed `），周围为 Disable/ExaminePickup/资源键碎片，非完整游戏台词。
- 21 个 IVF 视频已离线解码并每秒抽 1 帧，共 323 帧、6 张接触表。抽样画面未发现烧录式对白字幕；字幕仍由外部 SUB 资源提供。
  该方法不是逐帧 OCR 或无遗漏语音转写，原始配音和视频保持原作。
- EXE 中 ImGui/调试控制台、异常、日志、路径、符号、JSON 配置键不冒充游戏菜单文本。
- BugSplat/Steam API DLL 的错误报告/平台界面为外部组件，不混入剧情/设置表，也不以翻译标识符的方式处理。

### 五个原生显示常量：原文件偏移与槽长

槽长包含从原词起到下一个非 NUL 字节前的全部可用字节；实际读原 EXE 验证。

| 文件偏移 | 原文 | NUL 填充槽长 | UTF-8 译文 |
|---:|---|---:|---|
| `0x417870` | Accuracy | 12 | 命中率（9 字节） |
| `0x418178` | HI-RES CRT | 16 | 高清CRT（9 字节） |
| `0x4181BC` | RETRO | 12 | 复古（6 字节） |
| `0x4181C8` | RETRO CRT | 12 | 复古CRT（9 字节） |
| `0x4181D4` | HI-RES | 12 | 高清（6 字节） |

每条译文再加 NUL 均在原槽内。必须校验原 EXE 哈希、原词和原填充，不能盲写其他构建。
相邻其他语言的 CRT 显示词仍保留其语言路径，不误改全局技术标识符。

## 复现与检查

```powershell
python -X utf8 tools/image_text.py build 'C:\Program Files (x86)\Steam\steamapps\common\Dementium II\rom.zar' locales/zh-CN/image-text.json build/audit --font 'D:/Fonts/fusion-pixel-12px-proportional-zh_hans.ttf'
python -X utf8 -m unittest discover -s tests -p test_image_text.py -v
```

本轮实际结果：`BITMAP_TRANSLATION PASS: 41 images, 187 labels`，退出码 0；11 个纯合成图/合成 TTF 测试全部通过。
生成的 `asset-disposition-ledger.json` 覆盖 3471 个成员、988 个 PNG、836 个非替代语言 PNG。
`image-report.json` 记录 41 张图的前后哈希、标签数、改动像素数以及区域外不变断言。
实际字体从本机安装目录解析，未下载/重装；原游戏图仅位于忽略的 build 输出。
