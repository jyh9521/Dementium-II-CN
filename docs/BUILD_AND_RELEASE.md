# 构建与发布入口

依赖、输入、构建、测试与打包命令统一维护于[BUILDING.md](../BUILDING.md)。

- [发布身份与验收](STATUS.md)：当前Release、附件SHA与通关结论。
- [安装器构建](GUI_INSTALLER.md)：品牌输入、SDK、Material界面及恢复事务。
- [本地保留与清理](BUILD_STORAGE.md)：当前输出、单一原版基线及历史证据。
- [历史专项回归](history/BUILD_REGRESSIONS.md)：开发阶段红/绿/隔离回滚命令。

发布前核对生成物、安装器、Git提交及远端附件身份。已有Release及标签保留；推送源码不改动附件，不自动移动发布标签。
