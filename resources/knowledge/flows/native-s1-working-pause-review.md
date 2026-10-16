# 原 S1 启用任务的 Working、Pause 与回调异常

完整原 DispenseWorkTask.Start/DoWork 已在保真源码资源程序集上运行，而非仅在 Stop 入口返回。两轮分别使用 bound/replay 的16源码程序集，在8个独立应用目录执行4种用例，进程均exit0。每轮70次断言执行、29个不同标签；不计入正式1328，不能称70个不同业务行为。29个原方法的只读IL与原源码哈希一并保存。整体16工程/29组/1436文件/13项仍未完成。

## 本轮输入和边界

真实SDK硬件仓库为空，MachineWorkMode=OffLineWork，安全门未配置，加载配置为Belt。公开产品/步骤配置和原stage.UpdateTransportUnit建立一载具、一基板、一基岛、一焊点，IsProduct=true防止原循环替换该树。四层Identity配置开启，S1步骤无点胶/检测应用但仍注入S1RemainingSteps的未完成step。公开BaseInfo预置视觉和其他测高完成，载具测高未完成而MeasureHeightInSystem1=false：真实载具测高动作走原禁用配置Success分支，未执行测量硬件。四层原Identity.DoWork走离线分支，提交实际对象的IsIdentity。

所有节点仍来自原DispenseActionNodes注册集合，原任务自己Init/GetNext/Finish，没有替换ActionNode/Signal/Task/queue/单例或私有写入。公开WorkStart/WorkStop回调用于观察、同步暂停与明确异常注入，这是本轮fixture边界，不能称自然现场故障。原Machine.Pause/Continue/Stop实际执行；构造原UI/Program.Main、预点胶来料等待、在线视觉/点胶/测量/轴、S2、SQL和设备退出未执行。只读私有WorkMessages供断言使用。

## 实际结果

|用例|每轮检查|原Task结果|故障发生时/退出时设备状态|关键观察|
|---|---:|---|---|---|
|Pause→Continue→Stop|20|RanToCompletion|Stop|Pause阻塞下一身份动作；Continue执行四层身份动作，原AllowDispenseTransferToBondSignal.Set可见|
|Pause→Stop|20|RanToCompletion|Stop|下一载具身份动作仍在Stop状态执行1次；后续Stop检查退出，未发送放行|
|Identity.WorkStart抛出|15|Faulted|Working|同一异常实例进入Task.AggregateException；身份未提交、WorkStop未调用、未进入Running|
|Identity.WorkStop抛出|15|Faulted|Working|身份已提交、节点Stop，但当前消息未完成；异常进入Task.AggregateException|

暂停由载具测高WorkStop调用原Machine.Pause触发。观察到原任务完成第2个消息后在下一Signal.WaitStart睡眠，100ms有界等待未完成且Identity调用为0、放行信号Reset。此时再次Start保留同一Running任务。Pause→Stop两轮均观察到Identity.WorkStart:Stop及WorkStop:Stop，随后原Finish清空当前选择并重置消息Finished。此结论对应该同步释放时序，不宣称每次任意时刻Stop必然再运行一次动作，也不从离线身份标记推出真实轴运动。

正常继续两轮均观察到四层Identity调用各1次和放行Set，随后观察者调用原Stop收尾。原循环在观察者Stop前已进入第二轮载具测高回调，原始trace完整保留；本轮没有“恰好一个完整循环”的断言。步骤没有点胶/检测应用，S1RemainingSteps[step]仍false，故不能把身份完成/发送放行称为实际点胶制程完成。禁用测高分支未置IsMeasureHeight，这是重复回调的原行为，未改写源逻辑。

两个回调故障均使前两个消息保持Finished、载具Identity消息未Finished且仍为当前选择，原任务没有执行末尾Finish。设备状态在故障观察时仍Working，放行Reset；fixture随后调用原Stop清理，不能说测试进程最终设备仍Working。工作开始回调在节点try前，工作结束回调在finally内；节点对算法异常的catch不能兜住这两种回调异常。任务外层和Start lambda没有catch或finally停机，实际Task Faulted不会自动调用其ret!=Success分支的Machine.Stop。

## 原因与限定流程

原Signal.WaitStart先检查Stop，再在Pause循环体检查Stop并Sleep(20)。如果睡眠期间Pause变成Stop，循环条件仅比较Pause，跳出后直接return true；没有退出循环后的Stop检查。原DoWork把此返回当成下一动作准入，未再检查Stop，因而该窗口可执行一个原动作。IL保留了具体分支和20ms调用；两个独立宿主上的原任务验证把此前SDK门的单独现象推进到实际业务任务。

~~~mermaid
flowchart TD
  A[原 Start 创建 LongRunning Task] --> B[原 Init / InjectSteps / 工作调度]
  B --> C[载具测高禁用配置返回 Success]
  C --> D[原 WorkStop 调用 Machine.Pause]
  D --> E[下一个 Signal.WaitStart 在 Pause 睡眠]
  E -->|Continue| F[四层原离线身份动作]
  F --> G[原放行信号 Set]
  E -->|Sleep期间 Stop| H[WaitStart 返回 true]
  H --> I[一个原载具身份动作在 Stop 下运行]
  I --> J[下一等待返回 false / 不放行 / Finish]
  B --> K[原身份动作回调异常]
  K --> L[Task Faulted / 设备仍 Working / 当前消息未完成]
~~~

图中同步、状态变化和故障回调均来自上述fixture；不把图推广为全自动生产/在线设备流程。

## 构建、失败保留与下一步

新宿主两次成功emit的字节SHA相同，162元数据引用含10个直接源码引用，均迁入新bound资源产物；运行映射172项加载16源码程序集，replay明确使用replay物理文件。4种result和标签两轮逐项相同；完整stdout还含隔离根/程序集路径/时间日志，未声称完整原JSON字节相同。29原IL方法包括原任务和Start lambda、四Identity门/动作、载具测高、调度、Machine状态方法、Signal及统计周期。

准备阶段错误地期待16个直接源码引用，实际是10个；此守卫失败16ce34/exit1保留原脚本。两次宿主编译因ActionNodeMessage命名空间遗漏失败（97fc92、e4fc12/exit1），输入版本及完整诊断保留；其声明虽在Infrastructure目录，实际namespace是Services。修正宿主using后成功，不修改生产源码或原编译器。原父5113绑定验证通过，本轮新增87累计5200绑定；绑定数不是业务覆盖率。

后续继续S1非离线GetInputSignal/预点胶、Retry与返回错误路径、分段交互等待，以及S2真实Working/来料/放行和动作异常边界；各在线下层、安全门/设备、SQL/完整构建部署仍待验收。本文记录原有边界，不修复生产逻辑。见[测试](native-s1-working-pause-test.json)、[审计](native-s1-working-pause-audit.json)、[进度](native-s1-working-pause-progress.json)。原阅读器和40专题3817/正式1328保持冻结。
