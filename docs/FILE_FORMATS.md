# 已实现文件格式

本页列出已实现入口，不使用通用模板代替实际逆向结论。

| 格式 | 实现与证据 |
| --- | --- |
| ZAR1外层归档与VFS `~INDEX` | [TECHNICAL_ANALYSIS.md](TECHNICAL_ANALYSIS.md)，`tools/localize.py` |
| UTF-8独立文本、TBL及SUB记录 | [TECHNICAL_ANALYSIS.md](TECHNICAL_ANALYSIS.md)，extract/import_text/validate |
| d1-rgba JSON/PNG字库 | [FONT_ROUTING_AUDIT.md](FONT_ROUTING_AUDIT.md)，`tools/font_pipeline.py` |
| zar-sparse-delta-v1 | `tools/localize.py`，追加保留、双向哈希与字节守卫 |
| native-menu-pe-v1原生EXE差分 | [NATIVE_CHEAT_MENU.md](NATIVE_CHEAT_MENU.md)，debug_menu/build_resource_payload |
| 资源级安装载荷与备份记录 | [GUI_INSTALLER.md](GUI_INSTALLER.md)，`installer/ResourceEngine.cs` |

原版身份与未知字段按记录保留。归档成员可变长不代表内联菜单容量已验证；CPU回放不代替实际窗口显示。
