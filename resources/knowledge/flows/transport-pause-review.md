# 固晶放行下游：输送暂停与状态提交

日期：2026-09-29。32项受控检查通过。执行完整原TransferBondToWaitingUnload方法（TransportController.cs:1531–1810）及完整原Signal.cs、MachineEnum.cs；真实Thread、Task与事件句柄，运行时见测试回执。不是整个TransportController、外层TransportTask或产品.NET Framework宿主。

## 暂停时序决定入口行为

- 已进入真实Signal.Wait内部轮询后，将测试状态存储改为Pause并发送放行事件：方法继续调用固晶气缸、挡料气缸、固晶皮带与等待段皮带替身；随后转移材料对象、刷新并调用Save替身。所有记录的动作及保存调用均发生在Pause。
- 进入Wait前已经Pause，即使事件预先置位，也没有动作调用；显式恢复Working后完成。
- 等待中保持Stop且不发送事件，Wait返回false，方法返回Abort，没有硬件替身调用。这里直接修改测试状态，不等同于执行原Machine.Stop全部副作用。
- 在Wait已成功返回后的日志观察点将状态改为Pause或Stop，方法仍完成动作、状态转移与Save；此方法后续路径没有再次调用状态门控。不是对原Stop停轴效果的实验。

以上与S2 SendAway收尾在Pause仍发信号的结果构成相邻链路证据，但本轮直接发送同类真实事件，没有把两个完整生产任务同时运行，不能声称生产并发频率或竞态覆盖。

## 入口、异常与材料提交

固晶区无料或等待段有料均返回NoStart，不读取机器状态或调用硬件。直接调用isManual=true时绕过信号，即使测试状态Stop仍完成；结尾再次UnClamp，共两次。上层手动按钮及其禁用状态未在本轮验证。

原方法内部Task.Run/Task.WaitAll保持真实执行。UnClamp替身异常后，另一气缸任务仍执行，但皮带不启动；异常转换为Exception并调用日志及提示。皮带异常和Save异常同样返回Exception；方法本身没有把测试机器状态改为Stop。Save失败前材料对象与状态已经转移，不会由catch回滚。外层TransportTask会处理返回结果，不能从本轮断言系统最终仍Working。

固晶出口未感应到料的卡料分支选择Abort时，不调用Save，保留原材料对象与Alarm传送状态；Retry、Ignore及第二段卡料路径未覆盖。

## 测试边界

MachineStateModel为volatile测试状态存储。传感器、气缸、运动控制、对话框、日志、TransportProgram、材料对象刷新与Save均为替身；没有读写生产配方，没有连接运动板卡。传感器序列固定为正常通过，另有一例出口卡料。检查证明原方法的调用顺序和内存赋值，不证明实体皮带在安全门打开后运行，也不证明配置已落盘。

下一步应接入原外层输送任务的返回值处理和原机器停止链，检查下层控制器及驱动是否另有门控，并验证空跑消费者和供晶要料等待。29组仍部分复核，完整构建、原生UI、生产并发与真实设备验收未完成。

运行：node scripts/test-transport-pause.cjs。来源审计：node scripts/build-transport-pause-audit.cjs --check。

观测修正（2026-09-30）：并发Set/Wait路径不再把公开State当作事件句柄。原Signal.Set先唤醒事件再写元数据，原Wait随后也写State，两个线程存在写入顺序竞争；测试在任务到达相应阶段后检查真实AutoReset事件已消费。保留原断言数量与原生产方法，不改变现场代码或设备验收范围。
