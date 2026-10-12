# 当前监控证据与待办范围

本页整理 2026-10-06 后续监控验证，供继续任务清单时定位。整体 16 工程、29 组、1436 源文件及 13 项要求保持未完成，检查数量不累加为全项目覆盖率。

|范围|当前证据|未验收部分|
|---|---|---|
|在线门控及缺失硬件|[边界报告](native-online-monitor-boundary-review.md)：NormalWork 下未配置返回；缺门控/加热模块抛异常，缺激光由 null 门放行|真实设备状态、传感器输入和报警 UI|
|在线循环及重启|[生命周期报告](native-online-monitor-loop-review.md)：监控启动、存活重复启动复用、标志退出后创建新线程，图像/统计消费者启动|真实设备参与、生产状态下完整成功循环、并发 Start 竞态|
|在线线程故障|[线程身份及双进程重放](native-online-monitor-fault-replay-review.md)：原监控线程的安全门空引用未处理，消费者和 DB Lazy 尚未创建；199 个哈希绑定通过|实际报警、故障恢复、原 Program.Main 异常处理器组合、0xC0000005 和 CLR 格式化失败的底层原因|
|早期单次故障记录|[早期报告](native-online-monitor-fault-review.md)：仅异常终止事件；本轮保留，不覆写|旧宿主 500ms 返回与终止并发，因此线程身份和副作用以新双进程记录为准|

后续仍需匹配厂商驱动/设备与 VM、真实统计实体 SQL 持久化、目标设备 DPI/客户区布局、完整 MSBuild/LC/Fody 与 MSI/现场部署。当前受控和非设备原生证据不足以关闭这些要求。

## 正式回归状态更正

之前几轮聊天把 `verify-all` 输出的 `checks:1328` 子检查通过写成完整回归通过，该说法范围过大。此前启动的六个完整 `verify-all.cjs` 会话已在当前工具轮询中终止或不可再访问；没有取得最终 `verify-all: PASS` 或完整流程 exit 0，因此不能把它们计为完整回归通过。本轮不再新增完整回归进程。

此前记录的会话句柄 40871、62894、62864、94019、66479、36335 已在当前工具轮询中全部返回 `Unknown process id`，因此不能继续等待或把它们视为存活任务。首次检查时的只读快照仍保存在 `.archify-work/formal-verification-live-status.json`，但不作为当前运行状态证明。

本轮专项核验命令 `node .archify-work/verify-online-monitor-fault-replay.cjs` 已实际 exit 0；它验证新的两个子进程、异常回执、线程身份和 199 个哈希绑定，不代表完整 `verify-all` 的最终结果。

## 本轮坐标专项重放

`verify-coordinate-native-source.cjs --check`、`verify-coordinate-native-source-progress.cjs --check` 和 `verify-coordinate-lifecycle.cjs --check` 均通过；生命周期回执为 113 项、3 个原始坐标文件。坐标产品终态核验未通过历史冻结哈希检查：旧组合绑定的 `transport-loading-belt-integration-harness.cs.txt` 与当前 harness 不同，且旧终态仍绑定上一版模块阅读器摘要。该结果只说明历史组合不能用当前输入重放，不能改写为当前源码或新坐标证据失败；正式冻结产物保持不变。

本轮 whole-node 隔离闭包继续推进：v119 在 v94 上加入 `SlideFluxerController.cs` 与 `SlideFluxer.cs`，错误由 457 降至 455；随后 v120 再加入 `ForceTorque.cs`、`PickRefEnd.cs` 和 `RtuConnectConfig.cs`，源码输入 177、引用 70，错误降至 448。退出码仍为 1，DLL 未验收；加入完整 `ForceCalibrationService.cs` 反而回升到 452。证据见 [v120 进度](whole-node-source-compile-v120-progress.json) 与 [v120 复核](whole-node-source-compile-v120-review.md)；正式 642 错误基线不变。

在 v120 上继续逐个测试 10 个小型真实源候选：没有候选把错误数降到 448 以下；`IPTController.cs` 与 `EpoxyMaterialProgram.cs` 保持 448 个错误，其余新增候选增加到 449–461 个错误。候选 DLL 均未验收，结果见 [v120 小型候选进度](whole-node-source-compile-v120-small-candidate-progress.json) 与 [复核](whole-node-source-compile-v120-small-candidate-review.md)。

后台通知支线新增只读写入面盘点：37 个 ActionNodes 源文件中登记 54 个晶圆/翻转台/刮胶盘信号或名称写入匹配点，并保存源码哈希与附近异步启动行。该证据扩展了静态覆盖，仍不代表 Task 生命周期、异常监督或设备运行完成；见 [通知写入审计](async-notification-write-surface-audit.json) 与 [复核](async-notification-write-surface-review.md)。

对其中 8 个真正承载通知 sink 的 `Task.Run` 块继续核对后，8 个启动处均未保存返回 Task，后续近邻源码也未见该块的 `await`/`Wait` 观察。该结论是词法源码证据，仍未替代运行时任务/异常/停止回收验证；见 [Task 生命周期审计](async-notification-task-lifecycle-audit.json) 与 [复核](async-notification-task-lifecycle-review.md)。

绑定程序集 IL 也已复核：Pick、Substrate、UpLook 三个动作节点共 24 个 `Task.Run` 调用点，12 个立即 `pop`、12 个保存局部变量；6 个 `DoWork` 通知调用点均立即 `pop`。该结果以程序集哈希锚定，仍保留运行时执行和设备边界；见 [IL 审计](async-notification-il-audit.json) 与 [复核](async-notification-il-review.md)。

编程页面支线新增 5 个间接保存/模态源文件闭环审计：对话框返回对象、确认时仓库保存、通用仓库 FormClosed 保存及父页面委托均已登记，并保留当前源码哈希。该证据补足静态保存路径，仍不代表 DevExpress UI、外部 Singleton 文件或现场配置运行成功；见 [对话框保存审计](programming-dialog-save-closure.json) 与 [复核](programming-dialog-save-closure-review.md)。

通用仓库所依赖的 `FrmCreateName` 没有仓库内源文件，本轮改以随附 `AKRS.Galaxy2.Infrastructure.dll` 做只读 Mono.Cecil 边界核对：类型、构造参数、`ValidatePredicate`、`CreateName`、确认/取消结果及文本编辑校验的 IL 均已记录，并用程序集 SHA-256 固定版本。该证据仍不覆盖真实 UI、部署一致性或运行时异常；见 [外部命名对话框 IL 审计](programming-external-dialog-il.json) 与 [复核](programming-external-dialog-il-review.md)。

