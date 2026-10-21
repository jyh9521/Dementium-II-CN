# 文件地图

| 路径 | 用途 | 跟踪/分发 |
|---|---|---|
| tools/localize.py | ZAR1、提取、校验、字体、重建、差分 | 源码 |
| tools/verify.py | 本机构建离线往返、中文字形、回滚 | 源码 |
| tools/record_verification.py | 精确命令/输入/输出/退出码 | 源码 |
| tools/install_patch.py | 明确执行的版本锁定安装/卸载；无启动功能 | 源码/实验包 |
| tools/package_probe.py | 白名单确定性实验包 | 源码 |
| tools/fetch_font.py | 固定官方字体下载/哈希 | 源码 |
| tools/ROLLBACK.sh | 在 build/rollback-shell 恢复额外副本 | 源码，可执行 |
| tests/test_*.py | 合成资源和安装器测试 | 源码；不含游戏资产 |
| locales/zh-CN/smoke.json | 完整源映射＋单项中文实验 | 翻译数据 |
| assets/supported-build.json | 本机分析构建的身份锁定 | 元数据 |
| assets/fonts/source.json、OFL.txt | 字体来源/许可证 | 元数据/许可证 |
| assets/fonts/*.otf | 本地缓存的固定字体 | 忽略；由工具下载 |
| build/inventory/ | 原文件和封包成员清单、字符串候选 | 仅本地 |
| build/evidence/ | REA 静态分析证据 | 仅本地，不分发反编译正文 |
| build/smoke/rom.zar | 修改版完整资源 | 仅本地，不分发 |
| build/smoke/patch.json | 最小实验的稀疏差分 | 实验包 |
| build/smoke/font-preview.png | 字形静态预览，非游戏画面 | 仅本地 |
| build/probes/ | 显示测试矩阵 | 仅本地，未作运行验收 |
| build/rollback*/rom.zar | 恢复的额外副本 | 仅本地 |
| build/VERIFICATION.txt | 精确离线证据 | 仅本地 |
| dist/*.zip | 未经正式验收的技术实验包 | 仅本地，未发布 Release |

AGENTS.md 和 docs/LOCALIZATION_STANDARD.md 保留本地，忽略且不打包。
