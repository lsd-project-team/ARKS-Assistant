# ZX2200 轴到位等待：源码与随仓库程序集的分层契约

更新：2026-09-28。范围仅为 `trunk` 中的业务调用和随仓库提供的三个 .NET 程序集；没有运行控制器、设备或完整生产任务。这里的 **IL 是编译产物证据，不是缺失的 C# 源码**。工程师可用[交互时序图](motion-arrival-sequence.html)、[图中每条消息的证据索引](motion-arrival-sequence.evidence.json)、[原始源码](../../trunk/AKRS.ZX2200/BondSystem/Modules/BondModule.cs)、[逐条IL/程序集哈希](motion-arrival-binary-evidence.json)及[复现脚本](../../scripts/extract-motion-arrival.ps1)核查。

## 可确认的执行链

1. `BondModule.cs:489–497`：先分别下发 X、Y 绝对移动，再调用 `MotionService.WaitAxesArrival`；第二个例子 `:808–817` 先下发 X、Y、T，再等待三轴。该文件其余调用起点为 `:578、:626、:683、:765、:846、:860`，见快照 `source.calls`。这些调用均传入 `true` 和 `AccuracyMode.HighAccuracy`（枚举值 0）。调用不同于同步插补或设备实际完成证明。
2. `AKRS.Galaxy2.LogicHardware.dll` 的 `MotionService.WaitAxesArrival`，`IL_000e–IL_0083` 逐个处理元组；`IL_0018–IL_0030` 把轴、布尔值、目标位置、精度传给 `Axis.WaitForArrival`。返回值不是 `ExcuteResult.Success`（枚举值 3）时，`IL_0037–IL_0067` 构造并抛出 `DriveMotionException`。`IL_006b–IL_007e` 捕获异常、加入列表并继续下一轴；循环结束若有异常，`IL_0085–IL_00b0` 创建 `AggregateException`、调用错误日志、抛出聚合异常。此包装层没有统一超时计时或停轴调用。
3. `Axis.WaitForArrival` 有 Fody `JudgeInitAspect` 包装：`IL_0055–IL_0083` 可在切面设置短路流行为时跳过执行体。切面 `JudgeInitAspect.OnEntry` 的 `IL_0001–IL_007b` 使用生产状态与 `IsInit` 决策并能写入预设返回值。单轴真正的执行体为 `Axis::$_executor_WaitForArrival`；不可把外层方法直接视为无门控。
4. 单轴执行体在 `SynSymbolize` 监视器内：`IL_0014–IL_0040` 对 `HighSpeed=1` 调用驱动 `WaitInCommandPosition`，对 `HighAccuracy=0` 调用 `WaitInRealPosition`。`IL_0042–IL_00b4` 仅在布尔实参为真时取得实测位置；若 `Abs(实测－目标)>2`，先显示对话框、后抛 `LogicHardwareException`；正常路径返回 `Success=3`，finally 释放锁。异常没有在单轴执行体被改写为成功。注意异常文本后半句写的是“超过0.5mm”，而比较常量确实为 **2**；这项文案与代码不一致，不能把0.5mm当作实现阈值，也不能跨T旋转轴假定同一物理单位。
5. `AKRS.Galaxy2.Drive.dll` 对四类轴分别实现两种等待方法，具体是否启用要以现场轴配置为准。LeadShine E5032 使用 `Stopwatch`，在指令/实测等待路径分别出现30,000ms与3,000ms、30,000ms与10,000ms的分段阈值；ACS 调 SDK `WaitLogicalMotionEnd`/`WaitMotionEnd` 并传数值30、捕获并封装异常；GT 使用可配置 `WaitMoveDoneTimeout` 与 `GetState` 轮询，实测路径先等待指令路径；ETEL 调外部 `DsaDrive.waitMovement`/`waitWindow` 并传数值30,000。准确语义和时间单位涉及驱动SDK实现及现场配置，不能仅凭常量断言统一超时策略。逐条方法名、分支及IL偏移见 `methods.drivers`。

## 仍需确认

- 缺三个依赖的原始 C# 实现；本次证据基于当前 DLL 的 SHA-256，重新编译或更换程序集后须重新提取并复核。
- 未确认现场实际选用的控制器、轴映射、`WaitMoveDoneTimeout` 与目标位置单位；没有厂商SDK内部到位/取消/停轴契约或实机回执。
- 包装层的聚合异常意味着其他轴可能仍被依次等待；不能因此推论运动被自动停止。对话框可能阻塞，实际交互与异常处理链未端到端测试。
- 本轮不是设备安全验收，也不把独立编译产物当作与本地源码同一版本的完整证明；需要对应构建记录及现场样本来关联合同。

## 重现和审核

在仓库根目录运行 `node scripts/verify-motion-arrival-contract.cjs`，验证八处业务调用、枚举、IL模式和固定快照；如程序集或源码**有意变更**，先人工审阅差异，再运行 `node scripts/verify-motion-arrival-contract.cjs --update` 并重审本页。脚本只用随仓库的 Mono.Cecil **读取**程序集元数据，不装载或执行设备 DLL。此前[安全移动审查](safe-motion-workflow-review.md)将到位等待的实现标为未知；本页只收窄到随仓库当前二进制中的包装、单轴和驱动调用，缺失源码/SDK与真机验收仍未解除。

时序图的10条消息均绑定了上述精确位置，共20个锚点；`node scripts/verify-motion-arrival-sequence.cjs` 校验图、IL和源码指纹。Archify showcase交付为9/9检查、零错误零警告；官方 `visual-check` 以本机Edge测得四种桌面视口、两种主题通过；两张最终主题截图已人工检查。这仍不能取代业务执行或设备验收。
