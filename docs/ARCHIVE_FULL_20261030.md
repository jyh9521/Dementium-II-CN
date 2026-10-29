# 2026-10-30 独立统一归档

## 单包恢复，不再依赖两份归档

统一包采用 `standalone-engineering-archive` 格式，包含当前已提交源码、完整 Git 历史、构建输入、兼容配方和验证证据。恢复不再要求20261024精简包与20261029增量包同时存在。

`ARCHIVE_MANIFEST.json`列出每个文件的用途、长度和SHA-256，以及源码提交、分支、当前安装器和源文件差分清单。`SHA256.json`覆盖全部ZIP成员，唯独不包含自身；成员集合、清单字段和内容身份同时校验。Shell脚本保留可执行位，ZIP成员顺序、时间戳和权限固定。

此包是本地工程维护归档，完整游戏原件仅作为本地重建输入；源码仓库仍不提交游戏整包、字体二进制和品牌原图。

## 保留布局与历史依赖

- `build/original/`保持build 26123896原件身份。它是唯一完整ROM基线，也是历史ROM恢复器和新版源差分共同依赖的基线，不应替换为最新原版。
- `build/update-26260428/source-deltas/`与`build/update-26286386/source-deltas/`保留各版原版EXE/ROM的精确差分，所需源文件位于同一统一包内。
- `build/maintenance/archive-20261024/rom-recovery.json`、`recover.py`、`ROLLBACK.sh`及`recovery/`保留旧中文ROM恢复链。旧完整中文ROM的`ee0533f2...`身份已经由这条链保存；对应历史路径见清单，旧证据按原始含义保留。
- `build/archive/font-inputs/`、`installer/branding/`、独立兼容配方及必要的小型原生EXE夹具保留；重复原件和可以按哈希精确还原的大文件不重复装入。
- 当前`patch.json`、`exe-patch.json`、资源稀疏配方与构建报告保留。当前中文完整输出留在活动工程中，统一归档通过输入和配方重建，不再保存另一份大ROM副本。
- `source-history.bundle`是所有可达引用的完整历史，不是增量Git包。归档不复制`.git`缓存、hooks或工作区索引；恢复时从bundle生成干净仓库。
- `build/archive/history/`保留同路径被后续构建覆盖的历史非Git证据和两份原归档的原始清单；`preservation-ledger.json`逐项记录Git提交、保留别名或精确差分。两个旧安装器以当前安装器为基线保存压缩COPY/ADD差分，不再保留两份重复运行时。
- SDK、依赖目录、编译缓存、重复安装器、安装器ZIP与临时安装/回滚游戏副本不归档。工具链重装与游戏文件恢复分别处理。

## 验证和提取

以下命令使用活动工程中的脚本。提取器只创建新目录，在完整ZIP校验通过后写入临时目录，逐文件读回成功才公布最终目录；已有目录、链接、目录联接、重复成员、大小写冲突、路径穿越或损坏文件均停止操作。

```powershell
python -B -X utf8 tools/archive_full.py verify --archive "D:/Archives/Dementium-II-CN-统一归档-20261030.zip"
python -B -X utf8 tools/archive_full.py extract --archive "D:/Archives/Dementium-II-CN-统一归档-20261030.zip" --output "D:/Rebuild/Dementium-II-full"
```

解压后，工程根目录为`D:/Rebuild/Dementium-II-full/Dementium-II-CN/`。从该目录执行以下命令可恢复完整Git历史；该步骤不联网、不覆盖源码，要求`.git`尚不存在。

```powershell
python -B -X utf8 tools/archive_full.py restore-git --repository .
git status --short
```

历史导入核对bundle身份、独立性、源码提交、分支及干净工作区。默认远端取回映射恢复为普通工作仓库映射，而不是镜像映射。

## 最新原版恢复

原版恢复仅使用Python标准库、统一包内的旧原版与精确差分；不依赖字体、SDK或联网。输出必须位于解压工程之外，且尚不存在，避免混淆归档基线和新原版。

```powershell
python -B -X utf8 tools/archive_full.py restore-sources --repository . --manifest build/update-26286386/source-deltas/manifest.json --output "D:/Rebuild/Dementium-II-original-26286386"
```

build 26260428采用同样命令，只将清单路径和新输出目录改为对应版本。旧中文ROM仍通过保留的历史恢复器生成单独文件：

```powershell
bash build/maintenance/archive-20261024/ROLLBACK.sh --relative build/head-bob-wording/final/rom.zar --output "D:/Rebuild/Dementium-II-historical-rom.zar"
```

恢复器均核对完整目标SHA-256。历史报告中的旧绝对路径不作为新的恢复依赖，实际路径从当前解压工程解析。

旧安装器可用包内当前安装器和历史差分离线还原；输出文件按原归档日期命名，原发布名和SHA-256保留在历史映射表中：

```powershell
python -B -X utf8 tools/archive_full.py restore-sources --repository . --manifest build/archive/history/installer-deltas/manifest.json --output "D:/Rebuild/Dementium-II-historical-installers"
```

恢复源文件后按[BUILDING.md](../BUILDING.md)配置字体和固定版本依赖，使用最新原版重建。归档校验、源文件恢复、中文构建、原生CPU回放与游戏内验收分别记录和判断。

## 明确选择后打包

打包器自动包含全部已提交源码和完整历史；非Git文件必须逐项写入显式计划，不递归猜测哪些生成物需要保留。计划的`files`条目包含`path`和`role`，用途可选`input`、`evidence`、`recipe`、`installer`、`native-fixture`或`baseline-input`。`installer`只允许一个指定路径，完整ROM只允许选定基线目录中的原件。所有列入`source_manifests`的差分清单都必须能在包内找到相同哈希的原件与差分。

```json
{
  "schema": 1,
  "baseline_directory": "build/original",
  "installer": "dist/Dementium-II-CN-v1.1.3-build26286386.exe",
  "source_manifests": [
    "build/update-26260428/source-deltas/manifest.json",
    "build/update-26286386/source-deltas/manifest.json"
  ],
  "files": [
    {"path": "build/original/rom.zar", "role": "baseline-input"},
    {"path": "build/original/Dementium II.exe", "role": "baseline-input"},
    {"path": "dist/Dementium-II-CN-v1.1.3-build26286386.exe", "role": "installer"}
  ]
}
```

以上仅演示字段结构，不是完整打包清单；字体、品牌图、各版源差分、兼容配方和全部必要证据也须逐项加入。实际选择清单保存在本轮验证目录。

```powershell
python -B -X utf8 -m unittest discover -s tests -p test_archive_full.py -v
python -B -X utf8 tools/archive_full.py pack --plan build/update-26286386/archive-plan.json --output "D:/Archives/Dementium-II-CN-统一归档-20261030.zip"
```

打包要求已跟踪源码无未提交修改。生成过程核对所有输入身份，重新打开最终ZIP逐成员验证；旧包的清理是独立步骤，只在统一包、Git恢复和实际源文件恢复全部验证后执行。
