# 机器框架模块：职责、调用与缺失项

更新：2026-09-28。本章继续从自动化主流程向框架内部追踪，范围为 AKRS.Galaxy2.Machine 和 AKRS.Galaxy2.MachineSupport 及其在 ZX2200 中的直接使用。模块文件清单不是模块验收结论。

## 首先确认的职责边界

2026-09-29配置核对：`Services/MachineService.cs`在本机Debug/Release AnyCPU求值中均未纳入Compile；下表对空静态类的描述仅是仓库源码事实，不能作为当前产物中存在该类的证据。其他文件不因此被排除，详见[逐文件影响表](compile-scope-impact.md)。

BaseMachine 构造 TraceSignal、SingleSignal、PauseSignal，封装单步和状态写入。它不是 ZX2200 的完整生产调度器：PauseWork/StartWork/StopWork 直接写共享 MachineState，而已复核的 ZX2200 Machine.Pause/Stop 有不同实现，不能按名字合并。[BaseMachine 26–147](../../trunk/AKRS.Galaxy2.Machine/BaseMachine.cs#L26)

TraceWait 调用 TraceSignal.Wait 后未使用返回值，最终返回 true。这个局部事实不能直接当作 ZX2200 自动工作中的实际缺陷：还必须找到活跃调用方，确认是否进入该方法。[BaseMachine 86–94](../../trunk/AKRS.Galaxy2.Machine/BaseMachine.cs#L86)

RuntimeProvider.ThreadFlag 是 volatile bool。注释称关闭它可终止所有循环线程，但实现只是共享字段；只有真正检查该字段的循环才受它影响，不能用注释替代退出证明。[RuntimeProvider 33–48](../../trunk/AKRS.Galaxy2.MachineSupport/RuntimeProvider.cs#L33)

## 本轮复核范围

已读取两个分组的9个行为源码文件及2个AssemblyInfo，追踪下述代表调用方。源码定义已复核，所有消费方、二进制行为、构建与运行闭环仍未完成，因此两个分组均标“部分复核”，不标模块完成。


## 职责和定义清单

|分组/文件|实际职责|范围与边界|
|---|---|---|
|Machine/BaseMachine.cs|三个信号、单步/共享状态写入、ExitApp设ThreadFlag=false|ZX2200 Machine实际继承SingletonNoSave，而非该类；trunk C#词法检索未找到其他BaseMachine显式使用，不能推出外部DLL/反射绝不使用|
|Machine/MachineService.cs|空静态类|不具有额外调度、监控或安全复位实现|
|Machine/MachineStateModel.cs|状态/工作模式单例、JSON加载保存、人工观察标记开关|构造/初值Stop不代表从已有JSON加载后必为Stop；状态保存和恢复取决于外部JsonFormatHelper|
|Machine/Signal.cs|EventWaitHandle包装与状态检查|公开State不是读取内核事件的实时查询，Wait(outTime)未使用outTime且不更新AutoReset的公开State|
|Machine/SignalPool.cs|定义23个生产信号；Init仅登记其中12个|SignalList不是所有信号的全集，更不是线程/信号队列；成员被替换时列表也不自动更新|
|Machine/Enums/MachineEnum.cs|状态、工作模式、系统选择、信号状态、上料方式和轴模式枚举|枚举声明本身不执行状态迁移约束|
|MachineSupport/MachineConfigContext.cs|RecipeID持久化与配方仓库查询|已存在文件读失败或返回null时没有新建实例的兜底；声明locker但GetInstance未使用lock|
|MachineSupport/PathConfig.cs|基于Application.StartupPath组合Settings与配方/硬件/设备路径|路径构造不创建目录、不写文件；GetModuleRecipeConfigFileName在RecipeDirPath基础上再次附加RecipeID|
|MachineSupport/RuntimeProvider.cs|当前用户、ThreadFlag、SystemType共享字段|不提供线程管理器、取消等待、Join或账号鉴权实现|
|两组Properties/AssemblyInfo.cs|程序集名称、版本1.0.0.0、COM可见性元数据|仅元数据审阅，不算自动化行为覆盖|

## 实际调用与数据链路

|调用方→目标|关系类型|输入/输出及源码依据|
|---|---|---|
|ZX2200 Machine→SingletonNoSave<Machine>|继承|并非BaseMachine。[Machine.cs67](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs#L67)|
|Machine.SetState→MachineStateModel→StatisticsService队列|状态写入/队列投递|新旧不同才写状态和加入变更记录；不是硬件停止回调。[StateRelated52–68](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.StateRelated.cs#L52)|
|Signal.Wait/WaitStart→MachineStateModel|状态读取|Stop/Pause协作检查；Wait(int)只WaitOne(recycleTime)一次。[Signal116–228](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L116)|
|FrmProductionMode.BtnOK_Click→MachineStateModel.Save|UI写模式/持久化调用|SelectedIndex转MachineWorkMode，然后Save；Save将实例交JsonFormatHelper。[窗体28–34](../../trunk/AKRS.ZX2200/Main/Machine/Product/Controls/FrmProductionMode.cs#L28)、[模型79–92](../../trunk/AKRS.Galaxy2.Machine/Models/MachineStateModel.cs#L79)|
|UcMainSystem.BarBtLoad_ItemClick→MachineConfigContext|写RecipeID/保存配置|选择窗体OK且Recipe非null才赋ID、保存，之后按旧配方条件重载；这是代表入口，未覆盖完整重载生命周期。[804–820](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L804)|
|Machine.DataSave→SaveMachineConfig|同步直接调用|多模块保存链的一个调用；不证明整体事务成功。[Machine.cs352、383](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs#L352)|
|MachineConfigContext.GetInstance→DirAndFileHelper/JsonFormatHelper|外部文件helper调用|Settings/MachineConfig.json不存在才new；存在时读取，异常弹窗但可能返回null。[55–85](../../trunk/AKRS.Galaxy2.MachineSupport/Config/MachineConfigContext.cs#L55)|
|MachineConfigContext.CurrentRecipe/RecipeName→RecipeRepository|外部仓库查询|传RecipeID；RecipeName对返回对象使用?.，CurrentRecipe可返回null。[25–37](../../trunk/AKRS.Galaxy2.MachineSupport/Config/MachineConfigContext.cs#L25)|
|MachineStateModel.GetInstance/Save→JsonFormatHelper|外部序列化调用|双检锁，读结果null才new，局部没有读异常catch；目标Settings/DeviceParams/MachineStateModelPath.json。[39–82](../../trunk/AKRS.Galaxy2.Machine/Models/MachineStateModel.cs#L39)|
|PathConfig.RecipeDirPath→MachineConfigContext.RecipeID|派生路径读取|Settings/RecipeParams/<ID>，GetModuleRecipeConfigFileName再附加<ID>/<module>.json。[82–149](../../trunk/AKRS.Galaxy2.MachineSupport/Config/PathConfig.cs#L82)|
|FrmSignalDisplay.InitControl→SignalPool.SignalList|界面数据绑定|仅绑定12项清单，其他11个信号不会因其属性存在而自动出现在此数据源。[窗体30–35](../../trunk/AKRS.ZX2200/Main/Controls/FrmSignalDisplay.cs#L30)、[池193–214](../../trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs#L193)|
|Machine.StartBackGroundThread→RuntimeProvider.ThreadFlag|循环条件读取|该循环读取ThreadFlag；不能推广到只读MachineState或私有标志的其他任务。[Operate662–700](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L662)|

## 信号展示遗漏不等于信号未实现

SignalPool定义23个Signal属性，而SignalList只登记12个。未登记的是：System2SingleStepSignal、System1SingleStepSignal、AllowLoaderMoveSignal、LoaderAllowPushSignal、AllowUnloaderMoveSignal、UnloaderAllowPushSignal、IsEjectionComplete、IsFlipTableAllowPickSignal、IsAllowDipFluxSignal、BondDipFluxFinishSignal、AllowSlideOutSignal。这些属性仍可被生产流程直接使用；界面未列出不能当作功能缺失。[完整定义60–186](../../trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs#L60)。

Signal构造函数把initialState传给EventWaitHandle，但公开State初值始终ReSet；Set/ReSet更新公开State，Wait()/WaitSingleStep成功时仅在AutoReset下改回ReSet，Wait(int)没有此更新。因此展示字段可能与事件实际消费状态不同。当前池内23个声明都initialState=false；不把允许传true的构造能力说成当前已有该运行实例。[Signal26–108](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L26)、[116–195](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L116)。

## 配置、外部库及失败处理

- 根目录是Application.StartupPath，不是固定源码目录；MachineConfig.json、MachineStateModelPath.json与RecipeParams都由PathConfig派生。路径存在、权限、文件锁和写入原子性不能从路径属性推出。
- MachineConfigContext读取异常仅MessageBox，可能返回null；Save没有局部catch。状态模型GetInstance双检锁但同样依赖外部JsonFormatHelper读写行为；不能推断文件损坏自动修复或事务保存。
- Machine项目以HintPath引用libs下MachineSupport.dll；ZX2200自身同时ProjectReference两个源码项目。存在源码和DLL两条引用路径，需构建解析/加载版本确认，不能直接认定运行DLL就是当前源码。[Machine.csproj39–58](../../trunk/AKRS.Galaxy2.Machine/AKRS.Galaxy2.Machine.csproj#L39)、[ZX2200.csproj4102–4109](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L4102)。
- MachineSupport通过libs引用Infrastructure、Recipe、UserManager及Newtonsoft.Json；对应DLL在仓库中存在，缺的是所用外部类的源码级实现与运行版本证明，不应写成“库文件全部缺失”。[MachineSupport.csproj37–52](../../trunk/AKRS.Galaxy2.MachineSupport/AKRS.Galaxy2.MachineSupport.csproj#L37)。
- PathConfig.GetModuleRecipeConfigFileName重复附加RecipeID是方法体事实；当前trunk C#检索未找到显式调用，尚不能当作真实生产配方路径故障。

## 已完成与未完成

已完成：上述源码定义、代表直接调用、输入输出、错误分支和外部实现边界的静态复核；完整文件快照哈希与结构化调用登记见module-review-evidence.json、module-reviews.json。

未完成：全调用方/事件与反射绑定覆盖；配置异常对完整启动/配方重载的影响；路径重复是否被外部DLL使用；线程状态并发时序；全部信号等待点；外部helper和仓库的实现；依赖版本解析、编译与实机。下一步先进入ZX2200/Main的初始化、配方加载和生产调度连接点，再沿其调用补配置/统计与运动模块。
