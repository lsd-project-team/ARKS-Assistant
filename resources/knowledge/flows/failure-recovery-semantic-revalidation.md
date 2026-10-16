# 暂停、重试、停止与线程边界：源码复核

更新：2026-09-28。范围：S1/S2结果分派、机器暂停/继续/停止/急停、信号等待和所列外围监控。静态源码复核，不是设备安全认证或实机验证。

## 真实流程摘要（绘图前）

1. S1执行动作后，Retry保留未完成消息并重新选择；Success标当前消息完成；其他返回先尝试回安全位再Stop并返回。未执行的IsDoWork=false动作也会标消息完成。
2. S2的Retry重新选消息；Alarm对话框的Retry则直接goto RetryCommand，在同一个actionNode上重试，不重新走循环顶部WaitStart/GetNextActionNode。Ignore落到FinishCurrentActionNode；Abort/Exception调用Stop、抬Z、按配置收胶盘后返回。switch未列出的返回值也会落到标消息完成，不能泛称任何非Success都会停止。
3. 门监控仅在已配置安全门、Working且门未关闭时Pause；关门自动继续的代码是注释。Pause本身只SetState(Pause)。
4. Continue在未配置门时直接Working；配置门且门开只提示；配置门且门关会设置两套IsFirstDispense=true再Working。这里没有创建或重启任务。
5. WaitStart在Pause时轮询，在Stop时返回false；Wait()进入事件等待后主要检查Stop，不每轮重新检查Pause。料仓任务以while(IsWorking)为外层条件，若在Pause时再次判断可退出；之后Continue不能复活已退出的任务。
6. 普通Stop置Stop、清登记弹窗、设置停止报警、关闭单步、复位需晶信号、仅Online配置关闭要料、关闭顶针吹气/真空、清焊后缺陷计数。不是关闭全部输出，也没有统一等待线程退出。
7. 急停先对轴调用StopMove(false,true)，再Stop，然后调用三套Abort方法。Bond与晶圆Abort没有实际终止语句，S1仅Task.Dispose。不能把方法名当作线程已退出的证据；前序异常还可能阻断后序清理。
8. 晶圆任务catch弹窗后Stop；料仓catch仅弹窗。后台编码器检查仅返回false时调用Stop：环境/算法异常和捕获的通讯异常返回false；光强不佳提示分支没有相同的false返回，不能画成所有编码器报警必Stop。

## 源码入口

- [S1结果、启动与Abort：DispenseWorkTask 117–215](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L117)
- [S2结果与局部重试：BondTask 213–325](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L213)；[空Abort 382–384](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L382)
- [机器Pause/Continue/Stop/EmergencyStop 314–402](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L314)
- [信号Wait、Wait(outTime)、WaitStart 116–228](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L116)
- [门监控与编码器 276–421](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Sustain.cs#L276)
- [后台线程顺序 662–700](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L662)
- [上料仓 63–129](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/LoaderTask.cs#L63)；[下料仓 56–127](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/UnloaderTask.cs#L56)
- [晶圆catch 375–385](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L375)；[晶圆Abort 1431–1437](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1431)
- [Stop清理的下层调用与重启边界](stop-cleanup-review.md)

## 当前未完成项

全部等待点、驱动异常的真实返回与硬件退出、所有后台温度/耗材/传感器分支、任务生命周期竞态仍需逐一验收。无设备执行，不以状态字段或图中终点声称设备已安全停止。


## 关系逐条复核

|关系|分类与边界|证据位置|
|---|---|---|
|ret→retry|条件控制流：动作返回Retry，不Finish当前消息|S1 151–154；S2 253–258|
|retry→next|条件控制流：continue回循环顶部WaitStart/GetNextActionNode|S1 117–154；S2 214–258|
|ret→alarm|条件控制流：仅S2的Alarm枚举|BondTask 277–289|
|alarm→next|人工Ignore：break后FinishCurrentActionNode|BondTask 310–319|
|alarm→ret|人工Retry：goto RetryCommand，保留当前actionNode|BondTask 224–232、307–308|
|alarm→stop|人工Abort：Stop，再抬Z、条件收胶盘、返回|BondTask 293–305|
|ret→stop|条件控制流：S1非Retry且非Success；S2 Abort/Exception|S1 151–161；S2 236–275|
|door→pause|门配置/Working/未关时直接Pause，或人工调用Pause|Sustain 276–288；Operate 314–318|
|pause→continue|人工请求，不是自动调用；Continue方法本身不验证原状态为Pause|Operate 323–342|
|continue→running|状态轮询边界：改Working后仍存活任务可从等待继续；非创建线程调用|Operate 323–342；Signal 202–228；料仓循环|
|fault→stop|条件控制流：直接Stop或指定catch/编码器false路径|Operate 347–378；Sustain 310–319、326–421；Wafer 375–385|
|emergency→stop|直接调用链：轴StopMove调用返回后执行Machine.Stop|Operate 383–401|
|stop→exit|状态轮询边界：仅对应检查点可返回false；并非统一退出通知或Join|Signal 116–228；各任务外层循环及Abort方法|

补充的alarm→ret箭头使已有八章关系总数从100变为101；增加的是已确认的局部控制流，不能据此提高全项目业务覆盖声明。

## 输入、输出和等待限制

输入包括动作ExcuteResult、人工DialogResult、MachineState、门配置/门状态、编码器读数、信号事件、载具消息Finished和运行模式。输出包括状态变更、指定电气/轴请求、消息完成/重做标记、弹窗与变更日志队列；不等于全部输出关闭或硬件完成。

Wait(int outTime)的实现没有使用outTime，而是WaitOne(recycleTime)一次；与Wait()循环等待不能混用。WaitSingleStep以IsSingleStepWork为退出条件；Stop将其设false。WaitStart/Wait存在状态切换并发窗口，未做时序运行验证。

StartBackGroundThread以ThreadFlag为循环条件，顺序执行门、编码器、登出、温度、耗材、传感器、图像保存启动、数据库保存启动，尾部Thread.Sleep(100)。StartLaserEncoderCheckTask里的Task.Delay(100)未await，不作为实际轮询周期依据。此处只确认调用顺序，其他后台任务内部异常隔离和阻塞仍需独立审阅。

机器IsWorking仅比较Working枚举；SetState只有状态改变时赋值并将日志加入DbEntityBlockingCollection。[Machine.StateRelated 25–68](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.StateRelated.cs#L25)。日志队列处理与数据库落盘不在本章完成声明。

## 后续应优先验证的静态风险

1. S2 Alarm Retry绕过循环顶部WaitStart；暂停/停止与人工重试并发时，实际动作门控应单独测试。
2. S2未列枚举仍可能标消息完成；应核对各动作返回值协议及质量记录预期。
3. Continue未重建料仓任务，需测Pause落在外层循环条件和事件等待内两种时机。
4. 光强异常提示路径与环境/算法/通讯异常的Stop策略不同；需确认业务要求，不能自动改源码。
5. Stop清理没有统一finally，任务Abort不是退出确认，驱动失败后的设备状态尚未验收。

## 本轮交付核验

Archify九项检查通过，0错误0警告；Edge桌面自动检查通过。初次截图发现重试与停止线重叠，调整报警节点和重试通道后重新deliver与visual-check；最终1440×900浅色截图已目视复核。交付哈希与原始浏览器结果分别见同名delivery.json和browser-check.json，未改写工具visualReview字段。统一门户完整导航与设备运行不在本次展示验收内。
