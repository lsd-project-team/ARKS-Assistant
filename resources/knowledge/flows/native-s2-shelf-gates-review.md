# 原S2吸嘴架前提、单步门及送走信号

两个全新 Framework CLR 宿主各58个不同断言通过，31个原方法IL、13源码哈希、16保真资源源程序集。父5661+新增56=5717冻结绑定。本轮执行原公开控制器/模块和绑定真实任务receiver的私有SendAway；没有启动S2生产Task。

## 实际原吸嘴架与硬件前提

完整原S2/Transport/SDK构造器、空硬件仓库/缺原硬件文件、Machine OffLineWork/Stop、safeDoor=false/Belt；实际NozzleShelf/Repository.Add公开建立12槽模型。原ToolBankCoordinateSystem和AxisY均自然null，没有替换SDK、动作或写私有消息。配置名字和模式仅为明确测试fixture。

原System2Domain.WaitSingleStep在单步关闭时直接true，即使Stop。原Controller.MoveShelfToHome/NoWait继续进入原模块，实际缺AxisY抛NullReference；模块没有OffLine/Stop短路。原换吸嘴位置缺坐标系先抛错；原GetYAxisPos、IsAtHome、IsShelfAtChangePos先访问缺轴。不能据这些故障说完成真实归零或到位。

原传感器slot -1/0/13返回false；1至12分别实际访问对应缺失Sensor并原NullReference。原IsNozzleShelfEmpty在第一槽就故障。enabled=false的CheckToolBankConfiguration原true，甚至模型缺失；enabled=true缺模型先null，空名字读取Sensor再决定是否报警。本轮Sensor读取即抛错，未进入报警UI/SQL。

实际12槽前6槽填非空但未注册吸嘴的测试名字，原检查跳过这些Sensor并在第7空槽读取失败；前7槽全部非空时直接true，其余5槽仍空，也没有真实Sensor/吸嘴就绪验证。原检查明确写死前7槽；公开把数组改为6槽且6个非空名字，则索引第7槽时越界。恢复真实12槽后，在后面槽配置TouchDown/BMC，原OffLine TouchDown=false、Compensate模式按实际名字匹配true；这只是名义在库判定，不代表物理工具存在/可用。

原BondModuleController.MoveToSafePos/MoveToChangeNozzleSafePos的OffLine分支直接return，不访问轴。原S2 cylinder close配置禁用直接return；启用则访问缺输入Sensor，先于输出/等待/报警抛错。本轮未发送任何硬件命令。

## 三个原单步等待

每轮3个fixture线程实际调用同一原Controller.MoveShelfToHome，进入单步等待后保持阻塞；线程全部Join，未仿造信号/等待或替换线程实现。

|公开释放前提|原结果|观察状态|
|---|---|---|
|原Machine.Stop|原Abort，不进入模块|Stop / singleStep=false / 信号ReSet|
|公开关闭singleStep模式|原Abort，不进入模块|Working / singleStep=false / 信号ReSet|
|原单步Signal.Set|原等待消费后进入缺轴模块并NullReference|Working / singleStep仍true / 信号ReSet|

Stop/Disable分支不凭空提供Abort，由原Signal.WaitSingleStep false产生；Set分支不能用缺轴故障代替实际移动成功。每个分支最后用原OffLine Stop收尾，没有后台fixture线程遗留。

## 原SendAway与两个Wait重载

原私有SendAway直接绑定实际BondTask receiver，不创建生产Task。IsTransportConfigured=true下，Stop不发信号，Working发AllowBondTransferToWaitingUnloadSignal；Pause同样发，因为方法只检查IsStop。后续真实输送任务并未执行，不能推断已移动载具或完整生产握手。

原无参Wait消费底层AutoReset事件并把公开State重置。原Wait(int)只消费底层事件，公开State保持Set；再Wait(int)实际false，但State仍Set。这修正了首次验证的错误假设，不代表重复实物生产。IL还显示参数outTime未用于WaitOne，使用实际recycleTime；本轮不以时钟计时声称精确超时长度。Pause期间由SendAway产生的事件在Continue后用原无参Wait消费；未配置输送且Stop时SendAway不保存mapping/弹窗。

## 原任务静态入口与尚未运行的清零

原BondTask.DoWork先ResetInformation，再WaitStart、MoveShelfToHome、MoveToSafePos、ResetBondhead、取得component、来料门、UI/三种补偿。原IL在MoveShelfToHome和ResetBondhead调用后立即pop，任务未检查这两个返回值。前一轮完整S2任务在缺吸嘴架AxisY处Faulted的证据保持；本轮单步Abort是直接控制器调用，不能声称已经让完整任务通过该前提。

原ResetBondhead在OffLine下也没有模式短路：Modbus配置走真实Modbus，其他配置写实际清零输出；捕获后原MessageBoxExt.Show→Alarm→DBService.Insert会直接SQL。即使只收集UI委托，SQL仍执行。本轮只读取这些原源码与IL，没有调用ResetBondhead、Modbus、报警、SQL/真实UI，也没有以硬件或方法替身绕过该前提。清零成功、忽略/Abort/Retry、补偿及完整S2工作/退出链仍需真实前提和后续核验。

~~~mermaid
flowchart TD
  A[原S2控制器 / 单步门] --> B{单步等待释放}
  B -->|Stop或关闭模式| C[原Abort / 未进模块]
  B -->|Set| D[原模块 / 缺AxisY异常]
  E[原12槽公开模型] --> F[原配置检查固定前7槽]
  F --> G[非空名字跳过Sensor / 可返回true]
  H[原SendAway直接绑定] --> I{IsStop}
  I -->|是| J[无放行]
  I -->|否 / 含Pause| K[真实放行Signal.Set]
  K --> L[无参Wait重置State / timed Wait保留State]
  M[完整BondTask / 静态] -.回零与清零返回pop.-> A
~~~

## 失败保存与验收范围

首次编译成功，原CLR51检查后因错误预期Wait(int)重置State而exit1，primary原目录及Cases/Probe/compile副本均保留。第二版和独立重编译在两个全新accepted目录各58固定断言通过；emit SHA相同，结果/标签严格一致，不宣称完整stdout字节相同。最初26方法IL也保留，最终31方法增加原Wait重载与报警等只读证据。父预点胶/保真资源在guarded流水线18986/1968ac通过；冻结验证cf6b40无session。

162引用含10个直接原源码程序集引用，runtime-map172项。公开12槽名字/数组/模式是测试配置，单步等待与送走helper为直接入口，整原任务未启动。生产C#/工程未改，无私有写、SDK/动作替身、物理轴/工具/贴片、清零、相机、真实UI、SQL、完整原MSBuild或部署。正式1328/旧40专题3817/主阅读器保持冻结；继续完整S2清零/补偿/输入/UI/退出前提、整Retry传播与工程设备验收，16工程/29组/1436文件/13项整体目标未完成。

见[测试](native-s2-shelf-gates-test.json)、[审计](native-s2-shelf-gates-audit.json)、[进度](native-s2-shelf-gates-progress.json)。
