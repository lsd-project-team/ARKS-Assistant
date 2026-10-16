# 激光状态监控调度与外部硬件关闭边界

更新：2026-09-28。源码静态复核，不运行设备或加载硬件DLL。

## 调度链

MainForm_Load调用StartBackGroundThread。仅当字段为空或线程不存活时创建并启动IsBackground=true的“后台监控线程”。while(RuntimeProvider.ThreadFlag)内串行执行：安全门检查 → 激光检查 → 自动登出 → 温度报警 → 耗材检查 → 信号扫描 → 启动图像保存 → 启动统计保存 → Thread.Sleep(100)。

StartLaserEncoderCheckTask名字含Task，但自身同步调用LaserEncoderCheck；返回false才调用Stop。末尾Task.Delay(100)未await/Wait，不能把它画成阻塞100ms的检查周期。实际循环还受到前后检查耗时及弹窗阻塞影响，非固定100ms独立定时器。外层线程委托没有catch，某一步抛出未处理异常时后续步骤不保证继续。本轮没有验证运行库进程终止策略。

## 检测分支

|条件|方法行为|返回后影响|
|---|---|---|
|硬件对象null或未配置|直接true|该包装器不Stop|
|环境传感器false|提示确认/退出；Abort调用ExitSoftware；若继续返回false|包装器在返回false后Stop，提示前未先Stop|
|算法状态false|同上|同上|
|光强状态不等于3|提示确认/退出；Abort调用ExitSoftware；否则继续尾部true|仅确认后不会由该包装器Stop|
|try内查询等操作抛异常|catch显示通讯异常，提供确认/退出选项，但dialog变量未被使用；返回false|该catch没有调用ExitSoftware；返回后包装器Stop|

GetHardware及缺省配置判断位于try之前，不能把这些位置的异常也归入通讯异常catch。Stop后的后续监控步骤仍可能执行，因为Stop本身不修改这个循环条件。

## 预热不是已接入的启动门控

MachineInitSuccess内LaserEncoderCheck调用被注释。LaserEncoderCheck中GetWarmupStatus分支同样被注释。Machine和BondModuleController各有WaitLaserEncoderWarmupAsync方法：循环等待1秒、超过242秒抛TimeoutException，前者以硬件null放行，后者以配置关闭放行。本轮trunk非bin/obj C#具名搜索只找到这两个声明，未找到调用；不将其绘为当前自动启动必经步骤，也不以文本零命中排除反射或外部调用。

## 退出标志与硬件契约

RuntimeProvider.ThreadFlag是默认true的volatile静态字段。共享BaseMachine.ExitApp会置Stop、ThreadFlag=false及IsExitApp=true；但ZX2200的Machine继承SingletonNoSave，而非BaseMachine，ExitSoftware中没有调用ExitApp。trunk C#具名搜索只找到ExitApp声明，不能借用这个共享类方法证明实际退出已停止后台循环。

ZX2200.ExitSoftware先DataSave，条件关闭加热，非离线调用HardwareRepositoryService.CloseAllHardware，最后Environment.Exit(0)。硬件关闭内层异常被吞；外层保存/加热等异常也被吞且可能跳过后续清理。该函数未先停止/Join后台监控线程。因此清理期间是否仍发生硬件查询是待验证的并发边界，而非本轮已观察到的故障。

当前trunk C#未找到HardwareRepositoryService或LaserEncoder类声明；工程引用AKRS.Galaxy2.LogicHardware，HintPath为libs/AKRS.Galaxy2.LogicHardware.dll，SpecificVersion=False。本地DLL存在，184320字节，SHA256为`5d88c570a5823b35cd347f008357a6dd3b6a81b3b079dd93a7bab2f20b04b250`。这是磁盘文件身份，不证明实际加载版本、DLL内部关闭顺序、线程安全或成功返回契约。

## 源码索引

在[源码阅读器](module-source-explorer.html)搜索lasermon。除注明外路径相对trunk/AKRS.ZX2200。

|证据ID|文件与行号|
|---|---|
|main-load（复用）|Main/Controls/MainForm.cs:232–271|
|module-background（复用）|Main/Machine/MachineSupport/Machine.Operate.cs:662–700|
|lasermon-wrapper|Main/Machine/MachineSupport/Machine.Sustain.cs:310–320|
|lasermon-check|同上:326–422|
|lasermon-start-comment|Main/Machine/MachineSupport/Machine.Operate.cs:438–443|
|lasermon-warm-machine|同上:753–784|
|lasermon-warm-bond|BondSystem/Controllers/BondModuleController.cs:870–888|
|lasermon-flag|trunk/AKRS.Galaxy2.MachineSupport/RuntimeProvider.cs:33–43|
|lasermon-base-exit|trunk/AKRS.Galaxy2.Machine/BaseMachine.cs:151–165|
|lasermon-machine-type|Main/Machine/MachineSupport/Machine.cs:67–67|
|lasermon-dependency|AKRS.ZX2200.csproj:281–284|
|auth-exit（复用）|Main/Machine/MachineSupport/Machine.Operate.cs:706–739|

## 交接验收缺口

- [ ] 对照实际配置和故障日志确认缺失硬件、光强异常、通讯异常选择的设备表现。
- [ ] 独立测试串行监控中的弹窗阻塞、异常退出和关闭期间的并发查询。
- [ ] 获取匹配DLL源码或经允许的API契约资料，核对硬件关闭顺序、幂等、异常及线程安全；不得凭接口名补全。
- [ ] 如需启用预热门控或修复退出行为，应另行授权修改生产程序。本次只完善理解与证据。
