# 点胶1传入点胶2：原夹紧、Unit 偏移与实际任务验证

原 `TransferDispense1ToDispense2`、点胶 Clamp/同步皮带、Unit.System1MoveDistance/TransportUnitInfo/CoordinateSystem、BaseMatter 信息/坐标声明、配置/预点胶属性及控制器私有程式 getter 已接入完整输送生产器、两条 UI、准备链、真实供晶 Task、原 Stop 和既有下游链。276 项受控检查通过：136 个完整方法、65 个属性、8 个枚举、14 个字段、23 条信号初始化契约，共 223 段原代码、106 个来源文件；本专题增加 124 段链路源码快照。

原方法体、真实 Signal、父任务和 500ms/200ms/50ms 延时保持不变。GeneralCoordinateSystem/Distance、BaseInformation 类型、Unit 构造函数、域/程式/配置生命周期、SDK、仓库、日志/对话框/保存和原生控件是明确替身。坐标与信息的原属性、cast getter 和偏移方法已编译，不等于完整产品模型验收：原无参 Unit 构造函数为空，本轮夹具为准备数据初始化 BaseInfo；原 Refresh 也仍为替身，真实构造/Init/Refresh 已列入下一项源码证据。剩余三个入料传输与原项目构建、配置/DLL、原生 UI 和设备验收继续待完成，29 个源码组保持 partial。

## 实际第四任务与五阶段链

两条 UI 入口各覆盖 Complete/Divide、第一段标志 true/false，以及全部六种装卸配置。真实父任务通过 AllowDispense1TransferToDispense2Signal.Wait 接收许可，再顺序调用 UnClamp、挡料1下降、挡料2上升、同步皮带、Clamp；收到许可之前无这些动作。

非手动方法只检查 HasMaterial，不使用手动 Divide/IsTuInDispense1 条件。即使 Complete 或第一段标志已 false，也可执行并发布本次 TransferToDispense2FinishedSignal。两次实际事件验证重复动作：在 Divide 配置、初始 X=10、DistanceToRight=13 时，X 先为 23、再为 36。第二次不因标志已 false 而跳过。

手动模式只允许 Divide 且第一段标志 true；无料门在许可等待之前返回 NoStart并保留真实事件。直接手动调用不要求输入事件，也不发布父任务完成事件。原方法不调用 Save 或 Refresh。

两条 UI 的连续链由实际点胶1→点胶2、点胶→Bond、Bond→等待区、等待区→出料、出料→收板机父任务完成，Unit 身份保持，观察到点胶同步/异步各一次、Bond 同步一次、三次 Refresh 和四次 Save。最终坐标/标志在 Refresh 替身下保留，只证明该受控组合的身份和提交顺序；原 Refresh 会重新初始化坐标和其他产品状态，其实际结果仍待验证。

## 原夹紧和配置防护

四种 Clamp 模式、附加真空参数 false/true、附加输出为 null、可选 PL 限位为 null 与有输入但 false，分别验证输出值、先后顺序、原采样和报警路径。Lowering 不使用附加真空；其余真空模式仅在对象非 null 且参数 true 时操作。空皮带设置提示后正常返回；必需首路 PL 为 null 则直接抛错。

UnClamp 与挡料下降同时受系统1和输送配置保护；Clamp 只检查系统1，挡料上升和同步皮带不受这两个 helper 的配置保护。实际父任务在四个配置组合中都可继续提交偏移与预点胶标志，不能把 helper 的静默返回当作控制器 NoStart。

UnClamp 与 Clamp 的 Ignore/Retry/Abort 均经原方法执行。Retry 再次运行相应输出和采样；Abort 调用原 Stop 后正常返回 void，顺序控制器仍可能完成同步运动、区段状态、坐标/标志和 Success 发布。原父任务下一轮 WaitStart 才退出。此处没有原 Task.Run/WaitAll 子批次，气缸方法在当前父任务内顺序调用。

## 运动、Stop/Pause 和直接偏移

全部 13 个 SDK 返回码在受控成功回馈下被原同步 void 包装忽略；运动抛异常则进入原父任务 catch。位置 19、配置速度 80×倍率0.375=30，默认 accuracyMode 为 HighAccuracy(0)，沿用[SDK 静态契约](transport-dispense-relative-sdk-evidence.json)的四方法/两个仓库 DLL 证据。未执行 SDK 或证明部署版本、设备运动与到位。

许可等待中的 Stop 返回 Abort，无偏移/标志/完成信号；进入控制器前 Pause 保留事件并阻止动作，恢复 Working 后执行；进入前 Stop 阻止控制器并保留事后设置的真实事件。两条 UI 在许可已接受后 Stop/Pause，内部没有新的机器状态门控，仍完成动作、偏移、标志和发布，机器状态保持 Stop/Pause。

原 Unit.System1MoveDistance 在 Divide 时仅对 X 加当前 DistanceToRight。-13/0/13 三个值与 Complete/Divide 组合直接执行，其他区段标志和预点胶标志不由这个方法更新。Distance 与坐标 SDK 类型在本轮为替身，这些数值检查不证明实际坐标 SDK 校验规则。预点胶属性的原 initializer 为 true，距离配置原默认值为 0；这不是原无参 Unit 构造后的完整对象状态。

## 晚期故障、域/程式替换和任务状态

两条 UI 下八个日志、输出、同步运动、坐标和域读取抛错位置，分别进入原第四父任务外层 catch。方法没有本地 catch 或 Exception 返回分支。对话框正常返回时 Task 正常结束，而机器仍 Working、真实供晶仍活跃、未发布本次完成事件；对话框再抛错时实际 Task Faulted，异常被检查观察。

日志接受前失败保留原 Ready/第一段标志；气缸或同步运动失败保留 Transfering。区段已设 HasMaterial/Ready、第一段标志 false 后，null Unit、配置、坐标、Distance、信息、错误 BaseInfo 类型或 null 域控制器可再失败。原 cast getter 的 InvalidCast 与后续 null 信息分别测试；信息/域失败之前 X 已偏移，标志仍可能未写。原方法无回滚和 Save。

域读取观察门在原坐标更新之后、预点胶写入之前持有。替换域控制器对象仍经原私有 getter 获取同一全局程式；替换全局程式则把预点胶标志写到新程式 Unit，先前 Unit 的坐标和旧区段提交保留。此为注入的域/程式变化边界，不证明实际生命周期会这样变化。

## 验证与接续

专项：`node scripts/test-transport-dispense12-integration.cjs`；来源审计：`node scripts/build-transport-dispense12-integration-audit.cjs --check`。审计绑定全部来源/片段哈希、偏移/行号、原信号初始化、报告及精确数量，并确认本传输无 Task.Run/WaitAll、Save 和本地 catch。

38 项基线通过后，初次扩展在清理中出现 NullReference：故障场景把域控制器置 null，原 Stop 也依赖该字段。清理前恢复夹具字段、完善错误输出后，276 项扩展通过。日志为 `.archify-work/dispense12-integration-baseline.log`、`dispense12-integration-expanded.log`、`dispense12-integration-expanded-v2.log`。恢复字段、清除故障注入、释放观察门和 Stop/等待线程是测试清理，不计作生产恢复或设备停止证明。统一回归和四宽度阅读器结果于收尾登记回执。

下一项原入料皮带→点胶1、实际入料父任务、原装卸配置/传感器/皮带/需料包装及 Unit 构造/Init/Refresh 边界，见[接续源码](transport-loading-belt-next-evidence.json)。其余两条入料、载具检查/MapMaterial、真实产品/程序/池/域/SDK 与现场验收继续推进。
