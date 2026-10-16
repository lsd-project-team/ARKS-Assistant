# 停止与恢复对料仓任务的实际影响

2026-09-28。限定静态复核；结合[料仓握手](loader-unloader-handshake-source-review.md)、[输送控制器](bin-transfer-controller-source-review.md)和[停止清理专题](stop-cleanup-review.md)。本轮没有运行设备，也没有以代码状态代替物理安全验证。

## 入口事实

- Pause只SetState(Pause)。Continue未配置安全门时直接设Working；配置门且未关闭则弹窗，不恢复；门关闭时设置两个IsFirstDispense=true再设Working。Continue本身没有创建料仓Task或重新启动控制器。
- Stop先SetState(Stop)，投递清窗，设置停止报警状态，退出单步，复位Bond需料；Online模式关要料，关顶针真空，清焊后缺陷计数。方法里没有料仓皮带/推杆的StopMove、取消Token、Task.Wait或Join。下层硬件是否存在其他联锁不能由这段代码排除。
- EmergencyStop先对仓库中所有Axis并行调用StopMove(false,true)，返回后才调用Stop及三个Abort包装。该入口无finally保证后续步骤；任一前段调用抛错可能使后续未执行。没有专门终止料仓Task或局部后台缩回Task。
- IsAllowTaskClosed每次重建WorkTasks，包含料仓输送和上下料Task，但只拒绝Status==Running。它不是逐一确认终态，也不Wait；局部movePushRodHomeTask未被此列表登记。启动准备据此可能拒绝重新Start，但Continue不调用该检查。

证据：[Pause/Continue/Stop](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L314)、[EmergencyStop](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L383)、[任务检查](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs#L201)、[启动前拒绝](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L198)。

## 按执行位置分析

|执行位置|代码响应|不能作出的保证 / 需验证时序|
|---|---|---|
|料仓任务while(IsWorking)边界|Working以外直接退出循环|若恰在Pause时到达边界，Continue不会重建该Task；是否发生需时序验证|
|Signal.WaitStart|Stop返回false；Pause轮询等待|并发状态切换仍有窗口，不能当锁或取消令牌|
|Signal.Wait事件循环|检查Stop后WaitOne；事件成功返回true|未重新检查Pause；Stop在检查后发生且事件同时满足时，返回前没有第二次Stop检查|
|上料入口while(true)|传感器有料break；推杆到位无料则报警|无本地Stop/Pause；状态改变不能单独让该循环退出|
|上料后台缩回Task|到位则缩回；未到位且计时超过10秒break|无Stop/Pause；轮询退出限时不覆盖阻塞中的轴调用；局部Task未纳入退出清单|
|下料皮带while(IsMoving)|运动变false退出；传感器变false也退出|轴被急停导致Moving=false后，后续逻辑并没有统一Stop门控|
|下料采样变量初值false且未进循环|进入后续else推杆段|若急停在该窗口导致Moving=false，代码上存在继续执行推杆调用的路径；驱动是否允许动作未知|
|下料最后采样值true后轴停止|进入卡料对话框|不是自动Abort；是否已有对话框被清除和后续对话框登记时序不同|
|Wait返回false或控制器返回Abort|任务返回；Abort分支先调用Machine.Stop|并不等待局部后台Task全部结束|
|任务已结束后Continue|仅改Working|不会重新执行LoaderTask.Start/UnloaderTask.Start|

这些是条件路径分析，不是已复现故障。尤其不能因为急停停止了某轴，就断言代码里的所有循环、后续命令和后台Task都已结束。

## 清窗不是同步取消所有报警

ClearMessageBox遍历当前msgBoxDict，对每个窗体BeginInvoke：Hide、DialogResult=Abort、Dispose；随即Clear字典。没有等待UI回调全部执行，也未获取Show使用的UiLock。Show在非线程ID1路径持UiLock调用Alarm；Alarm登记窗口、ShowDialog、移除窗口、更新报警状态、记录DBService.Insert后返回dr。MainForm.SendUiAction绑定PostAction，后者使用Invoke。

因此当前已登记且成功执行关闭回调的对话框，可能促使对应分支收到Abort；但Clear后才登记或尚在锁外等待的报警不由此前遍历覆盖。不能将一次ClearMessageBox解释为永久取消以后所有报警；UI执行失败、字典并发和数据库写入异常仍需隔离测试。Alarm内没有因此恢复Working的语句。

证据：[清窗](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/AKRSMessageBoxExt.cs#L42)、[Show与Alarm](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/AKRSMessageBoxExt.cs#L136)、[MainForm调度](../../trunk/AKRS.ZX2200/Main/Controls/MainForm.cs#L50)。

## 工程师后续验收清单

- 在可控假轴/假传感器环境分别暂停于循环边界、WaitStart、WaitOne，检查Continue后任务实例和状态。
- 停止时固定上料入口无料、推杆不到位，确认上层轮询以及记录中的Running是否持续；禁止直接在生产设备上注入此故障。
- 下料在启动皮带后、首次IsMoving读取前置停止反馈，记录是否发出后续推杆命令以及驱动层拒绝/接受条件。
- 控制上料末端Retry/Ignore/Abort与旧后台缩回Task重叠，检查重启门控能否发现仍存活的局部Task。
- 将报警注册置于Clear前后两侧，确认Abort返回、DB日志及字典生命周期，不把GUI恢复当作硬件停止验收。
- 下一源码重点：Axis.StopMove/命令门控的实际可用实现与配置、层位移动下层及持久化恢复；外部缺源码时明确停在边界。