S2 自检支线新增原始程序集 IL 证据：`CheckIsReady`、动作控制器自检、配方自检、吸嘴架程序自检和七槽传感器检查均已按当前 ZX2200 哈希记录；调用顺序明确了焊头真空、两层 UI 自检、传感器读取和报警对话框边界。此项仍是只读二进制证据，未执行生产 UI、硬件或设备；见 [原始 S2 自检 IL 审计](original-s2-selfcheck-il.json) 与 [复核](original-s2-selfcheck-il-review.md)。

动作节点支线新增一项可复现的 AfterBond 离线分支：基于现有原始节点夹具增量执行 605 项检查，确认 `AfterBondCheckActionNode.DoWork` 在离线模式返回成功、写入当前步骤并完成回调收尾；UI 刷新委托使用无操作替身，硬件仓库保持为空。见 [AfterBond 增量审计](after-bond-offline-extension-progress.json) 与 [复核](after-bond-offline-extension-review.md)。

S2 清零/Retry 支线继续完成原始 IL 增量审计：`BondTask.DoWork` 无本地异常处理器，来料成功后按 PickUpCompensationVision→System2TemperatureCompensation→ScanReferencePoints 顺序通过三项补偿门，任一失败早退且均先于 InjectSteps；随后按 InjectSteps→IsFirstDispense→Enable→载具产品/输送配置判断→必要时重建 System2 TransportUnit 并设置 IsProduct→IsNewProduct 顺序初始化上下文；再按 WaitStart→GetNextActionNode 空值退出→IsDoWork→CloseDispenseCylinder→节点 DoWork→FinishCurrentActionNode→再次 WaitStart 执行；`ResetBondhead()` 返回值紧接 `pop`，随后进入首组件查询；动作 Abort/Exception/报警终止调用 Stop 和安全位移，Retry 回到 `WaitStart`，成功路径完成产品、补偿归一化、可选顶针耗时保存后进入 `SendAway` 和 UI 刷新；`BondHeadController.ResetBondhead()` 与 `ModbusService.ResetBondhead()` 各有 Catch 处理器，前者按 ForceZeroMode 分支到 Modbus/IO，含 30ms 等待和 Retry/Ignore/Abort 映射，后者绑定寄存器 94 两次写入及 50ms 等待。程序集哈希、异常处理器、调用关系和控制流邻接均通过校验；未执行真实任务、Retry、UI、Modbus、轴、数据库、VM 或设备。见 [原始 S2 清零 IL 审计](original-s2-reset-il.json) 与 [复核](original-s2-reset-il-review.md)。

S2 来料信号门继续完成原始 IL 增量审计：`BondTask.GetIncomingSignal` 的补偿直通、输送完成信号等待、未配置输送时的提示/映射/`Machine.Stop` 三路边界均已按当前程序集哈希固定并通过校验；未执行真实信号、输送、UI、任务、数据库、VM 或设备。见 [原始 S2 来料信号 IL 审计](original-s2-incoming-signal-il.json) 与 [复核](original-s2-incoming-signal-il-review.md)。

S2 完成后送走载具继续完成原始 IL 增量审计：`BondTask.SendAway` 的允许传送信号、Stop 抑制、AutoSaveMapping、载具清理和人工取料提示边界均按当前程序集哈希固定并通过校验；未执行真实传送、Mapping、UI、任务、数据库、VM 或设备。见 [原始 S2 送走 IL 审计](original-s2-send-away-il.json) 与 [复核](original-s2-send-away-il-review.md)。

S2 任务入口继续完成原始 IL 增量审计：`BondTask.Start` 的 Running 状态门、`Task.Factory.StartNew`、`CancellationToken.None`、LongRunning、默认调度器和返回 `true` 均按当前程序集哈希固定并通过校验；未执行真实线程、异常监督、停止回收、并发或设备。见 [原始 S2 入口 IL 审计](original-s2-start-il.json) 与 [复核](original-s2-start-il-review.md)。

S2 任务工作线程继续完成原始 IL 增量审计：`BondTask.<Start>b__20_0` 先设置“固晶工作线程”线程名，再调用 `DoWork()`；程序集哈希、两处调用和无分支结构均通过校验，未执行真实调度、异常监督、停止回收、并发或设备。见 [原始 S2 工作线程 IL 审计](original-s2-start-worker-il.json) 与 [复核](original-s2-start-worker-il-review.md)。

S2 任务关闭入口继续完成原始 IL 增量审计：`BondTask.AbortThread` 仅含 `nop`/`ret`，无调用、字段写入或分支；程序集哈希和两条指令均通过校验，未执行真实停止回收、并发或设备。见 [原始 S2 AbortThread IL 审计](original-s2-abort-thread-il.json) 与 [复核](original-s2-abort-thread-il-review.md)。

S2 Task integration 夹具已按当前源码快速复跑：59 项检查、13 个原始方法提取及审计绑定均通过；证据仍限定于受控服务、信号、动作、Stop、Retry/异常和存储替身，不代表真实设备、完整调度或部署。见 [S2 Task integration 当前复核](s2-task-integration-current-review.md)。

S2 door pause 夹具已按当前源码快速复跑：37 项检查、17 个原始方法提取及审计绑定均通过，覆盖门暂停/恢复、单步、来料等待、Stop 抑制和动作失败推进；证据仍使用受控线程、事件与信号替身，不代表真实传感器、UI、设备或部署。见 [S2 door pause 当前复核](s2-door-pause-current-review.md)。

S2 消息/层级状态夹具已按当前源码快速复跑：`test-s2-context-update.cjs` 14 项检查全部通过，覆盖消息绑定、禁用步骤保留、重复项顺序、层级缺失、仓储异常和空输入；证据仍使用受控容器与仓储替身，不代表真实配方、任务、UI、硬件或部署。见 [S2 context update 当前复核](s2-context-update-current-review.md)。

S2 节点选择与预点胶分配夹具已按当前源码快速复跑：节点选择 9 项、预点胶分配 13 项全部通过，覆盖 Finish 推进、特殊节点重复拒绝、缺失注册、网格分配、耗尽重建、维度变化、越界和保存失败；证据仍使用受控节点、坐标、参数、UI 答案和保存替身，不代表完整任务、设备或部署。见 [S2 节点选择当前复核](s2-node-selection-current-review.md) 与 [S2 预点胶分配当前复核](s2-predispense-allocation-current-review.md)。

