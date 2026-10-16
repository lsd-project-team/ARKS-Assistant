# AKRS.Galaxy2.PR：配方视觉复制与加载复核

2026-09-28。状态：部分复核。87个文件中，本轮涉及PREntity、BaseAlg、VisionEntityRepository三个文件的指定方法，不代表整个视觉框架和算法完成验收。

## 入口和代表关系

主程序ReLoadRecipe收集名称后调用BaseAlg.InitVmProcedure；新配方复制委托TuService.CopyOldRecipePR调用PREntity.CopyPREntity。上层控制流见[配方链路复核](recipe-initialization-source-review.md)。

|方法|实际行为与边界|源码|
|---|---|---|
|CopyPREntity|源不存在返回null；文件helper复制prc→Clone→改Alg.Name→初始化过程→SetName→AddVisionEntity；未检查Clone的null。|[740–766](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L740)|
|Clone|Guid.json相对路径保存/读取/删除后改名；catch返回null，无finally清临时文件，序列化覆盖范围取决于外部helper。|[659–675](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L659)|
|InitVmProcedure|锁内加载保存prc或通用模板，依次赋过程、名称、参数和图像工具；catch仅日志，不返回失败。|[291–319](../../trunk/AKRS.Galaxy2.PR/Models/Algs/BaseAlg.cs#L291)|
|GetPRSavePath|标定/其他分别定位DeviceParams下设备标定PR/所有产品PR；必要时建目录，异常返回null。|[325–351](../../trunk/AKRS.Galaxy2.PR/Models/Algs/BaseAlg.cs#L325)|
|GetInstance|锁内读取仓库，读回null则创建空仓库；无本地catch，不能假定读取抛异常也创建空仓库。|[43–64](../../trunk/AKRS.Galaxy2.PR/Resipository/VisionEntityRepository.cs#L43)|
|AddVisionEntity / Find|Find取首个同名对象；Add先移除首个同名对象再追加，不保存、不清所有重复项。|[75–86](../../trunk/AKRS.Galaxy2.PR/Resipository/VisionEntityRepository.cs#L75)；[136–140](../../trunk/AKRS.Galaxy2.PR/Resipository/VisionEntityRepository.cs#L136)|
|Save|保存主文件，存在时删旧备份再复制；catch仅日志。返回不能保证保存或备份成功。|[109–128](../../trunk/AKRS.Galaxy2.PR/Resipository/VisionEntityRepository.cs#L109)|

RemoveDuplicatesEntity仅创建局部列表，未写回仓库：[91–95](../../trunk/AKRS.Galaxy2.PR/Resipository/VisionEntityRepository.cs#L91)。这不证明系统其他地方没有去重。

## 输入输出及缺失项

### 已补深：主程序加载清单的四类来源

|来源|名称产生规则与边界|源码|
|---|---|---|
|载具|合并料盒及静态盘载具并筛选仓库存在项，再按搜索/校正/相机/TU蘸胶条件添加DieMatch、DieBlob、DieFrame、上下视和Dip模板。主入口仍以CurrentAllocationsConfig非null为门控。|[WaferSystemProgram96–239](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemProgram.cs#L96)；[主入口37–45](../../trunk/AKRS.ZX2200/BondSystem/Services/System2CommonService.cs#L37)|
|顶针|筛选库与槽位配置存在，过滤null并Distinct后取EjectMatchName；没有额外检查PR实体存在。|[246–307](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemProgram.cs#L246)|
|焊后检测|配置名称经Find解析后，对每项添加P1PRName和BacsideCrackDetectPRName；不去重。Find还会从输入配置名称列表RemoveAt删除未找到项。正向for删除后继续i++，相邻缺失项可能被跳过，后续调用结果可能不同；不是纯读取。|[PostBondProgram31–84](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/PostBondProgram.cs#L31)|
|吸嘴与产品定位|吸嘴库非null时，对非空NozzleName追加NozzlePR；定位GetPrNames只添加P1、P2、P3，不添加P4。两者未去重或查询模板实体是否存在。|[NozzleShelfProgram203–218](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/NozzleShelfProgram.cs#L203)；[LocateConfig159–179](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/LocateConfig.cs#L159)|

第四点不是不存在：LocateConfig定义[P4PRName81–82](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/LocateConfig.cs#L81)，并在角度判断中使用[197–202](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/LocateConfig.cs#L197)。这里只确认这条GetPrNames加载清单未包含P4，不能扩大为软件所有路径都不会加载P4；实际四点定位运行影响和其他加载路径待测试/追踪。

主聚合方法还固定添加IPTCenterCircle，未全局去重。[System2CommonService37–92](../../trunk/AKRS.ZX2200/BondSystem/Services/System2CommonService.cs#L37)。去重发生在哪一层必须分别说明：载具/顶针列表有Distinct，最终PR名称列表没有，不可互相代替。

输入是源/目标名、算法类别、仓库文件及prc；输出涉及内存实体、SDK过程、主文件/备份及日志。VmProcedure/VmSolution是SDK边界；JSON和文件helper未取得实现，不能推断覆盖、事务或完整深拷贝语义。

- 继续识别执行、结果、坐标、相机/光源/标定以及UI编辑生命周期。
- 核实序列化类型信息、同名prc覆盖和缺失/损坏模板恢复。
- 核实实际依赖版本，完成构建和SDK测试；本轮未运行设备、未修改生产源码。

## 2026-09-28：运行入口补充

已补硬件DoWork、静态锁、取图、FindModel、展示和存图委托，详见[视觉执行与异步存图](vision-runtime-module-review.md)。算法调用在存图try之前；Success/Fail赋值在存图分支之后，不能只看FindModel推断最终结果。派生算法和SDK仍待展开。

## 胶量算法路径补充

已核实工厂、切换、图像注入和EpoxyDetectAlg的输入/聚合/异常分支，见[胶量算法证据](epoxy-algorithm-source-review.md)。这是单一算法分支，不代表全部PR类型或配方已验证。
