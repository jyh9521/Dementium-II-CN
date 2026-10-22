# 全文交付验证（2026-10-21）

## 完成范围

- 3471个成员审计；179个英语文本资源676条记录，520条中文、156条有明确原因保留，未译/空白0。
- 41张图片187个物理标签及5个EXE显示常量完成中文配方；原游戏完整文件不进入Git。
- 既有和新增译文遵循句末标点规则；剧情可有句号，无内部标点的单句设置/物体说明/操作提示无句末句号。
- 27条已译中文留有具体场景核对备注，不是待译英文；品牌、姓名、谜题字母、不可辨微字的保留依据见覆盖报告。

## 实际执行结果

均在本机既有固定Python依赖与已锁定字体环境执行，不代表全新操作系统测试。本轮未启动游戏，Steam原安装8文件SHA-256保持不变。

| 检查 | 字面结果 | 退出码 |
|---|---|---:|
| `python -X utf8 -m unittest discover -s tests -q` | `Ran 106 tests` / `OK` | 0 |
| `python -X utf8 tools/lint_locale.py build/full-zh-CN/text.json` | `"violations": [], "count": 0` | 0 |
| `python -X utf8 tools/check_document_layout.py build/full-zh-CN/rom.zar --output build/full-zh-CN/postcard-layout` | `POSTCARD lines=4 overlap=FALSE within_pane=TRUE clearance=33px game_launch=NEVER result=PASS` | 0 |
| `python -X utf8 tools/check_probe.py --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium II" --package dist/Dementium-II-zh-CN-preview.zip --output build/full-package-test` | `PACKAGE_TEST install=PASS idempotence=PASS uninstall=PASS restore=BYTE_IDENTICAL game_launch=NEVER result=PASS` | 0 |
| Git Bash执行 `tools/ROLLBACK_FULL.sh` | `ROLLBACK_BUNDLE rom_sha256=0068275df89d923100c2d09484426424bd999531881bd488e92da291356a96d7 exe_sha256=b71ce6d2d803a7ded50c07c5ca918658fb0b1423db68bbc31129c257909123c2 modified_retained=YES result=PASS` | 0 |

三向原件/修改/恢复的完整命令、输入、字面输出和退出码：本地 `build/full-zh-CN/VERIFICATION.txt` 及 `verification.json`。安装四阶段逐项记录在 `build/full-package-test/results.json`。恢复后的资源菜单文本为`New Game`，EXE及ROM与原件同哈希；修改副本仍保持中文。无游戏行为启动验证。

## 确定性重建

由当前Git索引树通过`git archive`导出干净源码到`build/qa-source`，不拷贝旧构建中间件。在该目录执行`tools/build_locale.py --game`原安装路径、`tools/package_locale.py`及106项测试，均退出0。两个源树输出以下六项哈希完全相同，明细在`build/full-zh-CN/reproducibility.json`。

| 输出 | SHA-256 |
|---|---|
| rom.zar | 5a05c1f123d91ecb4d801847b8bbad4acce99b114f14873fcb656ca2bfce041d |
| Dementium II.exe | a6a933aff676e8ac9744f78e8d49fe530745369e6c5a8d125c7c40c8cf9742d6 |
| patch.json | b3ae8c8cad54bdad5784641cd6113fe28f6232b6a996913b2c6d1aa3370e16b1 |
| exe-patch.json | f5e4db274cea1fe00af3aff1844a05846839933c744d4a61c7bb90d4ba08bd48 |
| release-manifest.json | 48d4cb3ebb107c9c27f6bb61792c8d911760bca080a620af5f561b9de1377627 |
| Dementium-II-zh-CN-preview.zip | 9feed55d9a61192e8a013a6b9d7680247c3c27d6c5c487161fdf76916364e638 |

## 本地交付和保留

命令在仓库根目录执行。

- MODIFIED_FILE：`build/full-zh-CN/rom.zar`，同目录有完整EXE及依赖，供手动启动验证。
- DIFF_FILE：`build/full-zh-CN/patch.json`；原生显示常量另见`exe-patch.json`。
- VERIFICATION：`build/full-zh-CN/VERIFICATION.txt`。
- ROLLBACK：`tools/ROLLBACK_FULL.sh`，Git可执行位100755，恢复到独立目录，不覆盖修改版。
- 差分包：`dist/Dementium-II-zh-CN-preview.zip`，13成员、CRC及成员哈希验证通过；不含完整EXE、DLL、ZAR、PNG或字体。

初始成果已提交推送c5e644a；本轮全文源码和文档随后统一提交推送。历史重复构建可恢复归档，旧原件、证据和存档不删除。完整通关、最终画面和27条语境待实机验收，不用离线成功替代。