S2 动作前点胶气缸门继续完成原始 IL 增量审计：`BondTask.CloseDispenseCylinder` 按动作 `IsCloseCylinder` 条件调用 `CloseDispenseHeightMeasurementCylinder()`；程序集哈希、16 条 IL 和单一分支均通过校验，未执行真实气缸、点胶、任务或设备。见 [原始 S2 气缸门 IL 审计](original-s2-close-cylinder-il.json) 与 [复核](original-s2-close-cylinder-il-review.md)。

2026-10-07 快速复核：native-s2-compensation-prerequisites 严格绑定校验通过（primary/replay 各 51 项、31 个方法、5770 项冻结绑定）；采用既有隔离产物，未覆盖真实 UI、Modbus、SQL、VM、设备或部署。

2026-10-07 并行快速复核：S2 动作边界（31/轮）、清零传播（70/轮）、料架门（58/轮）和任务入口（497/轮）严格绑定均通过；任务入口仍保留实际 122 S2 tasks/轮、20 完成、102 在料架轴前故障的边界，未宣称完整生产链完成。

2026-10-07 S2 自检运行时增量：native-s2-readiness bound/replay 两轮各 56 项实际运行通过（13 行矩阵、12 个拒绝/恢复门、26 次公开分派），已由 verify-s2-self-check-runtime-current.cjs 严格绑定到 s2-self-check 当前进度；真实传感器/真空/视觉、UI 继续、SQL、VM、生产 Task、节点动作和设备仍未执行。

2026-10-07 阅读器指针复核：整机环境当前证据与 native-runtime-reader 当前语义/浏览器证据已交叉绑定通过（123 项、135 文件、47 主题、4997 快照、63 源文件、1456 声明、0 浏览器错误）；历史 browser-results.json 漂移保留为历史边界，未扩大为生产运行或设备验收。

2026-10-07 教学聚合增量：29 个历史 pending 片段已与当前 1,144 项集成回执逐项绑定，独立 reconciliation 通过；未改写历史 next-evidence 输入，真实 SDK/UI/生产调度/SQL/VM/设备/部署边界保留。

2026-10-07 当前隔离重绑定：transport-teaching-current-rebind 已通过 1,144 项、449 个源码片段、23 个信号绑定；当前 loading-belt harness 哈希为 9da5544beee7205d4463a45f29f75cef69022f7c49e0e997fa34c67c525da7aa，历史 formal test 快照已恢复并与执行前哈希一致。该收据仅收敛当前源码证据，不覆盖真实 SDK、原生 UI、生产调度、SQL、VM、设备、构建或部署。见 [当前重绑定收据](transport-teaching-current-rebind.json) 与 [验证器](../../scripts/verify-transport-teaching-current-rebind.cjs)。

2026-10-07 并行增量：检查就绪集成当前复核通过 1,209 项、469 个源码片段；检查仓储集成当前复核通过 1,303 项、498 个源码片段；两项均保持受控配置/仓储/UI/持久化/设备/信号边界，不升级为真实 SDK、生产调度或设备验收。

历史检查就绪/检查仓储审计链复核仍失败于同一 loading-belt 夹具哈希漂移（旧期望 02aebc2f…，当前 9da5544b…）；当前源码注册器和 1,209/1,303 项隔离测试已通过，历史输入未被改写。

2026-10-07 并行增量：产品声明、Transport Unit 服务、坐标/产品路由当前源码复核分别通过 1,328/512、1,011/391、1,031/420 项/片段；均保留受控替身边界，未扩大为生产或设备验收。

2026-10-07 审计收敛：三项输送集成 audit/evidence 已串行按当前正式测试快照重建，三项严格 --check 均通过；检查就绪/检查仓储历史审计仍单独保留 loading-belt 哈希漂移边界。

2026-10-07 产品生命周期增量：Opposite/产品就绪/TransportProgram 重置探针通过 29 项/7 片段；product-config-native-source 严格校验通过 36 项、72 个位置、22 个源码文件，仍保持启动组合与生产验收边界。

2026-10-07 坐标生命周期增量：当前独立探针通过 113 项、3 个未修改坐标源文件；组合审计仍保持 1,031 项边界，未扩大为原生 SDK、VM、设备或部署验收。

2026-10-07 仓储数据增量：Singleton Load 27/3/3、检查仓储准备 50/29/3、JSON SDK 52 个位置/26 个独立断言/2 进程均严格校验通过；这些证据仍不代表产品持久化、原生 UI、部署或设备验收。

2026-10-07 原生启动增量：native-program-main-entry 当前绑定复核通过 41 项/轮、19,106 个冻结绑定，246 个源码文件清单重新指纹；完整 UI、硬件、SQL、VM、联合构建和部署仍未验收。

2026-10-07 MainForm 增量：上下文、关闭保存、布局合成当前绑定分别通过 40/14,205、60/14,818、47/18,705；完整布局、在线设备、SQL、VM、联合构建和部署仍未验收。

2026-10-07 当前链收敛：transport-inspection-current-chain-verified 已通过教学重绑定 1,144、检查就绪 1,209、检查仓储 1,303 的当前源码纳入关系；准备快照仍有 1 个历史 loading-belt 哈希漂移，已隔离记录。见 [当前链进度](transport-inspection-current-chain-progress.json)。

2026-10-07 浏览器证据增量：runtime explorer 47/4,997/240、dispense explorer 52/5,257/500 主题/证据/运行时边界均通过 verifier，浏览器错误为 0；生产运行和设备边界保持不变。

2026-10-07 就绪/动作增量：焊后检测就绪通过 45/22，动作目录控制器通过 251/119/37/16/3,292 且 replay 一致；仍限定于隔离夹具和源码绑定。

2026-10-07 启动准备重绑定：三份静态快照（20/20/44 项，449/469/498 片段）按当前 harness 重绑定通过，历史输入未改写；原生 UI、设备、SDK、SQL、VM、构建和部署边界仍保留。见 [当前重绑定](transport-inspection-startup-preparation-current-rebind.json)。

2026-10-07 整机编译候选：追加 33 个真实源码输入的隔离候选编译失败（1,176 错误 vs 正式 642），已登记为 not-promoted 候选，正式基线保持不变。见 [候选进度](whole-node-source-closure-candidate-progress.json)。

2026-10-07 整机闭包分组诊断：Dispense（追加 9、132 输入、686 错误）、BondForce/Nozzle（追加 7、130 输入、654 错误）、Wafer（追加 16、139 输入、1,120 错误）均未降低正式 642 错误；分组结果仅用于定位缺失依赖，正式输入与 whole-node 基线保持不变。见 [分组进度](whole-node-source-closure-groups-progress.json)。

