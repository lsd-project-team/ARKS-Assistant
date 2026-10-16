# 原完整S2任务的单步退出、清零故障与UI分派传播

两个全新 Framework CLR 宿主各70个不同断言通过；每轮实际启动8个原LongRunning S2任务，4个预期Faulted、4个在Stop下正常完成。原任务确实执行，不再只靠直接helper或静态IL；范围限清零前提和故障退出，没有完成生产循环。18原IL、14源码哈希、16保真源程序集，父5770+新增44=5814冻结绑定。

## 原任务和明确测试配置

完整原S2/Transport/SDK构造器、空硬件仓库/原硬件文件缺失；Machine OffLineWork、safeDoor=false、Belt、配置输送、未配刮胶盘。真实AxisY与焊头压力清零Electric均null，Modbus客户端自然null，没有注入私有状态/消息、替换原节点、任务、单例、SDK或返回值。公开ForceZeroMode、Enable、单步模式、实际Signal以及UI委托为明确fixture。

四个组合分别是Modbus/Enable=true和IO/Enable=false，各搭配原Stop或公开关闭单步；不是所有Enable×模式组合的完整矩阵。输入原TransferToBondFinishedSignal.Set，放行/单步信号ReSet。首次原Start产生真实LongRunning任务，原ResetInformation把公开计数19清到0、IsBondArriveSearchPos清false；任务保持Running、120ms等待未完成，未进入报警回调。结合首个原单步守卫及后续原栈，观察限定在第一个吸嘴架单步等待。

在此期间再次原Start保持相同Running任务；原AbortThread空方法不改变等待、单步标志或回调计数。没有用AbortThread实现终止或声称取消了任务。

## 单步退出后原清零仍发生

原Machine.Stop关闭singleStep；公开关闭模式也让原Signal.WaitSingleStep false，原NozzleShelfController返回Abort，未访问缺AxisY。原BondTask调用后立即pop返回值，没有据Abort结束当前循环。OffLine MoveToSafePos直接return，随后仍执行原BondHeadController.ResetBondhead。Stop是在已经进入循环后的等待中发生，本轮两个Stop组合实际在设备已Stop时到达清零报警，不只是静态猜测。

Modbus配置调用原ModbusService.ResetBondhead，实际自然null客户端首次失败、内部catch/50ms后再次null，外层原清零捕获。IO配置在首次原BondHeadForceResetZeroElectric.SetOutputValue(true)遇自然null，未发送输出，也未走后续30ms/false输出。两个原下层故障分别以真实NullReference栈写入清零失败文本，再进入原LogHelper.Post和MessageBoxExt.Show→Alarm。

## 公开UI故障与原Task传播

测试公开MainForm.SendUiAction收集原Action，递归只读提取infoText/标题，然后throw同一个本模式InvalidOperationException。没有执行收集Action、构造窗口、假装人工选择或返回DialogResult。原Alarm在这个委托之后才设置handle字段并直接DBService.Insert；委托throw中断在SQL之前，实际DBService Lazy始终未创建。这不是只收集委托后正常返回的SQL路径验收。

当前原Task没有catch/finally接住这个分派异常，Task Faulted，InnerException与测试注入异常同一对象，栈保留原Alarm、Show、ResetBondhead、BondTask.DoWork。原下层清零NullReference已被外层捕获，在收集文本中保存；实际Task Faulted的直接原因是明确公开UI故障，不能写成未捕获清零NullReference自然使Task Faulted。

|原组合|故障观察设备状态|输入/输出State|原Task|
|---|---|---|---|
|关闭单步 / Modbus / Enable=true|Working|Set / ReSet|公开UI故障，Faulted|
|原Stop / Modbus / Enable=true|Stop|Set / ReSet|公开UI故障，Faulted|
|关闭单步 / IO / Enable=false|Working|Set / ReSet|公开UI故障，Faulted|
|原Stop / IO / Enable=false|Stop|Set / ReSet|公开UI故障，Faulted|

每次只收集1个原UI Action。原来料helper尚未执行，输入State保持Set、未放行，单步信号State ReSet；没有将这些状态等同实物载具或完整握手。原Enable的判断在这些入口调用之后，所以本轮Enable=false的两个IO模式同样进入清零；不代表关闭所有子任务/设备。

## 原任务恢复入口与Stop退出

每个预期Faulted任务之后调用原OffLine Stop收尾，再调用原Start：它接受Stop下启动，替换先前Faulted任务为新LongRunning任务。新任务执行ResetInformation后在最外WaitStart Stop守卫退出，RanToCompletion；没有新增清零UI或消费输入/放行。每轮总8个实际新任务全部终态，4Faulted/4正常，12次Start包括4次保持相同Running任务。

这个正常完成只是Stop守卫退出，不是恢复生产成功。原清零bool的DialogResult Retry/Ignore/Abort映射、外层递归返回丢弃、SQL/UI正常完成，以及清零成功后输入/补偿/调度/退出仍未执行。本轮也未对原生产源码修复忽略Abort行为。

~~~mermaid
flowchart TD
 A[原S2 Start / LongRunning / Working] --> B[原运行字段Reset]
 B --> C[原吸嘴架单步等待]
 C -->|原Stop或公开关闭模式| D[原Abort]
 D --> E[任务丢弃返回 / 原OffLine安全位短路]
 E --> F[原清零 / Modbus或IO自然null]
 F --> G[外层捕获 / 原Alarm]
 G --> H[公开UI fixture抛同实例 / SQL之前]
 H --> I[原Task Faulted / 输入保留 / 未放行]
 I --> J[原Stop / 原Start重建]
 J --> K[原WaitStart停止守卫 / 正常完成]
~~~

## 验证及剩余

首次编译/原生70检查通过，独立重编译及全新replay宿主再次70通过，emit SHA相同、结果/固定标签严格相同，不声明完整stdout字节一致。两轮各16源程序集物理bound/replay加载，162引用中10直接源引用，runtime-map172项。父补偿/保真资源47448/c578de流水线通过，冻结验证1bf846无session；没有为子命令虚构独立会话。

没有生产C#/工程修改、私有写、SDK/动作/返回替身、物理压力清零、寄存器/串口IO、轴/贴片、真实相机/UI、SQL、完整原MSBuild或部署。原任务入口已执行，successfulProductionCycleExecuted=false；正式1328/旧40专题3817/主阅读器保持冻结。继续原S2清零结果正常返回及真实依赖、输入/补偿/完整动作和退出，整Retry/完整输送握手、构建设备验收；16工程/29组/1436文件/13项整体目标未完成。

见[测试](native-s2-reset-propagation-test.json)、[审计](native-s2-reset-propagation-audit.json)、[进度](native-s2-reset-propagation-progress.json)。
