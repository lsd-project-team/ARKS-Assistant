# ZX2200/TransportUnitSystem：生产载具模型与动作注入

2026-09-28。状态：部分复核。这里追踪载具实体的生成、坐标与动作注入；不把该数据模型模块等同于TransportSystem的硬件搬运调度，也不声称完成全部示教、映射和视觉计算。

## 已确认的执行顺序

1. 产品配置初始化更新当前配方目录下的ProductConfiguration.json路径，并清除单例；IsTransportUnitReady只检查TransportUnitConfig.IsAssistantSucceed，不等同于所有配置及设备均可用。[ProductConfiguration.cs:71](../../trunk/AKRS.ZX2200/TransportUnitSystem/ProductConfiguration.cs#L71)。
2. 带系统参数的TransportUnit构造先建立BaseInfo，再执行Init、生成时间名称，最后按System1或其他值选择系统偏移。字符串构造也执行Init，但不调用这两个系统偏移方法；无参构造为空。[TransportUnit.cs:65](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/TransportUnit.cs#L65)。
3. Init读取当前异形配置，建立TU坐标，按IsOppositeSex选择常规或异形基板构造，随后ModifyMatter，再先调用System2的InjectSteps、后调用System1的InjectSteps。这里是注入调用顺序，不是实际点胶/贴装运动的执行顺序。[TransportUnit.cs:107](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/TransportUnit.cs#L107)。
4. 常规基板构造会修改当前SubstrateConfig：非多件设数量及行列为1并重建坐标；输入间距分支重写坐标列表，然后按Count创建Substrate。异形分支按DownConfigs创建。不能把实体构造当成无副作用的配置读取。[TransportUnit.cs:261](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/TransportUnit.cs#L261)。

## 文件存储边界

TransportUnitStorage使用静态只读路径（配方目录/TransportUnitStoragePath），Save建目录并调用JSON helper，Read直接调用helper；包装方法没有本地catch或重试。路径在类型初始化时求值，并非每次Save重新取得当前配方目录。这里只确认该包装实现，尚不把它列为已证实的生产自动存储链路。[TransportUnitStorage.cs:25](../../trunk/AKRS.ZX2200/TransportUnitSystem/Model/TransportUnitStorage.cs#L25)。

## 正常上料及跨载台交接

- TransferAutoLoaderToLoading在上料段无料时发要料信号并检查前端来料；超时可Retry跳回要料、Abort返回、Ignore关闭ContinuousFeeding并返回NoStart。成功段先置HasMaterial，再构造System2载具，最后TransportProgram.Save；异常catch返回Exception，未见恢复此前状态的代码。构造或保存失败不应被描述为无副作用失败。[入口439](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L439)；[分支及创建489–549](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L489)。
- 上料到点胶段把同一个TU引用赋给目标，调用Refresh后清空来源；点胶到Bond段也传递引用，只有目标为null且isManual时才重新构造，随后Refresh及保存。这不是每次搬运都创建全新产品。[交接826](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L826)；[交接1478](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1478)。
- Refresh重建TU坐标、逐基板Refresh，清TU及所有基板/基岛/焊点的IsVisioned和IsMeasureHeight，并复位两个偏移标记。这里只证明这些标记置false，不声称删除了全部视觉结果对象；下层Refresh是否改变其他状态仍待展开。[Refresh135](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/TransportUnit.cs#L135)；[逐基板362](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/TransportUnit.cs#L362)；[清理601–642](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/TransportUnit.cs#L601)。
- SetSystem1OffSet/SetSystem2OffSet各自检查对应标记，未应用才将配置偏移累加到Distance并置true。两者不是互斥分支，刷新后可以再次应用；何时再次调用需结合各生产任务核对。[526–551](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/TransportUnit.cs#L526)。

## 动作注入与异常副作用

System2Domain.ActionNodesService实际类型是S2ActionNodeController，System1对应S1ActionNodeController，不能按相近服务文件名猜测。[S2类型113](../../trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs#L113)；[S1类型87](../../trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs#L87)。两套InjectSteps遍历基板→基岛→焊点→ProcessSteps，按BondPositionName匹配；仅在字典没有ProcessStepName时添加false，已有键不覆盖。方法本身没有执行设备动作，也不清除旧步骤键。[S1 859–882](../../trunk/AKRS.ZX2200/Main/Machine/Process/S1ActionNodeController.cs#L859)；[S2 1410–1433](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1410)。

ModifyMatter按异形、LagerNumber数组或普通配置列表更新焊点状态。任意try内异常都会调用ClearInformation并保存产品配置；ClearInformation清普通状态列表，并按当前数量建立默认Enable数组。catch没有重新抛原异常、返回失败或再次调用ModifyMatter，因此清理/保存成功后构造可继续注入步骤，实体此前已修改的项也未回滚；若catch中的清理或保存再次抛异常，则仍会向外传播。[ModifyMatter887–957](../../trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs#L887)；[ClearInformation38–55](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/OtherConfig.cs#L38)。这属于需复现实验的配置副作用，不凭静态源码判定实际产品必然受影响。

常规Substrate构造按配置计算WorkIndex、建立坐标后CreateModule；异形构造使用传入的OppositeSex并调用InitModuleByOppositeSex。下层基岛和焊点常规/异形构造已补充静态复核，见[mapping-constructor-config-review.md](mapping-constructor-config-review.md)；运行仍未验收。[Substrate51–99](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/Substrate.cs#L51)。

## 输入、输出与待完成项

- 输入：产品配置、异形层级、机器坐标系、系统选择、两套动作服务；输出：TU实体、基板集合、注入后的动作数据及偏移状态。
- 已读构造与初始化方法没有本地异常重试或回滚；上层生产调用如何处理，需按实际调用方分别核对。
- 待闭合：构造及Refresh的实际配置/坐标库行为、偏移实际调用时机、全部ProcessSteps生成与消费、视觉更新，以及Mapping端到端运行；已有专题不等同整体完成；生产完整传送控制另见既有专题，不以本轮局部交接读取替代。
- 外部Singleton及JSON helper实现/版本、配置一致性、构建和实机运行仍未验证。
