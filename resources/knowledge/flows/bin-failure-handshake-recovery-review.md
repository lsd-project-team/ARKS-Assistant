# 料仓任务异常后：四信号握手、等待和恢复边界

更新：2026-09-28。范围：LoaderBin上下料自动工作与输送任务之间四个具名信号；不代表全工程全部信号或实机状态验收。

## 正常交互顺序

|信号|模式/初值/轮询|源码发送者|消费者与复位|
|---|---|---|---|
|LoaderAllowPushSignal|ManualReset / false / 100ms|LoaderTask首次当前层就位后，以及后续移动返回后Set|上料输送Wait；控制器非NoStart/Abort/Exception分支后显式ReSet|
|AllowLoaderMoveSignal|AutoReset / false / 100ms|上料输送复位允许推料后Set|LoaderTask.Wait后移动到下一层；正常等待消费自动复位|
|UnloaderAllowPushSignal|ManualReset / false / 100ms|UnloaderTask首次和后续当前层移动返回后Set|下料输送Wait；控制器返回路径经过200ms延时后显式ReSet|
|AllowUnloaderMoveSignal|AutoReset / false / 100ms|下料输送复位允许推料后Set|UnloaderTask.Wait后移动当前层；正常等待消费自动复位|

上下料Worker的Abort返回分支先Stop并return；其他未处理枚举值不能统称Success。上料输送Success另发TransferToDispense1FinishedSignal并清PrepareFeeding；None也进入复位/允许移动，NoStart延时500ms后continue，不复位ManualReset信号。下料NoStart也延时后continue，Abort/Exception停止返回；非这些分支经过200ms再复位/发允许移动。见binwait-loader-consumer、binwait-unloader-consumer及binmissing-*-worker。

## 缺失配置异常如何影响握手

前一专题已证实：有料盒路径中配置为空会在LayerNum访问抛异常，LoaderTask/UnloaderTask本地catch仅提示。首次移动异常会跳过本次允许推料Set。如果输送任务已到该Wait、信号未被置位、设备状态没有被其他来源停止，那么该等待没有本地整体期限，可持续轮询。不能据此断言所有并行任务均已停止，或设备必然处于某个实际状态。

反方向同样存在局部退出：输送委托try内异常catch也仅提示；若异常发生在ReSet/允许移动Set之前，这轮握手可能留在不同状态。仅凭catch无法确定信号最终值，必须对应具体抛异常语句。信号操作本身也可能抛异常，不假定一定成功。

## Wait与暂停/停止的精确语义

- 无参Wait先WaitStart；false立即退出。然后循环：检查Stop，Sleep(5)，WaitOne(recycleTime)；未取到信号就重试，没有累计超时。100ms是单次WaitOne期限，不是100ms后任务失败。
- Pause只由入口WaitStart处理；一旦进入事件轮询，循环只检查Stop，不再次检查Pause。因此不能声称Wait内部在任何时刻都会阻断暂停后的事件消费。
- 观察到Stop时返回false，上下料输送及料仓Worker相应if返回。Stop检查与WaitOne之间、WaitOne成功与方法返回之间并非原子区间，不能保证瞬间Stop绝不伴随一次成功返回。
- AutoReset成功等待后还将State属性写ReSet；ManualReset消费不自动复位，需显式ReSet。事件与State字段不是同一原子写入；UI状态标签不等价于完整同步证明。

## Stop、Continue、重新Start

|操作|本范围内的实际行为|边界|
|---|---|---|
|Stop|先SetState(Stop)，随后清弹窗等；本方法不显式复位这四个料仓信号|等待靠观察Stop退出；不是join所有任务，也不保证所有动作已结束|
|Continue|门条件通过后SetState(Working)，特定分支设置首胶标志|不重建料仓/输送任务，不重新Set这四信号；不能作为已退出Worker的恢复保证|
|重新Start准备|CleanFile后ResetMachineSignal，包含四信号ReSet；然后总复位与IsAllowTaskClosed检查|拒绝启动也可能已清信号；不能把“启动被拒绝”等同无副作用|
|IsAllowTaskClosed|登记上下料Worker及两输送任务等，任一Task.Status==Running就false|只比较Running，不是逐个确认终态；无法由此保证无并发或已成功恢复|

因异常退出的生产者不再发信号、消费者仍Running时，直接再次Start可能被任务关闭检查拒绝；Continue也不会创建新的生产者。这里说明源码可达条件，不给出未经设备验证的操作规程。

## 交接缺口

- [ ] 在隔离环境注入生产者/消费者失败，记录四事件状态、Task状态与MachineState时间线。
- [ ] 验证Stop与Continue/Start重设Working的并发窗口，特别是已有任务尚未观察Stop时。
- [ ] 补全其他输送段、供晶、固晶的失败后等待传播，不能以本四信号替代全局结论。
- [ ] 第三方DLL、反射、别名持有信号的行为不由具名文本扫描证明。

