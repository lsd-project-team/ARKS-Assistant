# 原 S1 点胶动作的 Abort/Fail、外层早退与 finally 刷新

本轮在两轮全新 Framework CLR 宿主运行六个模式，12个宿主全部 exit0。每轮120次断言执行、34个不同标签；direct/single-stop/single-toggle/predispense-stop/refresh-null/refresh-throw 分别18/23/22/19/19/19。每轮实际原 S1 Start 创建5个 LongRunning 任务，3个 RanToCompletion、2个预期 Faulted；另外直接调用原具体点胶动作2次，返回 Abort 和 Fail。26个原方法 IL、12个原源码文件哈希冻结，没有提供虚假动作返回值。

## 原输入与测试边界

实际原 S1/Transport/SDK 构造器和注册动作不变。公开配置一个 bp、一个启用 step，EpoxyNameApplicationName=unreached-return-fixture、DefectName=Null，原排序会注入真实点胶消息。该胶型名字故意在返回门之后才访问，本轮没有创建胶型或验证其可用性。原 UpdateTransportUnit 建立 carrier/substrate/module/bp 四个实体，EntityState=Process、IsProduct=true；视觉/测高通过公开属性预置完成，身份配置 OnForSearch。

真实 Machine Working/OffLineWork，SDK硬件空、safeDoor=false、Belt。原 Repository.Add 保存实际未示教 Dispenser 并按名字解析，预点胶 Mode/Timing 都 Off；原 PreDispenseAction 在 IsDispense=false 分支返回 Success，没有物理挤胶、预点胶、报警/UI或图形插补。普通模式的公开预点胶 WorkStop 回调调用原 Machine.Stop；单步模式的公开动作 WorkStart 打开 IsSingleStepWork，主观察线程执行原 Stop 或显式清除这个公开标志，作为明确测试同步条件。

原 UcMainSystem.ReFreshSystem1TuAction 初始自然 null。除 refresh-null 外，公开槽位赋予仅记录次数的 observer；refresh-throw 的同一公开委托显式抛出测试异常。未构造原 UI 控件或把 observer 当成真实刷新实现。没有私有写、替换动作/任务/Signal/单例/SDK或生产源码修改。

direct 模式用原 Init/InjectSteps/GetNext/FinishCurrent 选中实际点胶节点，但不调用已跳过节点的 DoWork，不能算身份动作执行；仅其余5个真实任务各执行4个原身份动作，共20次/轮。direct 第二次 DoWork 明确绕过外层 IsDoWork 检查，因为第一次离线执行已把步骤标完成；这不是对正常调度重做规则的验证。一个 direct 测试线程已 Join，所有原任务均终止。

## 原返回与状态事实

|模式|实际原路径|观察到的结果|
|---|---|---|
|direct|原 Signal.WaitSingleStep 在单步模式关闭时 false，原 Domain.WaitSingleStep 绕过该等待而 true；随后实际点胶进入单步等待，原 Stop 关闭模式；第二次直接执行中预点胶回调 Stop|原具体动作返回 Abort，随后返回 Fail；两次 finally/nodeStop/公开刷新 observer 都执行。离线步骤 true，原 IsDoWork 随后 false|
|single-stop|原真实任务进入点胶，离线步骤先 true，原 SDK 单步等待100ms仍阻塞；原 Machine.Stop 清除单步模式且不 Set 事件|原等待下一次轮询 false，动作 Abort，原任务 nonSuccess 路径正常返回、设备 Stop，无预点胶|
|single-toggle|同上，但观察线程仅公开清除 IsSingleStepWork，未先调用 Stop|原等待 false/动作 Abort，外层原任务自行执行安全位置分支与 Stop，再正常返回|
|predispense-stop|未启用单步；实际 Off/Off 预点胶成功，在其公开 WorkStop 调用原 Stop；随后原 Signal.WaitStart false|原动作 Fail，外层真实任务正常返回，设备 Stop|
|refresh-null|与上述相同的 Fail 路径，但原公开 UI 刷新槽位自然未赋值|原 finally 在未检查 null 的委托 Invoke 处抛出真实 NullReferenceException，真实 Task Faulted，没有将 Fail 交回任务循环|
|refresh-throw|Fail 路径后原 finally 调用公开刷新槽位，测试委托抛出同一异常实例|原 Task Faulted，Aggregate 内同一注入异常；不是自然现场刷新故障|

三个正常早退与两个 finally 故障均保留前12条已完成消息、当前未完成的 S1DispenseActionNode；原最后 Finish 没有执行，AllowDispenseTransferToBondSignal 始终 ReSet。与上一轮分段交互 Wait=false 仍 Success 后走正常循环退出并 Finish 的行为不同，本轮是实际原点胶的 nonSuccess 早退路径。失败前四个身份动作都已执行，离线 RemainingS1Steps[step] 却是 true，原 IsDoWork 会跳过该步骤；这只是原 OffLineWork 提前提交，不是实物点胶完成。IsFirstDispense 观察仍 true，未到成功路径的末尾修改。

