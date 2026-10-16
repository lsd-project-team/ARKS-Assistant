# ZX2200/WaferSubSystem：配方切换后的状态重建

2026-09-28。状态：部分复核。这里只复核配方清理、重建标记消费和槽位实体变化的指定方法；已有供片主图不代表174个文件全部验收。

## 从触发到状态更新

1. 配方重载调用InitWaferSystemProgram，清供片记忆并按配置置料盒/静态盘标记，之后改程式路径清单例。[初始化70–90](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemProgram.cs#L70)；[清理1207–1224](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L1207)。
2. 到达CheckIsReady后段才消费标记；静态盘同时要求硬件已配置。前面检查可能已返回，异常catch弹窗并返回false，无副作用回滚。[371–411](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemDomain.cs#L371)。
3. 静态盘先替换AdapterTablet，名字为空字符串就返回；非空才创建实体并Save。调用方仍设Good、可空更新AdapterState并复位标记，不能用标记false证明实体有效。[401–431](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/DeviceParams/WaferTableDevicePara.cs#L401)。
4. 料盒分支先CurrentAllocationsConfig?.SetAllSlotState(Good)，按当前料片类型初始化，再复位标记。配置为null会跳过批量设置，但仍继续后续语句。
5. 槽位窗口构造也会按料盒标记更新槽位和复位/保存标记，再深拷贝用于显示；无需点击保存就可能改数据。[FrmSlotsState47–61](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/FrmSlotsState.cs#L47)。

## 实体和槽位如何变化

|方法|源码行为|证据|
|---|---|---|
|AdapterTablet.CreateAdapterEntity|按Name查AdapterSetting；找不到直接返回，不清原AdapterState。找到则按MaxUseWaffleCount建状态数组，仅为载具配置非null项创建AdapterSlotEntity。|[34–59](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/Tablet/AdapterTablet.cs#L34)|
|WaferTablet.InitTabletInfo|从配置赋搜索方向和WaferCenter，置IsNewTablet=true；没有复制中心对象语句，不能证明位置独立；未清CurrentPoint。|[34–62](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/Tablet/WaferTablet.cs#L34)|
|MagazineAllocationsConfig.SetAllSlotState|循环MaxUseLayerCount按类型更新：NullTablet跳过，Wafer/Adapter要求配置存在；循环后Repository.Save。中途异常抛通用错误，不回滚前面各项。|[94–148](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Repositories/MagazineAllocations/MagazineAllocationsConfig.cs#L94)|
|AdapterEntity.SetAllSlotState|对象重载SetSlotState跳过null，其余先改盘状态，再调用槽位批量更新。index重载只改盘状态，两者不等价。|[36–94](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/AdapterEntity.cs#L36)|
|AdapterSlotEntity.SetAllSlotState|给非null槽赋状态；finally无论成功与否都将CurrentIndex置0。|[83–104](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/AdapterSlotEntity.cs#L83)|

## 保存边界

WaferSubDevicePara继承本地SingletonJson<T>，不能和缺源码的Singleton<T>混同。[19–117](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/DeviceParams/WaferSubDevicePara.cs#L19)：GetInstance加锁，Load先new T再调用读取helper；读回null时GetInstance再new。若读取抛异常，先前赋给instance的新对象可能仍保留。Save锁内保存静态instance，再调用CopyFile(FilePath,目录名加Baks,true,50)，没有本地catch；不凭参数50推断未见实现的轮转规则。

路径为DeviceParams/WaferSub/WaferSubDevicePara.json：[ZX2200PathConfig182](../../trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs#L182)。标记方法先改bool后Save，不是本地事务保证。

## 尚未完成

### 已补深：窗口不是统一确认后才提交

[FrmSlotsState 68–124](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/FrmSlotsState.cs#L68)：保存按钮先Save再置DialogResult.OK；全部填充先在副本上SetAllSlotState(Good)，再复位重建标记、刷新并Save。Save直接把副本TabletArray赋给当前配置TabletArray，再调用Repository.Save和显示刷新；不是再次深拷贝。赋值后两个配置可引用同一个数组。SetAllSlotState内部也会调用仓库Save，不能把“副本”理解成没有外部副作用。

[设置/清除按钮152–215](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/FrmSlotsState.cs#L152)在当前行有效时设Good/None，然后立即Save；槽位第二级按钮对Adapter类型有门控。绑定证据：[保存/全部填充110–120](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/FrmSlotsState.Designer.cs#L110)、[槽位按钮242](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/FrmSlotsState.Designer.cs#L242)、[料片按钮372](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/FrmSlotsState.Designer.cs#L372)。

[FormClosing273–279](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/FrmSlotsState.cs#L273)只Dispose映射控件，不恢复已保存数据；[主界面612–625](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L612)忽略ShowDialog返回值，只在返回后Dispose窗口。因此不能向接手人员承诺“关闭/未按保存就撤销全部修改”。控件内部尚未读取的其他编辑回调仍不能据此全部归类。

### 已补深：槽位实体构造与PR清单输入

[AdapterSlotEntity27–46](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/AdapterSlotEntity.cs#L27)参数为null时直接返回；否则保留配置引用，按行列数创建二维AcupointEntity数组，每项计算蛇形Index并保存行列号；位置为FirstPosition减列间距乘列号，再减行间距乘行号。无本地catch，也未在此段校验行列及载具配置。排序函数与配置合法性仍需单独核实，不能只据方法名认定排序正确。

[WaferSystemProgram.GetCarriers96–125](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemProgram.cs#L96)合并料盒及静态盘载具，按仓库IsExists筛选，最后过滤null并Distinct；未给Distinct传名称比较器，不能认定是按名称去重，且Name在最终null过滤前已使用。

[GetComponentCarriersPREntityNameList166–239](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemProgram.cs#L166)按双点搜索添加一或两个DieMatch，始终添加DieBlob，按框架搜索添加DieFrame；双点校正时上下视各两个模板，单点各一个，不支持的相机类型抛异常；TU蘸胶条件添加DipPR。主调用仍受CurrentAllocationsConfig非null门控，即使GetCarriers自身可合并静态盘，也不能假定只有静态盘时此清单必然被主调用收集。

[GetDistinctEjectionSettings246–266](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemProgram.cs#L246)先检查顶针库名及槽位顶针是否存在，过滤null后Distinct；[298–307](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemProgram.cs#L298)逐项取EjectMatchName，不额外校验PR实体。所有这些清单都只是名称输入，不代表相应模板已加载有效。

- 继续供片选择、进出料、搜索晶圆、实体构造与配置仓库内部调用，并与已有供片专题逐项对齐。
- [SortToSnakeHorizontal145–155](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/AdapterSlotEntity.cs#L145)已核实：偶数行索引为rowI*colC+colI，奇数行为rowI*colC+colC-colI-1，rowC参数未使用；方法未校验越界。[ConvertList162–171](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/AdapterSlotEntity.cs#L162)仅遍历二维数组形成列表，没有按Index排序；GetWaffleSlot另按CurrentIndex查找匹配项。因此遍历顺序与蛇形Index不能混用。
- 槽位构造、排序、即时保存和关闭边界已展开；继续数组配置一致性与保存helper，无配置却标记复位的影响需测试。
- 映射控件内部其他编辑回调未全部读取，不把窗口方法结论扩展为所有UI行为。
- 硬件运动、超时、SDK、构建与实机仍待验收；生产源码未修改。

[配方上下文](recipe-initialization-source-review.md) · [模块进度](module-review-status.md)
