# 2026-10-29 增量归档与离线恢复

## 基线与范围

本次 ZIP 依赖 `Dementium-II-CN-精简归档-20261024`，不是另一份完整工程备份。
旧归档内源码基线为 `f0346be72c46e0019b1a0a008229aa87c83ede45`，原版为 Steam build 26123896。
旧归档保持只读，既有字体、品牌输入、原版与历史资料不重复装入增量包。

`INCREMENT_MANIFEST.json` 记录基线提交、当前提交、每个新增或变更文件的前后长度与 SHA-256，以及已删除的跟踪路径。
`SHA256.json` 覆盖全部 ZIP 内容成员，打包后重新打开并逐成员校验。
ZIP 成员按名称排序，时间戳和权限规范化；Shell 脚本保留可执行位。

内容仅包括变更源码、增量 Git 历史、新安装器一份、必要的稀疏兼容配方与新证据。
完整原版和汉化游戏、重复安装器 ZIP、编译缓存、SDK、依赖目录均不包含。
未变化文件即使列入显式包含清单也会按旧归档同路径身份排除。

## 新版原版差分

`build/update-26260428/source-deltas/` 保存从旧归档原版到 build 26260428 的两份差分。
ROM 差分按成员身份复制未变化内容，兼容重命名、位置移动和成员新增；头部、间隙和尾部字节也参与最终整文件校验。
EXE 差分仅保存 COPY/ADD 指令与变更字节，不包含完整 EXE。
两份差分共同绑定源文件与目标文件的长度、SHA-256；解包恢复使用 Python 标准库，不依赖字体、SDK或联网。

| 差分 | 压缩后字节 | 新版目标 SHA-256 |
| --- | ---: | --- |
| `Dementium II.exe.delta.gz` | 1911136 | `d8bfc47c991f01dffc352c6d836f8f1f8dedbfc738a50d9c2342d9e1ae46cf87` |
| `rom.zar.delta.gz` | 192559 | `10344977341d6f0481cbefb05d3bf45ec094459eb9f6419b31663b5551fd90fe` |

差分复制579879215字节，仅保存5128913字节的目标字面量；压缩差分合计2103695字节。
已在独立目录恢复原版两文件并逐字节对照本次新版输入。

## 恢复步骤

1. 保留旧归档不变，将旧工程复制到新的工程目录。
2. 将增量包内 `Dementium-II-CN/` 的文件覆盖到新工程目录；清单中的删除路径仅是说明，不自动删除旧归档。
3. 若需恢复完整 Git 历史，在新工程执行 `git fetch ./source-history.bundle HEAD:refs/heads/archive-20261029`；导入后检查提交身份。此命令仅创建长期可达的分支引用，不重置或切换工作区。
4. 在新工程中运行以下命令，把新版原版恢复到尚不存在的独立目录。`--base` 指向未改动的旧归档工程，而不是覆盖后的新工程。

```powershell
python -B -X utf8 tools/archive_increment.py restore --base "D:/Archives/Dementium-II-CN-精简归档-20261024/Dementium-II-CN" --manifest build/update-26260428/source-deltas/manifest.json --output "D:/Rebuild/Dementium-II-original-26260428"
```

恢复器预检全部源文件、差分身份和目标内容后才写入临时目录；落盘校验成功后发布新目录。
已有输出目录、错误基线、损坏差分、目录穿越、符号链接和目录联接均会停止操作；旧原件不被覆盖。
随后按 [BUILDING.md](../BUILDING.md) 重新安装构建依赖，并以恢复出的新版原版目录构建。

## 重新生成与检查

差分生成输出必须为新目录：

```powershell
python -B -X utf8 tools/archive_increment.py delta --base "D:/Archives/Dementium-II-CN-精简归档-20261024/Dementium-II-CN" --output build/source-deltas-rebuilt --file "build/original/Dementium II.exe" --file build/original/rom.zar
python -B -X utf8 -m unittest discover -s tests -p test_archive_increment.py -q
```

最终打包要求当前源码已提交；只读比较已跟踪文件，再通过重复 `--include` 逐一选择必要的非 Git 证据。
`--installer` 是唯一允许装入 ZIP 的 EXE，`--bundle` 保存相对旧提交的增量 Git 历史；既有输出 ZIP 不会被覆盖。

```powershell
python -B -X utf8 tools/archive_increment.py pack --base "D:/Archives/Dementium-II-CN-精简归档-20261024/Dementium-II-CN" --output dist/increment.zip --installer dist/Dementium-II-CN-v1.1.3.exe --bundle --include build/update-26260428/source-deltas/manifest.json --include "build/update-26260428/source-deltas/Dementium II.exe.delta.gz" --include build/update-26260428/source-deltas/rom.zar.delta.gz
python -B -X utf8 tools/archive_increment.py verify --archive dist/increment.zip
```

实际交付包含完整新证据白名单；以上打包命令只演示源码、安装器及源差分的最小选项。
增量归档完整性、离线重建、原生机器码回放与游戏内画面验收分别记录。
