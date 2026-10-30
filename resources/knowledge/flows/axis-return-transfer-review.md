# 轴相对命令：初始化切面与上层忽略返回值

日期：2026-09-29。84项受控运行断言通过，另12项只读二进制契约检查通过。两类证据不能合并为驱动执行覆盖率。

## 运行验证：返回值与抛异常不同

沿用完整原输送、夹爪、Machine.Stop/状态/报警、两个皮带控制器及模块转发方法，共9个原方法；完整原Signal与MachineEnum文件参与编译。轴终端替身现使用与随仓库DLL一致的ExcuteResult SendRelativeMoveCommand(double,double)签名，结果枚举13个成员的名称和值由二进制检查逐项核对。旧测试的void轴替身只证明调用发生，本专项补齐返回结果契约。

24组返回场景：两段轴分别返回Success、NoStart、Fail、Exception、ParaError、Abort；分别在Working和原夹爪报警执行原Stop后的Stop状态测试。原模块SendRelativeMoveCommandBelt返回void且不检查轴返回值。所有24组在固定正常传感器序列下，父输送仍返回Success、尝试两段轴调用、转移材料对象并调用Save替身；没有由这些返回码新增的机器状态处理。每组3个断言，共72项。

4组异常场景：两段轴分别在上述两种状态抛出异常。父方法catch返回Exception，不转移材料或调用Save；固晶轴抛出时尚未调用等待段轴，等待段轴抛出时前一段轴已被调用。每组3个断言，共12项。

轴返回码由替身设定，不能认定真实轴会在每种状态下产生全部六类结果；传感器仍模拟完成，所以材料提交结论有该条件。未调用真实Axis DLL、运动SDK或设备，Save不落盘。

## 当前随仓库DLL的只读证据

Mono.Cecil读取三个程序集并绑定SHA-256；完整IL记录在axis-relative-contract-evidence.json。包含两个相对运动重载、两个执行体、JudgeInitAspect.OnEntry和仓库状态属性，共6个方法。

1. 两参数包装在IL_003c–IL_0042把枚举常量3（Success）作为JudgeInitAspect的预设返回值；OnEntry设置短路流行为后，IL_005e–IL_006d读取返回值直接退出，跳过执行体。MovePara重载也具备同类包装。
2. 切面先检查HardwareRepository.IsHardwareOnProductState；为true时直接返回，不做后续初始化判断。该属性自身只是独立bool字段读取，不等于MachineState的Working、Pause或Stop。属性赋值来源及现场取值仍待核实。
3. Axis直接基类为HardwareBase，因此这里走实例IsInit路径；在上述仓库bool为false且IsInit为false时，切面设置预设Success并短路。此处的Success不能证明下发过运动指令。没有把这段IL重新编写成C#并冒充原DLL运行。
4. 两参数执行体构造MovePara、处理速度并委托另一重载。MovePara执行体在参数为空时返回ParaError（8）；防碰撞CanMove拒绝后提示并返回Exception（7）；超软限位路径提示后抛LogicHardwareException。这三种情况不可都解释为抛异常。
5. 正常路径将参数换算后调用返回void的IAxisDrive.SendRelativeMoveCommand，再返回Success。初始化、碰撞、软限位及底层驱动的完整组合尚未端到端执行；不能由选定方法中缺少直接Pause检查就断言实机绕过所有安全联锁。

## 后续

接入外层TransportTask对返回结果的处理；核实IsHardwareOnProductState的设置与实际加载DLL版本；补空跑消费者及供晶要料暂停。完整构建、原生UI、生产并发和设备验收仍未完成，29组继续部分复核。生产源码与设备配置未修改。

运行：node scripts/test-axis-return-transfer.cjs。二进制检查：node scripts/verify-axis-relative-contract.cjs。综合来源审计：node scripts/build-axis-return-transfer-audit.cjs --check。
