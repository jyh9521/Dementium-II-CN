# 行走晃动固定容量加载修复（2026-10-24）

## 实际根因

原汉化在OPTIONSNEW.TBL追加“轻微”为索引48，并把HEAD BOB中间索引41改为48。真实原生加载器只加载48行；指针表0到47之后的+0x180保存整个原始文本缓冲区地址，不是第49行指针。读取索引48就返回文件第一行“反转”。这与设置值、控制轴反转或混装无关。

旧verify_option_context人工构造49个指针，绕过真实加载器，因而给出错误的PASS。新的验证串接实际ROM资源→原生打开/分割/指针表构建→原生getter。仅文件流、分配器边界使用确定性替身，不启动游戏。

## 修复

- 恢复原始48行表和原生[16,41,18]索引，不扩大对象或覆盖buffer所有权字段。
- 通过locale的context_literals配置“轻微”“关闭”，存入只读.locmenu；受守卫的HEAD BOB getter分支返回独立字符串。
- 代码位于RX .locui的空闲保留区，39字节，新增设置写入为0；无RWX节和新导入。
- 保留普通状态、小地图关/半透明/不透明及原表第0行“反转”。0到7全部原始状态按原生归一化逻辑处理，不改变设置值与默认值。
- 当前26152271与兼容26123896均修复；26099941没有HEAD BOB，不增加此hook。
- 字体extra_texts保留轻微/关闭，删除不安全的表格扩展依赖。

## 精确证据

原错误EXE：36a578418ce15e282f05a72ceb0bdea1df5360f5232dec06bd29b61bf6eefc72。
原错误ROM：bb89fef88d84b71b0ade27caf57aafe5e061988cf1729b8613976ffde874de96。
修正EXE：fafe1863524cbbeb3b758d617c63b0fdd84c65af28bd47464bc6a70d11a08549。
修正ROM：b38bdba2dcfa877c93d79f64153abcf8111c2a314e8162d1d5060e52a962c283。

真实loader红阶段：普通/反转/关，resource_rows=49、loader_rows=48、slot48_is_backing_buffer=true，断言退出1。
绿阶段：普通/轻微/关闭，resource_rows=loader_rows=48；小地图、首行反转及设置内存不变，退出0。
隔离回滚恢复错误基线的完整字节与相同错误显示，修正输出保留，退出0。这里只是验证逆操作，不写实际Steam目录。

7项端到端回归包括同ROM红绿、两版、ASLR、8状态、容量/跳转/stub/index字节突变守卫。精确命令、输入、输出与退出码在build/head-bob-runtime-fix/VERIFICATION.txt；实际旧坏补丁的带receipt升级记录在upgrade-real-corrected.log。

升级测试以真实原版副本安装旧49行+坏EXE，随后升级为新48行+正确EXE；原版备份与receipt.original不变，幂等通过，再恢复得到原始双文件并清理备份。不得把旧坏target保留为新payload的已安装变体。

REA原版资源xref证据：ev_9587c5e2899d66f071c061fbfae165471f14162484f65065928c4b300d2dadb2；原生loader反编译证据：ev_322196ef92db25e8fc9751cde14d8cfbe5cf6423795d209c3ced186c26aa8625。

离线原生代码回放与随后游戏内复验分别记录，不把前者作为实机画面验收。

## 本轮交付与集成

全库437项运行：259项通过、178项夹具依赖测试跳过；81项C#测试与15阶段安装器集成全部退出0。两个原生版本、真实旧坏补丁升级、原件备份保留、幂等和原版恢复均通过。
ROM相对坏基线只改变EN/OPTIONSNEW.TBL及其~INDEX尺寸字段；其他成员（含字体像素、地图与配置）逐字节一致。两次完整构建的EXE/ROM/差分/文本逐字节一致，来源清单与最终源码匹配。

当前修正版仍为未发布的v1.1.2，安装器78,512,153字节，SHA-256：
3e4791eb8619818a13cb48afef1ca7c4408042a6e4e423dd184510355ebbea09。
ZIP：72,435,744字节，SHA-256：
1fa46a90cbbb93b89d0bbf3a3707694535ee889de7d1389946ca2ee4c56906c1。

实际Steam目录与存档没有被本轮工具改写；游戏没有自动启动。新Release附件仍待手动上传。
