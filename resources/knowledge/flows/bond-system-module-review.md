# ZX2200/BondSystem：贴装领域与启动前检查

2026-09-28。状态：部分复核。已有[贴装调度专题](bonding-semantic-revalidation.md)保留；本轮补领域自检及其配方/硬件依赖，不等同于全部贴装动作、标定、视觉和硬件运行验收。

## 主入口与执行顺序

Machine.CheckEnvironment依次检查WaferSystemDomain、System2Domain、System1Domain、产品示教、焊点示教、ProcessDomain；false立即返回。[Machine.Operate.cs:89](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L89)。

System2Domain.CheckIsReady先调用OpenBondHeadVaccum，然后才判断IsActiveSelfCheck；关闭自检仍会先发出开吸附调用。开启时依次检查BondProgram、动作步骤、ULM/焊头参数、按条件检查吸嘴架参数、力控标定、温漂/取片偏移点位、吸嘴架硬件配置、按条件进行焊头吸嘴逻辑/物理检测、处理记忆中有料，最后检查预点胶报警。[System2Domain.cs:594–770](../../trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs#L594)。

这个检查不是纯只读：物理无吸嘴但逻辑有吸嘴时，选择Yes会调用SetCurrentNozzleName清记忆；记忆中有料时选择OK调用ThrowAction。这里没有检查ThrowAction返回值，取消抛料仍继续后续预点胶检查。方法没有包住全过程的本地catch或回滚。[705–770](../../trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs#L705)。

## 配方与步骤检查

BondProgram先调用NozzleShelfProgram.SelfCheck，再遍历当前GetCarriers。每个载盘配置依次检查：吸嘴名非空；贴片、取片、IPT取片、IPT放片处于Force模式时，力值必须严格位于最小最大值之间；按AdjustCamera检查对应上视或下视P1点是否等于默认点；关真空延时不得大于PlacementDelay；配置IPT时，IPT关真空延时不得大于IPTPlacementDelay。任一不满足立即false；遍历结束true。[BondProgram.cs:85–211](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/BondProgram.cs#L85)。点坐标Equals底层语义及GetCarriers覆盖哪些实际生产配置仍须结合依赖验证。

动作步骤检查要求ProcessSteps非空；非异形产品再检查焊点名非空且存在。它不是对每个底层动作能否运行的全面验证。[S2ActionNodeController.cs:1359](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1359)。

## 吸嘴及硬件检查的精确边界

- NozzleShelf属性按NozzleShelfName查仓库，没有本地null兜底；GetNozzlesOnToolBank逐槽查NozzleRepository，仅将非null对象纳入列表，不在该方法报告缺失名称。[属性56–68](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/NozzleShelfProgram.cs#L56)；[实体列表165–180](../../trunk/AKRS.ZX2200/BondSystem/Models/Repositories/NozzleShelf/NozzleShelf.cs#L165)。
- 示教检查Any排除TouchDown和BMC，随后用来显示名称的FindLast只排除TouchDown，两个谓词并不相同；所以提示名不一定就是触发Any的那个普通吸嘴。后面的多吸嘴检查写作数组Find(...).Count()>1，命中后抛Exception；数组Find扩展实现尚未确认，不把它当作标准List.Find解读。[NozzleShelfProgram224–255](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/NozzleShelfProgram.cs#L224)。
- 槽位数组在构造中按设备SlotNum重建；硬件CheckToolBankConfiguration却直接检查索引0至6，且只拦截“配置名为空而对应传感器为true”。它没有对称检查“配置有名但传感器无物”，也没有在此方法保护不足7个槽位的数组。关闭IsToolBankEnable直接true。是否实际出现配置不一致需运行验证。[槽位构造26–59](../../trunk/AKRS.ZX2200/BondSystem/Models/Repositories/NozzleShelf/NozzleShelf.cs#L26)；[硬件检查73–179](../../trunk/AKRS.ZX2200/BondSystem/Controllers/NozzleShelfController.cs#L73)。
- OpenBondHeadVaccum在离线、单步等待false或已开真空时提前返回；它是void，自检调用方没有获得成功/失败布尔值。单步等待取决于IsSingleStepWork。后续无参IsToolOnBondheadPhy直接置输出true、等待200ms，再按数字IO或模拟值小于阈值判断；这个方法本身没有相同的离线分支。不能笼统声称离线自检没有任何硬件调用。[开真空217–237](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.GasIORelated.cs#L217)；[物理检测127–148](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.GasIORelated.cs#L127)；[单步777–788](../../trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs#L777)。
- IsToolOnBondheadLogic只判断当前吸嘴名非空；清吸嘴名会先改BondHeadParam，再调用BondDevicePara.Save，没有该方法内的回滚。[逻辑检测172–176](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.GasIORelated.cs#L172)；[保存895–899](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs#L895)。

## 抛料与工作任务衔接

ThrowAction读取原吹气比例→移到抛料位→吹气等待→恢复比例等待→关吹气→Z抬安全位→清IsMaterialOnBondhead→AbandonNumber加1→true。检测吸嘴是否仍有料的代码被注释；没有统一catch/finally，底层抛异常会中断，计数/记忆清理不构成抛料物理成功证明。[806–857](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondModuleController.MovementRelated.cs#L806)。

BondTask.Start仅按任务为null或Status不等于Running决定创建LongRunning任务，并返回true；不等待首个工序成功，AbortThread为空。DoWork首先重置运行信息，WaitStart后执行回安全位及焊头复位，按Enable、提前换嘴开关和首个组件决定换嘴，换嘴false则Stop并return。后续来料、补偿、动作调度及送出详见已有调度专题，尚未以此宣称全部下层动作验收。[Start361–384](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L361)；[DoWork100–147](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L100)。

## 输入、输出与待完成

- 输入：当前配方载盘/吸嘴/工序、设备点位、启用开关、吸嘴传感器与运行记忆；输出：bool或向外异常，以及检查过程中可能产生的硬件/记忆修改。
- 待继续：数组Find扩展和仓库/保存实现、槽位配置与硬件映射、启动后补偿和换嘴内部、下层取贴/视觉/轨迹/力控及耗材生命周期。
- SDK实现、参数文件与实际设备版本、构建、错误注入和实机仍未验证。
