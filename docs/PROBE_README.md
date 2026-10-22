# Dementium II 简体中文技术实验包

状态：**仅离线验证通过，不是完整汉化，不是正式发行版。**

适配 Steam AppID 5342930，build 26091059；不适配 2013 HD 版。
唯一翻译是英文语言资源中的 `New Game → 新游戏`；另外附带所需的三个字形。
中文游戏显示、字号、换行、稳定性均等待人工验收。

本包不启动游戏，不包含完整游戏 EXE、DLL、rom.zar 或字体文件。
需要 Python 3.11+；应用补丁不需要安装第三方 Python 包。

## 推荐先在独立副本检查

手动复制游戏到独立测试目录，使用下列命令。`--game` 必须指向副本。

```powershell
python -X utf8 ./install_patch.py install --game "D:/Dementium-II-test" --allow-experimental
python -X utf8 ./install_patch.py uninstall --game "D:/Dementium-II-test" --allow-experimental
```

工具先检查 EXE 和资源包的版本哈希，首次安装备份到
`.dementium-locale/original.zar`，然后原子替换目标文件。重复执行返回已有状态。
卸载保留备份，并拒绝覆盖被其他补丁或 Steam 更新过的文件。
真实安装目录操作与游戏启动均需手动确认，工具不会代为启动。
语言需保持英语，因为本实验替换 `EN/` 资源，不增加语言选择项。

## 许可证

项目工具采用 MIT；原创译文采用 CC BY-SA 4.0；Noto 字形采用随包的 SIL OFL 1.1。
原游戏内容的权利保持不变。本包仅含构建差分与修补工具。

## 待验收

- 主菜单显示“新游戏”，没有乱码或方框。
- 保留其他菜单项、加载和存档行为。
- 720p、1080p、4K 分辨率的对齐与裁切。
- 扩展测试矩阵中的标点、数字、中英混排、长文本和换行。

没有上述游戏实测证据前，不把此包称为完成汉化或公开正式版。
