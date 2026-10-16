# Mapping恢复的对象构造与制程状态

更新：2026-09-28。承接码值Mapping专题。本轮增加实际C#原方法隔离测试，未构建/运行ZX2200主程序，不加载厂商硬件DLL，不操作现场文件。

## 恢复执行顺序

ReadTransportMappingByComponent创建TransportUnit(字符串原因)；构造先创建TransportUnitInfo，调用Init，再生成时间戳名称。Init取当前异形配置、初始化载具坐标，按配置走异形或普通基板初始化，执行ModifyMatter，然后按S2、S1顺序注入制程。

构造返回后，读取方法再次调用S2、S1 InjectSteps，之后才赋文件中的配方/批次/编号/面别和逐位置状态。因此文件头配方不会在这段路径中先切换配方再构造对象。具体坐标和ModifyMatter完整副作用仍待展开，不能将构造当作纯数据反序列化。

## 注入、完成与禁用

两套InjectSteps均遍历基板→模块→焊点→当前ProcessSteps，只在步骤BondPositionName等于焊点Name且字典不含ProcessStepName时加入false。重复注入不会覆盖已有true，也不会增加同名键。名称不匹配的焊点不获得该步骤。

SetFinishedInSystem1/2复制各自字典键再逐一设true，不从文件恢复每步历史、时间或中间进度。IsFinishedInSystem2在字典为空时直接true，有任一false时false，全部true时true。因此“完成”判定必须结合是否成功注入所需步骤，不能把空字典true解释成实际执行过制程。

Mapping的X路径调用SetMatterDisable：基板向各模块递归，模块向各焊点递归，焊点仅把MatterProductState置Disable。它与将步骤字典置true是不同操作；本轮不推断下游每个调度器如何处理禁用状态。

## 隔离测试结果：8项通过

命令：`node scripts/test-mapping-step-semantics.cjs`。结果文件：[mapping-step-semantics-test.json](mapping-step-semantics-test.json)。

脚本从当前源码提取两个InjectSteps、两个SetFinished及IsFinishedInSystem2的原方法体；用最小内存对象承载相同字段，调用系统.NET Framework C#编译器编译执行，记录源文件哈希。临时源文件/可执行文件在完成后清理，不引用生产程序集。

已验证：重复步骤名只加入一次；名称不匹配不注入；新步骤false；重复注入保留true；一个false使完成判定false；完成方法把现有键置true；空S2字典返回true；原生无参Split保留连续空格和结尾空格产生的空字段。

**范围限制：这不是完整Mapping导出/导入往返测试。** 未执行真实TransportUnit构造、坐标/配置单例、文件读写、UI或设备。C#容器是测试替身，行为结论仅限被提取的方法。完整文件格式、单位置及多阵列样本往返仍未完成。

## 精确证据

在[源码阅读器](module-source-explorer.html)搜索restorestep；复用已有tu-construct-init、tu-inject-s1、tu-inject-s2、codemap-read。路径相对trunk/AKRS.ZX2200。

|ID|文件与行号|
|---|---|
|tu-construct-init|TransportUnitSystem/Module/Matter/TransportUnit.cs:65–143|
|tu-inject-s1|Main/Machine/Process/S1ActionNodeController.cs:859–882|
|tu-inject-s2|Main/Machine/Process/S2ActionNodeController.cs:1410–1433|
|codemap-read|TransportUnitSystem/Service/TuService.cs:1953–2079|
|restorestep-finish1|TransportUnitSystem/Module/Information/BondPositionInfo.cs:166–178|
|restorestep-finish2|同上:200–212|
|restorestep-isfinished2|同上:145–161|
|restorestep-disable-bond|TransportUnitSystem/Module/Matter/BondPosition.cs:205–208|
|restorestep-disable-module|同目录Module.cs:329–335|
|restorestep-disable-substrate|同目录Substrate.cs:323–329|

下一步：把构造/注入/导入覆盖关系接入恢复专题图，并补真实编解码方法的隔离文件样本；随后逐一追踪禁用与完成状态的调度消费，不以本轮8项测试替代这些缺口。
