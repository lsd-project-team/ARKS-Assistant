# 原 S1/S2 来料等待、预点胶门与 S2 入口故障

本轮直接绑定原完整任务对象上的私有GetInputSignal/GetIncomingSignal方法，没有复制实现。两个独立Framework CLR宿主分别加载原16个bound/replay保真资源程序集，逐轮54个不同断言通过，31个原方法IL只读留存。另实际启动原S2 LongRunning任务，两轮各Enable=true/false的2个任务都在来料方法之前因真实缺失吸嘴架AxisY而Faulted。宿主进程2次exit0表示预期观察被验证，不表示4个原S2任务生产成功。

## 原输入与限制

Application.StartupPath自然指向每个专属宿主目录，硬件配置文件缺席，真实SDK仓库为空，没有替身硬件。原DispenserRepository.Add保存真实未示教Dispenser，原DispenserProgram.Dispenser通过配置名字Find该对象。预点胶Mode/Timing都Off，原PreDispenseAction.DoWork在IsDispense=false分支返回Success；未运行IsAlarm弹窗、挤胶、插补、图像检测或真实预点胶。公开回调用于记录、精确Pause和故障注入；一个WorkStart故障用例公开置IsManual=true但在try之前抛出，没有进入手动点胶分支。

私有方法以绑定真实receiver的Func<bool>原委托直接调用，5个等待线程是明确的fixture线程；正常用例全部Join完成。不是原S1在线Start/DoWork的成功执行：该主路径前置安全移动仍依赖真实轴。S2配置来料Wait方法也直接调用，不能用它的成功覆盖本轮实际原S2任务在更早吸嘴架运动位置的故障。无私有写、动作/Signal/Task/单例/SDK替换，无UI控制构造、SQL和设备运行；Enable=false也不是外层硬件步骤的开关。

## 来料消费结果

|原路径|实际观察|范围|
|---|---|---|
|S1初始Stop|先调用原预点胶1次，随后false；预点胶节点Stop|当前只测Off/Off无物理动作|
|S1 Working+Set|原预点胶1次→State=ReSet→true；随后原Signal.Wait仍可消费同一底层事件|证明状态/事件分离，未证明实物重复生产|
|S1 Pause+Set→Continue|暂停期间不调用预点胶、不消费State；Continue后调用1次并返回true|100ms有界阻塞观察|
|S1 Pause+Set→Stop|停止释放后仍调用预点胶1次，返回false，State和事件仍Set|Stop检查位于预点胶之后|
|S1未Set轮询|真实预点胶连续3次，在第3次WorkStop调用原Pause；Stop后第4次预点胶再返回false|次数由公开fixture回调同步，不推断无限或现场频率|
|S1非法SignalState值|预点胶1次后抛出原“点胶入料载台来料信号异常”|公开999值是明确故障注入|
|S2配置流道+Set|原Signal.Wait同时消费AutoReset事件和State；第二次有界事件等待false|原两个信号定义均AutoReset，周期100ms|
|S2配置流道Pause→Continue/Stop|Pause不消费已Set事件；Continue返回true且消费；Stop返回false且保留事件|Signal.Wait在WaitStart后另有Stop检查|
|S2 CompensateWork私有门|设备Stop时仍直接true，不消费配置流道事件|只证明该helper，原整任务仍有外层WaitStart|
|S2未配置流道+已有实际TU|设备Stop时私有门仍true、不弹窗|实际UpdateTransportUnit建立对象，不证明整任务越过Stop|

S1调用Signal.set_State，没有调用Signal.ReSet；IL与实际Wait二次消费一致。当前源码检索中的S1消费者是State轮询，输送任务调用Set，Machine启动路径显式ReSet。因此这里记录的是SDK公开状态与底层事件不一致，不能把辅助原Wait消费直接改称生产重复来料/重复实物。未测试第二消费者在现场出现、并发信号丢失或所有调度时序。

原S1输入门没有catch：WorkStart的同一异常实例直接传播，并绕过finally的IsManual=false清理；WorkStop异常发生在原finally已经置节点Stop和IsManual=false之后，仍传播。未用虚假Action返回Abort/Retry/Exception去冒充原预点胶失败，本轮nonSuccessPreDispenseReturnBranchExecuted=false；这些真实返回失败、配置报警/UI和物理动作仍待验收。

