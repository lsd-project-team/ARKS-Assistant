# 完整输送域、当前上下文与原始离线节点验证

180项原生CLR4.0.30319.42000检查通过；测试EXE、完整结果、实际保存的输送JSON及两份只读IL重放一致。业务使用1137份原Compile源码的完整Main/资源产物，16个源码资源程序集的真实物理位置核对通过。测试宿主是新代码；原源码、SDK单例、路径和业务类型未替换。

## 原始对象与执行范围

实际TransportDomain、TransportController、TransportModule、TransportProgram构造并绑定5个载台、8个模组和3个任务对象。五个子控制器初始引用同一原单例的五个载台对象。只读Main构造闭包39个精确签名方法加22个选定方法IL，以及SDK Singleton的5个方法，限定展开范围不含所有外部/动态分派。原硬件/环形限位配置路径来自宿主Application.StartupPath；运行前缺失配置、实际SDK硬件仓库为空。IsTransportConfigured=false的原StartTask及Enable=false的上下料Start入口返回，没有创建其Task字段中的任务对象，未调用输送模组初始化或在线任务循环。

两个载台通过原UpdateTransportUnit创建两棵独立2基板×2基岛×2焊点树，原构造器调用S1/S2完整步骤注入。两个原动作控制器公开GetNextActionNode/FinishCurrentActionNode各完整遍历53条消息，共106次选取，返回原目录节点引用，当前工序和适用实体上下文对应实际树。仅反射读取WorkMessages、任务字段和模组字段；没有反射写当前消息或实体，没有未初始化对象。

8种原始识别节点（S1/S2×载具/基板/基岛/焊点）的完整IsDoWork核验失败实体、关闭识别、启用未完成实体、识别完成后的跳过。MachineWorkMode=OffLineWork时实际DoWork成功返回30次，将对应原实体IsIdentity标记true并保持末态Stop；WorkStart在Running赋值之前，WorkStop在Stop赋值之后。另2次原DoWork尝试由测试回调抛异常：开始回调在try之前，异常直接外抛、State仍Idle且不调用WorkStop；停止回调异常从finally外抛，但IsIdentity副作用已提交且State为Stop。共32次DoWork调用尝试，不把2次异常计为正常成功。没有在线识别、相机/轴动作、VM算法、报警弹窗或原Program.Main。

## 已复现的当前上下文边界

1. [S2初始化当前消息](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L930)没有在消息前置层级未匹配时清除较低层缓存。真实排程索引28的BondSubstrateVision消息是基板2/基岛0/无工序，当前Substrate已是2，Module仍来自基板1的基岛2，BondPosition仍为bp-b，CurrentMatter显示“基板号2基岛号2焊点名称bp-b”。同位置S1按当前消息重新计算，Module/BondPosition为null。此处是可观察的混合上下文，不推断该前置动作一定读取较低层缓存驱动设备。
2. [S2 GetNext](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1042)耗尽排程后返回null、当前消息清除，最后的实体缓存仍在；GetCurrentProcessStepName空引用，S2焊点识别条件会读取已识别缓存而跳过。S1同场景当前实体为null，其焊点识别条件空引用。正常调用方在GetNext返回null时如何退出，仍需完整任务链验证。
3. S2 Finish重置排程再取得第一条载具前置消息，旧实体缓存仍在；[ChangeNameToActionNode](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1082)用参数映射节点名称，却通过内部当前消息刷新上下文，传入另一基板/基岛/步骤不会切换实体。未知节点返回null，缓存保持。

## 保存、重载与引用合同

原TransportProgram真实SDK Save/Load执行，宿主固定配方目录下TransportSystemProgram.json为2011字节、HeaterTemperature=123。源码明确以JsonIgnore排除运行态TransportUnit/有料状态/传输状态，JSON及实际重载符合声明：运行态单位为空、无料、Ready。这里不把主动排除运行态字段写成序列化故障。

SDK Load会替换静态单例。此前构造的5个子控制器[基类SubSectionProgram引用](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/BondSubSectionController.cs#L75)仍指向旧载台，原单位仍在；TransportController.IsExistTu与域单例getter读取新载台，返回无单位。同一个固晶控制器的[派生bondSubSectionProgram getter](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/BondSubSectionController.cs#L60)也读取新单例，和它的基类引用不同。S2先前缓存焊点仍在，两个系统的载具识别条件则因新载台单位null空引用；S1载具视觉条件抛明确的缺失单位异常。不同方法使用哪条引用必须逐一核对，本次未把所有派生运动方法都归为使用旧引用，也未证明真实配方入口缺少重建。

实际SDK Save是实例方法，但内部序列化静态instance。通过旧对象调用Save时，它的HeaterTemperature=999不会被保存，新单例的123被保存，文件字节保持。只读SDK IL确认Load的stsfld instance与Save的ldsfld instance/SaveGenericObject调用；不是用替身仿造。

## 证据与剩余

首轮测试宿主编译actualexit1/4条错误：ActionLevelEnum原成员是Carrier、ElementCoordinate缺少原坐标命名空间；失败源码/日志保存，仅修改宿主枚举和imports。先通过176项，再追加4项核验基类/派生新旧引用、耗尽/重载后的实际节点条件及32次调用口径；原176条名称/顺序是180项子序列。30份新增冻结文件绑定父3292份，共3322份。见[测试](native-transport-context-test.json)、[审计](native-transport-context-audit.json)、[进度](native-transport-context-progress.json)。

本次180不同于原生251、旧受控278/目录119、正式1328、其他58/98/124；不相加认定覆盖，也不改40专题3817快照。LC5/Fody2/VM5失败和388资源1498条通过证据保持。下一步核对真实配方重载/重建合同与节点选择后的任务异常/退出，再推进在线节点/下层算法、就绪负分支、PR/校准/测量、IO稳定性和原完整构建/部署/UI/设备；16工程/29组/1436文件/13项整体未完成。