2026-10-07 whole-action SDK 当前重绑定：历史产品声明 test/audit 两个输入哈希漂移已隔离，当前重绑定验证通过两份 SDK 各 278 项、556 个放置、55 个编译单元、512 个源码片段和两份运行日志；历史回执保持原哈希，未并入正式 1328 回归。见 [当前重绑定](transport-whole-action-sdk-current-rebind.json)。

2026-10-07 动作下层快速复核：轴相对移动 IL 12/6、到位等待 8 调用点/8 驱动方法、安全移动序列 10 消息/20 锚点及 1440/850/390 浏览器视图均通过；浏览器错误为 0，仍不代表真实轴、IO、相机、设备或生产任务执行。见 [安全移动浏览器收据](safe-motion-browser-check.json)。

2026-10-07 原生就绪当前重绑定：节点前置 584/9,836 与检测就绪 108/10,344 的完整进度绑定已在共享历史计划哈希漂移下重新通过；历史快照未改写，下游指针保持一致。见 [当前重绑定](native-readiness-current-rebind.json)。

2026-10-07 原生 S1/S2 当前重绑定扩展：S1 工作循环/步骤提交/停止恢复/缺陷结果通过 126/10,006、85/10,096、51/10,164、109/10,250；S2 任务入口/就绪通过 497/10,857、56/10,455。8 套验证器均保留历史快照并通过当前源码绑定。见 [统一重绑定](native-readiness-current-rebind.json)。

2026-10-07 后台任务/持久化增量：通知 IL 24/6、后台任务契约 14/3、Save 契约 9/12、持久化写入 5/11、信号等待/任务状态/后台任务图/邦头校准图及生产门浏览器 134 条证据均通过；TemperatureCompensationEntity 未匹配仍登记为源码缺口，未宣称运行时数据安全或设备完成。

2026-10-07 温补消费者回放：异步数据库消费者 11 项隔离检查复跑通过，重现温补对象无 Insert/告警分支且后续队列项继续消费；使用受控数据库替身，未连接现场数据库或设备。

2026-10-07 启动链增量：生产启动 30、普通启动 175/91、启动配置 63/29、启动入口 43/39、任务并发 47、UI 启动模式 262/114 项/片段及对应审计全部通过；仍限定于隔离调度、线程、UI 和状态替身。

2026-10-07 任务生命周期增量：配方任务 100/3,376、Machine Stop 70/3,418 直接通过；Machine closure 310/10,761、退出消费者 25/17,846、监控消费者 40/18,295 在共享历史计划哈希漂移下经当前重绑定通过，历史快照未改写。

2026-10-07 输送/上下料增量：Transport context 180/3,322 直接通过；Transport environment 3,141/11,799、晶圆输送 660/11,165、Loader/Unloader 773/11,381、进出料握手 550/11,622、料仓就绪 834/11,474 当前重绑定通过，历史快照保持不变。

2026-10-07 复核提速：native-readiness-current-rebind 现按每批 4 个独立进程并行执行 29 套验证器，本轮完整回放约 1.87 秒；结果、历史快照和正式整机编译基线均保持稳定。

2026-10-07 任务/UI 生命周期增量：统一当前重绑定新增辅助任务 487/10,974、载具就绪 100/10,544、整机环境 123/10,685、配方实时重载 93/11,965、配方 UI 重载 48/12,379、UI 停止恢复 572/12,534 六套验证器；历史快照和正式基线保持不变。

2026-10-07 主程序/配方交互增量：MainForm 上下文、关闭保存、布局、PR 初始化、Program.Main、配方新建拷贝和配方对话框当前重绑定通过，分别为 40/14,205、60/14,818、47/18,705、31/14,446、41/19,106、163/13,651、89/12,916；客户区矩阵独立当前校验仍为 71 项，历史快照保持不变。

2026-10-07 算法/动作选择增量：配方动作选择当前重绑定通过 31,655 项/9,734 绑定，算法选择通过 163 项/9,609 绑定；未扩大为生产 Task、算法 VM、在线 UI、设备或部署验收。

2026-10-07 点胶/消费者增量：点胶控制、控制器、窗体、输入、策略、几何、源码读取、渲染、数据库保存、力控校准、统计生产者和视觉图像队列当前校验均通过（35/6,163、40/6,653、40/6,444、44/6,380、51/6,594、50/6,111、260/6,535、42/6,326、42/3,461、46/5,961、60/3,491、53/3,579）；仍不代表 SQL 写入、算法 VM、真实设备或在线生产。

2026-10-07 构建/部署前置增量：MSBuild 当前重绑定通过 40 次构建调用，Setup/Vdproj 通过 465 条清单记录（393 存在、72 缺失、195 依赖）；历史非计划快照保持一致，未生成 MSI 或执行安装。

2026-10-07 SDK 准备增量：full-framework、whole-config、whole-entity 当前重绑定分别通过 1,328+116、142、187 项；编译/运行退出码均为 0，浏览器主题快照 3,817，历史输入仅保留产品声明 test/audit 两个哈希漂移，未加入正式 1,328 回归。

2026-10-07 源码读取/配置准备增量：dispatch reader、virtual dispatch provenance、Bond 配置准备和产品配置准备当前重绑定通过，分别为 9,513、9,474、56/112 和 36/72；历史快照未改写。

2026-10-07 MainForm 客户区增量：视口矩阵当前重绑定通过两轮各 71 项，已保留右侧 384、底部 206 的溢出事实及其余历史快照；未宣称布局修复或在线 UI/设备完成。

2026-10-07 整机闭包细分：Dispense 参数/程序、BondForce/Nozzle、Wafer/搜索芯片三个候选组分别为 141/700、196/1,499、149/1,072 输入/错误，均未降低正式 642；结果仅用于依赖排序，正式基线保持不变。

