# 生产任务启动门控与停止后状态重入

更新：2026-09-28。范围：Machine.Start 后续五类任务的 Start、首次循环门控及归位包装。静态证据，不是实机行为判定。

## 核心结论

非补偿模式下，Transport.StartTask 因载具Abort调用Stop并正常返回后，Machine.Start仍调用WaferSubSystemTask.Start。供晶Start并非单纯等待状态：创建分支在Block.StartInit与清空PreviousNeedChipName后显式SetState(Working)，已有Running任务分支也SetState(Working)。因此，在前置调用正常完成且无其他并发状态改写时，存在Stop被后续Start重新改成Working的源码路径。初始化异常被本Start捕获后提示；不能宣称所有情况都必然改写成功。

SetState 在状态不同的时候先构造日志对象、赋值MachineState，再向统计队列Add；不是启动合法性校验器。日志构造或队列异常的时机必须区分，赋值后Add失败不等同赋值回滚。

## 五类任务对照

|任务|Start条件与状态修改|首次WaitStart之前|循环入口|
|---|---|---|---|
|供晶|null或非Running则初始化并建LongRunning Task；创建和已有Running两分支均写Working|命名线程，进入Dowork try|WaitStart后才进入供晶循环|
|点胶|仅null或非Running创建；未设置Working；返回true|S1ActionNodeController.Init|WaitStart后才MoveToSafePos|
|固晶|仅null或非Running创建；未设置Working；返回true|System2RunTimeProvider.ResetInformation|WaitStart后才回吸嘴架、固晶模组安全位和焊头复位|
|滑动助焊|未配置则throw；null或非Running创建；返回true|SlideFluxerHomeWaitArrive|归位调用以后才WaitStart|
|翻转|null或非Running分支先写Working再创建；已有Running不改写|FlipTableGoHome|归位调用以后才WaitStart|

以上Task采用CancellationToken.None、LongRunning、Default调度器。Start返回不等于任务完成；只比较Running也不等于排除了WaitingToRun等尚未执行状态。后续[47项受控检查](task-start-concurrency-review.md)已验证全部TaskStatus门控及供晶两个并发调用创建两个任务；默认调度器现场时间窗口和真实业务后果仍待验证。

## 循环前归位的边界

- 助焊：OffLineWork返回；其余模式调用SlideFluxerHome → SetOutputValue(false)，然后轮询负限位，超过10秒throw。该包装没有Stop/Pause判断，也未Sleep。后续DoWork循环的WaitStart不能保护已发生的前置调用。
- 翻转：FlipTableGoHome → FlipModuleGoHome → FlipTableAxisT.AbsoluteMove(0)。这两个包装没有设备状态判断；轴层的保护、返回含义和硬件执行需另查，不凭函数名认定真实回零完成。
- Signal.WaitStart：首次读Stop返回false；Pause循环内部检查Stop并Sleep(20)，离开Pause循环返回true。它是分散检查点，不是对整段动作的原子保护。

## 与上一轮结论的连接

输送异常catch正常返回与载具Abort分支，都可能继续进入供晶Start；后续不是统一拒绝Start。是否发生设备动作仍依赖配置、初始化、调度、信号、轴SDK和并发状态变化。未执行设备或业务源码，未修改trunk。

## 未完成项

- [x] Block.StartInit本地初始化失败与非null引用重试行为：见[9项隔离检查](wafer-start-init-review.md)。
- [x] 五类入口全部TaskStatus、供晶并发双调用及停止状态交错：见[47项检查](task-start-concurrency-review.md)。
- [x] SetState队列Add失败/阻塞与原Stop清理截断：见[18项检查中的9项状态/队列场景](state-queue-failure-review.md)。
- [ ] 其余初始状态准备、真实UI和业务循环、完整Stop/Start并发、现场调度器与硬件影响。
- [ ] 下层Axis/IO安全保护与现场状态验证。
- [ ] 失效料仓配置解引用、其他域完整就绪条件。

## 源码证据

- [taskgate-wafer-start：trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs:1373–1426](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1373) · [查看快照](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=taskgate-wafer-start)
- [taskgate-wafer-loop：trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs:64–83](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L64) · [查看快照](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=taskgate-wafer-loop)
- [taskgate-dispense-start：trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs:189–207](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L189) · [查看快照](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=taskgate-dispense-start)
- [taskgate-dispense-loop：trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs:63–83](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L63) · [查看快照](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=taskgate-dispense-loop)
- [taskgate-bond-start：trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs:361–377](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L361) · [查看快照](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=taskgate-bond-start)
- [taskgate-bond-loop：trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs:100–116](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L100) · [查看快照](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=taskgate-bond-loop)
- [taskgate-slide-start：trunk/AKRS.ZX2200/BondSystem/Tasks/SlideFluxerTask.cs:227–250](../../trunk/AKRS.ZX2200/BondSystem/Tasks/SlideFluxerTask.cs#L227) · [查看快照](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=taskgate-slide-start)
- [taskgate-slide-loop：trunk/AKRS.ZX2200/BondSystem/Tasks/SlideFluxerTask.cs:92–104](../../trunk/AKRS.ZX2200/BondSystem/Tasks/SlideFluxerTask.cs#L92) · [查看快照](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=taskgate-slide-loop)
- [taskgate-flip-start：trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs:260–277](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs#L260) · [查看快照](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=taskgate-flip-start)
- [taskgate-flip-loop：trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs:57–68](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs#L57) · [查看快照](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=taskgate-flip-loop)
- [taskgate-setstate：trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.StateRelated.cs:52–68](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.StateRelated.cs#L52) · [查看快照](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=taskgate-setstate)
- [taskgate-wait：trunk/AKRS.Galaxy2.Machine/Models/Signal.cs:202–228](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L202) · [查看快照](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=taskgate-wait)
- [taskgate-slide-controller：trunk/AKRS.ZX2200/BondSystem/Controllers/SlideFluxerController.cs:55–77](../../trunk/AKRS.ZX2200/BondSystem/Controllers/SlideFluxerController.cs#L55) · [查看快照](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=taskgate-slide-controller)
- [taskgate-slide-output：trunk/AKRS.ZX2200/BondSystem/Modules/SlideFluxer.cs:57–69](../../trunk/AKRS.ZX2200/BondSystem/Modules/SlideFluxer.cs#L57) · [查看快照](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=taskgate-slide-output)
- [taskgate-flip-controller：trunk/AKRS.ZX2200/WaferSubSystem/Controllers/FlipTableController.cs:118–121](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/FlipTableController.cs#L118) · [查看快照](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=taskgate-flip-controller)
- [taskgate-flip-axis：trunk/AKRS.ZX2200/WaferSubSystem/Modules/FlipModule.cs:103–106](../../trunk/AKRS.ZX2200/WaferSubSystem/Modules/FlipModule.cs#L103) · [查看快照](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=taskgate-flip-axis)