## 实际 S2 Working 入口和停止故障

原BondTask.Start在Working创建真正LongRunning任务。Enable=true和false都先调用NozzleShelfController.MoveShelfToHome→NozzleShelfModule.MoveShelfToHome→实际缺失AxisY.AbsoluteMove，出现原NullReferenceException。两个任务均保留三层原栈，Task.AggregateException内只有该原异常。原ResetInformation已把预置UpLookAutoSkipCount=7改0、IsBondArriveSearchPos=true改false；来料信号仍Set、设备仍Working。再次Start替换前一个Faulted任务，第二个仍在同一前置动作失败。原DoWork没有catch，未到来料、UI刷新、补偿、InjectSteps或实际固晶动作；离线模式未屏蔽吸嘴架这一实际Axis调用。fixture观察后原Stop清理，不能说进程最终状态Working。

在独立CompensateWork门用例中，原Machine.Stop先把状态改Stop，随后EjectController.CloseEjectionTableVacuum→WaferSubController.ResetCyc遇到实际缺失输出而NullReferenceException。ResetCyc只在OffLineWork返回，CompensateWork不属于该模式；原缺失输出/状态先提交事实被实际捕获，没有替换硬件或直接伪造此异常。最初用例把这个Stop当作必成功，宿主已完成38断言后真实exit1；原失败完整保存，修正为明确断言此实际原边界，之后继续验证私有来料门。原Machine Stop其他模式/生产设备退出仍非整体完成。

## 已执行和静态关系

~~~mermaid
flowchart TD
  A[直接绑定原 S1 GetInputSignal] --> B[Pause时Sleep并continue]
  B -->|离开Pause| C[原PreDispenseAction / Off-Off返回Success]
  C --> D{原Machine IsStop}
  D -->|是| E[false / 保留来料状态与事件]
  D -->|否且Signal State Set| F[仅State ReSet / true]
  F --> G[底层AutoReset事件仍可被原Wait消费]
  H[直接绑定原 S2 GetIncomingSignal] --> I[配置流道 / 原Signal.Wait]
  I -->|Continue| J[消费事件和State / true]
  I -->|Stop| K[不消费 / false]
  L[实际原S2 Start Working] --> M[ResetInformation]
  M --> N[原吸嘴架控制器 / 模组 / AxisY调用]
  N --> O[真实缺失Axis / Task Faulted / 设备Working]
  O -.->|未到达| H
~~~

图将直接方法验证与真实任务入口区分；未到达的边不代表本轮执行成功。31方法IL、19个原源码文件哈希、实际source16物理位置以及两轮result/标签一致性冻结；不声称完整stdout JSON字节一致，隔离路径和原日志时间仍保留。

## 失败保留与下一步

宿主编译v1因只读IsCompensateWork误赋值和多变量var失败；改用真实MachineWorkMode=CompensateWork驱动getter。v2因System2Module命名空间遗漏失败。成功前误启动过0字节无效输出，系统EFTYPE/childExit=null，未创建CLR进程，不能算一次原生业务失败；保留该目录并给runner加成功编译守卫。v3成功后原Compensate Stop异常使首个CLR宿主真实exit1/38已过；对应原Probe/输入/日志留存。v4和重编译两次成功emit字节一致，两个全新accepted目录各54检查通过。没有删改旧失败、旧源码/资源/阅读器或原编译器。

父5200冻结绑定验收通过，本轮新增72累计5272。断言54独立于正式1328；新绑定数不是业务覆盖率。整体16工程/29组/1436文件/13项仍未完成。下一步原S1分段交互Wait/Retry与返回故障、预点胶真实配置失败和下层；S2前置安全/压力清零/补偿及UI刷新前提，真实任务动作和生产退出仍待验收。在线IO/轴、相机VM、SQL、LC/Fody和完整原MSBuild/部署保留未完成范围。

见[测试](native-task-input-gates-test.json)、[审计](native-task-input-gates-audit.json)、[进度](native-task-input-gates-progress.json)。
