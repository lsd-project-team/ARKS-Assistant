# 急停与Abort：真实Task状态及异常截断

日期：2026-09-29。87项检查通过，测试程序集纳入44份原成员片段；并非这些成员的全部分支覆盖。执行原EmergencyStop、Stop与三种Abort方法，使用真实.NET Framework Task和Parallel.ForEach。

## 实际结果

| 方法/阶段 | 已验证行为 |
|---|---|
| 点胶AbortThread | 原方法只有DispenseTask.Dispose。五种未完成Task状态均抛InvalidOperationException；三种已完成状态成功释放等待句柄；null抛NullReferenceException |
| 固晶AbortThread | 原方法为空；八种Task状态保持不变，null不报错 |
| 供晶AbortWaferSubThread | 原方法只有注释；八种Task状态保持不变，null不报错 |
| EmergencyStop正常轴调用 | 每轴调用StopMove(false,true)，Parallel完成后执行Stop，再按点胶、固晶、供晶顺序调用Abort |
| 未完成点胶Task | Stop已执行，但Dispose抛异常，后续固晶和供晶Abort均未调用 |
| 已完成点胶Task | 三个Abort均返回，但受控Running固晶与供晶Task仍在运行；原关闭判定仍为false |
| 禁用S1配置 | 急停仍调用点胶Abort，null仍抛异常，未按配置跳过 |
| 轴停止抛异常 | Parallel抛AggregateException；本次未执行Stop及三个Abort。不保证其他轴是否都被尝试 |
| Stop清理抛异常 | 六个注入故障点均使三个Abort不执行；不将部分状态写入当作完整清理成功 |

此外验证空轴列表仍继续Stop/Abort、null轴列表以及硬件查找异常在Stop前截断。

## 检查构成

- 三种Abort×八种真实状态×行为/资源两项断言：48项。
- 急停×八种点胶状态×三项顺序和存活断言：24项。
- 三种null任务：3项；S1开关下null点胶：2项。
- null轴列表、轴故障、查找故障：3项。
- Stop六个故障位置：6项；空轴列表成功：1项。
- 合计87项；42条结构化观测保留在回执。

## 证据与边界

原方法从生产文件按签名提取，绑定文件与片段SHA256；实际使用随项目Singleton/JSON程序集。Abort包装器只记录调用入口后转调不变的原方法体。轴命令、状态setter、信号、UI及业务任务体是替身；Task本身及调度状态为真实Framework对象。每个阻塞样本在finally释放并等待结束，有超时上限。对已Dispose样本的清理兼容仅存在测试组合器内。

本结果不证明物理急停有效、不证明生产线程可取消，不构成整机安全或设备认证。生产源码未修改。44个纳入成员包括复用脚手架所需方法，不能据此声称全部运行覆盖。

复现：`node scripts/test-emergency-abort.cjs`；审计：`node scripts/build-emergency-abort-audit.cjs --check`。

前置证据见[Task关闭门控](task-closure-review.md)及[停止生命周期](stop-shutdown-lifecycle-review.md)。下一步核对实际急停触发入口、异常承接及不同入口的收尾行为；完整依赖、生产并发、原生UI与设备验收仍未完成，29组保持部分复核。

