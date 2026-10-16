# 授权与后台监控：源码复核

更新：2026-09-28。范围：启动授权、授权辅助进程、设备后台循环、保存线程及退出边界。静态源码复核，不代表硬件或授权系统运行验收；不是全工程完成声明。证据快照登记在 module-review-evidence.json，auth-* 标识对应下列方法。

## 简明工作步骤

1. ZX2200 的 Program.Main 按 IsDetectingEncryption 配置决定是否调用 CheckYtSoftKey；失败释放互斥后返回。检查成功后又调用 InitSoftKey、读取日期和用户信息。该重复初始化会进入释放旧连接和重建辅助进程路径，不能当成纯读取。见 [启动门禁](../../trunk/AKRS.ZX2200/Program.cs#L138)。
2. CheckYtSoftKey 顺序执行初始化、取授权日期、取用户号；任一步返回失败则结束。非永久授权打开模态窗口；返回 Cancel 则失败。窗口按本机 DateTime.Now 显示日期，过期时禁用确认按钮；确认设 OK，取消事件只关闭窗口。关闭结果依赖 WinForms/UIForm 行为，未运行验证。见 [授权检查](../../trunk/AKRS.Galaxy.SoftKey/AKRS.Galaxy.SoftKey/SoftkeyManager.cs#L20)、[授权窗口](../../trunk/AKRS.Galaxy.SoftKey/AKRS.Galaxy.SoftKey/FormSoftKey.cs#L16)。
3. 连接创建时处理同名 AuthenticatorBG_x86 进程，启动新的辅助程序并传入共享结果标识和 6000ms 更新间隔，启动独立读取线程。调用方每10ms检查首次读取和错误状态；没有独立的总超时参数。见 [连接启动](../../trunk/AKRS.Galaxy.SoftKey/AKRS.Galaxy.SoftKey/SoftkeyManager.cs#L233)。
4. 读取线程通过外部 Authenticator API 获取用户号、期限和最近检查时间。成功后约6000ms再读；用户号为0在第10次检测时设 Nokey 并退出，前9次间隔10ms；读取异常累计到第10次设 ConnectError 并退出，前9次间隔1000ms；日期转换异常直接设 TimeError 并退出。异常计数没有在成功后清零，不能描述为“连续10次异常”。见 [读取循环](../../trunk/AKRS.Galaxy.SoftKey/AKRS.Galaxy.SoftKey/SoftkeyManager.cs#L282)。
5. 主窗体 Load 的就绪条件通过后启动设备后台线程。它与授权读取线程独立；不是生产启动，也不是授权刷新调用。后台循环按顺序检查安全门、激光尺、登录超时、温度、耗材、传感器，然后确保存图和数据库线程启动，最后 Sleep(100)。每轮实际时间还包含所有检查及交互等待，不是固定100ms调度。见 [主窗体加载](../../trunk/AKRS.ZX2200/Main/Controls/MainForm.cs#L232)、[后台循环](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L662)。
6. 关闭主窗体前要求机器处于 Stop；关闭后调用 ExitSoftware，尝试保存数据、关闭配置的加热及非离线硬件，最终 Environment.Exit(0)。没有在该路径显式等待图片/数据库队列清空或调用 ReleaseSoftKey。见 [窗体关闭](../../trunk/AKRS.ZX2200/Main/Controls/MainForm.cs#L280)、[退出](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L706)。

## 模块与调用关系

|链路|实际调用 / 输出|失败与边界|
|---|---|---|
|SoftKey 独立程序|Program.Main → CheckYtSoftKey，结果保存在局部变量|未根据结果分派后续业务；不能混同 ZX2200 主入口。见 [独立入口](../../trunk/AKRS.Galaxy.SoftKey/AKRS.Galaxy.SoftKey/Program.cs#L12)|
|初始化|InitSoftKey → Release旧连接 → CreateSoftkeyProcess|创建失败日志及弹窗后false；捕获初始化异常后false。Release 使用 Abort/Join 与进程终止，无超时参数。见 [初始化](../../trunk/AKRS.Galaxy.SoftKey/AKRS.Galaxy.SoftKey/SoftkeyManager.cs#L65)、[释放](../../trunk/AKRS.Galaxy.SoftKey/AKRS.Galaxy.SoftKey/SoftkeyManager.cs#L339)|
|授权数据|GetUserId读取连接缓存；GetDateDue读取期限，默认DateTime视为永久|GetDateDue本身总返回true，未检查读取线程错误状态；不能据此证明持续授权健康。LastTime属性getter引用自身，是静态递归风险，未证明存在调用。见 [缓存读取](../../trunk/AKRS.Galaxy.SoftKey/AKRS.Galaxy.SoftKey/SoftkeyManager.cs#L104)、[LastTime](../../trunk/AKRS.Galaxy.SoftKey/AKRS.Galaxy.SoftKey/SoftkeyManager.cs#L228)|
|安全门|配置开启且工作中、门未关 → Pause|自动继续逻辑被注释。见 [安全门](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Sustain.cs#L276)|
|激光尺外层|StartLaserEncoderCheckTask → LaserEncoderCheck，false → Stop|方法末 Task.Delay(100) 未await，不能当成阻塞延迟；底层各检查另行复核。见 [激光尺入口](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Sustain.cs#L310)|
|登录超时|满足配置、用户角色和空闲时长条件 → 清CurrentLoginUser并提示|是账户退出，不是生产Stop。见 [AutoLogOut](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L640)|
|温度|配置加热、工作中、加热开启且Alarm → Stop并提示；到温后记录时间和预热标志|预热比较使用TimeSpan.Minutes分量，不是TotalMinutes；长时行为待验证。见 [温度监控](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L449)|
|耗材|BackgroundConsumable → ScanConsumables；到期弹窗Ignore继续，Abort → Stop和Clear|弹窗“10分钟后提醒”为文本；具体提醒判定依赖耗材实现，未据文本推断定时器。见 [耗材扫描](../../trunk/AKRS.ZX2200/SupportFeature/Consumables/ConsumablesProgram.cs#L64)|
|传感器|StartScan直接调用ScanSensor；离线返回；工作中、未配置输送、有工作单元且真空失败 → Stop和报警|通用sensor循环内报警被注释；StartScan自身未创建线程。见 [传感器](../../trunk/AKRS.ZX2200/SupportFeature/SensorCheckScan/NeedScanSensorPool.cs#L36)|
|图片保存|StartSaveThread → 后台Thread → SaveBitmap → BlockingCollection.Take → Save(Bmp) → Dispose|无限循环、阻塞取队列，无局部catch或取消/排空协议。见 [图片消费者](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L326)|
|数据库保存|StartSaveThread → 后台Thread → SaveEntityToDb → Take → 按类型DBService.Insert|参数变更实体需SugarTable属性；未匹配类型没有写入分支；无局部catch/重试。见 [数据库消费者](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L97)|

## 退出、异常和外部依赖

- 后台总循环没有包围整轮的catch；不能保证任何检查抛异常后仍执行后续检查，也不能仅凭IsAlive检查承诺异常自动恢复。保存线程同样不能据此宣称可靠重试或不丢数据。
- RuntimeProvider.ThreadFlag 是循环条件；BaseMachine.ExitApp 将其置false并设置Stop/IsExitApp。对 trunk 的 C# 文本搜索仅发现该方法定义，未找到直接调用；反射或外部调用未排除。实际窗体退出链不能自动等同于调用ExitApp。见 [ExitApp](../../trunk/AKRS.Galaxy2.Machine/BaseMachine.cs#L160)。
- ExitSoftware 的硬件关闭异常和外层异常被吞掉，之后仍退出。若DataSave抛异常，后面的加热/硬件关闭会被跳过；退出码0不代表保存和硬件关闭全部成功。
- 生产准备方法中的授权检查块被注释，不是正在执行的门禁。见 [准备检查](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L185)。授权线程报错如何传递至运行中设备，不在上述后台循环中实现，待查外部实现/现场机制。
- 项目声明依赖Authenticator.dll、USL3.dll和UI库；辅助程序及Authenticator接口的内部行为不应根据调用名称臆造。见 [项目依赖](../../trunk/AKRS.Galaxy.SoftKey/AKRS.Galaxy.SoftKey/AKRS.Galaxy.SoftKey.csproj)。本轮未启动辅助程序、访问加密锁或操作设备。

## 进度与下一验收项

- 已完成本专题的限定范围源码摘要、代表关系、输入输出与失败路径登记；SoftKey组从待复核转为部分复核。
- 未完成：外部授权组件源码/契约、窗口关闭结果实测、线程故障的进程级处理、保存队列生产者全覆盖、DBService事务与持久性、全部后台检查下层和设备退出实测。
- 图形同步：新增[后台监控与退出交互图](background-lifecycle-workflow.html)，节点/关系证据见 background-lifecycle-workflow-evidence.json。该图仅覆盖设备后台与退出外层，不代表授权内部或全部业务已图形化。9项结构检查与4种桌面尺寸浏览器检查通过；已查看1440×900浅色截图，画面留白较多，尚未完成全门户视觉验收。
