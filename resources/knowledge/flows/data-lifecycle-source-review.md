# 数据生产者与退出生命周期

2026-09-28。补充已有统计主链，限定到所列方法；不表示所有事件或运行时AOP织入已验证。

## 三类日志路径

视觉报警的两个VisionAlarm重载均持有UiLock，创建开始时间，Invoke显示模态窗口并取人工结果；关闭后填处理时间/类型/分类，直接DBService.Insert，然后ResetAlarm并返回。它不经过容量500的统计队列；写库失败在DBService内被记录后返回，不能以ResetAlarm推断报警已保存。[234–303](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcmainSystem.Action.cs#L234)。

PropertyChangeAop.OnPropertyChangedEvent仅在InitSuccess时继续，还过滤before/after为null、空字符串、Equals相等、XYZ点相等，以及缺少TreeProgramListArgsAttribute.ShowText的属性。随后读取对象Name、当前用户名并构造ParameterChangeLogEntity入队。因此null/空值转换等并不完整记录，也不能把此路径当作所有属性变更审计。[37–104](../../trunk/AKRS.ZX2200/Infrastructure/AOP/Module/PropertyChangeAop.cs#L37)。

MethodAopAttribute.OnEntry只处理两个参数及特定UI事件类型；工具栏按钮先检查角色，权限不足设置FlowBehavior.Return并返回，未进入后面的点击日志。其他分支记录树选项、列表或按钮；OnException记录通用界面操作异常。日志发生于进入方法，不证明操作已成功，OnExit为空；实际哪些方法被织入仍需验证。[27–113](../../trunk/AKRS.ZX2200/Infrastructure/AOP/Module/MethodAopAttribute.cs#L27)。

Machine.SetState在状态变化时先写内存MachineState，再Add参数日志。队列满时可能出现内存状态已经更新但调用仍阻塞；不是数据库提交成功后才切换状态。[52–68](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.StateRelated.cs#L52)。

## 退出与保存次序

窗口FormClosing仅在IsStop时允许关闭；否则Cancel并提示先停止。FormClosed调用ExitSoftware。其他入口也可直接调用ExitSoftware，例如激光干涉尺检查中人工选择退出，故不能把窗口IsStop检查概括为所有退出入口的统一前置条件。[窗口278–298](../../trunk/AKRS.ZX2200/Main/Controls/MainForm.cs#L278)；[其他入口359–407](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Sustain.cs#L359)。

ExitSoftware显示进度→DataSave→按配置关闭加热器→非离线时CloseAllHardware→关闭进度窗→Environment.Exit(0)。内层硬件关闭和外层均有空catch，最后仍退出；未见退出前统计/存图队列CompleteAdding、消费者Join或排空等待。不把“保存数据中”文字等同于记录全部落库。[706–738](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L706)。

DataSave依序调用供片、贴装、载具/运输、点胶和机器配置/仓库Save，最后设PropertyChangeAop.InitSuccess=true；整个序列共用一个try/catch，若某次Save抛出异常则后续调用不继续，catch记录并弹窗，没有返回失败码。各Save内部可能自行捕获异常，其原子性不能由此方法保证。此序列没有调用统计队列排空；配置保存与数据库日志保存必须分开画。[352–413](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs#L352)。

## 未完成与交接测试

- 继续验证AOP编译织入、事件绑定、参数注解覆盖和运行权限分支；本轮只证明方法体逻辑。
- 覆盖数据库断连时报警窗口返回、队列满时状态/按钮阻塞、null/空属性变化未记录、退出时待保存记录等场景。
- 追踪各仓库Save的异常吞噬/覆盖规则，以及所有退出入口、硬件关闭和线程终止语义。
- 本轮没有关闭程序、连接数据库、执行硬件动作或修改生产代码。
