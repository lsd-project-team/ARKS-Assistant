# 原S2补偿计算、触发前提与Modbus离线边界

两个全新 Framework CLR accepted宿主各51个不同断言通过，31原方法IL、14源码哈希、16保真资源源程序集。父5717+新增53=5770冻结绑定。实际执行原补偿公开入口与绑定真实receiver的私有插值，以及原下层Modbus方法，没有复制算法/类型或启动完整生产任务。

## 原Modbus连接和清零

完整原S2/SDK构造器，Machine OffLineWork/Stop，硬件仓库空，safeDoor=false/Belt/slideFluxer未配置。原ModbusService.ConnectBondhead/ConnectManometer在OffLine分支直接true，实际两个私有客户端仍null（仅反射读取）。因此不能把连接返回true说成已连接设备。

直接原ResetBondhead/ResetManometer各一次，没有OffLine短路：首次访问自然null进入catch，原Thread.Sleep(50)后再次访问null并抛原NullReference；没有实际寄存器写或串口。原ReadBondForce/ReadManometer以及两个Disconnect亦自然null异常。故障均有实际原方法栈、没有客户端/硬件替身或私有写，DB Lazy始终未创建。

这里执行的是下层ModbusService.ResetBondhead，不是外层BondHeadController.ResetBondhead。外层捕获后会进入原MessageBoxExt.Show/Alarm和直接DBService.Insert；只收集UI委托并不能避免SQL。因此外层清零、实际压力清零、报警选择和完整S2清零传播本轮未执行，原IL证据单独保存。原Task对其bool返回的忽略仍是静态结论。

## 原触发与真实视觉前提

配置禁用时，原PickUpCompensationVision和System2TemperatureCompensation在first=true仍true，保留已有补偿与时间；禁用的getter返回零。启用后明确公开设置Last时间为Now-60分钟、间隔10，first=false原门不进入视觉且时间保持；Now-11分钟原门进入。原IL两者调用TimeSpan.Minutes，没有TotalMinutes，结论限定这两种公开时间fixture，不是等待了60分钟的实验。

first=true绕过取片间隔；直接TpMarkCompensate.TemperatureCompensation没有启用/周期守卫。上述入口和启用第一点实时扫描合计6次实际进入原BondModule.GetHardware，空硬件下自然NullReference，均先于运动、灯光Task、相机算法和持久化。原System2CommonVision即使DryCycle也先解析硬件，再走默认MatchResult分支；本轮在硬件解析处故障，没有执行DryCycle视觉成功。

原System2TemperatureCompensation在调用下层TemperatureCompensation后立即pop其bool，并最后true，原IL已核验。真实下层视觉null返回false的路径本轮未到达，不能声称已在完整任务证明这个false被忽略。

## 两类温漂getter边界

公开真实SDK Point2D作为明确数值fixture，非相机测量。启用且数据null返回零；精确±0.2允许，取片直接符号、温漂取相反符号。温漂0.200001先原Xtra提示后抛Exception，取片0.200001只原Xtra提示后仍返回原输入，没有夹限。NaN通过原Abs比较并继续输出NaN，不新增提示。

公开MainForm.SendUiAction只收集两个原Action，递归只读提取真实警告文本，没有执行委托/构造窗口。实际DBService Lazy保持未创建；这属于原Xtra路径，不覆盖MessageBoxExt的SQL报警。

## 原实时补偿与四点计算

实际RealTimeCorrection singleton在宿主缺配置文件下，ReferencePoints/ReferencePointsCompensate为null、IsAssistanted=false。禁用Scan(first=true)和四个null输入计算均直接成功/零；启用Scan(first=false)仍true，既不读null数组也不更新私有LastTime。first=true读取null数组故障；公开设一个真实Point3D后进入原视觉工厂故障。LastTime只反射读取，没有写，配置JSON没有保存。

原GetCompensatePoint3D依次检查输入null、数组null、IsAssistanted；内部catch只throw new Exception(ex.Message)，实际原异常类型和InnerException丢失。短compensated数组与空数组没有额外就绪检查，分别发生索引/Max空序列故障，再被同样包装。这些是公开无效配置负分支，不代表有效实测标定。

公开原SDK数组(0,0,0)、(10,0,0)、(20,0,0)及测试补偿点(0,0,0)、(10.2,0.4,9)、(20,0,0)，绑定原GetCompensatePosByPoint：X5/Y999/Z-999按X权重返回(0.1,0.2,4.5)，说明查找/权重不使用caller Y/Z；X25用最后两个点外推，返回(-0.1,-0.2,-4.5)，未拒绝大于最大X；小于最小X拒绝。

实际原公开四点输入X5/10/15/19，先做(取片补偿-取片视觉补偿)-(贴片补偿-焊后视觉补偿)，返回约(-0.18,0,0)，明确丢弃计算出的Y/Z。单点精确0.5偏移允许，0.500001抛ArgumentNullException；组合偏移大于0.5而各点仍合规时，公开入口直接返回零。这几种行为是当前原实现，不是本轮修复或物理误差容限验收。

Scan first=false只有first门，不按配置时间自动重扫。first=true的空数组可绕过视觉循环进入Save/LastTime及FileHelper.CreateFileByDate，静态上目录硬编码D盘再按配方日期导出Excel；本轮没有执行空数组首扫、JSON保存、D盘导出或真实模板/相机。已有FileHelper/Scan原IL与源码哈希用于后续持久化验收，未以关闭导出或替换路径伪造成功。

~~~mermaid
flowchart TD
 A[原Modbus Offline Connect] --> B[true / clients仍null]
 B --> C[原Reset / catch后再访问 / NullReference]
 D[原温漂与取片门] --> E[Minutes分量 / first绕过]
 E --> F[原GetHardware / 6次自然故障]
 G[原实时Scan] --> H{first}
 H -->|否| I[true / 不重扫]
 H -->|是| F
 J[原SDK公开数值fixture] --> K[原四点差值]
 K --> L[单点超限抛错 / 组合超限零 / 只返回X]
~~~

## 证据与剩余

第一版宿主50断言均通过，但summary错误写死工厂失败5，保留诊断目录与Cases/Probe/compile。第二版用实际异常栈计数6并增加固定断言，两轮各51通过，原emit SHA相同、结果与标签严格相同，不宣称全stdout字节一致。诊断版50不加入accepted51或覆盖计数。父原吸嘴架/保真资源在99748/884010流水线通过，冻结后验证d9d795无session。

162编译引用含10直接源码引用，runtime-map172项。没有生产C#/工程修改、私有状态写、SDK/动作/算法替身、外层焊头清零、串口IO、物理力控/轴/贴片、真实视觉/UI、SQL、完整原MSBuild或部署。正式1328/旧40专题3817/主阅读器保持冻结。继续完整S2清零故障与任务传播、补偿成功所需真实前提、整Retry和生产握手退出、构建设备验收；16工程/29组/1436文件/13项整体目标未完成。

见[测试](native-s2-compensation-prerequisites-test.json)、[审计](native-s2-compensation-prerequisites-audit.json)、[进度](native-s2-compensation-prerequisites-progress.json)。
