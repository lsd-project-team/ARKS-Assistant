# 插补运动测试：入口、参数与代表运动分支

更新：2026-09-28。部分复核；未运行此程序、未发出运动命令。

## 流程摘要

WinExe 项目的 Main 打开 FrmPVTTest。实例字段取得 MovePositions 单例并创建 Movements；构造函数初始化界面，但 Init() 调用被注释。用户分别通过采点、保存、运动按钮触发同步处理函数。运动分支互相独立，不存在源码已证明的 PT→PVT→插补自动顺序。本轮深入两轴PT和名为两轴插补的实际 UmlMovement；其他运动方法仍待逐段复核。

## 入口、参数及按钮路由

- [Program.cs:14](../../trunk/InterpolationMovementTest/Program.cs#L14)：Application.Run(new FrmPVTTest())。已读入口未调用 InitAllHardware；硬件仓库能否就绪不能据此推定。
- [FrmPVTTest.cs:27](../../trunk/InterpolationMovementTest/FrmPVTTest.cs#L27)：Init() 被注释，不能宣称持久化值自动回填界面。[36–61行](../../trunk/InterpolationMovementTest/FrmPVTTest.cs#L36)按 BondX/BondY/BondZ/焊头T 名称访问硬件，并取得参数单例。
- [采点1:68](../../trunk/InterpolationMovementTest/FrmPVTTest.cs#L68)：读四轴 GetRealPosition 到第一组控件后调用 Save。Save 将界面所有五点的位置、角度、时间、XYZ速度和T速度写入对象后调用 movePositions.Save，见 [139–196行](../../trunk/InterpolationMovementTest/FrmPVTTest.cs#L139)。因此采一个点也会提交其他控件当前值；本次未动态验证默认值覆盖风险。
- [MovePositions.cs](../../trunk/InterpolationMovementTest/Helper/MovePositions.cs#L15)：静态构造指定 PathConfig.DeviceDirPath 下 PVTMovePositions.json；保存方法来自 Singleton 基类，当前未取得其实现，不声明原子写入、备份或成功保证。
- [264–329行](../../trunk/InterpolationMovementTest/FrmPVTTest.cs#L264)：四个PT/PVT按钮分别调用对应二/四轴方法；两轴插补按钮实际调用 UmlMovement，四轴插补调用 InterpolationMovementWithFourAxis。运动按钮没有先调用窗体 Save，编辑控件后直接运动不能假定使用最新控件值。
- 保存按钮调用 Save 后显示成功文案，没有自行检查保存结果；该提示不是磁盘持久化证据。额外按钮调用 DBService.Instance.ToString，不能据此声称执行具体数据库查询。

## 分支A：两轴插补按钮实际执行四轴五段

证据：[UmlMovement:229–293](../../trunk/InterpolationMovementTest/Helper/Movements.cs#L229)。

1. 获取 X/Y/Z/T 的 ETEL 驱动，获取名称 ETEL 的 AxisCard 和主站。
2. 建立含四个驱动的 DsaIpolGroup → setMaster → ipolBegin → ipolSetAbsMode(true,-1)。
3. 设置 ipolUSpeed(0.1)、ipolUTime(0.25,0.1)。
4. 按 Point1→Point5 依次提交五个 ipolULine；每点 X/Y除1000、Z取负再除1000、角度除360。这里未使用每点 Time/Vel/TVel。
5. ipolWaitMovement(100000) → ipolEnd。此处数值仅按源码参数记录，不擅自推断SDK时间单位。

方法没有局部 catch/finally/重试；如果等待或更早调用抛错，后面的 ipolEnd 不保证执行。按钮直接同步调用，未见此处 Task.Run 或取消流程。SDK实际等待与停止语义尚待验证，不能把调用返回画成已完成设备验收。

## 分支B：两轴PT只提交两点

证据：[PTWithTwoAxis:1045–1173](../../trunk/InterpolationMovementTest/Helper/Movements.cs#L1045)。

1. 先对 BondX、BondY 分别 AbsoluteMove(0)，再获取驱动/主站并建立两轴组。这些调用位于 try 之前，前置移动与后续之间没有可见的独立 Wait 调用；不能推断 AbsoluteMove 本身是否阻塞。
2. try 内 setMaster → ipolBegin →绝对模式→ Point1 的 ipolPt → ipolBeginConcatenation → Point2 的 ipolPt。位置X/Y除1000，时间读取各点Time；传入60000参数。第3–5点的指令被注释。
3. ipolWaitMovement(60000) → ipolEnd。
4. 仅 catch DsaException：diag；对已打开X/Y驱动，如正在移动则 quickStop并waitMovement，如上电则powerOff，再close；最后关闭已打开主站并return。没有重试，也没有布尔成功输出。清理本身无嵌套异常保护，前置取驱动/移动不在该catch覆盖内。

## 不要混入的代码与未完成项

- FrmTest.cs 是另一旧窗体，调用 AbsoluteMove 与带bool参数的四轴插补；当前项目显式 Compile 清单未包含 FrmTest.cs，Main 也不选择它。不能直接把它的按钮加入有效流程或据它单独判定当前项目编译失败，见 [csproj:168](../../trunk/InterpolationMovementTest/InterpolationMovementTest.csproj#L168)。导入targets后的最终编译项仍未求值。
- 其他二/四轴 PVT、四轴PT和插补、未等待运动方法、UI Init、其他采点处理函数及资源尚未完整语义复核。
- LogicHardware、Drive、MachineSupport、ETEL SDK 的初始化、限位/互锁、参数单位、超时和持久化内部仍需证据；引用不等于运行就绪。
- 未进行构建、驱动兼容性、设备或模拟器运行。没有把测试路径当作生产主链；这里只增加辅助运动来源及风险边界。
