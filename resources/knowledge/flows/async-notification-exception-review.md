# 后台通知、共享字段与全局异常边界

更新：2026-09-28。范围为自动生产中 Pick/UpLook/SubstrateCameraCorrection 三类通知任务及 Program 异常入口；静态证据，不是并发故障复现或修复。

## 结论摘要

1. 三类通知由 Task.Run 启动，在调用点不等待返回任务，不把芯片对象、芯片名和下一类型一起保存为局部不可变快照后传入。
2. component 是表达式属性，每次经 S2ActionNodeController.GetCurrentComponent 查询当前 ProcessStep 对应的仓库对象；nextComponentName 则是动作实例字段，在该动作下一次准备/执行时会更新。两者的数据来源与更新时间不同。
3. 调度选择下一动作会更新 CurrentBondActionNode，经 ChangeNameToActionNode → InitCurrentMessage 更新 ProcessStep。动作来自仓库已有对象集合。因此后台委托延迟执行时，有读取后来制程状态或后来字段值的可能；尚未通过运行证明具体混用发生。
4. Program 注册 UI ThreadException 和 AppDomain UnhandledException，两处理器只显示异常信息；函数体没有 Machine.Stop。不能用这两个入口证明生产 Task 异常一定停止设备。
5. 本轮 C# 文本扫描未找到 UnobservedTaskException / OnlyOnFaulted / TaskStatus.Faulted / IsFaulted 具名引用（以扫描结果为准）。未覆盖反射、别名和DLL，不能宣称全系统没有任何异常监督。

## 数据从哪里读，何时改变

|读取对象|来源与写入|通知里的使用|
|---|---|---|
|Pick.component|动态属性→actionNodesService.GetCurrentComponent().component|每次条件判断、名称赋值和日志可以重新读取|
|UpLook.component|动态属性→System2Domain.ActionNodesService.GetCurrentComponent().component|后台判断下一类型是否不同、是否翻转，并可能读取Name|
|SubstrateCameraCorrection.component|同样是动态属性|SendSignalToWaferTable比较当前类型并记录日志|
|nextComponentName|三个动作各自的实例字段；Pick.Prepare、UpLook.DoWork/重取、Substrate.Prepare等写入|通知读取字段，不是Task创建时冻结的名称参数|
|当前芯片类型|GetCurrentComponentName读取ProcessStep.ComponentName；ProcessStep空返回空串，名称null只提示后返回|GetCurrentComponent遍历配置集合，找不到返回(false,null)，通知的.component属性没有在此检查isSuccess|

GetCurrentComponent 在遍历中反复读取 GetCurrentComponentName，最后再比较名称；未见该方法将当前名称先复制成一次查询使用的快照。不能将这段检查视为多字段一致性事务。即使 string/引用单次读取完整，也不代表先后读取对应同一制程。

## 调度与通知之间的可达交错（推断，非实测）

假设通知Task尚未运行：

1. 动作启动通知Task。
2. 动作返回后，固晶线程继续 FinishCurrentActionNode/GetNextActionNode。
3. 新动作选择更新CurrentBondActionNode与ProcessStep。
4. 原通知Task此时读取component，得到的是新的当前查询结果；它仍可能读取旧的nextComponentName字段。若同一个动作实例已再次运行，该字段也可能已经更新。

上述推断由“没有等待通知Task”“动态getter”“调度更新共享状态”“仓库复用实例”共同支持。它不是所有配方必现，也不证明一定发错芯片。应以动作ID、产品/制程ID、通知创建和执行时间、发送的名称来验证。禁止为了演示而直接运行设备。

## 全局异常入口实际做了什么

- Program.cs:99–105：设置CatchException，订阅Application.ThreadException和AppDomain.CurrentDomain.UnhandledException。
- AppUIThreadException:281–285、AppThreadException:292–296：只调用AKRSXtraMessageBox.Show，后者将ExceptionObject强转Exception；没有Stop、Join或恢复任务调用。
- 通知委托后续抛异常不会返回到已启动Task.Run的那层同步try/catch。调用点没有保存返回Task、Wait/await或连接Continuation来处理该通知结果。运行库终止策略、垃圾回收触发和外部库行为尚未验证。
- 源码中存在其他手动/测试窗口的ContinueWith，不等于这些生产通知已被观察；BackgroundThreadService也不能仅凭名称视为全局任务监督器。随仓库 DLL 的[后台任务静态 IL 契约](background-task-contract-review.md)已复核主界面刷新任务，不能据此延伸到这里的 `Task.Run` 生产通知或推定现场加载版本。

可重建扫描：`node scripts/build-task-exception-audit.cjs`；只读校验：加`--check`。结果见[扫描记录](task-exception-audit.json)，包括扫描文件集合哈希、原始命中行和查询词。文本中注释也会计入，不将零命中当成语义上的不存在。

## 证据索引

新增ID以 asyncflow- 为前缀，可在[源码阅读器](module-source-explorer.html)搜索。路径相对trunk/AKRS.ZX2200。

|后缀|文件与行号|
|---|---|
|register|Program.cs:97–107|
|handlers|Program.cs:281–296|
|pick-fields|BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs:104–135|
|up-fields|同目录 UpLookCorrectionActionNode.cs:104–140|
|sub-fields|同目录 SubstrateCameraCorrectionActionNode.cs:75–110|
|repository|BondSystem/Models/ActionNodes/BondActionNodeRepository.cs:59–83|
|repository-list|同上文件:262–279|
|service-list|Main/Machine/Process/S2ActionNodeController.cs:44–55|
|current-context|同上文件:930–943|
|current-component|同上文件:1270–1316|

复用证据：waferflow-notify / notify-methods / request；visionroute-up-next / sub-call / sub-next；bondflow-cursor / work。源码哈希与精确片段在登记表中绑定。

## 后续验收清单

- [ ] 核对通知委托全部写入点与其他辅助/双点/读码路径，不把三个代表路径当成全量。
- [ ] 在隔离测试或经授权设备日志中记录通知生命周期及读取值，验证是否有实际交错。
- [ ] 明确异常监督由本地代码、运行库还是外部DLL承担，并复核停止输出、等待任务和关闭流程。
- [ ] 对每个外部运动/线程服务标注源码缺失、调用证据与待验证契约，避免用“已完成分析”替代缺失实现。
- [ ] 若后续授权改造，再设计输入快照、可观察Task、取消/排队和停止策略；本轮没有改生产源码。
