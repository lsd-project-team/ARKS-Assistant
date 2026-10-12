# 点胶传入 Bond：原控制器、气缸与完整连续链验证

原 `TransferDispenseToBond`、点胶解夹/挡料/出口/异步皮带、Bond 夹紧/挡料/同步皮带及共用 RelativeMove 包装已接入完整原输送生产器、两条 UI 启动入口、准备链、真实供晶 Task 和原 Stop。184 项受控检查通过，包含 132 个完整方法、57 个属性、8 个枚举、13 个字段、23 条信号初始化契约，共 210 段原代码、96 个来源文件；本专题回链 111 段源码快照。

原方法体、Task.Run/WaitAll、Signal 事件和 500ms/200ms 等延时保持不变。SDK 输入/限位/轴状态/运动/停止、仓库、产品配置、原生控件、日志/对话框/保存仍是明确替身。手动创建 TransportUnit 的构造函数与 Bond.OpenVacuum 本轮也为替身，不能据此宣称完整产品模型或真空区域行为已验收。为编译原 override 同步皮带方法，夹具基类补虚拟成员；这是类型适配，生产源码未修改。其余四个入料/点胶传输、程序/池/域生命周期、原项目构建、部署配置/DLL、原生 UI 和设备验收继续待完成，29 个源码组保持 partial。

## 原父任务、子任务与连续传输

两条 UI 入口各覆盖配置系统1与不配置系统1：父任务先停在真实 AllowDispenseTransferToBondSignal.Wait，收到实际事件后才执行子任务和皮带。初始 Bond 为 NoMaterial，因此这些检查避开原生产器启动时“Bond 已有料”的另外两条发布路径；本报告的失败后不发布结论限定本次传输结果。

原首批在配置系统1时分配五个 Task.Run，未配置时分配四个；第二批始终三个，分别经实际 WaitAll 汇合。观察到的输出任务 ID 分别为八个和五个：未配置系统1时两个挡料下降子任务仍被分配，但在原配置防护处返回，不产生输出。输出 ID 数量不代表全部任务分配数。原源码审计另行核验八处 Task.Run 和两处 WaitAll。

两条 UI 入口各执行完整点胶→Bond→等待区→出料区→收板机链，依靠实际 transferDispenseToBondTask、transferBondToWaitingUnloadTask、transferWaitingUnloadToUnloadBeltTask、transferUnloadBeltToAutoUnloaderTask。同一 Unit 三次 Refresh、四次 Save；点胶异步运动一次，Bond 同步/异步各一次，出料轴两次运动。替身保存/SMEMA 门用于观察中间提交，随后释放，未把观察门当作生产逻辑。

## 夹紧、解夹与配置分支

四种点胶 UnClamp 模式和四种 Bond Clamp 模式核验输出值及先后顺序，保留原固定延时。点胶可选后两路 NL 限位和 Bond 可选后两路 PL 限位为 null 时跳过；首路是必需项，null 引发原子任务故障，由 WaitAll 进入控制器 catch。设置为空时的原提示返回与后续皮带包装抛错也分别验证。

点胶 UnClamp、两路挡料下降同时受系统1/输送配置防护；挡料上升不受该防护。Bond Clamp 在未配置输送时调用 OpenVacuum，本轮只验证进入明确标记的替身。控制器的物料门与手动 Divide/IsTuInDispense1 条件分别测试；直接手动调用不等待或发布生产器事件，在 Working/Pause/Stop 下均可执行。

解夹与夹紧的 Ignore/Retry/Abort 各覆盖一次。Retry 回到原 helper 起点并再次采样；Abort 调用原 Stop 后正常返回 void，WaitAll 仍可结束，父控制器继续移动、刷新 Unit、保存并返回 Success，实际父任务仍发布本次完成事件。机器状态保持 Stop，下一轮外层 WaitStart 才结束任务。

## 卡料、SDK 与停止时序

首段、尾段卡料各覆盖 Abort/Ignore/Retry。首段 Ignore 跳过同步 Bond 皮带，但执行第二批子任务并提交物料；尾段 Ignore 则在同步皮带已经调用后提交。Retry 重做首批及相关运动。Abort 返回原父任务后执行 Stop，不提交或发布本次完成信号。

全部 13 个 ExcuteResult 返回码在受控、成功的轴状态/出口序列下均被原 void 运动包装忽略；SDK 抛异常与返回码区别测试。点胶传感器参数保持 CheckStateForNums(true,1,0)。源代码按轴配置速度 80 乘倍率，得到点胶 30、Bond 20；这不证明实际速度或到位。

[SDK 静态契约](transport-dispense-relative-sdk-evidence.json)保存四个 RelativeMove/执行器方法的元数据和 IL、两个仓库 DLL 哈希。原两实参调用选择三参数 overload，accuracyMode 默认 HighAccuracy(0)，位置与速度由原包装传入。仅静态读取，不执行 SDK，也未证明部署版本。

收到信号前原 Stop 使真实 Wait 返回 Abort，无动作、提交或本次完成事件；两条 UI 入口在收到信号后 Stop/Pause，原内部无再次状态门控，仍完成运动、提交、保存和发布。清理停止/释放观察门/等待线程只用于结束测试，不计作设备停止结果。

## Exception、Unit 别名与部分提交

十二个输出、轴、出口、Refresh 和 Save 故障在原 catch 内观察：原控制器返回 Exception，父任务的结果 switch 无 Exception 分支，既不 Stop，也不发布本次完成信号；真实供晶与父任务保持活跃，UI 启动 catch 不接收这个返回值。提交前失败后父任务再次进入控制器，在已消费的真实输入事件上等待；Save 失败后已提交 NoMaterial，下一次被物料门返回 NoStart。

Refresh 前已把点胶 Unit 赋给 Bond；Refresh 抛错保留双方相同对象，而两段物料状态尚未提交。Save 抛错则保留源 Unit 已清空、Bond HasMaterial、双方 Ready 的内存状态，不能视为持久化成功。正常模式 null Unit 在 Refresh 处失败；手动模式走原 System2 构造分支，但构造函数本轮为明确替身。这些路径均无回滚。

## 验证与接续

专项运行 `node scripts/test-transport-dispense-bond-integration.cjs`；来源审计 `node scripts/build-transport-dispense-bond-integration-audit.cjs --check`；SDK 静态核验 `node scripts/build-transport-dispense-relative-sdk.cjs --check`。审计固定数量、全部来源/片段哈希、行号/偏移、原信号初始化、报告哈希及 Task.Run/WaitAll 结构。

基线先出现夹具 ProductConfiguration 重复声明和同步 override 缺少基成员的编译错误，修正类型适配后 30 项基线通过，扩展后 184 项通过；记录在 `.archify-work/dispense-bond-integration-baseline-v2.log`、`dispense-bond-integration-baseline-v3.log`、`dispense-bond-integration-expanded.log`。统一回归与四种阅读器宽度结果在收尾后登记验证回执。

下一项为原点胶1→点胶2控制器、点胶 Clamp/同步皮带、Unit 坐标偏移和预点胶标志，见[接续源码](transport-dispense12-next-evidence.json)。其余入料、载具检查/MapMaterial、程序/池/域/SDK 与现场验收继续保留。
