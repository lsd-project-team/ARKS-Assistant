# 公共视觉：源码复核

覆盖原清单 05.01–05.06，以 ZX2200 主程序调用为入口，沿直接引用工程阅读 PR 实现。设备代码只读；Archify 引用此已提交复核记录，原文件字节指纹与行范围另由 source-evidence.json 核对。算法模块及相机驱动的现场行为不因静态说明而视为验证。

## 模板集合与初始化

System2CommonService.GetCurrentRecipePREntityNameList 收集当前料片、顶针、焊后检测、吸嘴、普通或异形产品层级的定位模板，并加入 IPTCenterCircle。LocateConfig.GetPrNames 仅收集 P1–P3 非空名称，没有 P4。不能把这个集合称为当前工程所有视觉引用的完整检查器。

Machine.InitPR 返回 Task：关闭旧方案、创建新方案、获取名称集合；模板仓库为空时尝试从备份恢复配置。逐名查找，找到则调用 Alg?.InitVmProcedure，找不到仅记日志。末尾调用目前完全注释的 LoadDispensePr，然后置 PrInitSuccess=true。BaseAlg.InitVmProcedure 优先载入产品 .prc，否则载入默认算法 .prc，捕获异常后只记日志。标志为 true 不保证每个模板及算法实际有效；外层异常则弹窗、记日志并重新抛出。此入口没有先复位旧的成功标志。

依据：System2CommonService.cs 37–90；LocateConfig.cs 159–178；Machine.Sustain.cs 116–179；DispenseRunTimeProvider.cs 85–128；BaseAlg.cs 291–318。

## 单个定位点的调用链

S1/S2 按 BaseMatter 和 P1–P4 类型获取示教点、模板名与对焦配置，把局部拍照点转到 G0，再应用所属工位的相机偏移。S1 先等待单步、拒绝 Fail 实体；S2 按 BondCameraVision 调用。自动定位失败且 IsAroundLocate 开启时，按 +X、−X、+Y、−Y 尝试周围位置，成功即结束搜索。

自动结果为空时，调用物料定位报警对话；OK 使用回传 MatchResult，Ignore 禁用对象并返回 false，Abort 停机返回 false，其他也返回 false。OK 本身未统一保证回传非空结果。成功路径将匹配值转换成 G0 与局部结果，ChooseInfoByType 选择对应 P1–P4，SaveInfo 写入匹配中心/角度、局部点、G0 点、拍照 G0 位置及 IsVisionSuccess/IsUpData。这里保存的是对象字段，不是落盘保存。

依据：System1Domain.cs 205–360；System2Domain.cs 444–585；TuService.cs 472–522；VisionResult.cs 60–67。

## 硬件、采图与算法

DispenseVision 与 BondCameraVision 在有目标点时，启动灯光任务并移动，随后 Wait 灯光任务。S1 使用灯光标定映射，S2 使用 Bond 硬件；可选对焦后，DryCycle 返回新建 MatchResult，没有执行本次真实定位，但之前可能已经移动或设灯。S2 自动重试由 VisionRetryTimesLimit 控制，每次等待 DownLookVisionDelay；S1 单次接口没有同一重试循环。相机命令返回与算法结果分别处理，不能以方法返回推定全部驱动到位。

PREntity.SetHardware 绑定相机、XYZ 和灯名。DoWork 在锁内可覆盖硬件；isSetLight=true 时设灯、等待 15ms，并设置曝光/增益/伽马，设置失败在此只记日志继续。另一 SetLight 接口则检查失败并抛异常，两个入口不同。Excute 先采灰度图；空图记日志并维持 None，非空则复制图、按闪光配置异步关灯，再 SetImage/FindModel、写 AlgResults。FindModel 或前部调用异常并非都由存图 catch 捕获。

依据：DispenseVisionController.cs 123–185；System2Controller.Vision.cs 159–281；PREntity.cs 101–179、339–431、458–637。

## 结果、缺陷与距离

VisionService.Vision 找不到模板时报警并返回 null；DoWork 非 Success 返回 null；MatchResult 成功时只复制中心和角度，其他成功结果直接返回。VisionDefect 成功返回 AlgResults；它在 null 判断前已写 IsDefectPR=true，缺失模板可能先触发空引用，不能画成保证到达的报警分支。DoWork 成功表示算法调用成功，缺陷列表的 IsSuccess 仍需调用者按算法含义判断。

