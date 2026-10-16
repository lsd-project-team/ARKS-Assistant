# 编程页面保存：程序集实现与文件边界

更新：2026-09-28。本页沿[非接口页面事件保存](noninterface-save-events-review.md)继续追踪 `Save()`；源码锚点加上仓库随附 `AKRS.Galaxy2.Infrastructure.dll` 的[精确IL、元数据令牌与哈希](persistence-save-binary-evidence.json)。可复现提取命令为 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/extract-persistence-save.ps1`，核对命令为 `node scripts/verify-persistence-save-contract.cjs`。**这证明随仓库二进制的方法体，不证明现场加载的版本或执行成功。**

## 调用关系和目标

|页面事件所调用的模型/库|定义与Save实现|目标路径来源|区别|
|---|---|---|---|
|[运输单元、焊点页面](noninterface-save-events-review.md) → `ProductConfiguration.GetInstance().Save()`|[继承外部Singleton](../../trunk/AKRS.ZX2200/TransportUnitSystem/ProductConfiguration.cs#L22)；静态[FilePath赋值](../../trunk/AKRS.ZX2200/TransportUnitSystem/ProductConfiguration.cs#L27)|`RecipeDirPath / ProductConfiguration.json`|随附 `Singleton.Save` IL `IL_0013–IL_0022` 锁内把静态instance与FilePath交给`SaveGenericObject`|
|[点胶列表事件](noninterface-save-events-review.md) → `System1Program.Save()` / `BondProgram.Save()`|[System1Program](../../trunk/AKRS.ZX2200/DispenseSystem/Models/System1Program.cs#L18)、[BondProgram](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/BondProgram.cs#L25)均继承Singleton|[DispenseProgram.json](../../trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs#L90)、[BondProgram.json](../../trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs#L158)；位于当前配方目录|各自是对象Save，不是仓库列表Save|
|[胶型仓库、焊后仓库](noninterface-save-events-review.md) → `EpoxyApplicationRepository.Save()` / `PostBondInspectionRepository.Save()`|两者继承[BaseSettingRepository.Save](../../trunk/AKRS.ZX2200/Infrastructure/Models/BaseModels/BaseSettingRepository.cs#L82)，直接调用`JsonFormatHelper<T>.SaveGenericList`|[EpoxyApplicationRepository.json](../../trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs#L105)、[PostBondInspectionRepository.json](../../trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs#L298)，位于DeviceDirPath|列表Save走另一套文件打开方式|
|[焊后PR删除回调](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/PostBond/UcAddPostBond.cs#L64) → `VisionEntityRepository.Save()`|[源码Save 109–128](../../trunk/AKRS.Galaxy2.PR/Resipository/VisionEntityRepository.cs#L109)调用对象Save；成功到文件存在判断后复制备份；catch只记日志|[TemplateConfigRepositoryPath](../../trunk/AKRS.Galaxy2.MachineSupport/Config/PathConfig.cs#L140)位于DeviceDirPath；备份也在该目录|备份复制的是保存后的文件，非前一版；异常可在该层被吞掉|

[PathConfig.Root](../../trunk/AKRS.Galaxy2.MachineSupport/Config/PathConfig.cs#L40)为 `Application.StartupPath`；[RecipeDirPath](../../trunk/AKRS.Galaxy2.MachineSupport/Config/PathConfig.cs#L88)拼接当前 `MachineConfigContext.RecipeID`，而[DeviceDirPath](../../trunk/AKRS.Galaxy2.MachineSupport/Config/PathConfig.cs#L94)不以配方ID分目录。对象模型的静态FilePath在[ProductConfiguration静态构造](../../trunk/AKRS.ZX2200/TransportUnitSystem/ProductConfiguration.cs#L27)、[System1Program静态构造](../../trunk/AKRS.ZX2200/DispenseSystem/Models/System1Program.cs#L23)、[BondProgram静态构造](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/BondProgram.cs#L76)赋值，另有[显式重新初始化](../../trunk/AKRS.ZX2200/TransportUnitSystem/ProductConfiguration.cs#L71)等赋值路径。不能仅凭动态RecipeDirPath断言**每次Save**都会重新计算当前配方路径；配方切换后的调用顺序需另验。

## 随附程序集中的保存步骤

1. `Singleton.Save`：取得泛型单例锁 (`IL_0001–IL_000c`)，读取静态instance与FilePath (`IL_0013–IL_0018`)，调用 `JsonFormatHelper<T>.SaveGenericObject` (`IL_001d`)，finally退出锁；这里没有本地catch。证据见[IL快照](persistence-save-binary-evidence.json)的 `methods.singletonSave`。
2. `SaveGenericObject`：读取目标目录，必要时建目录 (`IL_0001–IL_002d`)；目标不存在时先 `File.Create` 并Dispose (`IL_002e–IL_0048`)；构造同目录随机临时名 (`IL_0049–IL_0054`)；序列化并向临时文件写一行 (`IL_0056–IL_00ed`)；目标存在则 `File.Replace(temp, target, null)` (`IL_00ed–IL_0103`)，否则 `File.Move(temp, target)` (`IL_0106–IL_010e`)。异常处理含删除临时文件、再以新Exception抛出 (`IL_0113–IL_013c`)。**未证明所有异常都进入catch；目标预创建位于主要catch范围之前，首次保存失败可能留下空目标文件。**
3. `SaveGenericList`：必要时建目录、目标不存在时创建目标，随后对**目标文件**以 `FileMode.Create` / `FileAccess.Write` 打开 (`IL_0001–IL_0049`)，序列化并写入 (`IL_004b–IL_00a3`)，finally释放writer和stream；该方法中未找到临时文件、`File.Replace`或本地catch。因此列表写入与对象替换策略不同；写入或序列化失败时，原内容可能已被截断，是否如此取决于实际失败阶段。
4. `JsonSerialize`错误回调：两个方法都设置Json.NET `Error`处理器；随附IL的回调读取错误消息、`Console.WriteLine` 并将 `ErrorContext.Handled=true`。因此即使方法正常返回，也不能只凭无异常证明所有字段完整序列化。详细见[两种回调IL](persistence-save-binary-evidence.json)。

## 配方切换后的读取与实例重建（随仓库 DLL 静态证据）

1. [加载旧配方](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L804)与[新建后切换](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L320)先赋 `RecipeID`、保存机器配置，仅在旧配方为空或 ID 改变时调用 `ReLoadRecipe`。后者[按六种程序顺序重置路径与实例](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L124)：Product、Transport、Bond、System1、Wafer、Process；其中[Wafer 初始化](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemProgram.cs#L70)先清理供片记忆，再赋新 FilePath、清单例。这些步骤位于 `ReLoadRecipe` 的[try 之前](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L149)：若此阶段抛异常，本方法的 catch/finally 不会恢复先前禁用的界面。这是源码控制流风险，不代表现场已发生。
2. 随附 DLL 的 `Singleton<T>.GetInstance` 在锁内检查静态 instance；为空则调用 `Load` (`IL_0013–IL_002b`)，返回后仍为空才调用 `Activator.CreateInstance<T>()` (`IL_002c–IL_0048`)。`Load` 先创建 T 并赋给 instance (`IL_0001–IL_0006`)，再以静态 FilePath 调用 `ReadGenericObject` 并重赋 instance (`IL_000b–IL_0015`)，随后对非空的 Singleton 实例订阅嵌套属性变化 (`IL_001a–IL_0048`)。因此“重置为null”与“已读到正确 JSON”不是同一件事。构造、读入、订阅仍可能有副作用或异常。
3. `ReadGenericObject` 对不存在的文件直接返回 T 的默认值 (`IL_0001–IL_0019`)；存在时打开读取并反序列化 (`IL_001f–IL_008b`)；捕获范围内的异常弹出 MessageBox 并返回默认值 (`IL_00a5–IL_00f3`)。之后 `GetInstance` 若仍为空，才新建 T；默认实例不等于成功载入配方。不能把所有异常都当作安全兜底：`File.Exists` 在读取 catch 之前，`Load` 的构造和属性订阅也不在 `ReadGenericObject` 的 catch 内。
4. `ReadGenericList` 在读取前检查目录并对不存在的目标**先创建空文件** (`IL_0001–IL_0045`)，然后打开文件反序列化 (`IL_0047–IL_00bd`)；其 catch 弹出 MessageBox、返回 null (`IL_00d7–IL_011e`)。源码中的[BaseSettingRepository.Load](../../trunk/AKRS.ZX2200/Infrastructure/Models/BaseModels/BaseSettingRepository.cs#L90)把 null 转为新空列表。因此首次读空文件、损坏 JSON 与读到真实的空列表在调用者对象层面都可能呈现空集合，但文件和提示行为不同。目录/文件预创建位于读取 catch 之前，实际权限或磁盘异常仍需受控验证。

上述每个 IL 方法及异常处理边界均保存在[带 DLL/SHA256 的可重提取快照](persistence-save-binary-evidence.json)，由 `scripts/verify-persistence-save-contract.cjs` 核验；它不说明现场实际加载的 DLL、FilePath 最终值或设备行为。

## 错误传播和待补证据

- `BaseSettingRepository.Save`本地没有catch，列表helper也无catch；外层用户界面是否处理错误需逐个调用点复核。`VisionEntityRepository.Save`却在[catch](../../trunk/AKRS.Galaxy2.PR/Resipository/VisionEntityRepository.cs#L124)仅记录日志，不向调用者返回成功标志。跨多种配置文件的顺序Save不是已证明的事务。
- 这里的程序集来自仓库 `libs/`，不是现场加载清单；框架 `File.Replace` 的磁盘保证、权限、杀进程时序和设备文件系统行为未测试。需要记录现场实际DLL哈希、配方ID、文件样本及受控故障注入结果。
- 下一步沿[编程页面Confirm方法体](programming-confirm-bodies.md)逐页对齐保存目标、前置校验与UI门控，并在模拟目录和隔离依赖下验证对象/列表文件失败路径；未经验证不能用静态审查代替设备验收。