## 本次具名引用清单

扫描trunk内1436个C#文件，排除bin/obj/.git；发现20行直接包含四个名称。清单包括声明，不是动态调用图。

- [trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs:74](../../trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs#L74)：public Signal AllowLoaderMoveSignal { get; set; } = new Signal("允许上料信号", 100, EventResetMode.AutoReset, false);
- [trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs:79](../../trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs#L79)：public Signal LoaderAllowPushSignal { get; set; } = new Signal("上料仓允许推料信号", 100, EventResetMode.ManualReset, false);
- [trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs:119](../../trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs#L119)：public Signal AllowUnloaderMoveSignal { get; set; } = new Signal("允许下料信号", 100, EventResetMode.AutoReset, false);
- [trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs:124](../../trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs#L124)：public Signal UnloaderAllowPushSignal { get; set; } = new Signal("下料仓允许推料信号", 100, EventResetMode.ManualReset, false);
- [trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:149](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L149)：SignalPool.GetInstance().AllowUnloaderMoveSignal.ReSet();
- [trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:150](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L150)：SignalPool.GetInstance().AllowLoaderMoveSignal.ReSet();
- [trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:151](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L151)：SignalPool.GetInstance().LoaderAllowPushSignal.ReSet();
- [trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:152](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L152)：SignalPool.GetInstance().UnloaderAllowPushSignal.ReSet();
- [trunk/AKRS.ZX2200/TransportSystem/Tasks/LoaderTask.cs:93](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/LoaderTask.cs#L93)：SignalPool.GetInstance().LoaderAllowPushSignal.Set();
- [trunk/AKRS.ZX2200/TransportSystem/Tasks/LoaderTask.cs:99](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/LoaderTask.cs#L99)：if (!SignalPool.GetInstance().AllowLoaderMoveSignal.Wait())
- [trunk/AKRS.ZX2200/TransportSystem/Tasks/LoaderTask.cs:119](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/LoaderTask.cs#L119)：SignalPool.GetInstance().LoaderAllowPushSignal.Set();
- [trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:375](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L375)：if (!SignalPool.GetInstance().LoaderAllowPushSignal.Wait())
- [trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:412](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L412)：SignalPool.GetInstance().LoaderAllowPushSignal.ReSet();
- [trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:415](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L415)：SignalPool.GetInstance().AllowLoaderMoveSignal.Set();
- [trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:677](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L677)：if (!SignalPool.GetInstance().UnloaderAllowPushSignal.Wait())
- [trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:706](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L706)：SignalPool.GetInstance().UnloaderAllowPushSignal.ReSet();
- [trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:709](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L709)：SignalPool.GetInstance().AllowUnloaderMoveSignal.Set();
- [trunk/AKRS.ZX2200/TransportSystem/Tasks/UnloaderTask.cs:92](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/UnloaderTask.cs#L92)：SignalPool.GetInstance().UnloaderAllowPushSignal.Set();
- [trunk/AKRS.ZX2200/TransportSystem/Tasks/UnloaderTask.cs:97](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/UnloaderTask.cs#L97)：if (!SignalPool.GetInstance().AllowUnloaderMoveSignal.Wait())
- [trunk/AKRS.ZX2200/TransportSystem/Tasks/UnloaderTask.cs:117](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/UnloaderTask.cs#L117)：SignalPool.GetInstance().UnloaderAllowPushSignal.Set();

## 绑定源码快照

- [binwait-loader-def 69–79](../../trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs#L69) · [阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binwait-loader-def)
- [binwait-unloader-def 116–124](../../trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs#L116) · [阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binwait-unloader-def)
- [binwait-wait 116–145](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L116) · [阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binwait-wait)
- [binwait-loader-consumer 314–424](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L314) · [阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binwait-loader-consumer)
- [binwait-unloader-consumer 664–718](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L664) · [阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binwait-unloader-consumer)
- [binwait-reset 133–163](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L133) · [阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binwait-reset)
- [binwait-stop 347–378](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L347) · [阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binwait-stop)
- [binwait-continue 323–342](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L323) · [阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binwait-continue)
- [binwait-taskclosed 201–262](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs#L201) · [阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binwait-taskclosed)
- 关联已有证据：binmissing-loader-worker、binmissing-unloader-worker、taskgate-wait、startgate-prepare。

## 交互图与验收

[Archify正常/异常握手时序图](bin-failure-handshake-sequence.html) · [可编辑规格](bin-failure-handshake-sequence.archify.json)。两段为条件场景；不是保证发生的实机连续轨迹。9/9 showcase、0错误/0警告；Edge四桌面尺寸自动检查通过；已查看1440浅/深和2048浅色截图，无明显遮挡。规格/产物哈希和独立视觉记录见bin-failure-handshake-sequence.review.json。
