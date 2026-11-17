# Personal Chinese Translation Style

This is the owner's Chinese-language preference. Apply it to Simplified or Traditional Chinese catalogs selected by the project; keep it out of locale-neutral engine logic.
Other locales define their own punctuation policy.

## Required sentence-ending rule

故事文本、人物对话以外的文本里，只要一句话中间没有逗号和顿号，这个句子的最后就不要加句号。

Operational interpretation:

1. Classify by content, not resource name. `story` and `dialogue` are exempt; `other` follows this rule. Resolve `unknown` before approval.
2. Judge each sentence separately, not an entire record, paragraph or file.
3. A comma means `，` or `,`; an enumeration comma means `、`.
4. If a sentence contains none of these marks, omit its final full stop `。` (and an ASCII `.` when it really functions as a sentence-ending full stop).
5. A comma/enumeration comma permits the normal style decision; it does not require adding a final full stop.
6. Preserve question marks, exclamation marks and ellipses. Keep decimal points, versions, paths, extensions and other non-sentence dots intact.
7. Ignore verified invisible control/formatting tokens when finding the visible sentence ending; preserve the tokens themselves.
8. A closing quote/bracket after a full stop does not hide the full stop from this rule. A colon or semicolon does not count as a comma.

The rule follows logical sentences, not layout lines. A newline or ellipsis alone does not prove that a new sentence begins; preserve both without discarding a comma earlier in the same sentence. Independent messages/ellipsis-ended sentences must be separated into verified spans when context establishes that boundary.
The plain-text checker treats `。！？!?` and clear ASCII sentence-ending periods at the current quote/bracket depth as boundaries. Punctuation in a nested quote does not reset its enclosing sentence. Commas in a completed preceding sentence do not exempt the next one.
Mixed narrative/UI content requires role-specific spans. Ambiguous quotation or dot semantics require contextual review rather than global deletion.

## Examples

| Role | Before | Result |
|---|---|---|
| other | 保存成功。 | 保存成功 |
| other | 请选择一个存档。 | 请选择一个存档 |
| other | 提高攻击力；持续十秒。 | 提高攻击力；持续十秒 |
| other | 保存完成，请继续。 | 保存完成，请继续。 |
| other | 获得药草、铁矿石。 | 获得药草、铁矿石。 |
| other | 保存完成，请继续。按键返回。 | 保存完成，请继续。按键返回 |
| other | 「保存成功。」 | 「保存成功」 |
| other | 是否覆盖？ | 是否覆盖？ |
| other | 正在加载…… | 正在加载…… |
| other | 版本 1.2.3 | 版本 1.2.3 |
| other | 保存完成，〈换行〉请继续。 | 保留句号；换行属于同一句的排版 |
| other | 保存完成，请稍候……然后继续。 | 保留句号；省略号属于同一句 |
| other | 请确认，选择“成功！”按钮。 | 保留末尾句号；内层感叹号不切断外层句子 |
| story | 夜色渐深。 | 夜色渐深。 |
| dialogue | 我马上回来。 | 我马上回来。 |

System/tutorial/item-description text normally uses `other`; a lore passage or spoken tutorial line may instead be story/dialogue according to actual content.
Do not insert unnecessary commas merely to retain a final full stop.

## 本项目适配与验证

本次为文档迁移，没有更改现有译文、locale JSON、检查器或构建结果。旧检查器的通过结果不能证明符合新版逐逻辑句规则；具体差异见[迁移记录](../../docs/MIGRATION.md)。后续修改相关文本时，先按内容分类，再补充游戏控制码和可见文本 span 的适配及正反例；在适配完成前逐条人工复核，不使用旧自动修复批量回写。

至少覆盖：中文/半角逗号、顿号、冒号/分号不豁免、同记录多句、换行/省略号不自动断句、嵌套引号、混合故事/系统片段、受保护 token、小数/版本/文件名及歧义 ASCII 末尾点。歧义标记为待复核，保留问号、感叹号、省略号和机器语法。每个有意例外记录字符串 ID、理由和维护者批准。

README 和其他项目说明的解释性正文不受游戏文本句号规则约束；引述的游戏译文与翻译示例仍受约束，错误/修改前例子须标清。

## 项目用语与排版

保留本项目 [TRANSLATING](../../TRANSLATING.md) 指定的术语源、人物口吻、字体、换行、数值和单位约定。新增语言在自己的 locale 层维护规则，不把中文规则写入通用引擎代码。