WorkStop 与预点胶 WorkStop 都实际观察到步骤已 true。原点胶先提交离线步骤再等待单步；single-stop 的 finishedBefore/finishedAfter 都12，事件 ReSet，没有预点胶。停止能释放该等待的原因是 Machine.Stop 清除单步标志，不能称作 SDK 单步方法直接检查 Machine.Stop，也不代表任何等待都能停止。

## 源码和 IL

原 S1DispenseActionNode.cs:64 的 S1FinishedStep 位于 WaitSingleStep:68 之前；等待 false 在70返回 Abort。原预点胶 nonSuccess 会返回 Alarm，但本轮没有运行该分支，实际预点胶始终原 Success；随后 Signal.WaitStart false 在84返回 Fail。图形取得、坐标计算、插补、统计刷新以及成功末尾均未到达。

原 Signal.cs:175 的 WaitSingleStep 只检查 IsSingleStepWork、Sleep5、WaitOne(recycleTime)，没有 WaitStart/IsStop 调用。原 System1Domain.cs:534 在模式关闭时直接 true，在已经进入 SDK 等待后模式变关闭则得到 false。原 Machine.Operate.cs:359 把该标志置 false。本轮证据包含直接返回、已经阻塞的线程、实际原任务早退与相同 IL，未推断所有事件竞争时序。

原 S1DispenseActionNode.cs:169 的 get_ReFreshSystem1TuAction → callvirt Action.Invoke 在 finally 中，没有 null 检查；原 IL IL_037a getter / IL_037f Invoke 位于 Finally handler 863–903，已在 Catch handler 792–863 之外。原 catch 因而不处理自然 null 或测试刷新异常。节点 Stop/WorkStop 先执行，原 Task 外层 DoWork 无 catch，异常成为 Faulted；这里设备已经由预点胶回调 Stop，不是 Working 状态下的故障。

原 DispenseWorkTask.cs:151 判断 Retry 后 continue，155–161 的 nonSuccess 执行 MoveToSafePos、Machine.Stop、return，早于 FinishCurrent:165、BondRelease 和 Finish。安全移动在 OffLineWork 的真实早退分支不驱动轴。本轮实际 Abort/Fail 的正常任务结果支持该原路径；Retry 分支仅静态捕获，actualRetryReturnExecuted=false，不以实际动作成功或外层非Success替代 Retry 验收。

~~~mermaid
flowchart TD
  A[原启用离线 S1 / 前12条完成] --> B[原具体点胶 / 离线 step=true]
  B --> C[原Domain单步门]
  C -->|已进入SDK等待后关闭模式| D[原动作 Abort]
  C -->|未启用单步| E[原Off/Off预点胶 Success]
  E --> F[公开回调原Stop / 原WaitStart false]
  F --> G[原动作待返回 Fail]
  D --> H[原finally / nodeStop / WorkStop]
  G --> H
  H --> I{原公开刷新委托}
  I -->|明确observer成功| J[原外层 nonSuccess / MoveSafe / Stop / return]
  J --> K[保留前12条 / 当前消息未完成 / 无BondRelease]
  I -->|自然null 或 测试throw| L[异常从finally传播 / 原Task Faulted]
  L --> K
~~~

该补充图与主阅读器8章节/89节点/101边分开记录；主阅读器及正式1328/旧40专题3817保持冻结，没有声称这些原运行观察已提升全部模块完成状态。

## 复核和后续

每个宿主实际加载16个 bound/replay 保真资源程序集，runtime-map172项，162编译引用中10个直接原源码程序集引用。两次成功编译的 Probe SHA 相同；两轮 result 与标签严格一致，完整stdout含独立路径、日志和时间，不声明其字节相同。本轮没有失败编译或失败宿主；两个预期 Faulted 是原任务结果，宿主准确验证后 exit0。

父分段交互/输入门/保真资源验证在有退出守卫的同一流水线51051/e20a09通过；未为三个子验证虚构独立工具会话。父5383+新增117=5500冻结绑定；数量不是业务覆盖率。原测试源码、宿主、输出、IL、12源码、审计/报告/进度有哈希或基线，未重写旧冻结记录。

继续原胶量检测 Retry 的真实结果处理与重做调度、预点胶真实配置失败/下层、S2安全/清零/补偿/UI前提、真实输送握手及生产退出。在线 IO/轴、相机 VM、SQL、LC/Fody、完整原 MSBuild/部署仍未验收，16工程/29组/1436文件/13项整体目标未完成。

见[测试](native-s1-return-gates-test.json)、[审计](native-s1-return-gates-audit.json)、[进度](native-s1-return-gates-progress.json)。
