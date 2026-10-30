# Mapping导入到生产动作：对象与门控

更新：2026-09-28。本专题是当前源码静态分析，未操作设备。

## 已核实的执行链

S1/S2载具菜单分别用DispenseSubSectionProgram、BondSubSectionProgram构造同一Mapping窗口，Transport属性始终读取构造传入的baseSubSectionProgram.TransportUnit。文件导入按钮却固定把读取结果赋给BondSubSectionProgram.TransportUnit；扫码输入ID按钮则赋给baseSubSectionProgram.TransportUnit。因而在S1窗口使用文件导入时，写入S2对象而显示仍读取S1对象；这是代码中的目标差异，不是已经现场复现的故障。

Machine.Start先PrepareMachineReadyToStart，成功后置Working；非补偿模式启动输送和供晶任务，再按配置启动点胶任务，之后执行S2 ActionNodesService.Init再BondTask.Start。输送任务已先启动，因此不能把这一段当成所有任务串行结束的证明。

BondTask运行中，补偿模式先创建测试TransportUnit；随后对当前BondSubSectionProgram.TransportUnit注入步骤。Enable分支内，若IsProduct为false且启用输送，再用System2构造器创建新TransportUnit并将新对象IsProduct设true。TransportUnitInfo.IsProduct默认false；码值读取方法未设置该字段。Mapping窗口Load将当时对象设true，但导入后替换的新对象未在该按钮内设true。由此存在恢复对象被这条条件路径替换的静态风险，是否实际走到该分支取决于模式、Enable、输送配置和其他时序，尚未做运行复现。

## 动作如何消费恢复步骤

BondPosition.IsS1NeedStep / IsS2NeedStep直接对对应RemainingSteps字典按stepName索引并取反，不执行TryGetValue；键缺失会抛异常，不能理解成自动跳过或自动补步骤。

PickActionNode.IsDoWork先检查Disable或EnableInSystem1，再用当前步骤名调用IsS2NeedStep；字典true时返回false。BondActionNode还先要求EntityState==Process，然后检查相同的状态及步骤条件。S1DispenseActionNode先确认焊点非null，再检查Disable/EnableInSystem2和IsS1NeedStep。字典已true时可经这些门控跳过取片、固晶或点胶动作；不代表全部其他动作都不执行。

BondTask循环GetNextActionNode后检查actionNode.IsDoWork；为false时不进入执行分支，但仍到FinishCurrentActionNode，将该队列消息标为完成。这条桥接连接了“恢复步骤字典”与“独立动作队列Finished”，前提是同一恢复对象没有被替换且步骤键匹配。

## 尚未闭合

- 输送任务启动后对同一载具的并发赋值与其余重建路径。
- S1点胶循环如何标记跳过动作、其余校正/蘸胶/检验动作的门控。
- 不修改现场源码；上述条件分支须用匹配配置的隔离样本与后续运行证据验证。
- 完整Mapping编解码往返、配方和尺寸一致性仍未验收。

证据导航将在源码阅读器以restorestart前缀登记。

## 进一步核实：动作与S1循环

上视校正、下视校正、蘸胶、焊后检查均先检查禁用/仅S1启用，再按当前步骤名查IsS2NeedStep；蘸胶还要求DipMode不是Off。和取片、固晶一起，这六类S2动作在对应字典键为true且执行到这些门控时会返回false。这里不代表测高、整载具定位等所有动作都被跳过。

S1 DispenseWorkTask在Enable分支中，IsProduct为false便创建System1新载具并设true，**没有S2那项IsTransportConfigured条件**，然后再注入步骤。S1循环对IsDoWork==false执行goto Finish，最后FinishCurrentActionNode；Retry回循环，其他非Success返回码则回安全位置、Stop并返回。

输送StartTask在未配置输送时直接返回；正常分支在启动transportTask之前，可能按IsReverseSearch调用TransportProgram.RefreshTransportUnit，然后MapMaterial。RefreshTransportUnit对现有点胶、固晶、待下料对象调用Refresh，非直接new；Refresh和MapMaterial内部的全部副作用仍待下一步核对。StartTask返回void，内部检查失败Stop+return或catch提示，不返回启动成功布尔值；Machine.Start所示调用处没有据返回值阻止后续S2 Init。

## 原始方法隔离测试：30项通过

命令：`node scripts/test-mapping-action-gates.cjs`。结果：[mapping-action-gates-test.json](mapping-action-gates-test.json)。

提取七个实际IsDoWork方法（S2取片、固晶、上视、下视、蘸胶、焊后检查，以及S1点胶）和两个原始字典查询方法，用最小内存对象/服务/枚举替身编译执行。每个来源记录文件与方法片段SHA256。

每类门控分别验证：步骤false时允许；步骤true时跳过；Disable时即使缺键也提前返回false；启用且缺键时抛KeyNotFoundException。另验证非Process实体被Bond门控拒绝，但Pick门控本身不检查EntityState。合计30项。测试日志中的executes仅指IsDoWork返回true，未执行DoWork。

**不包含**：生产对象构造、实际单例/配置加载、启动/线程、输送搜索、完整Mapping编解码、设备或厂商DLL。这些替身测试不能证明现场可续跑。

## 新的优先核对项

1. 导入后的IsProduct=false何时改变，以及S1/S2重建条件是否会丢失恢复状态。
2. S1文件导入固定写S2与扫码写当前窗口的差异，是否符合产品设计。
3. Refresh与MapBelt是否进一步改变状态；后续输送交接是否保留对象身份。
4. 完整编解码样本验证，继续区分程序分析缺口与现场运行验证缺口。
