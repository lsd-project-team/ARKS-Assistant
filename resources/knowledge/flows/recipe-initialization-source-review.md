# 配方初始化、视觉加载和复制：源码内部复核

更新：2026-09-28。范围是Main配方链路调用到的指定方法，跨模块证据不意味着这些模块已经完整验收。生产源码未修改。

## 真实工作顺序

ReLoadRecipe先将PrInitSuccess置false，然后依次调用六个程式初始化方法；前四个只改FilePath并将instance置null，第五个先清除供片记忆并按条件置重建标记，第六个再改路径并清实例。此时尚不能证明所有配方JSON已成功读取。在线分支随后关闭旧视觉方案、创建新方案、收集PR名称、逐项初始化视觉过程，再调用目前无实际语句的LoadDispensePr，最后置PrInitSuccess=true。离线是在六个初始化之后才跳过视觉过程。

主调用证据：[InitProgramNodes / ReLoadRecipe 124–203](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L124)。

## 六个程式初始化

基础目录由当前RecipeID决定：Settings/RecipeParams/<RecipeID>；见[PathConfig 82–88](../../trunk/AKRS.Galaxy2.MachineSupport/Config/PathConfig.cs#L82)。下列JSON扩展名和文件路径来自代码，实际序列化/反序列化行为不能只据扩展名判断。

|顺序|方法与目标文件|真实副作用/失败边界|源码|
|---|---|---|---|
|1|InitProductConfiguration / ProductConfiguration.json|FilePath更新，instance=null；方法本身没有读文件、迁移数据或Save。|[ProductConfiguration 71–75](../../trunk/AKRS.ZX2200/TransportUnitSystem/ProductConfiguration.cs#L71)|
|2|InitTransportSystemProgram / TransportSystemProgram.json|同样只改路径并清单例。|[TransportProgram 71–75](../../trunk/AKRS.ZX2200/TransportSystem/Models/TransportProgram.cs#L71)；[路径 71](../../trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs#L71)|
|3|InitBondProgram / BondProgram.json|同样只改路径并清单例。|[BondProgram 216–220](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/BondProgram.cs#L216)；[路径 158](../../trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs#L158)|
|4|InitSystem1Program / DispenseProgram.json|同样只改路径并清单例。|[System1Program 56–60](../../trunk/AKRS.ZX2200/DispenseSystem/Models/System1Program.cs#L56)；[路径 90](../../trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs#L90)|
|5|InitWaferSystemProgram / WaferSystemProgram.json|先ClearWaferSubMemory，成功后才改路径、清单例；清理期间异常则后两步不会到达。catch用new Exception(e.Message)重新抛出，没有保留原异常作为InnerException。|[WaferSystemProgram 70–90](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemProgram.cs#L70)；[路径 187](../../trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs#L187)|
|6|InitProcessProgram / ProcessProgram.json|只改路径并清单例；若前面的供片初始化抛出，本步不会执行。|[ProcessDomain 37–41](../../trunk/AKRS.ZX2200/Main/Machine/Process/ProcessDomain.cs#L37)；[路径 173](../../trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs#L173)|

这些类型继承 Singleton<T>；排除 bin/obj 的 trunk C# 源码未包含该通用基类定义。现已从[随仓库 DLL 静态 IL](persistence-save-contract-review.md)核对 GetInstance 在锁内先 Load、仍为空才构造 T，Load 则先构造、再按 FilePath 读取 JSON。缺失文件、读出 null 或捕获范围内反序列化失败可使其走默认实例分支；构造和属性订阅异常不在 JSON helper 的 catch 内。此证据不证明现场实际加载版本、配置迁移、磁盘保证或生产成功；也不能与仓库另一个 SingletonJson<T> 混同。

## 供片记忆清理不是全部状态归零

[ClearWaferSubMemory 1207–1224](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L1207)无条件执行CurrentSlotConfig=null、CurrentTablet=new NullTablet、CurrentLayerNo=0。CurrentStaticAdapterTablet直接赋新对象的语句是注释。

IsClearStaticAdapter为true时使用默认两个true参数；false时传(true,false)，仍清上述三项并置料盒重建标记，只跳过静态华夫重建标记的置位；不会主动清除先前已经为true的静态标记。

两个SetNeedReCreate...方法都先将bool置true，然后调用WaferSubDevicePara.Save：[料盒 125–129](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/DeviceParams/MagazineBoxDevicePara.cs#L125)、[静态华夫 418–422](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/DeviceParams/WaferTableDevicePara.cs#L418)。因此清理有保存调用副作用，不能当成纯内存操作；Save失败前内存可能已经改变。标记置位也不等于此处已经重建实体。

## 视觉清单和成功标记的边界

1. [GetCurrentRecipePREntityNameList 37–92](../../trunk/AKRS.ZX2200/BondSystem/Services/System2CommonService.cs#L37)：按条件收集供片载具、顶针、焊后检测，添加吸嘴PR；异形产品按BaseConfigs收集，否则收集TU左右/普通定位、基板、基岛和焊点定位；固定添加IPTCenterCircle。此方法没有去重，未验证各名称均能找到实体。子方法返回项完整性仍待各自核实。异常弹窗后throw ex。
2. 主调用对找不到实体只写日志并继续；找到实体则调用InitVmProcedure，随后写“加载成功”。不能从这条日志推断SDK已成功加载。
3. [BaseAlg.InitVmProcedure 291–319](../../trunk/AKRS.Galaxy2.PR/Models/Algs/BaseAlg.cs#L291)：加锁，若保存目录下<Name>.prc存在则Load该文件，否则Load通用模板；设置过程名、参数、图像源和输出图像工具。**所有这些语句位于catch内，异常只记录日志，不重抛，也没有成功返回值。** 多个字段逐次赋值，无统一回滚。
4. [GetPRSavePath 325–351](../../trunk/AKRS.Galaxy2.PR/Models/Algs/BaseAlg.cs#L325)：Calibration类别使用DeviceParams/设备标定PR，其余使用DeviceParams/所有产品PR，目录不存在时创建；异常记录日志并返回null。不是每个配方自己的PR目录。通用模板来源为Application.StartupPath/AlgFlowTemplates，见[SourcePR 34](../../trunk/AKRS.Galaxy2.PR/Models/Algs/BaseAlg.cs#L34)。
5. [LoadDispensePr 85–128](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispensePara/DispenseRunTimeProvider.cs#L85)的函数体全部是注释，没有执行清空、复制、加载、异常处理或配置判断。主调用仍然存在，但不能将此空操作画成已完成的点胶模板复制。

据此，存在“单个PR加载出错被内部记录 → 主调用仍写成功日志 → 后续PrInitSuccess=true”的静态控制路径；是否发生及对设备影响未实测。此标记表达代码设置的状态，不是所有视觉模板有效性的完整验证。

## 新配方PR复制链路

[TuService.CopyOldRecipePR 1081–1163](../../trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs#L1081)：查询旧名称对应ID→临时将ProductConfiguration.FilePath指向旧配方→清单例→读取产品配置并拼接候选名称→恢复当前RecipeDirPath并再次清单例→按视觉仓库中实际存在且名字匹配的实体复制→仓库Save。

- 候选包括异形定位Mark或普通TU/基板/基岛/焊点Mark与ID识别项；不是全仓库复制，也不能等同于上面的全部运行PR清单。
- 恢复路径不是finally；候选构造期间异常可能使路径仍指向旧配方。未匹配到仓库实体的候选不会进入复制循环。
- 新名称由string.Replace(oldName,newName)生成，是匹配子串的替换，不是仅前缀替换；该方法未做去重。
- [PREntity.CopyPREntity 740–766](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L740)：源实体为空返回null；否则调用文件复制helper、Clone、修改算法名称、InitVmProcedure、SetName、AddVisionEntity，返回对象。调用方未检查返回值。
- CopyOldRecipePR没有局部事务回滚；中途异常可能中断最后的仓库Save。Helper的覆盖策略、Clone深浅复制、AddVisionEntity同名策略尚待核实，不能从方法名推断。PREntity文件部分中文注释编码显示异常，结论以可读可执行语句为依据，未重编码源文件。

## 本轮补深与后续缺口

### 已补深：克隆、同名处理与重建消费方

- [PREntity.Clone 659–675](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L659)通过相对路径Guid.json调用保存、读取helper，再删除临时文件并SetName。不是MemberwiseClone，也不能在缺少序列化helper实现时宣布所有运行对象完整深拷贝。任何异常直接返回null；删除不在finally，前面失败可能留下临时文件。CopyPREntity随后直接访问返回对象的Alg，未检查null，因此克隆失败可在调用方继续抛异常。
- [VisionEntityRepository.AddVisionEntity 75–86](../../trunk/AKRS.Galaxy2.PR/Resipository/VisionEntityRepository.cs#L75)用List.Find找到首个名字相等对象，若存在则移除，再Add新对象；不是拒绝同名，也不是删除全部重复对象。此方法本身没有Save。
- [RemoveDuplicatesEntity 91–95](../../trunk/AKRS.Galaxy2.PR/Resipository/VisionEntityRepository.cs#L91)只将首组转换为局部列表，未写回PRVisionList；不能把其名称当成实际清理全仓库重复项的证据。
- [VisionEntityRepository.Save 109–128](../../trunk/AKRS.Galaxy2.PR/Resipository/VisionEntityRepository.cs#L109)先调用保存helper，再在主文件存在时删除旧备份、复制主文件为备份；异常只日志，不重抛。CopyOldRecipePR返回不能单独证明仓库文件/备份保存成功；删除备份与复制之间没有局部回滚。
- 供片重建标记在[WaferSystemDomain.CheckIsReady 371–411](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemDomain.cs#L371)被消费。不是设置标记立即执行：必须到达该检查段。静态硬件已配置且静态重建标记为true时创建静态载具，设Good并复位标记；料盒标记为true时将当前配置槽位置Good，按当前料片类型初始化Wafer或Adapter，再复位标记。前面检查返回或抛出时不会到达此段；该方法末尾catch弹窗并返回false，未回滚已有副作用。
- [CreateStateWithStaticAdapterTablet 401–413](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/DeviceParams/WaferTableDevicePara.cs#L401)先替换CurrentStaticAdapterTablet；名称为空字符串时直接返回，未创建Adapter实体。调用方没有检查本方法完成状态，仍继续设SlotState=Good、可空访问AdapterState并复位重建标记。这是静态控制路径，不是已经复现的设备故障。
- 另一消费入口是[FrmSlotsState构造函数 47–61](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/FrmSlotsState.cs#L47)：打开窗口时若料盒标记置位，就将当前配置槽位置Good并复位/保存标记，再深拷贝配置用于显示。此操作发生在用户点击保存前，窗口不是纯只读查看；该路径没有同样的当前Wafer/Adapter初始化分支。
- 两个ResetNeed...方法先将标记false再Save：[料盒 134–138](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/DeviceParams/MagazineBoxDevicePara.cs#L134)、[静态盘 427–431](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/DeviceParams/WaferTableDevicePara.cs#L427)。保存与内存复位不是在这些方法里实现的事务。

载具实体创建、槽位递归更新及本地SingletonJson保存包装已继续展开，见[供片重建模块复核](wafer-rebuild-module-review.md)；缺失helper仍未取得实现。

- 追踪Singleton<T>、文件复制helper的实际依赖版本/实现；未取得实现不宣布JSON迁移或覆盖策略已清楚。
- Clone、AddVisionEntity和重建标记两个消费入口已核实；继续运行PR清单子方法、槽位构造/窗口提交语义和序列化helper，确认更下层行为。
- 核对运行中切换配方的UI权限/禁用条件及异常恢复入口；本轮未执行设备动作。
- 增补重载失败、模板缺失、复制部分失败等测试场景，再进行可构建环境与实机验收。

[上层Main链路](main-module-review.md) · [模块进度](module-review-status.md)


模块交接：[视觉复制与加载](vision-recipe-module-review.md) · [供片重建与保存](wafer-rebuild-module-review.md)。
