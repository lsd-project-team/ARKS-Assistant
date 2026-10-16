# 生产启动：就绪检查与失败传播边界

状态：指定方法静态复核；不是全部配置有效性验证或实机验收。源码未修改。

## 实际启动顺序

1. Machine.Start 调用 PrepareMachineReadyToStart；false 直接返回，成功后先 SetState(Working)。Prepare 中先清理文件、复位信号，再检查总复位等条件；检查失败不代表此前没有副作用。
2. CheckOperatingEnvironment 顺序短路检查晶圆域、S2、S1、TU示教、焊点示教、制程。IsTransportUnitReady 本方法只检查 TransportUnitConfig.IsAssistantSucceed；不能据此声称料仓名称和全部配置均已校验。各域内部检查仍需分别追踪。
3. 非补偿模式进入 TransportDomain.StartTask，然后调用 WaferSubSystemTask.Start；配置S1且非补偿模式时启动点胶任务。之后初始化S2动作节点、调用BondTask.Start，再按硬件及补偿条件调用滑动助焊和翻转任务，最后调用两项华夫盒真空检查。以上是调用顺序，不是并发任务完成顺序。
4. StartTask 未配置输送则返回；初始化 TransportModule 后，DryCycle 直接调用 StartDryRun。正常模式先检查载具，再按 Online 清除请求信号、按逆向搜索刷新TU、MapMaterial；LoaderBin 模式启动上下料任务，最后启动输送任务。

## 载具检查与重试

- 先读取出料口输入：LoaderBin 或 OnlineWithAutoUnloader 且有料时弹出重试/终止。再读取入料口输入：LoaderBin 或 OnlineWithAutoLoader 且有料时弹出重试/终止。
- 任一 Retry 都跳回同一个标签，重新从出料口开始检查；Abort 返回 false。该方法没有重试计数上限。传感器包装、弹窗关闭的实际返回值未在本专题验收。
- MapMaterial 先 Bond.MapBelt(true)，配置S1才 Dispense.MapBelt(true)；Online/OnlineWithAutoLoader 再根据前端传感器更新上料段状态。这是实际调用，不把注释当作下层检测效果的证明。

## 关键失败边界

- 载具检查 false：StartTask 调用 Machine.Stop 后 return，但其返回类型为 void。Machine.Start 在该调用之后没有判断结果或立即检查设备状态，源码控制流仍到达后续任务的 Start 调用。
- StartTask try 范围异常：catch 写日志并显示错误，本 catch 未显式 Stop、rethrow 或向调用方返回失败标志；如果日志/弹窗正常返回，外层继续后续调用。如果 catch 自身抛异常则属于另一条路径。
- 不能据此断言设备停止后一定运动：每个任务 Start 和工作循环可能有状态门控，需继续逐一追踪并在测试环境确认。
- 当前方法范围未证明存在启动事务、全任务启动成功确认或统一回滚。也不能由局部未见校验推出全工程不存在校验。

## 后续验收清单

- [ ] 将所有任务 Start / 工作循环状态门控与上述两类失败传播逐一对应。
- [ ] 追踪失效 LoaderBin/UnloaderBin 名称的首次解引用、捕获位置及后续状态。
- [ ] 逐项展开 Wafer/S1/S2/Process 就绪检查和 MapBelt 内部分支。
- [ ] 在隔离测试环境模拟 Abort、配置缺失与初始化异常；本次未执行设备操作。

## 可溯源证据

- [CheckOperatingEnvironment 89–128](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L89) · 证据ID：startgate-environment · [源码快照阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=startgate-environment)
- [PrepareMachineReadyToStart 185–256](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L185) · 证据ID：startgate-prepare · [源码快照阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=startgate-prepare)
- [Start 261–309](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L261) · 证据ID：startgate-launch · [源码快照阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=startgate-launch)
- [IsTransportUnitReady 89–99](../../trunk/AKRS.ZX2200/TransportUnitSystem/ProductConfiguration.cs#L89) · 证据ID：startgate-tu · [源码快照阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=startgate-tu)
- [StartTask 84–141](../../trunk/AKRS.ZX2200/TransportSystem/Models/TransportDomain.cs#L84) · 证据ID：startgate-transport · [源码快照阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=startgate-transport)
- [CheckCarrierBeforeLoaderMove 2454–2526](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L2454) · 证据ID：startgate-carrier · [源码快照阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=startgate-carrier)
- [MapMaterial 132–145](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L132) · 证据ID：startgate-map · [源码快照阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=startgate-map)

## 后续复核已推进

[五类任务启动门控与循环前动作](production-task-start-gates-review.md)已完成指定方法静态复核：供晶Start两分支写Working，翻转创建分支写Working；助焊和翻转归位在首次WaitStart之前。上述检查清单仍保留全链路和运行验收缺口。
