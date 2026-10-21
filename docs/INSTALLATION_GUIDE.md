# 安装与恢复

当前仅提供技术实验包，具体说明见 [PROBE_README.md](PROBE_README.md)。
本轮没有向 Steam 安装目录安装任何内容。

优先使用低侵入的独立测试副本。应用前同时验证 EXE、rom.zar 哈希；备份在目标副本的 `.dementium-locale/original.zar`。
恢复时验证当前修改版和备份的完整哈希，原子写回；恢复后保留备份，便于人工检查。
不修改游戏存档、用户配置、Steam 语言或其他文件，不自动启动游戏。

离线单文件差分流程可以通过 `tools/localize.py patch` 输出到另一个文件，不改变输入。
`tools/ROLLBACK.sh` 固定在项目 build 目录恢复一个额外副本，保留修改版产物。
这与在真实安装目录卸载补丁是两种不同操作。
