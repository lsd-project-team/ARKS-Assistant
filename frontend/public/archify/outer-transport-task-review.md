# 外层固晶到等待区任务：返回值、循环与异常

日期：2026-09-29。范围为正常生产 Start 中 transferBondToWaitingUnloadTask 的原委托体，接入9个原方法及完整 Signal 原类。16个场景、52项受控断言；生产源码不变，模块状态仍为 partial。

## 实现和证据

- `TransportTask.cs:558–598` 委托体逐字提取，限定 `Start()` 与 `StartDryRun()` 之间的唯一赋值；保存文件和片段哈希。没有把整个 Start 当成已执行的方法。
- 沿用原 TransferBondToWaitingUnload、UnClamp、BlockCylinderDownAndDelay、两段皮带包装、模块命令、Stop、SetState、SetStopStateAlarm。精确行号及来源见 `outer-transport-task-test.json`。
- 使用真实 Task、线程和事件；适配器每次调用原输送方法并返回原结果，不伪造返回码。屏障只控制返回后的调度，以观察下一循环。
- 运行时为本机 .NET 10.0.11；轴、传感器、配置存储、日志、弹窗及服务为替身。传感器按完成序列返回，未执行产品宿主、原生UI、实际Axis DLL或驱动。

## 场景与结果

| 场景 | 已验证行为 |
|---|---|
| 正常成功后再次循环 | Success记录后继续；原方法第二次因材料已转移返回NoStart；只调用一次保存和两段轴接口 |
| 无材料NoStart | 连续两次调用，既不移动、不保存，也不调用Stop；外部Stop后在下一WaitStart退出 |
| 原UnClamp报警Abort | 内层Stop后仍调用轴并保存，返回Success；外层记录Success且不重复Stop，随后因已Stop退出 |
| 两段轴各自抛异常 | 内层返回Exception，外层记录后调用原Stop；无材料提交、不再循环，Task正常完成 |
| 堵料Abort | 外层调用原Stop；没有保存，任务正常结束 |
| Success日志抛异常 | 材料已提交；外层catch记录并弹窗，任务正常完成但机器仍Working |
| Stop创建状态日志抛异常 | 状态尚未写入；外层catch结束任务，机器仍Working，后续停止清理未执行 |
| Stop日志入队或报警器Stop抛异常 | 状态已Stop，但后续退出单步、关要料和真空未完成；外层catch结束任务 |
| 外层catch自身日志/弹窗抛异常 | Task变为Faulted；没有额外Stop，机器仍Working |
| 线程命名抛异常 | 命名调用在try之前，Task变为Faulted，外层catch未执行 |
| 入口Stop/Pause | Stop不调用输送；Pause阻塞，恢复Working后可完成原输送 |
| 两次循环之间Pause | 已提交Success不回滚，下一次调用被WaitStart阻止；恢复后返回NoStart |

## 解释

原外层catch只记录并弹窗，没有Stop或重新抛出。因此 TaskStatus.RanToCompletion 不能作为设备停妥或业务成功的判据。Stop内部异常可能保留Working，或留下已Stop但清理不完整的状态。外层只根据内层返回码处理，不能识别UnClamp以void返回造成的“已停止但输送返回成功”。

这些是给定替身与调度条件下的可重复结果；不证明设备实际继续运动，也不证明现场日志一定抛异常。当前不自动修改生产控制逻辑，避免在缺少现场配置和验收条件时改变机械行为。

## 复现与审计

- `node scripts/test-outer-transport-task.cjs`
- `node scripts/build-outer-transport-task-audit.cjs --check`
- 来源审计覆盖12个测试/依赖文件、9个原方法和1段任务委托；检查来源哈希、片段行号、唯一断言名和报告哈希。
- 统一回归与阅读器验证另见 `outer-transport-task-integration-verification.json`；只有生成并通过该回执才算完成本增量收尾。

## 尚未完成

完整Start的任务去重/重启、ConfigureAwait(false)调用处、全部运输任务并发、空跑任务、供晶消费者、实际仓库状态属性与加载DLL版本、原生UI和设备验收仍待完成。本报告不将委托测试扩展为上述范围通过。