BacksideCrackDetect 在离线/空跑返回 false；在线先用给定匹配值 SetFix，再执行模板。首结果 IsSuccess=true 表示检测到崩边；执行不成功也返回 true，未检测到则 false。模板不存在抛异常。不能把这里的 true 解释成“芯片合格”。

DistanceCheck 比较示教两点距离与结果两点距离，超过容差时弹出 Retry/Ignore/None/Abort；只有通过路径写 OldTwoPointDistance/TwoPointDistance。S1 Retry 回首点且后续改走人工定位；None 先禁用仍更新坐标。S2 Retry 重新识别两点后再次检查；None 禁用并直接 true，不更新该次坐标。Ignore 则继续所属更新路径。

依据：VisionService.cs 78–145、158–202、257–314；System2Controller.Vision.cs 737–775；System1Domain.cs 96–196；System2Domain.cs 279–432。

## 产品层级与动作返回

S1 的载具、基板、模块及焊点动作分别传当前对象到 System1MatterVision；S2 四层动作传到 System2ObjectVision，再到 System2MatterVision。S2 的 IsDoWork 检查定位开关、加工屏蔽、已定位状态；载具/基板/模块另检查子级工艺是否完成，基板另要求 EntityState.Process。S2 载具 Divide 直接成功；离线四层动作直接置定位标志并返回，S1 离线分支置标志后未统一直接返回。

这些动作在直接调用的 bool 结果未被检查时，末尾仍返回 Success；异常另转 Exception。节点 Success、IsVisioned、实际采图成功不能混作同一件事。普通域方法 AdjustType.None 会置 IsVisioned=true 后直接 true；Mapping 禁用且 byMapping=true 则跳过。定位结果何时更新父链见产品坐标专题，避免重复推导。

依据：S1CarrierVisionActionNode.cs 44–68；S1SubstrateVisionActionNode.cs 34–56；S1ModuleVisionActionNode.cs 36–58；S1DispenseCorrectionActionNode.cs 48–78；S2CarrierVisionActionNode.cs 36–123；S2SubstrateVisionActionNode.cs 55–139；S2ModuleVisionActionNode.cs 55–135；BondPositionVisionActionNode.cs 58–128；System2Domain.cs 267–292。

## 身份识别与墨点

S1/S2 MatterIdentity 关闭识别时直接 Success；开启后取身份配置的点和模板执行 CodeResult 识别，失败进入报警。Ignore 禁用对象但返回 Success，Abort 停机返回 Abort；正常或人工识别成功后才置 IsIdentity 并写 IdentityCode。CheckInkDotActionNode.DoWork 当前直接 Success，未执行其后注释里的墨点流程。

Nine 搜索中启用 IsInkDotSearch 时，以墨点模板设灯采一张图，对九个候选逐项检测；只处理 Exist=true 的候选，先按该颗匹配值 SetFix，再 DoWork(bmp)。首结果 IsSuccess=true 或执行失败均将 Exist=false。模板缺失抛异常；这条真实墨点链路与上面的空动作节点分开记录。

依据：System1Domain.cs 553–626；System2Domain.cs 1018–1090；CheckInkDotActionNode.cs 32–34；Block.SearchNine.cs 466–530。

## 人工处理与模板修改

界面 VisionAlarm 在 UiLock 内同步 Invoke 弹窗，读回 DialogResult 和 BaseAlgResult，再写报警记录并 ResetAlarm。报警后台可持续采图/执行模板以预览，编辑和 OK 先禁止预览、等待 isWork=false。普通 OK 再次 DoWork，失败则留在对话中允许重试；成功复制结果后返回 OK。无模板、双模板、晶圆线程及胶检分支可直接 OK，不保证新匹配值。Skip 返回 Ignore；Abort 主动 Stop 并返回 Abort；ReDispense 按钮返回 Retry，具体含义随调用者与显示文字而变。

修改模板先 Pause，按硬件打开编辑器；点胶灯值在进出编辑器时分别映射/反映射，然后仓库 Save、Continue、允许预览。此处理没有统一 finally 保证异常后恢复；不能画成编辑成功或异常都自动继续。AdjustAction 另有自身异常捕获及末尾重新读取 AlgResult，不把不同视觉包装方法合并成一个返回契约。

依据：UcmainSystem.Action.cs 273–301；FrmVisionAlarm.cs 135–184、273–329、339–407、415–507、565–567；System2Controller.Vision.cs 58–149。
