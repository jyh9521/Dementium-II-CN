# 全文独立文本 QA

2026-10-21，输入为 `build/full-zh-CN/text.json`、`locales/zh-CN/image-text.json` 和 `locales/zh-CN/executable-text.json`。本轮未启动游戏，文本审校与游戏内排版验收分别记录。

## 资源文本

- 676 条记录：520 条已有完整中文，156 条有明确理由保留原文。
- 493 条为 `text-reviewed`，27 条为 `reviewed-context-pending`；后者全部已有中文，仅词义、音译、谜题暗示或交互语境待实机进一步核对，不是待译英文。
- 149 条表格保留项已逐条复核：119 条制作人员表项全部为 118 行人名或人名组合、1 行游戏产品标题 `DEMENTIUM II`。职位、部门、致谢等可译标题均已翻译，没有以专名理由跳过这些标题。
- 另外 30 条表格保留项为 11 条 ALPHA 字母谜题、18 条 `N/A` 和 1 条 `AZERTY` 键盘布局标识。
- 7 条额外保留项为 6 条字幕帧率头 `29.970` 和 1 条英文单词字母谜题。信件中的 `NEWS` 保留方向/解谜字母含义；`GAF 13`、`F99`、`DS`、罗马数字及制作公司专名也不是漏译占位。
- 676 条控制码/变量 TOKEN 序列一致；所有可译记录均含中文，无空白或纯英文占位。

## 用户标点规则

- 全部 676 条资源记录、187 条图片标签和 5 条 EXE 标签调用 `lint_locale.lint`，结果均为零违规。
- 单句且没有内部自然语言标点的设置、物体说明、操作提示不留末尾句号；含冒号/逗号的说明可留句号；叙事文本正常使用句号。
- `|` 显示段单独判断；变量内部逗号、控制码不算自然语言标点。问号、感叹号、语义省略号保留。

## 图片与 EXE 文本复核

- 41 个图片资源共 187 个标签已复核源译配对，包括键鼠/手柄说明、地图、死亡提示及场景招牌。所有标签已有中文；键位本体和专名处理不当作漏译。
- 地图/招牌 `Pelf → 佩尔夫` 与术语表相同；`Back/Map/Items/Flashlight/Attack/Move → 返回/地图/物品/手电筒/攻击/移动` 与资源表一致。
- `Equip Last → 上次武器`、`Reload → 装填` 为紧凑标签表达；图片换行仅用于既定标签空间，不增加句末句号。
- 5 条 EXE 标签为 `Accuracy → 命中率`、`HI-RES CRT → 高清CRT`、`RETRO → 复古`、`RETRO CRT → 复古CRT`、`HI-RES → 高清`，中文 UTF-8 加终止符均位于已审计槽容量内。`CRT` 是显示技术缩写。
- 此项验证译文与容量，不代替位图清除区/字形边界检查及实机逐场景确认。

## 术语一致性

逐项搜索原文术语与中文对应，23 组常用术语全部通过：William/Elizabeth/Amanda/Malatesta、Bright Dawn/Pelf/Redmoor、Health Pills/Health Pack/Antidote/Adrenaline、Keycard/Skeleton Key/Fumigator/Soul Vessel、Revolver/Sledgehammer/Shotgun/Assault Rifle/Dynamite/Nailgun/Flashlight/Ceremonial Knife。人名、地点、物品的所有命中记录均使用术语表规定中文。

`BONESAW → 骨锯` 与 `Buzz Saw → 电锯` 维持术语表说明的原文差异；Point 地名、章节双关、部分交互动词和设置枚举仍保留中文及场景待核对说明，没有伪装成已经实机确认。

机器检查明细及输入 SHA-256 保存在构建输出 `build/qa/final-text-qa.json`。
