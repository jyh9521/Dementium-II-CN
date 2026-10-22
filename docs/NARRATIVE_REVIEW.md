# 叙事与查看文本审校（2026-10-21）

## 覆盖范围

已对照当前版本 `build/source.en.json`，逐条审校 `locales/zh-CN/narrative.map.json` 的全部 201 条记录：82 条 SUB 记录（其中 6 条帧率数据）、119 条 EXAMINE 记录。没有空译文。此处“文本审校”不等于全流程实机验收。

- `narrative`：122 条；对白、广播、信件、明信片、文献、墓志铭与谜题诗等。
- `ui`：72 条；查看物品、操作提示及交互结果等。
- `preserved`：7 条；6 个帧率头和 1 条字母谜题。
- `text-reviewed`：188 条；`reviewed-context-pending`：6 条；`exempt`：7 条。

## 本次修改

- 追溯应用标点规则：删除 45 条没有内部自然语言标点的单句说明/提示的句末句号；标题与控制码不算内部标点。
- 另对 14 条译文调整语义、语气或术语，包括：补回“碾碎灵魂？”的问句语气；将气雾罐名称与术语表统一；纠正开场床位说明；改善怪事揭露对白、墓志铭和书信的中文表达。
- 共 59 条目标文本改变，全部记录均增加 `text_type`。
- 保留全部保护标记、字幕 `|` 数量与物理记录；保留 12 张明信片既有短引言、045 紧凑剧情文本和署名换行，不撤销已修复的布局方案。

## 验证

命令：在项目根目录以 `python -X utf8 -` 运行审校脚本，按 ID 对齐原文，比较 `TOKEN.findall`、字幕分隔数量，并调用 `localize.validate`。退出状态为 0。原样结果：

```text
NARRATIVE_REVIEW records=201 changed_targets=59 punctuation_removed=45 tokens=PASS subtitle_breaks=PASS validation=PASS
TYPES {'preserved': 7, 'narrative': 122, 'ui': 72}
STATUS {'exempt': 7, 'text-reviewed': 188, 'reviewed-context-pending': 6}
```

## 已译但仍需场景确认的细节

以下条目没有缺译，不以缺乏上下文为由补造谜底或设定。
- `EN/EXAMINE.049:0000`：Turn on, tune in, drop out同为文化引语和可能的收音机提示；保留直译三段结构，待场景审校。
- `EN/EXAMINE.509:0000`：Noble Cannibal暂译高贵食人者；是否为敌人正式名称待场景确认。
- `EN/EXAMINE.510:0000`：墓志铭口香糖与wrapper双关待画面确认；现按糖纸直译。
- `EN/EXAMINE.515:0000`：NEWS保留大写谜题线索，可能兼指方位首字母；不增译方向答案。
- `EN/EXAMINE.522:0000`：谜题诗按原文意象译出；三者指代与道路触发顺序待场景验证。
- `EN/EXAMINE.545:0000`：psychoplasmic暂译精神质，须结合剧情或画面复核。


保留谜题 `NEWS` 大写以及字母谜题的英文词，以免破坏解谜线索。其他已音译的人名与原文拼写建立一一对应，不把未听取语音的音译宣称为官方译名。

本次未启动游戏、未修改脚本或布局配置、未提交或推送 Git。
