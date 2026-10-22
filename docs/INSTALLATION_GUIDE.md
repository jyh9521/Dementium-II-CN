# 安装与恢复

## 安装

1. 从[v1.0发布页](https://github.com/jyh9521/Dementium-II-CN/releases/tag/v1.0)下载 `Dementium-II-CN-v1.0.exe`，准备Steam 2026版游戏并退出运行。
2. 运行安装器，确认自动检测的Steam路径；未检测到时手动选择游戏目录中的 `rom.zar`。
3. 点击安装，等待完成，之后从Steam正常启动游戏。

安装器为Windows x64自包含程序，不需要Python或另装.NET，不包含游戏本体。已验证原生EXE版本见[版本身份](../assets/supported-build.json)。

## 升级与备份

有可信安装记录和完整原件备份的旧汉化可以直接升级。备份使用原文件名保存在 `cn-backup`，包含ROM、EXE与 `resource-state.json`。
安装期间请保留该目录；备份异常或文件被其他程序改写时，保留现场和日志再反馈。

## 恢复

退出游戏，运行同一安装器选择恢复。两个文件完整恢复且哈希校验成功后，安装器删除整个 `cn-backup`。
失败或仅部分恢复时保留备份；操作不修改存档与其他游戏数据。完整恢复后再次恢复为幂等操作。
实现和开发端验证见[GUI_INSTALLER.md](GUI_INSTALLER.md)。
