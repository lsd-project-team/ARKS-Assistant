# 任务关闭门控：真实Task状态与启动/界面消费者

后续组合验证（2026-09-30）：[原准备帮助方法与实际供晶Task](readiness-helpers-review.md)通过303项检查，将原信号复位、关闭、日志、初始化、环境和容量包装接入完整启动。原Running关闭拒绝前已清除需料/取料事件，现有实际供晶Task随后等待新请求。本文件原测试的隔离/依赖替身范围不扩大。


日期：2026-09-29。155项检查通过，包含16个原收集字段×8种真实.NET Task状态的128项矩阵，另有27项状态基准、配置边界、引用替换、缺失容器以及原启动/停止UI集成检查。测试纳入40份原成员片段；并非40个方法的全部分支覆盖。

## 本轮补上的证据

先前[停止生命周期](stop-shutdown-lifecycle-review.md)已静态指出IsAllowTaskClosed只拒绝Running；本轮直接提取完整原方法，使用真实Framework Task对象逐字段执行，随后把该方法接回[真实加载到启动](startup-config-review.md)和[原界面状态/Stop](startup-entry-review.md)脚手架。没有把TaskStatus枚举值塞入状态替身。

Task对象来自受控工厂：Created未启动；WaitingToRun由自定义TaskScheduler暂存；WaitingForActivation使用TaskCompletionSource；Running通过事件确认进入后阻塞；WaitingForChildrenToComplete使用实际AttachedToParent子任务；成功、取消、故障为已完成Task。故障被观察，样本finally释放并等待结束后Dispose。等待均有超时，不运行生产业务线程或硬件。

## 八种状态的结果

| 实际TaskStatus | IsCompleted | 原关闭判定 |
|---|---|---|
| Created | false | true |
| WaitingForActivation | false | true |
| WaitingToRun | false | true |
| Running | false | false |
| WaitingForChildrenToComplete | false | true |
| RanToCompletion | true | true |
| Canceled | true | true |
| Faulted | true | true |

16个字段逐一验证均符合该表。收据记录每个字段/状态的判定和真实IsCompleted。此结果证明该谓词不等于“全部Task完成”，也不区分完成成功、取消与故障；不推算真实生产调度窗口或现场重现频率。

## 收集范围与配置

配置启用S1时共16个字段：点胶、供晶、固晶、滑动助焊、翻转、九个输送动作、上料仓、下料仓。每次调用先重建WorkTasks，再顺序读取当前字段。

- 全部字段null仍返回true，列表保留16个null。
- 关闭S1配置后不读取点胶任务；测试中即使其真实Task仍Running也返回true，列表15项。S1容器缺失也在这一分支被跳过。
- 助焊和翻转的硬件开关关闭，不会从该方法的列表中排除对应任务；它们Running时仍阻断。
- 已收集的Running任务若当前域字段随后被置null，下一次调用会创建新列表并返回true，而旧列表及旧Task仍存在且Task尚未完成。此为明确构造的引用替换，不表示已在生产中观测到丢失引用；实际Start替换旧引用的独立证据见[启动并发报告](task-start-concurrency-review.md)。
- TransportDomain容器缺失时，方法在收集前5个字段后抛NullReferenceException，不会返回false或true。

## 两个真实消费者

### 启动准备

对8种真实状态分别执行原Machine.Start和PrepareMachineReadyToStart。其他业务依赖保持已准备：只有Running旧任务阻止Bond.Start调用；Created、WaitingForActivation、WaitingToRun和WaitingForChildrenToComplete的旧任务尚未完成时，原启动仍到达后续Start调用替身。

本轮任务Start内部仍是调用记录替身，没有据此声称真正重启了生产任务或证明重复执行的现场后果。实际旧任务在检查前后保持其受控状态。

### 停止提示UI

当状态Stop、Enabled=false且提示文本恰为设备正在停止，请稍后时，原ChangeUiByState使用该判定：只有Running保持禁用和提示，其余7种状态均恢复界面、隐藏提示，包括4种尚未完成状态。

另以受控Running固晶Task串联原Stop：Stop返回、机器状态Stop，但该Task未完成，原IsAllowTaskClosed仍false。普通Enabled=true的Stop界面刷新则启用配方按钮，受控Task仍在运行。这一步补实了上轮“任务未关闭”为布尔替身的缺口，但控件、状态setter和物理清理仍为替身；不能等同原生UI可点击、设备已停稳或全生产线程交错证明。

## 检查构成

| 分组 | 数量 |
|---|---:|
| Framework状态基准 |1|
| 16字段×8状态 |128|
| 全null、配置、引用重建及缺失容器 |8|
| 原停止提示UI×8状态 |8|
| 原启动准备×8状态 |8|
| 原Stop与普通停止UI |2|
| 合计 |155|

## 复现与来源

- node scripts/test-task-closure.cjs
- node scripts/build-task-closure-audit.cjs --check
- [测试收据和144份状态观察](task-closure-test.json)：源码/脚手架哈希、实际项目DLL身份、Framework版本。
- [审计收据](task-closure-audit.json)：报告、全部输入与原方法片段哈希绑定。

原门控位置：trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs:201–262。原启动、Stop及六个UI状态方法的完整位置保留在测试收据extractedMembers。

## 尚未完成

域容器、UI、硬件、任务体、状态setter为替身；真实业务循环如何退出、事件通知是否仍运行、实际Task引用写入并发、现场配置和调度、原生消息循环、完整依赖构建及设备闭环未验收。未改生产关闭判定或任务取消机制。下一步需按实际生产任务的结束条件追踪Stop后的退出和资源收尾，不能把此155项计作整机关闭成功。29组仍部分复核。
