# 启动时字体加载失败：双索引长度修复

## 启动故障与验证范围

2026-10-21 测试副本手动启动后，BugSplat 和本地日志均显示：
`Failed loading STB Image: /fonts/d2font_12x15.png`。
此前测试只验证 ZAR TOC 与完整 PNG，漏掉 VFS 的第二份长度目录；这是工程工具遗漏，并非安装操作错误。
本次未启动游戏、未改 Steam 原件；修复只更新项目测试副本。

## 已确认原因（静态代码＋离线重放）

| 资源 | 旧 ~INDEX 长度 | 新有效载荷 |
|---|---:|---:|
| FONTS/D2FONT_12X15.JSON | 25306 | 25701 |
| FONTS/D2FONT_12X15.PNG | 6128 | 6771 |
| EN/GAMEMODE.TBL | 436 | 437 |

初版只改了 ZAR TOC，未更新 ~INDEX。原始完整 PNG 可解码；按 VFS 声明的 6128 字节读取新图片时，得到 `image file is truncated`。
对同一坏包仅补 512 字节末尾对齐，仍然三处长度不匹配且解码失败，排除“仅尾部对齐”修复。
修复前后 PNG 与字体 JSON 有效载荷保持相同，只新增对 ~INDEX 的三个 size 字段更新；不靠重编码图片绕过。

静态证据链：
- `FUN_1401ea990`：读取 ~INDEX，count*16+8 为名称池基址。
  Evidence `ev_1195321bae358e2084c82d82219da2e8554bb31c848bc8e75b6279e06958edbf`。
- `FUN_1401bc120`：挂载 VFS::RomFile，把目录长度写入对象 +0x68。
  Evidence `ev_2a426f2ac301377231fd30c7ccda9e3e7d84ad24d4ee8eac0686327dfca9eee1`。
- `FUN_1401ba2a0`：RomFile vtable +0x38 指向此方法，返回 +0x68 长度。
  Evidence `ev_a00a18658244c542096f87e3112b10bfaa05cf7ce5564a2d8e302d71e322191e`。
- `FUN_1401bffe0`：读取文件缓冲区时调用 vtable +0x38 获取大小。
  Evidence `ev_98ae8e0c4e5575e6c4427b354c9643f112ec9741cf847f4d8163fde3d8dfdb0b`。
- `FUN_1401e5bf0 → FUN_1401e5380`：把缓冲区及长度交给内存图像解码；失败时打印现场所见 STB 错误。
  Evidence `ev_d9834459ae7940a2450426382fd522fcbd826b3f8b10a5b7c9ffbf2e8bc37d46`、`ev_b126f3986353a205ba0f67bb96ee9bd66e5cd35c2b81182a7684b802711b518f`。

## 实现与回归

`Zar.rebuild` 派生更新 ~INDEX，保留名称、顺序、flags 和外部条目；遇到未知非零 flags 的变长资源则拒绝。
修复后的变化成员数是 4（原三项＋~INDEX）。构建报告记录自动派生的成员。
新增真实文件长度重放工具和 8 项合成索引回归，测试总数 36。
失败样本保留在忽略的 `build/failures/stb-load/`，不上传原包、日志或截图。

复现命令（项目根目录）：

```powershell
python -X utf8 ./tools/check_runtime_assets.py ./build/failures/stb-load/rom.zar
# 退出 1：mismatches=3，font_decode=FAIL(image file is truncated)
python -X utf8 ./tools/check_runtime_assets.py ./build/smoke/rom.zar
# 退出 0：mismatches=0，font_decode=PASS
```

重放使用 Python 图像解码器与已确认的 VFS 长度路径，不声称执行了游戏或原生 STB 代码。
复验步骤为关闭 BugSplat 后重新运行原来的测试副本；中文主菜单及游戏稳定性仍待实际验收。