2026-10-07 整机闭包最小候选：追加两个 Dispense 参数文件后错误由 642 降至 574（减少 68），但候选仍编译失败，未提升正式基线；后续继续补齐传递依赖。
2026-10-07 整机闭包下一层探针：以两个 Dispense 参数文件的 574 错误种子比较六组依赖组合，BondDevicePara 最佳为 126/553（较正式减少 89、较种子减少 21）；其余为 127/585、129/579、128/1085、129/583、129/581。所有候选仍失败，仅保留诊断排序，最佳候选未提升正式 123/642/1 基线。
2026-10-07 复核提速：整机闭包下一层六组独立编译改为最多 4 个并行槽，本轮约 10.16 秒完成；结果计数与输入哈希保持，最佳候选仍为 553 错误，正式基线不变。
2026-10-07 BondDevicePara 闭包增量：以 553 错误候选为种子比较六组传递依赖，同目录设备参数组合最佳为 134/544（较正式减少 98、较种子减少 9）；其余组合为 129/567、132/616、142/1,158、154/657、130/610。候选仍失败，仅用于依赖排序，正式 123/642/1 基线保持不变。
2026-10-07 设备参数闭包增量：以 544 错误候选比较六组直接依赖，吸嘴核心最佳为 138/539（较正式减少 103、较种子减少 5）；校准参数 135/540、点胶枚举程序 136/543、力控服务 135/548、统计 135/551、BondModule 135/622。候选仍失败，正式 123/642/1 基线保持不变。
2026-10-07 吸嘴种子闭包增量：以 539 错误候选比较七组直接依赖，System1Domain/System2Domain 最佳为 140/509（较正式减少 133、较种子减少 30）；FrequencyConsumables 139/537、点胶枚举 140/538，其余组合仍较高。候选仍失败，正式 123/642/1 基线保持不变。
2026-10-07 System Domain 闭包增量：以 509 错误候选比较六组小依赖，耗材加点胶枚举/程序最佳为 143/502（较正式减少 140、较种子减少 7）；其余为 141/507、142/505、141/512、142/509、146/505。候选仍失败，正式 123/642/1 基线保持不变。
2026-10-07 502 候选下层探针：TimeConsumable 组合仍为 144/502，BondProgram 146/517、点胶 Services/Modules 150/612、统计/力控/校准 146/505、Bond 控制器 158/926、晶圆控制器 144/620；没有低于 502 的新候选，正式基线不变。
2026-10-07 晶圆闭包单文件探针：WaferSystemDomain 144/594、WaferSubSystemTask 144/640、组合 145/726、Eject/Flip 144/620，均高于当前 502 候选；正式基线不变。
2026-10-07 502 聚焦探针：BondProgram 144/511、S2DispenserProgram 144/505、System2Controller 144/595、BondModuleController 144/573、DispenseModule 144/551、点胶服务 144/517、力控 144/506、统计 144/505；无低于 502 的新候选。
2026-10-07 502 命名空间探针：针对缺失命名空间的四个单文件组合中，ActionNodesSortService 将候选降至 144/496（较正式基线减少 146、较前候选减少 6）；TimeConsumable 145/528、DispenserMoveHelper 145/531、ModbusService 145/505 均未改善。496 候选仍退出码 1，仅登记为未提升诊断，正式 123/642/1 基线未改写。
2026-10-07 服务闭包探针：以 149/473 候选再复探 14 个低依赖服务/声明文件，未低于 473；此前 JudgeHelper、CoordinateSystemHelper、ForceConfig、DefectCompensate、FlipTool 逐轮将候选从 496 降至 473。所有候选仍退出码 1，正式 123/642/1 基线未改写。
2026-10-07 根类型与程序闭包探针：CalibrateRunPara、IPTController、SlideFluxerController、UpLookController 组合将候选降至 153/465；程序模块组合未继续下降，EpoxyApplication 将其降至 154/460，GeometryService 降至 155/458，DispenserMoveHelper 再降至 156/456。所有候选仍退出码 1，正式 123/642/1 基线未改写。
2026-10-07 统计与力控闭包探针：StatisticsDomain、统计实体和 DBService 将候选从 156/456 降至 164/444；ForceCalibrationService 加两个闭环模型后继续降至 167/427。Modbus 扩展、Bond 程序和 Wafer 域高耦合组合均未改善，所有候选仍退出码 1，正式基线未改写。
2026-10-07 力控配置增量：单独加入 RtuConnectConfig.cs 将候选从 167/427 降至 168/423；在已有 Rtu 配置上加入 ModbusService、统计服务、耗材和程序文件均未低于 423，正式 123/642/1 基线未改写。
2026-10-07 模块闭包增量：低耦合模块并行探针中，SlideFluxer.cs 将候选从 168/423 降至 169/422；UpLook、Eject、Magazine、Flip 和 WaferTable 模块均未改善，正式基线未改写。
2026-10-07 耗材闭包增量：在 169/422 候选上并行验证 BaseConsumable、TimeConsumable、FrequencyConsumables 及 UI 组合；BaseConsumable+TimeConsumable 将候选降至 171/413（较正式基线减少 229、较前候选减少 9），其余组合未更低。候选仍退出码 1，仅登记为未提升诊断，正式 123/642/1 基线未改写。
2026-10-07 413 下一层依赖探针：以 171/413 候选并行复核晶圆控制器/参数、SearchChip、Bond 控制器、点胶程序和任务闭包；点胶程序组最高接近为 176/417，晶圆参数为 177/438、任务为 174/445，其余更高，未发现低于 413 的候选。程序细分中 FlipModuleProgram 保持 172/413，正式基线未改写。
2026-10-07 413 单符号与交叉探针：单文件最近为 FlipTableController 172/414、NozzleShelfController 172/416；两者交叉及 BondProgram 组合最低为 FlipTableController+NozzleShelfController 173/417，未低于 413。候选仍退出码 1，正式基线未改写。
2026-10-07 程序实现闭包增量：以 171/413 候选并行验证 FlipTask、模块实现和程序实现；单独加入 SlideFluxerProgram.cs 将候选降至 172/411（较正式基线减少 231、较前候选减少 2），DispenserProgram.cs 为 172/412，其余未更低。候选仍退出码 1，仅登记为未提升诊断，正式 123/642/1 基线未改写。
2026-10-07 程序实现复跑增量：以新的 172/411 候选重跑同一批单文件探针，DispenserProgram.cs 将候选进一步降至 173/410（较正式基线减少 232、较前候选减少 1）；SlideFluxerProgram、FlipModule 和 NozzleShelfModule 均保持或高于 411。候选仍退出码 1，正式基线未改写。
2026-10-07 S2 程序组合探针：以 173/410 候选比较 BondProgram 与 S2DispenserProgram 的最小组合，最低为 175/412；加入 S2 其余程序或 NozzleShelfController 后更高，未发现低于 410 的候选。正式基线未改写。
2026-10-07 SearchChip 实体闭包增量：以 173/410 候选拆分 SearchChip 单文件；PickRefEnd.cs 或 ReferencePoint.cs 单独均降至 174/408，近邻组合未继续下降。为保持最小输入，登记 PickRefEnd.cs，候选较正式基线减少 234 个错误，正式 123/642/1 基线未改写。
2026-10-07 SearchChip 408 复跑：以 174/408 候选重跑 SearchChip 单文件，MarkedDie、ReferencePoint、WaferMapDataConfig 及晶圆/弹出组合均未低于 408；当前候选保持不变，正式基线未改写。
2026-10-07 支持类型探针：以 174/408 候选并行验证 MachineStateModel、PREntity、UcMainSystem、力控曲线窗体和 Machine.SelfCheck；最低为 UcmainSystem.Action 175/461，均高于 408，正式基线未改写。
2026-10-07 点胶程序尾部组合增量：以 174/408 候选验证剩余点胶程序，System1OtherProgram.cs 单独为 175/406、EpoxyApplicationProgram.cs 为 175/407；两者组合将候选降至 176/405，较正式基线减少 237、较前候选减少 3。候选仍退出码 1，正式基线未改写。
2026-10-07 405 程序后续复核：在已有 System1OtherProgram+EpoxyApplicationProgram 闭包上加入 PreDispense、EpoxyMaterial、S2EpoxyMaterial、S2PreDispense 或 NozzleShelfModule 均未低于 405；最低保持 177/405，正式基线未改写。
2026-10-07 Bond 程序增量：以新的 176/405 候选重跑程序/模块近邻探针，单独加入 BondProgram.cs 将候选降至 177/404；其余程序和模块未低于 405。候选仍退出码 1，正式 123/642/1 基线未改写。
2026-10-07 404 协同复跑：以 177/404 候选重跑点胶、S2、Flip 和模块尾部文件，S2EpoxyMaterialProgram 最低为 178/406，其余均保持或高于 404，当前候选不变，正式基线未改写。
2026-10-07 CleanNozzle 程序增量：以 177/404 候选验证缺失程序类型，CleanNozzleProgram.cs 单独将候选降至 178/402（较正式基线减少 240、较前候选减少 2）；与 Nozzle/S2 邻接组合未进一步下降。候选仍退出码 1，正式基线未改写。
2026-10-07 点胶/补偿支持组合增量：以 178/402 候选验证点胶参数与 MotionAreaCompensate，PreDispensePlatePara.cs+CompensateCalculator.cs 将候选降至 180/398（较正式基线减少 244、较前候选减少 4）；加入 DataService 得到同错但多输入，正式基线未改写。
2026-10-07 398 支持复跑：以 180/398 候选重跑点胶仓储、任务和补偿文件，Dispenser/仓储保持 398，BondCompensate 为 399，DispenseWorkTask 为 401，未发现低于 398 的候选，正式基线未改写。
2026-10-07 缺失任务探针：以 180/398 候选拆分 SlideFluxerTask、BondTask、CalibController、S2DispenseController、System2Controller 和 NozzleShelfProgram；最低为 SlideFluxerTask 181/404，未发现低于 398 的候选，正式基线未改写。
2026-10-07 配置路径探针：以 180/398 候选验证 ZX2200PathConfig、PathConfig 与 MachineConfigContext；ZX2200PathConfig 为 181/449、MachineConfigContext 为 181/442，路径组合未形成可用下降，未发现低于 398 的候选，正式基线未改写。
2026-10-07 设备参数增量：以 180/398 候选验证补偿、产品、工具和设备参数来源，FlipTableDevicePara.cs 将候选降至 181/393（较正式基线减少 249、较前候选减少 5）；其余来源未低于 398。候选仍退出码 1，正式基线未改写。
2026-10-07 393 符号来源复跑：以 181/393 候选重跑补偿、产品、工具和 BondHead 来源，TransportUnitCompensate 与 ProductDomain 保持 393，其余更高，未发现低于 393 的候选，正式基线未改写。
2026-10-07 瓦片台控制器增量：以 181 输入/393 错误候选并行验证 EjectController、FlipTableController、WaferSubController 和 FlipTask；加入 FlipTableController.cs 得到 182 输入/392 错误，较正式基线减少 250、较前候选减少 1。其余候选均更高，候选仍退出码 1，正式基线未改写。
2026-10-07 Flip 模块依赖增量：以 182 输入/392 错误候选加入 FlipModule.cs 后降至 183/389，再加入 FlipModuleProgram.cs 降至 184/387，较正式基线减少 255、较前候选减少 2。其余晶圆模块依赖均更高，候选仍退出码 1，正式基线未改写。
2026-10-07 Flip 程序依赖复核：以 184 输入/387 错误候选验证 FlipToolRepository、EjectionBank 仓储、Static/DataOffsetHelper 及 Wafer 组合；最低保持 387，未产生更低候选，正式基线未改写。
2026-10-07 Bond partial 闭包复核：以 184 输入/387 错误候选比较 BondHead、BondModule、System2 和 NozzleShelf 组合，最低仍为 387，未发现可登记的新候选，正式基线未改写。
2026-10-07 晶圆视觉链当前复验：几何 180 项、视觉控制 118 项、视觉采集 112 项均按当前源码重跑通过，审计一致；结果仍属于隔离替身验证，未替代 SDK、标定、设备、UI 或联合构建验收。
2026-10-07 搜晶门控当前复验：172 项检查、9 个源码片段、2 个信号绑定以及搜晶图 12 节点/15 关系均通过；受控门控仍不替代真实并发、设备轴、TransportDomain.StartTask 或完整联合构建验收。
2026-10-07 完整启动当前复验：Machine.Start、PrepareMachineReadyToStart、TransportDomain.StartTask、晶圆启动、模式分派及 Stop 的当前源码组合共 175 项检查，启动审计同步通过；TransportTask.Start 原始生产者、外层 delegate、真实 UI/配置/DLL/SDK/设备和完整联合构建仍未宣称完成。
2026-10-07 启动准备复验：303 项就绪辅助检查与审计通过，覆盖复位、任务状态、初始化和运行环境门控；CleanFile、完整生产配置及设备边界保持未验收。
2026-10-07 TransportTask.Start 生产者复验：870 项、129 个源码片段与审计通过，覆盖九个 Task.Run 生产任务、信号发布、Stop/就绪协调和异常路径；真实控制器动作、硬件、构建/DLL 与完整调度仍保留。
2026-10-07 UI 启动/模式复验：262 项、114 个源码片段与审计通过；原生 UI 消息循环、SDK/设备及联合构建仍未验收。
2026-10-07 TransportUnit/TuService 当前复验：1011 项检查、391 个源码片段与审计通过，覆盖实体、坐标/行列/索引、状态掩码和服务生命周期；设备 SDK、原生 UI、SQL/VM、部署与联合构建仍未验收。
2026-10-07 传输载具/地图整链复验：1355 项、341 个源码片段、23 个信号绑定及审计通过；真实动作注入、日志、原生 UI、构建/DLL 与设备行为保持未验收。
2026-10-07 S1 点胶任务复验：30 项检查、6 个方法与审计通过；任务调度、硬件及设备验收仍保留。
2026-10-07 S2 任务复验：59 项检查、13 个方法与审计通过；动作服务、UI、硬件和存储仍未验收。
2026-10-07 Bond 传送复验：310 项检查、145 个源码片段与审计通过；真实控制器动作、硬件、构建/DLL 与完整调度仍未验收。
2026-10-07 自动上料复验：238 项检查、279 个源码片段、23 个信号绑定与审计通过；SDK、配置仓储、原生 UI、构建/DLL 和设备仍未验收。
2026-10-07 自动下料复验：287 项检查、186 个源码片段、23 个信号绑定与审计通过；真实轴/硬件、原生 UI、构建/DLL 和设备仍未验收。
2026-10-07 仓式上料复验：288 项检查、302 个源码片段、23 个信号绑定与审计通过；真实配置、SDK、原生 UI、构建/DLL 和设备仍未验收。
2026-10-07 输送等待段复验：1076 项检查、166 个源码片段与审计通过；设备、SDK、原生 UI、构建/DLL 和完整调度仍未验收。
2026-10-07 坐标/产品输送复验：1031 项检查、420 个源码片段与审计通过；实体服务、SDK、原生 UI、构建/DLL 和设备仍未验收。
2026-10-07 点胶 1/2 输送复验：276 项检查、223 个源码片段与审计通过；设备、控制器动作、SDK、原生 UI 和完整调度仍未验收。
2026-10-07 点胶至 Bond 输送复验：184 项检查、210 个源码片段与审计通过；硬件、控制器、SDK、原生 UI、构建/DLL 和完整调度仍未验收。
2026-10-07 加载皮带输送复验：252 项检查、275 个源码片段、23 个信号绑定与审计通过；控制器动作、SDK、原生 UI、构建/DLL 和设备仍未验收。
2026-10-07 仓式传送复验：578 项、180 个源码片段、23 个信号绑定与审计通过；SDK、轴硬件、仓储、原生 UI、构建/DLL 和设备仍未验收。
2026-10-07 输送产品声明复验：1328 项、512 个源码片段与审计通过；配置/仓储/SDK、原生 UI、构建/DLL 和设备仍未验收。
2026-10-07 输送检查就绪复验：1209 项、469 个源码片段与审计通过；仓储、单例、VM、动作注入、SDK、原生 UI 和完整构建仍未验收。
2026-10-07 输送检查仓储复验：1303 项、498 个源码片段与审计通过；正式回归、部署配置/DLL、UI、设备和整组验收仍未完成。
2026-10-07 外层 TransportTask 复验：52 项检查、9 个方法与任务委托审计通过；在线生产循环、设备和原生 UI 仍未验收。
2026-10-07 Transport Pause 复验：32 项检查通过，覆盖 Pause/Stop、材料门控、兄弟任务等待、保存失败和 Jam Abort；外层任务、设备和产品框架仍未验收。
2026-10-07 Transport UnClamp/Stop 复验：46 项检查、9 个方法与审计通过；物理设备、原生 I/O 和完整外层任务仍未验收。
2026-10-07 S2 上下文更新复验：14 项检查通过，覆盖消息/层级、重复选择、异常和空输入；真实配方仓储、Fody、硬件、UI 和部署仍未验收。
2026-10-07 S2 门控暂停复验：37 项检查、17 个方法与审计通过；完整 BondTask、设备和部署仍未验收。
2026-10-07 S2 节点选择复验：9 项检查通过；完整上下文、BondTask、域就绪和设备仍未验收。
2026-10-07 S2 预点胶分配复验：13 项检查通过，覆盖网格、分配、耗尽、维度变化、越界和保存失败；设备运动、持久化和生产执行仍未验收。
2026-10-07 S1 原生循环复验：任务循环、工作/暂停、停止恢复、分段交互四项绑定验证通过（252 次、8 进程、102 次、12 进程）；真实 UI、VM、SQL、设备和整机业务仍未验收。
2026-10-07 S1 原生边界复验：缺陷模式、返回门、返工上下文、步骤提交四项绑定验证通过（218 次、12 进程、2 进程、170 次）；完整重试循环、真实 UI/视觉/VM/SQL/设备与 MSBuild 仍未验收。
2026-10-07 S2 原生六项复验：动作、补偿、就绪、重置、货架和任务入口绑定验证全部通过；生产循环、UI/VM/SQL、硬件和整机启动仍未验收。
2026-10-07 Transport/wafer 原生入口复验：context 180 项、environment 6282 次、wafer 1320 次验证通过；完整生产业务、UI/SQL、设备和 MSBuild 仍未验收。
2026-10-07 Bond 配置原生源码复验：56 个断言、112 次布置、23 个源码文件及 8 个编译延续捕获通过；启动组合和设备仍未验收。
2026-10-07 产品配置原生源码复验：36 个断言、72 次布置、22 个源码文件及 8 个编译延续捕获通过；启动组合、SDK/设备和部署仍未验收。
2026-10-07 检查仓储原生源码复验：27 个断言、54 次布置、6 个源码文件通过；完整产品集成、启动、UI/设备和部署仍未验收。
2026-10-07 Whole Action SDK 当前重绑定：三项历史输入漂移已登记，两个 SDK 各 278 项、556 次放置、54 个原始文件与 55 个编译单元通过；未纳入正式 1328 回归。
2026-10-07 Full Framework/SDK 当前重绑定：受控 1328 项、SDK 116 项、6 个编译单元和 269 个冻结输入通过；Fody、MSBuild、原生 UI、设备和整组验收仍未完成。
2026-10-07 Mapping 恢复链复验：codec 25、constructor/state 14、step semantics 8、action gates 30 项隔离测试通过；页面 14 场景/51 处源码绑定通过，端到端运行验收仍为 0，浏览器复验因环境缺少 playwright 未执行。
2026-10-07 教学/视觉复验：Plate 16、Tool 6、Vision 17、Autofocus alternatives 8 项隔离检查通过；真实 UI、相机、硬件、算法和生产可达性仍未验收。
2026-10-07 动作/模式/视觉重试复验：动作控制 51、模式生命周期 34、视觉重试 7、自动对焦范围 3 项通过；完整生产任务、设备和 UI 仍未验收。
2026-10-07 动作排序复验：80 项检查、33 个方法与审计通过；动作服务、UI、硬件和生产调度仍未验收。
2026-10-07 启动配置/入口复验：启动配置 63 项、启动入口 43 项及审计通过；原生 UI、SDK、设备、构建和部署仍未验收。
2026-10-07 Emergency abort 复验：87 项检查、44 个源码成员与审计通过；真实急停链、硬件、UI 和设备仍未验收。
2026-10-07 Emergency entry 复验：27 项检查、45 个成员与审计通过；真实急停入口、UI、硬件和设备仍未验收。
2026-10-07 Door task/Safe door pause 复验：门任务暂停 28 项、Safe door pause 16 项及审计通过；安全门、调度、UI 和硬件仍未验收。
2026-10-07 Safe motion 复验：34 项 2D/4D 安全运动路径通过；真实轴、驱动器和设备仍未验收。
2026-10-07 Single-step door 复验：33 项检查、17 个方法与审计通过；真实门控、UI、硬件和任务调度仍未验收。
2026-10-07 Wafer action/safety/stop/eject 复验：210、135、172、110 项及审计通过；真实轴、设备、SDK、UI 和完整任务仍未验收。
2026-10-07 Wafer range/next-position 复验：105、229 项及审计通过；真实标定、视觉、设备和生产循环仍未验收。
2026-10-07 Wafer camera-clearance 复验：174 项检查、46 个源码片段与审计通过；真实相机、标定、轴硬件和设备仍未验收。
2026-10-07 Wafer blob-position 复验：131 项检查、58 个源码片段与审计通过；真实视觉算法、相机、标定和设备仍未验收。
2026-10-07 Wafer mark-center 复验：76 项检查、64 个源码片段与审计通过；真实标定、视觉、硬件和生产循环仍未验收。
2026-10-07 Wafer position-accuracy 复验：99 项检查、52 个源码片段与审计通过；真实相机、标定、坐标和设备仍未验收。
2026-10-07 动作控制/背景监控/曲线/周期/驱动复验：对应测试与审计均通过；真实 UI、设备和完整 Framework 仍未验收。
2026-10-07 Dispense/dry-run/editor/heating/stop/mode/mouse/parameter 复验：对应测试与审计均通过；真实 UI、设备和完整任务仍未验收。
2026-10-07 Pattern/pretreatment/repository/transform/startup/task-closure 复验：对应测试与审计均通过；真实数据库、UI、设备和完整构建仍未验收。
2026-10-07 Assistant/async/autofocus/axis/calibration/coordinate 复验：入口检查通过；异步通知生命周期仍为记录状态，真实数据库、硬件和完整 Framework 未验收。
2026-10-07 Bin/config/changejson/emergency/epoxy/gugao/ledger/manual-wafer 复验：入口检查通过；真实 UI、数据库、设备和部署运行仍未验收。
2026-10-07 Nozzle/postbond/process/recipe/resource/state/teaching/vision 复验：入口检查通过；真实 UI、设备、数据库和完整运行链路仍未验收。
2026-10-07 Wafer change-retry/consumer-pause/selection/start-init 复验：入口检查通过；consumer-pause/search/vision acquisition/vision control 审计通过，真实设备和生产循环仍未验收。
2026-10-07 Whole config/entity SDK 当前重绑定：config 142/284、entity 187/374，编译产物一致；formal 1328 回归与真实设备仍未验收。
2026-10-08 整机源码闭包 387 单文件探针：8 个缺失依赖单文件并行编译，最低 185/387，未提升当前 184/387 候选；正式 123/642/1 基线保持不变。
2026-10-08 整机源码闭包外部引用探针：184 输入/65 引用/370 错误，较 387 候选减少 17；仍为诊断结果，正式 123/642/1 基线不变。
2026-10-08 整机源码闭包 370 程序/仓储单文件探针：8 个单文件均退出码 1，最低 185/370，未继续下降；正式 123/642/1 基线不变。
2026-10-08 整机源码闭包 370 控制器单文件探针：8 个控制器均退出码 1，最低 185/373，未低于外部引用候选；正式 123/642/1 基线不变。
2026-10-08 整机源码闭包 367 组合候选：187 输入/65 引用/367 错误，较 370 减少 3；仍为诊断结果，正式 123/642/1 基线不变。
2026-10-08 整机源码闭包 Epoxy 仓储配对：188 输入/65 引用/368 错误，未优于 187/367 当前最佳候选。
2026-10-08 整机源码闭包模块/任务复核：单文件未低于 367，三文件最佳为 187 输入/65 引用/367 错误；正式 123/642/1 基线不变。
2026-10-08 整机源码闭包 Product/Statistics 与域组合复核：Product/Statistics 单文件最低 385，Controllers/Modules/Tasks/Services 组合 979，Repositories 369，UcMainSystem 828，BondSystem.Controls 2046；均未优于 187/367 当前最佳候选，正式 123/642/1 基线不变。
2026-10-08 整机源码闭包收尾审计：source-coverage-audit check、git diff --check 均通过；正式日志 SHA 与登记值一致，基线仍为 123 输入/642 错误/退出 1。

2026-10-08 配置源码当前重绑定复验：产品配置 36 项断言、72 次放置、22 个源码文件和 8 个编译延续捕获通过；Bond 配置 56 项断言、112 次放置、23 个源码文件通过。两项状态仍为启动组合待验收，未扩大为 SDK、设备、部署或整机成功。

2026-10-08 整机源码闭包 367 缺失类型前沿探针：任务/服务组合 192 输入/408 错误，控制器/模块组合 205/807，程式/仓储组合 195/371，耗材/主界面组合 190/691；均退出码 1，仅用于依赖排序，正式 123/642/1 基线不变。

2026-10-08 整机源码闭包 367 单文件前沿探针：`S2EpoxyMaterialProgram.cs` 将候选从 187 输入/367 错误降至 188/366；其余单文件未低于 366。该结果已登记为未提升候选，候选 DLL 未验收。

2026-10-08 整机源码闭包 366 程式/仓储组合复核：S2、点胶及 Dispenser 仓储组合最低保持 188 输入/366 错误，未产生低于当前候选的组合；正式基线仍为 123 输入/642 错误/退出码 1。
