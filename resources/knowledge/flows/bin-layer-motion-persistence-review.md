# 料仓层位移动、切仓与保存边界

2026-09-28。按自动生产链向下复核；不修改生产源代码、不执行设备动作。结合[任务握手](loader-unloader-handshake-source-review.md)、[输送内部步骤](bin-transfer-controller-source-review.md)、[停止恢复影响](bin-stop-resume-source-review.md)阅读。

## 参数如何到达动作

上料LoaderBinProgram以CurLoaderName查LoaderBinRepository.GetLoaderBin；下料以CurUnLoaderName查UnLoaderBinRepository.GetLoaderBin。两项对象属性都标JsonIgnore，默认CurBinType=BinA、CurPlaceLayer=1。仓库GetLoaderBin直接转换Find(name)结果；本次没有展开Find实现，不把注释“不存在返回空”当作完整错误契约，也没有证明名称缺失会自动补建。

TransportProgram持有两种料仓程序对象，继承Singleton<TransportProgram>；静态构造设置TransportSystemProgramFilePath，InitTransportSystemProgram重新设置路径并置instance=null。文件目标为PathConfig.RecipeDirPath/TransportSystemProgram.json，RecipeDirPath由RecipeRootDirPath与当前RecipeID组成。料仓几何参数对象由独立仓库读取，不能笼统说全部几何参数都直接存于TransportSystemProgram.json。

## 实际执行与决策

|动作|上料|下料|
|---|---|---|
|合法层号|num>0且num<=LayerNum|同左|
|Z坐标|FirstTabletLevel + TabletPitch × (num−1)|同左|
|推杆安全判据|abs(GetRealPosition())<2.5|abs(GetRealPosition())<5|
|移层前检查|不安全则MovePushRodHome，未检查返回或重新验证安全；再检查层号|同样顺序；缩回结果未检查|
|当前料盒Y|按A/B选择BinAPosY/BinBPosY；有推杆安全检查|按A/B选择Y；MoveToCurrentBin本方法没有同样的推杆安全检查|
|切换下一盒|安全判断/缩回→Y移动→改CurBinType→Save|同左；Y包装返回void|
|重置料仓|仅设层号1、盒A并Save|同左；不是实际硬件回零|
|MoveToLastTablet|移动到LayerNum，随后层号设LayerNum并Save|同左；不是注释旧代码的上一层|

