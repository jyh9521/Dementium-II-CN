# 《病房2》简体中文测试补丁

仅适用于 Steam 2026版 AppID5342930、build26099941。不是2013年HD版补丁。

文本资源已完成中文翻译和文本审校；图形标签及固定PC菜单字符串一并处理。
原始专名、按键标识、字母谜题、技术标识及原画不可辨认微缩字样按清单保留。
全流程游戏内验收仍待进行；本包不代表通关稳定性已经验证。

## 安装

退出游戏。安装 Python3.11或更新版本，将本压缩包解压到独立目录。
本包只带差分和工具，不带游戏EXE、DLL或完整资源；安装器不启动游戏。

在解压目录执行（按实际安装位置修改路径）：

```powershell
python -X utf8 ./install_patch.py install --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium II" --allow-experimental
```

安装器核对原文件哈希，备份两个原件到游戏目录的 `.dementium-locale/original.zar`、`original.exe`，
再应用资源和固定字符串补丁。未知版本或备份异常将停止写入。重复执行是幂等操作。
遇到文件占用时先关闭游戏，再重试，不删除备份或覆盖未知文件。

## 卸载与恢复

```powershell
python -X utf8 ./install_patch.py uninstall --game "C:/Program Files (x86)/Steam/steamapps/common/Dementium II" --allow-experimental
```

卸载恢复原包和原EXE字节，重复卸载不改其他数据。安装与卸载均不接触存档、Steam账号或云存档设置。
中断后可重试安装/卸载，工具会分别识别两个组件的原版/已安装状态；保留全部恢复备份。

## 字体与标点

普通中文与英文：Fusion Pixel12px；章节中文：ChillBitmap16px。字体许可证附包。
剧情按正常语气使用句号；设置、物体说明和操作提示的无内部标点单句不加句末句号。
明信片采用独立72px高度门禁，不缩小字号。

## 手工验收

从Steam手动启动后检查主菜单、画面设置各滤镜、按键图、开门/门禁卡提示、物品栏、明信片及收藏回看、
章节、死亡画面和字幕；确认中文、变量、文字区与按键图标正确，存读档正常。
问题反馈请附具体场景、原文/译文和截图。缺少实机上下文的词条保留审校备注，不等于仍未翻译。

工具代码：MIT；原创译文：CC BY-SA4.0。字体版权见随包许可证，游戏内容版权不变。
