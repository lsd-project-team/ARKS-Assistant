# 等待区传入出料皮带：完整生产器集成验证

原 `TransferWaitingUnloadToUnloadBelt`、共用运动/停止/有料包装已接入此前的原 Bond 传输、完整输送生产器、两条原 UI 启动入口、准备链、真实供晶 Task 和原 Stop。1,076 项受控检查通过：105 个完整方法、42 个属性、6 个枚举、13 个字段、23 条信号初始化契约，166 段原代码来自 73 个来源文件。专题阅读器保留这条链的 67 段快照。

这些检查编译并执行原方法，保留实际 Task.Run、WaitAll 和 Signal 事件；轴状态、传感器、停止反馈、I/O、日志、程序保存及原生控件由明确的替身提供。其余七个传输方法、实际 SDK 执行、部署 DLL、配置、原项目构建和设备验收仍待完成，29 个源码组继续为 partial。

## 配置、共享输入与实际任务

两条原 UI 入口分别验证 Belt、Online、OnlineWithAutoLoader、OnlineWithAutoUnloader 的实际第六个传输 Task；原第五、第六 Task 连续完成 Bond→等待区→出料区，保持共享物料对象、两次 Refresh/Save 和真实供晶需料/取料事件。None 和 LoaderBin 原启动不分配第六 Task，相关场景明确通过直接调用控制器验证。

288 组直接调用组合覆盖六种配置、两个等待区传感器值、两个出料区传感器值、两个等待区状态、两个出料区状态、三个出料区传输状态。Online 与 OnlineWithAutoUnloader 都检查出料区模组传感器，只有 Online 额外拒绝出料区程序 HasMaterial/Transfering。其他配置可覆盖已有出料区 TransportUnit；通过检查保留这个原行为。

连续链共用出料入口传感器，Bond 阶段已经消耗首轮输入样本。替身在 Bond 保存之后提供下一段输入变化，避免把前一个阶段的样本错误当作新一次运动的输入。首次夹具失败日志保留在 `.archify-work/waiting-integration-initial.log`，修正输入序列后独立基线 74 项和完整 1,076 项均通过。

## SDK 包装的准确边界

等待区模组调用 `CheckStateForNums(true,1,0)`，出料区模组调用 `CheckStateForNums(true,1,200)`；原 Stop 包装调用 `StopMove(false,true)`。DLL 元数据确认参数名为 `isWaitArrive`、`emg`，传感器第三参数原名 `checkInteval`；`GetAxisState().Moving` 对应 bool 字段。相关五个方法体及两个 DLL 哈希固化于 [SDK 元数据证据](transport-sdk-predicates-evidence.json)，仅证明仓库 DLL 的元数据与 IL。

两个轴分别覆盖全部 13 个 ExcuteResult。原 void 运动包装忽略返回码；检查为每次调用明确提供运动和输入成功序列，不以返回码推断实际轴状态。原模组 StopMove 对 null 轴不调用 SDK，而 IsMoving 无 null 防护。原 Bond 模组 HasMaterialInModule 保留并实测抛出 NotImplementedException。

## 停止、卡料和提交

方法内部无 Stop/Pause 检查。直接在 Stop/Pause 状态调用、或实际传输 Task 进入方法后改变状态，都可继续移动并保存成功；Pause 在外层阻止下一轮。提前 Pause 则先阻止原父任务进入方法。

连续运动配置只跳过出料轴 Stop，仍停止等待区轴，循环依赖 SDK 后续返回非运动状态。替身必须先经历入口变为无料的一轮，再提供轴停止；首轮夹具过早停止导致保留局部有料值并进入尾部卡料分支，该失败与修正见 `.archify-work/waiting-integration-expanded.log` 和 `waiting-integration-expanded-v2.log`。

首段与尾段卡料各覆盖 Abort、Ignore、Retry。Abort 由原父任务执行 Stop；Retry 再次发送等待区运动；首段 Ignore 可以不发送出料轴运动而提交物料。出料区 HasMaterialInModule 的尾部采样结果未参与最终成功判断，单独检查证明该返回值为 false 时仍可成功。

## 异常与物料归属

15 个传感器、轴状态、运动、停止、日志、Refresh、Save 边界分别验证原内层 Exception 返回及父任务 Stop。catch 只恢复等待区 SubSectionState，不回滚 TransportUnit、出料区状态或已发生的保存。Refresh 失败可使两区指向同一物料对象；提交之后日志或保存失败可留下等待区 HasMaterial 但 Unit 为 null、出料区已持有物料。

`stateTemp` 在 try 之前读取；这里抛出异常绕过控制器 catch，落入父任务 catch。内层日志/对话框、父任务结果日志、父任务 catch 对话框及 Stop 日志/UI 清理的嵌套故障也分别验证。部分失败留下 Working 与活跃供晶 Task，父任务 catch 自身失败可使实际 Task Faulted。检查观察原任务终态，随后释放替身门并结束资源；清理不计为生产流程的成功或停止证明。

## 验证与接续

专项命令为 `node scripts/test-transport-waiting-integration.cjs`，来源审计为 `node scripts/build-transport-waiting-integration-audit.cjs --check`，SDK 静态契约为 `node scripts/build-transport-sdk-predicates.cjs --check`。来源审计核对完整文件哈希、原文偏移、行号、片段哈希、信号初始化及报告哈希。

统一回归和四种宽度阅读器的结果另写入 [集成验证回执](transport-waiting-integration-verification.json)。下一步接入原等待区到出料 Bin 控制器及对应 LoaderBin 生产器路径，再继续剩余传输、载具检查/MapMaterial、程序/池/域/SDK 和现场验收；[接续证据](transport-waiting-next-evidence.json)区分已执行包装与仍待执行的方法。
