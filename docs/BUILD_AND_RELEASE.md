# 全文汉化构建与交付

支持Steam2026版AppID5342930、build26099941。输入哈希见 assets/supported-build.json。
依赖版本固定于 requirements.txt；字体由系统/用户Fonts目录与字体注册表自动发现，按SHA锁定，不下载/安装字体。

```powershell
python -m pip install -r ./requirements.txt
python -X utf8 ./tools/font_pipeline.py
python -X utf8 ./tools/build_locale.py --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium II"
python -X utf8 -m unittest discover -s ./tests -q
python -X utf8 ./tools/verify_locale.py baseline --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium II" --build ./build/full-zh-CN
python -X utf8 ./tools/verify_locale.py modified --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium II" --build ./build/full-zh-CN
python -X utf8 ./tools/rollback_locale.py ./build/full-zh-CN ./build/full-zh-CN/rollback-test
python -X utf8 ./tools/package_locale.py
python -X utf8 ./tools/check_probe.py --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium II" --package ./dist/Dementium-II-zh-CN-preview.zip --output ./build/full-package-test
```

生成目录 build/full-zh-CN 是完整可运行副本，包含本地重建的EXE/rom及原始依赖；工具从不执行其中EXE。
生成 dist/Dementium-II-zh-CN-preview.zip 仅含差分、安装器、版本身份、说明和许可证。
安装/卸载详见 PLAYER_README.md。未知版本、缺字体/字形、标点违规、越界、控制码变化均拒绝构建。

## 数据与复现

- 三个 *.map.json 保存所有已识别文本，image-text.json 保存图形标签，executable-text.json 保存固定槽标签。
- merge_locale.py 从原包全量提取并核对每个ID，OPEN/UNLOCK与EXAMINE同为UTF-8独立文本资源；TBL/SUB维持物理行。
- 源树指纹按文本输入的LF规范化内容计算；ZIP成员顺序/时间戳固定，避免Windows检出换行影响输出。
- 字体 atlas/元数据、文本二次提取、图形允许区域外不变、原EXE固定槽守卫、安装幂等和双组件恢复均有测试。
- 以干净源码副本重建并比较 rom.zar、patch.json、EXE、exe-patch.json及ZIP，不复制旧构建中间件。
- 历史最小实验仍保留，旧ZIP/旧脚本不是默认全文构建入口。
- 不上传AGENTS.md、内部LOCALIZATION_STANDARD.md或游戏完整文件；GitHub Release须单独授权。
