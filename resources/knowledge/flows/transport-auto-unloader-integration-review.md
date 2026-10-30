# 出料皮带传入收板机：完整生产器集成验证

原 `TransferUnloadBeltToAutoUnloader`、SMEMA 要料包装和三个硬件 getter 已接入完整输送生产器、两条原 UI 启动入口、准备链、真实供晶 Task、原 Stop，以及此前的 Bond 和两条等待区传输。287 项受控检查通过：114 个完整方法、53 个属性、6 个枚举、13 个字段、23 条信号初始化契约，共 186 段原代码、87 个来源文件；专题阅读器增加 87 段链路快照。

保留原 Task.Run/WaitAll 和实际 Signal 事件。硬件仓库、SDK 输入/轴状态/运动/停止、日志/对话框/程序保存及原生控件是明确的替身；其余五个入料/点胶传输、实际程序/池/域/SDK、原项目构建、部署配置/DLL、原生 UI 与设备验收仍待完成，29 个源码组继续为 partial。为编译原 readonly override getter，夹具的基础轴成员改为虚拟属性，并用 Axis 继承既有驱动替身；这是受控类型适配，不是生产源码修改。

## 实际第九任务与连续链

两条 UI 入口、Online/OnlineWithAutoUnloader 两种配置均验证实际第九父任务。原方法移出物料、清空 Unit/区段状态并保存，父任务继续进入原 NoMaterial 门控，供晶仍可处理独立需料事件。

四组完整连续链由实际第五、第六、第九 Task 完成 Bond→等待区→出料区→收板机，保持两个 Bond 子任务、两次 Refresh、三次 Save；等待区运动两次，出料轴运动两次并由原 Stop 包装停止两次。SDK 要料门在等待区保存时受控持有，用于观察三阶段提交，随后释放原方法继续执行。

72 组直接调用组合覆盖六配置、区段物料状态、三个传输状态、两个 SMEMA 输入。原控制器不检查配置，NoMaterial/Transfering 在读取要料信号之前返回 NoStart，Ready/Alarm 且有料时可读取信号并执行。实际第九任务仍只在 Online/OnlineWithAutoUnloader 分配；其他配置组合明确是直接调用控制器。

## 原硬件 getter 与 SDK 边界

三个原 getter 精确使用 `下游Smema要料信号`、`下料区后端物料检测`、`出料工作台X`。SMEMA 通过原模组/控制器包装直接读取 `GetInputValue()`，不调用 CheckStateForNums；出口物料仍调用 `CheckStateForNums(true,1,200)`，停止仍为 `StopMove(false,true)`。

[SDK 静态证据](transport-auto-unloader-sdk-evidence.json)保存 GetInputValue 与执行器两个方法体、无参数 bool 签名及两个仓库 DLL 哈希，仅验证元数据/IL，未执行 SDK 或证明部署版本。全部 13 个运动返回码在明确成功的运动状态/出口输入序列下均被原 void 包装忽略。

六个 null/错误类型硬件绑定分别验证原 getter 的 NullReference/InvalidCast 进入控制器 catch，并保留失败前的传输状态。动态替换仓库轴对象还证明：运动接收对象和速度取值可能来自不同次 getter；后续停止可针对替换后的轴。轴在最后一次出口采样后被移除时，原 Stop 的 null 防护可跳过停止仍提交。以上是注入的仓库变化场景，不证明实际配置会这样变化或设备运动结果。

## 卡料、停止与信号

首段卡料和尾段卡料分别覆盖 Abort/Ignore/Retry。两阶段使用相同报警文字，检查依靠精确 SDK 样本区分。Retry 再发运动；Ignore 不调用 Stop 也可清空物料并保存；Abort 由实际父任务执行原 Stop，之后在下一轮 WaitStart 退出。原第二个出口循环在有料时无 sleep，测试给出有限状态/输入序列，未修改该循环。

原 isManual 参数未参与分支，方法内部无 Stop/Pause 防护。两种参数值及稳定 Working/Stop/Pause 直接调用均可执行；实际父任务进入要料读取后执行原 Stop 或设为 Pause，仍可移动、停止轴并保存。Stop 后父任务与真实供晶退出，Pause 后父任务停在下一轮外部门控。提前 Stop/Pause 则阻止控制器工作，恢复 Working 可继续。

第九任务读取外部 SDK SMEMA 输入，不消费 Bin 的 AllowUnloaderMoveSignal。该真实事件被 Set 后要料仍为 false 时不移动；以后 SDK 要料变 true，无需再次发送 Signal 即可执行。

## Exception 返回被父任务忽略

九个要料/硬件/轴状态/运动/出口/停止/Save 故障分别验证：控制器 catch 返回 Exception，而原第九父任务只处理 NoStart/Abort/Success，未执行 Stop。机器仍 Working，真实供晶和父任务仍活跃，UI 启动 catch 不介入。

要料读取或其仓库 getter 在设置 Transfering 之前失败时，区段仍 Ready，父任务立即再次调用控制器。测试在第二次内层 catch 的受控门观察两个实际尝试，避免替身对话框立即返回后无限重试；未推断原生对话框关闭时间或设备 CPU 表现。

设置 Transfering 后失败时，状态不回滚，父任务下一次调用返回 NoStart，通常不再读取 SDK。Save 失败则保留已清空的 Unit、NoMaterial/Ready，下一次调用也被门控。原控制器无回滚，Save 调用失败不能当作持久化成功。null 皮带设置及 HasMaterial 但 Unit 为 null 的情形也分别验证。

内层日志/对话框自身抛错时，错误逃出控制器并进入父任务外层 catch，任务可正常结束但机器仍 Working、供晶仍活跃。父任务 catch 对话框再失败时，实际 Task Faulted 并被检查观察。Abort 后的 Stop 日志/UI 清理故障分别保留 Working/Stop 的提交顺序，未完成物料保存。

## 验证与接续

专项命令为 `node scripts/test-transport-auto-unloader-integration.cjs`，来源审计为 `node scripts/build-transport-auto-unloader-integration-audit.cjs --check`，SDK 静态契约为 `node scripts/build-transport-auto-unloader-sdk.cjs --check`。审计核对完整文件/片段哈希、原文偏移/行号、信号初始化和报告哈希。

初次基线有 C# var 多变量声明的夹具编译错误，拆开声明后 36 项连续流程检查通过，扩展到 287 项后仍通过；记录见 `.archify-work/auto-unloader-integration-baseline.log`、`auto-unloader-integration-baseline-v2.log`、`auto-unloader-integration-expanded.log`。清理释放替身门、改变 SDK 假状态以结束原循环并停止/等待任务，不计为原生产流程的成功或停止证明。统一回归与四种宽度阅读器结果见 [验证回执](transport-auto-unloader-integration-verification.json)。

下一项接原点胶→Bond 控制器、气缸/夹紧/同步皮带包装及实际第五父任务，再延伸现有连续链；[接续证据](transport-dispense-bond-next-evidence.json)保留原代码与待验证范围。其余四个入料/点胶传输、载具检查/MapMaterial、程序/池/域/SDK 和现场验收继续推进。
