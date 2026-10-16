# 标定参数来源与PR执行链

本专题补齐[标定子调用契约](calibration-dependency-contract-review.md)中的取放参数服务，并把既有[视觉运行审计](vision-runtime-module-review.md)连接到标定无参DoWork调用。没有运行设备，也不修改生产源码。

## 标定实际使用的分支

[标定构造component:1870–1906](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1870)使用BaseCarrierConfig，把取放前后慢速段开关设true，速度和距离来自bMCDevicePara，设置真空/取片/放片/吹气延时；取放模式显式为Distance，WeakBlowProportion=1000。输入是内存参数对象，不是动作服务自行加载配置文件。

| 调用类型 | 参数来源 | 选出的平台硬件 |
| --- | --- | --- |
| 首次CarrierWithWaffle取标 | 普通Pickup字段、PickupForceMode；不是IPT字段 | switch落default，VacuumElectric=null；BlowElectric保留默认null |
| 后续BMC取标 | 同样使用普通Pickup字段 | System2Module.BMCVacuumElectric；不设置平台吹气对象 |
| BondOnBMC放标 | 普通Bonding字段、PlacementDelay、VacuumOffDelay、BondingForceMode | 同一个System2Module.BMCVacuumElectric |

取片映射见[GetPickActionParameter:40–163](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/Commons/PickActionService.cs#L40)，放片映射见[GetBondActionParameter:24–127](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/Commons/BondActionService.cs#L24)。返回的是新参数对象和硬件引用，这两个构建方法没有发轴移动或写电磁阀。

[PickAction消费:175–188](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs#L175)先打开吸嘴真空，再以空条件访问关闭平台真空；平台吹气仅在对象非null且延时>0时进入。因此华夫盒平台VacuumElectric=null不能理解为没有吸嘴吸气。[BondAction:450–467](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs#L450)另消费平台真空对象；具体时序以控制器为准，参数构建本身不是动作完成。

## 其他分支及输入边界

- 取片LeftIPT/RightIPT选IPT慢速、延时、力及力控模式，分别绑定左右真空与吹气对象；FlipTable使用普通Pickup字段，但硬件来自FlipModule，吹气延时来自CurrentFlipTool.BlowDelay。不同单例或工具缺失可在构建阶段抛异常，方法无本地catch。
- 放片BondOnTU、DipFluxOnTU、BondOnBMC走普通Bonding字段；其余枚举走IPT字段。硬件switch仅识别左右IPT和BMC，其余VacuumElectric=null。不能将所有未知枚举自动判为拒绝。
- 慢速开关关闭时，相关距离/速度不被赋值。默认值来自[PickActionParameter:16–92](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/Commons/PickActionParameter.cs#L16)与[BondActionParameter:14–66](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/Commons/BondActionParameter.cs#L14)：距离显式0、未赋值数值属性默认0，吹气对象默认null。未见服务内范围或负值验证，不意味着上游UI允许任意值。
- 取片ForceControlOutTime总从component复制；IsResetForceControlAdvanceDuringPickup只在CarrierWithWafer保留component开关，其余强制false。[156–162](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/Commons/PickActionService.cs#L156)。
- 两服务component==null均抛ArgumentNullException；取片服务的异常参数文本却写GetBondActionParameter。文本不是另一服务被调用的证据。

## 标定调用PR后的真实工作步骤

标定两个LocatePosition调用的是无参DoWork，选中[PREntity覆盖方法:339–433](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L339)，默认hardware=null、isSetLight=true、postImage=true。不走接收Bitmap的另一个重载。

1. 获取静态锁；无传入hardware则不执行SetHardware，使用实体既有相机和灯光配置。设置启用灯光，等待15ms，设置曝光/增益/Gamma；这些设置返回false只记日志，未在此直接返回失败。[341–392](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L341)。
2. 调用Excute采图、算法和可选存图逻辑；原图使用using，副本在Excute正常返回后由DoWork释放。若调用抛异常，这个副本释放点可能到不了，不能称为统一finally清理。[394–399](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L394)。
3. Excute先设置None，空快照记录并返回；有图则克隆，按闪光设置处理灯光，再执行算法。[458–515](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L458)。算法及存图异常边界、委托和异步存图队列已在[视觉运行审计](vision-runtime-module-review.md)展开；这里不把入队等同于落盘。
4. 仅prResult==Success构造显示对象，读取AlgResults[0].OutPutImg1；默认postImage=true会优先向已连接的检测或通用视觉窗口Post，无接收窗口则Dispose显示图。[400–431](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L400)。这里无本地catch，所以即使算法已成功，结果集合或展示依赖异常仍可能阻止DoWork正常返回。
5. 正常返回的枚举再由LocatePosition判断；并非仅凭FindModel的布尔值决定标定能否继续。灯光、结果窗口与存图是标定PR调用的副作用，不应从链路图中全部省略。

## 剩余工作

证据：[参数与PR源码快照](calibration-parameter-pr-evidence.json)。生成器保存报告及源文件哈希，覆盖两个参数构建方法、默认参数类、标定配置构造和PR调用关键段；统一核验检查链接与漂移。本轮未新增硬件替身行为测试，不能将快照检查称为参数服务运行验收。

已完成本专题所列服务分支的静态追踪；尚未逐个验证BaseCarrierConfig真实默认值和配置加载、各派生算法与SDK、灯光/图像所有权及并发回调。沿用已有视觉审计结论，不重复提高模块完成统计。后续交互图应保留实际标定路径，其他类型仅作为条件分支补充。
