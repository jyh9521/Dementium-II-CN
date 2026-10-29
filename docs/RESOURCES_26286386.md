# Build 26286386：近战准星与新版资源保留

## 原版差异

本次比较只覆盖 build 26260428 → 26286386。两份 ROM 均有3474个成员、989张PNG。
当前原版为579290112字节，SHA-256为
`2b45218a899881aa00fa4ea4ab1fa849d8ff8fe280d4aa510e9042cdf8698aa1`。
前版 SHA-256为
`10344977341d6f0481cbefb05d3bf45ec094459eb9f6419b31663b5551fd90fe`。

逐成员比较发现7项变化：

| 资源 | 变化 |
| --- | --- |
| `EN/OPTIONSNEW.TBL` | 官方追加索引48：`MELEE CROSSHAIRS` |
| `DE/OPTIONSNEW.TBL` | 追加相同设置的德文标签 |
| `FR/OPTIONSNEW.TBL` | 追加相同设置的法文标签 |
| `IT/OPTIONSNEW.TBL` | 追加相同设置的意大利文标签 |
| `SP/OPTIONSNEW.TBL` | 追加相同设置的西班牙文标签 |
| `TEXTURES/OPTIONS/BUTTONSTRIP.PNG` | 增加一行空白选项按钮；保留新版原图 |
| `~INDEX` | 官方更新成员长度；本地化仅派生修改成员的长度字段 |

地图、场景、声音、字体、配置及其余3467个成员与前版逐字节相同。
没有新增或移除资源名。原有677条英文记录的内容、行号及控制前缀保持不变；
实际新增英文记录只有1条。选项资源哈希更新造成的既有记录元数据变化不计作文本改写。

`BUTTONSTRIP.PNG` 的尺寸仍为428×480；RGBA差异包含4503个像素，边界为
`[254,391,366,432]`。两张原图已分别打开核对，该成员不在本地化图片白名单内。
新版图像SHA-256为
`1e76b30eebcd5ea5f69d7ed82ce55e98b979926345e5c7f873d56832b500072d`。

## 结构化译文

`locales/zh-CN/tables.map.json` 新增：

```json
"EN/OPTIONSNEW.TBL:0048": {
  "target": "近战准星",
  "status": "text-reviewed",
  "text_type": "ui"
}
```

`locales/zh-CN/smoke.json` 从当前原版重新提取，保留当前资源哈希及位置。
合并结果为678条记录、522条译文、156条保留项、179个文本资源，空译文为零。
“近战准星”的四个字均已存在于既有译文和固定身份的12px正文字体中，无需增加字体输入。

该行是官方选项表的第49行，不是补丁追加的“轻微”状态字符串。
行走晃动仍为索引47；小地图共享状态索引41仍为“半透明”。
现有本地化表扩展配置不追加 `OPTIONSNEW.TBL` 行。
当前原生loader的49行容量、独立后备缓冲槽和近战开关位由原生专项单独验证。

## 已执行证据

`build/update-26286386/resources/` 保留源比较报告、文本合并三态记录及测试日志。

- 基线：当前原版配合旧译文集合，`merge_locale.py` 报
  `ValueError: Missing/extra translation IDs`，退出1。
- 修改：新增官方行的译文后，原样输出为
  `LOCALE records=678 translated=522 preserved=156 empty=0 tokens=PASS`，退出0。
- 隔离回滚：仅在另一个译文目录恢复旧表，旧表SHA-256重新一致；同一新ROM再次触发
  缺少翻译ID的原始门禁，退出1。当前译文文件仍保留新增行。
- 数据及合成回归：12项全部执行、0跳过；覆盖索引、行结束符、字体字符、官方按钮图保留，
  并以故意回退旧按钮图的负向样例确认资源审计会失败。
- 当前完整构建专项：7项全部执行、0跳过，其中2项直接读取本次原版与汉化ROM，确认49行
  选项以及新版按钮图、四种非英文选项表的逐字节保留；另5项为上述数据及合成测试。
- 完整成员审计使用前版已核验的222成员白名单，而不是由本次输出反推允许集合。
  原样输出为 `ARCHIVE_UPDATE source_changes=7 preserved=3252 localized=222 issues=0 result=PASS`，
  退出0。前版白名单来源报告SHA-256固定为
  `a55a4d275f1bbfb9d5a4e31bcc7d0913a94fab1f346ad19cd22344201313c3f4`。

复核命令：

```powershell
$env:PYTHONPATH = 'tests;tools'
python -B -X utf8 -m unittest test_resources_26286386.MeleeCrosshairResourceTests test_archive_update test_resource_revision -v

$env:DEMENTIUM_PREVIEW_ROM = (Resolve-Path 'build/full-zh-CN/rom.zar').Path
$env:DEMENTIUM_CURRENT_ORIGINAL_ROM = (Resolve-Path 'build/inputs/26286386/rom.zar').Path
python -B -X utf8 -m unittest test_resources_26286386 -v

python -B -X utf8 tools/audit_archive_update.py --previous build/inputs/26260428/rom.zar --current build/inputs/26286386/rom.zar --modified build/full-zh-CN/rom.zar --approved-report build/update-26286386/resources/build26260428-approved-resources.json --output build/update-26286386/resources/archive-update-audit.json
```

完整构建已检查实际输出中49行选项、近战标签、新版按钮图及四种非英文选项表，
并通过完整成员白名单审计确认其余官方更新保持不变。离线资源证据不代替游戏内布局验收。
本专项未执行游戏。
