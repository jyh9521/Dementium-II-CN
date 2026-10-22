# 全库存正文滚动覆盖复核（2026-10-22）

## 更正此前的覆盖表述

此前短信修复的专项用例覆盖5封图文信件（2封短信、3封长信），另有既有明信片绘制回归；这不等于逐项覆盖所有库存正文。“其他界面未改”是代码/资源保留结论，也不是所有界面已经完成运行验收。

本次按原生收藏入列范围生成全集，不用截图中的编号生成测试清单，也不用运行时阅读器的5个信件编号作为期望结果白名单。

## 全集如何确定

- 从实际PE的156296处LEA和1562b3处CMP/JA解码原生编号范围41..99，共59个编号槽。
- 当前归档共有119个EXAMINE正文资源；其中33个编号处于库存原生范围。
- 另外26个槽没有对应EXAMINE正文：44、54..72、94..99。它们逐个查表并明确列出，但不计为已执行或通过的文本。
- 范围外86个EXAMINE资源不属于本轮库存正文审计，不把库存结论泛化为现场阅读器或所有界面验收。

## 每项检查

所有33项均读取实际ROM正文及字体指标，通过实际PE的库存测量、UTF-8绘制与输入处理器运行：首次绘制、滚轮到底、滚轮返回、Down按下和松开。文字可完整显示的项必须不启用滚动、位移保持0、字形坐标不变且位于文字区域。长信另外逐个访问可达滚动窗口，检查终点不越过最后正文行。

期望判定按每项的可见内容范围与字体行高独立计算，保留段内空行；不是让当前reader_active状态自己证明自己正确。回放要求到达预期原生出口，指令上限耗尽不作为成功。

## 结果

- 应滚动且实际滚动：3项，078、090、091。
- 完整显示且不滚动：30项，包含12张明信片、16项其他物品说明及092/093两封短信。
- 当前包未发现其他库存正文误滚动；33项逐项清单及坐标、滚动终点在build/collection-scroll-audit/current/collection-scroll-audit.json和COLLECTION_SCROLL_AUDIT.md。
- 将同一全量审计指向历史失败版7f77ae72…，不指定故障编号，也能自动检出092和093两项。这是负对照，不是本轮又修了两次。
- 游戏EXE、ROM、安装包均不因本次补查而修改。新增通用审计工具与默认发现的回归test_collection_scroll_inventory.py，后续有新的库存正文资源也会自动纳入。

## 复现

在仓库根目录执行：

```powershell
python -X utf8 tools/audit_collection_scroll.py --exe "build/full-zh-CN/Dementium II.exe" --archive build/full-zh-CN/rom.zar --output build/collection-scroll-audit/current
python -X utf8 tools/audit_collection_scroll.py --exe "build/short-letter-scroll-fix/baseline/Dementium II.exe" --archive build/full-zh-CN/rom.zar --output build/collection-scroll-audit/historical-negative-control
```

第一条应退出0；历史失败版负对照应退出1。完整命令、输入哈希及实际输出在build/collection-scroll-audit/VERIFICATION.txt。

这是全库存资源模板的离线原生指令覆盖，不是运行游戏逐个领取后的GPU/窗口验收；存档相关动态占位符使用资源模板，未模拟所有具体存档替换值。没有自动启动游戏或读写存档。