源码：[上料层位/切仓](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/LoaderBinController.cs#L215)、[下料层位/切仓](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/UnLoaderBinController.cs#L170)、[上料层号和安全](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/LoaderBinController.cs#L348)、[下料安全](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/UnLoaderBinController.cs#L340)。

## 到位与返回值不能混为一谈

- 上料MoveAxisY/Z：IsReady=false返回Exception；软限位检查后，OffLineWork返回None，否则返回Axis.AbsoluteMove结果。MoveToTabletLevel返回Z结果，但生产MoveToCurrentPlaceLayer和MoveToNextPlaceLayer未接收它；MoveToCurrentBin/MoveToNextBin也未检查Y结果。若下层仅返回失败枚举而不抛错，所读上层仍可能继续返回Success或修改层号，继而任务发允许推料。
- 下料MoveAxisY/Z为void：IsReady=false直接return，OffLineWork直接return，其他情况调用AbsoluteMove且没有显式检查结果；上层无法凭该方法正常返回区分未执行和成功到位。
- IsReady检查Y/Z/推杆三个Axis对象是否非null，不验证轴使能、报警、位置或传感器。安全缩回函数内部会把失败转Exception枚举，但上述调用点忽略其结果；不能因此宣称安全动作完成。
- Y/Z软限位比较AxisSetPara的NLimit/PLimit，越界抛异常。Z检查使用的是Z参数，但异常文本展示Y的GetSoftLimit值；应区分真实检查对象与诊断文本。具体软限位、单位和物理标定仍需配置/SDK核验。

证据：[上料轴包装](../../trunk/AKRS.ZX2200/TransportSystem/Modules/LoaderBinModule.cs#L68)、[下料轴包装](../../trunk/AKRS.ZX2200/TransportSystem/Modules/UnloaderBinModule.cs#L74)、[上料软限位](../../trunk/AKRS.ZX2200/TransportSystem/Modules/LoaderBinModule.cs#L184)、[下料软限位](../../trunk/AKRS.ZX2200/TransportSystem/Modules/UnloaderBinModule.cs#L152)、[生产调用](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/LoaderBinController.cs#L449)。

## 保存与恢复的已知边界

- ResetLoader/ResetUnloader先改两个内存字段再Save。MoveToNextBin先调用Y移动、改盒号再Save。上料MoveToNextPlaceLayer先调用层位移动、层号递增再Save。这些所读方法没有补偿回滚或finally；但Save是否抛出、吞错、重试或原子替换不能从调用点决定。
- 本仓库源码检索未找到Axis与Singleton的类定义；主项目通过libs/AKRS.Galaxy2.LogicHardware.dll和libs/AKRS.Galaxy2.Infrastructure.dll引用，两文件本次确认存在。只证明声明和文件存在，未反编译、未加载生产DLL，也未验证MSBuild解析出的真实版本。
- 所以当前不能断言保存成功、断电后自动恢复到同一层，或Axis.AbsoluteMove/StopMove具有某种超时、取消与到位保障。也不能反向断言一定失败。
- 保存失败后的恢复要求需跨内存层号、实际位置、文件内容及后续启动加载四者检查；现有源码证据尚未把这个闭环证明完成。

证据：[程序对象及基类](../../trunk/AKRS.ZX2200/TransportSystem/Models/TransportProgram.cs#L20)、[路径](../../trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs#L71)、[配方目录](../../trunk/AKRS.Galaxy2.MachineSupport/Config/PathConfig.cs#L88)、[DLL引用](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L265)。

## 后续缺口

1. 展开BaseSettingRepository.Find/加载/保存及名称选择的实际调用，核实料仓名称无效或几何参数缺失时的进入路径。
2. 对照硬件配置中轴名、软限位、推杆安全阈值和方向；SDK源码或正式契约缺失时保留边界，不补写实现。
3. 在隔离环境覆盖失败枚举不抛错、轴对象缺失、保存抛错/静默失败等场景，分别观察允许推料信号、内存层号、目标文件和实际位置。
4. 将本轮下层返回差异纳入料仓交互图，不能再把移动调用箭头标为必然到位。

## 台账精确快照索引

- [trunk/AKRS.ZX2200/TransportSystem/Controllers/LoaderBinController.cs:215](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/LoaderBinController.cs#L215)
- [trunk/AKRS.ZX2200/TransportSystem/Controllers/UnLoaderBinController.cs:170](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/UnLoaderBinController.cs#L170)
- [trunk/AKRS.ZX2200/TransportSystem/Controllers/LoaderBinController.cs:348](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/LoaderBinController.cs#L348)
- [trunk/AKRS.ZX2200/TransportSystem/Controllers/UnLoaderBinController.cs:340](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/UnLoaderBinController.cs#L340)
- [trunk/AKRS.ZX2200/TransportSystem/Modules/LoaderBinModule.cs:68](../../trunk/AKRS.ZX2200/TransportSystem/Modules/LoaderBinModule.cs#L68)
- [trunk/AKRS.ZX2200/TransportSystem/Modules/UnloaderBinModule.cs:74](../../trunk/AKRS.ZX2200/TransportSystem/Modules/UnloaderBinModule.cs#L74)
- [trunk/AKRS.ZX2200/TransportSystem/Modules/LoaderBinModule.cs:184](../../trunk/AKRS.ZX2200/TransportSystem/Modules/LoaderBinModule.cs#L184)
- [trunk/AKRS.ZX2200/TransportSystem/Modules/UnloaderBinModule.cs:152](../../trunk/AKRS.ZX2200/TransportSystem/Modules/UnloaderBinModule.cs#L152)
- [trunk/AKRS.ZX2200/TransportSystem/Models/TransportProgram.cs:20](../../trunk/AKRS.ZX2200/TransportSystem/Models/TransportProgram.cs#L20)
- [trunk/AKRS.ZX2200/TransportSystem/Models/Programs/LoaderBinProgram.cs:11](../../trunk/AKRS.ZX2200/TransportSystem/Models/Programs/LoaderBinProgram.cs#L11)
- [trunk/AKRS.ZX2200/TransportSystem/Models/Programs/UnLoaderBinProgram.cs:18](../../trunk/AKRS.ZX2200/TransportSystem/Models/Programs/UnLoaderBinProgram.cs#L18)
- [trunk/AKRS.ZX2200/TransportSystem/Models/DatasetModels/StockBin/LoaderBinRepository.cs:11](../../trunk/AKRS.ZX2200/TransportSystem/Models/DatasetModels/StockBin/LoaderBinRepository.cs#L11)
- [trunk/AKRS.ZX2200/TransportSystem/Models/DatasetModels/StockBin/UnLoaderBinRepository.cs:11](../../trunk/AKRS.ZX2200/TransportSystem/Models/DatasetModels/StockBin/UnLoaderBinRepository.cs#L11)
- [trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs:66](../../trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs#L66)
- [trunk/AKRS.Galaxy2.MachineSupport/Config/PathConfig.cs:83](../../trunk/AKRS.Galaxy2.MachineSupport/Config/PathConfig.cs#L83)
- [trunk/AKRS.ZX2200/AKRS.ZX2200.csproj:265](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L265)
