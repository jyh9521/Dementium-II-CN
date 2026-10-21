# 可复现构建与发行门禁

Python 3.11+。核心封包/差分使用标准库；扫描需要 pefile；字体生成需要 Pillow、fonttools。

```powershell
python -m pip install -r ./requirements.txt
python -X utf8 ./tools/fetch_font.py
python -X utf8 ./tools/localize.py scan "C:/Program Files (x86)/Steam/steamapps/common/Dementium II" ./build/inventory
python -X utf8 ./tools/localize.py extract "C:/Program Files (x86)/Steam/steamapps/common/Dementium II/rom.zar" ./build/source.en.json
python -X utf8 ./tools/localize.py build "C:/Program Files (x86)/Steam/steamapps/common/Dementium II/rom.zar" ./locales/zh-CN/smoke.json ./build/smoke --font ./assets/fonts/NotoSansCJKsc-Regular.otf --identity ./assets/supported-build.json
python -X utf8 -m unittest discover -s ./tests -v
python -X utf8 ./tools/record_verification.py --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium II"
python -X utf8 ./tools/package_probe.py
```

这些命令没有游戏启动功能。build 输出不能选择原版目录。
UTF-8 必须显式指定；不能依赖本机 CP932/CP936 默认编码。
源数据、译文、字体、工具版本和支持版本固定后，产物应保持同一 SHA-256；测试记录见 build/。
压缩包时间戳和成员顺序固定，使用当前固定工具版本重复构建验证哈希。

## 数据与分发

smoke.json 是 666 条英文记录的完整映射，仅一个目标字段非空。
重复原文不自动合并。保留源文本、字节位置、资源哈希和状态。
全量翻译须等中文显示验收通过，不将 `capacity_bytes=null` 解读为运行时无限容量。
ZAR 变长成功只证明外层重定位，未证明内部菜单缓冲区可容纳任意长度。

dist 技术实验包只能包含脚本、版本身份、差分、许可证与说明。
打包使用固定白名单，不递归收集 build，不携带完整资源包、可执行文件、存档、日志或内部规范。
完整字体从固定官方提交下载；发行包只携带补字差分及字体许可证。
运行时验收和全流程 QA 完成前不得晋升为正式发行版。
GitHub Release 始终等待用户明确授权。
