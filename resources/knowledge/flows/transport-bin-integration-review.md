# 等待区传入出料 Bin：完整生产器集成验证

原 `TransferWaitingUnloadToUnloadBin`、缩回/推料/层号包装、模组运动/准备判定和参数 getter 已接入原 Bond、等待区皮带控制器、完整输送生产器、两条原 UI 启动入口、准备链、真实供晶 Task 和原 Stop。578 项受控检查通过：111 个完整方法、50 个属性、6 个枚举、13 个字段、23 条信号初始化契约，共 180 段原代码、82 个来源文件；专题阅读器增加 81 段链路快照。

检查保留原 Task.Run/WaitAll 和真实 Signal/EventWaitHandle。硬件和料盒配置仓库、轴状态/输入/AbsoluteMove 结果、日志/对话框/保存、原生控件是明确的替身。其他六个传输方法、原项目构建、实际配置与部署 DLL、原生 UI、SDK 及设备验收仍待完成，29 个源码组继续为 partial。

## 实际任务与信号

两条原 UI 入口均启动实际 LoaderBin 父任务。它等待原手动复位 UnloaderAllowPushSignal，执行缩回→推料→缩回，成功后复位输入，再发布原自动复位 AllowUnloaderMoveSignal。检查消费真实输出事件一次，并确认输入事件已复位；NoStart 保留原输入许可，后续有料时无需再次 Set。

两条 UI 的 Bond→等待区→Bin 连续链由原第五、第七 Task 执行，保留两个真实 Bond 子任务、共享物料对象、一次 Refresh、两次 Save。Bin 清空等待区 TransportUnit，但不把该对象赋给出料区；原方法仍把出料区标成 HasMaterial 并递增层号。

96 组直接调用组合覆盖六配置、有料输入、等待区物料状态、等待轴运动状态和出料区物料状态。Online/OnlineWithAutoUnloader 额外拒绝出料区 HasMaterial，其余配置没有该检查。实际 Bin Task 只由 LoaderBin 配置分配；其他配置的组合明确是直接调用控制器。

## 推杆包装与 SDK 签名

原缩回固定命令位置 4；推料读取当前料盒名称对应的 PushPos。模组要求 Y/Z/推杆三个轴均非 null，准备失败返回 Abort；即便离线模式，也先检查轴存在。OffLineWork 准备成功后返回 Success，不调用推杆 AbsoluteMove；其他模式透传 SDK 返回码。

缩回和推料包装均把全部非 Success 返回码转为 Exception，并记录日志。主传输方法处理推料失败报警，却忽略首次和最终缩回返回码。全部 13 个 SDK 返回码分别覆盖这三个调用位置；推料失败选择 Ignore 后可提交，缩回失败无需报警选择即可继续。SDK 抛出异常也分别验证包装吞掉异常后的行为。

DLL 静态检查确认 `AbsoluteMove(pos)` 选择四参数重载，默认 `isCheckPostion=false, vel=-1, accuracyMode=HighAccuracy(0)`；double/AccuracyMode 二参数重载的第二参数并非可选。替身按真实四参数签名编译，单独断言三个原推杆调用使用上述默认值。[SDK 元数据证据](transport-bin-sdk-evidence.json)保存六个重载/执行器方法体、可选参数常量、AccuracyMode 枚举和两个仓库 DLL 哈希，仅证明元数据和 IL，未执行 SDK。

## 重试、停止与输入

首段卡料、推料失败、尾部卡料分别覆盖 Abort/Ignore/Retry。首段 Ignore 可只缩回一次、跳过推料仍提交；首段 Retry 重启皮带；推料 Retry 只重复缩回和推料；尾部 Retry 额外缩回后重启皮带。Abort 由实际父任务执行 Stop，未完成层号和保存提交。

原方法内部无 Stop/Pause 检查，isManual 参数未参与分支。稳定 Stop/Pause 状态下直接调用仍会移动和保存；实际父任务进入方法后执行原 Stop 或设为 Pause，也可继续移动、保存并发布下料移动信号。完整 Stop 已结束真实供晶 Task，但在途 Bin 仍可发布成功。提前 Pause 阻止进入方法，恢复 Working 后使用真实许可继续；提前 Stop 则不执行控制器。

若 SDK 运动反馈使整个循环跳过，局部有料变量仍为默认 false，原方法可以直接推料；检查明确提供末尾传感器无料样本。推杆位置超出参数展示范围、NaN/Infinity 仍传给 SDK，检查用显式成功的 SDK 替身证明原包装未拦截，不代表设备接受这些值。

## 提交、层号与异常层次

13 个传感器、轴状态、运动/停止、日志、报警和 Save 边界分别验证内层 Exception 返回与实际父任务 Stop。catch 只恢复等待区 SubSectionState。Save 失败发生在清空物料、设置区段状态和层号加一之后：等待区可恢复 HasMaterial 但 Unit 为 null，出料区 HasMaterial 和新增层号保留。层号更新处程序对象为空时，物料提交已经发生，但未递增和保存。

原 CurPlaceLayer 默认 1，AddCurPlaceLayer 无夹限。在本受控默认 unchecked 编译下，-1/0/99/100 和 int.MaxValue 都直接加一，最后一项回绕到 int.MinValue；不以参数 UI 的范围属性推断运行时约束。等待区 HasMaterial 但 Unit 为 null 时仍可递增并保存。

初始 stateTemp 在 try 外；这里失败直接落入父任务 catch。内层日志/对话框、父任务 catch 对话框、Stop 日志/UI 清理故障分别验证 Working/Stop、活跃供晶和实际 Task Faulted 的状态。保存后销毁真实输入或输出 EventWaitHandle，分别使原 Signal.ReSet/Set 抛错：父任务正常结束于外层 catch，机器仍 Working、供晶仍活跃，保存和层号保留，输出未发布。

首轮扩展测试在提前 Stop 的断言处失败，因为供晶 Task 异步退出；后续等待实际终态再断言。SDK 替身签名修正过程中另有重复 AccuracyMode 夹具声明的编译失败，已合并到既有声明。失败记录保留于 `.archify-work/bin-integration-expanded.log`、`bin-integration-expanded-v2.log`，修正后 `bin-integration-expanded-v3.log` 的 578 项通过。生产源码未修改；清理阶段释放替身门、终止任务和恢复已销毁的测试信号，不计为生产流程成功。

## 验证与下一项

专项命令为 `node scripts/test-transport-bin-integration.cjs`；来源审计为 `node scripts/build-transport-bin-integration-audit.cjs --check`；SDK 静态契约为 `node scripts/build-transport-bin-sdk.cjs --check`。来源审计核对文件哈希、原文偏移/行号/片段哈希、23 条信号初始化和报告哈希。统一回归与四种宽度阅读器结果见 [集成验证回执](transport-bin-integration-verification.json)。

下一项接原出料皮带→收板机控制器和 SMEMA 要料包装，完成实际第九 Task 的生产链验证，接续见 [原代码证据](transport-auto-unloader-next-evidence.json)。其他入料/点胶传输、载具检查/MapMaterial、程序/池/域/SDK 及现场验收仍继续推进。
