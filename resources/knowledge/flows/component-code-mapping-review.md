# 芯片码值到Mapping文件与恢复链路

更新：2026-09-28。范围为本地C#静态控制流；未操作设备或读写现场D盘数据。

## 完整工作步骤

上视读码成功 → BondPositionInfo.ComponentCode → SaveMappingToLocal按AutoSaveBondPositionComponentMapping分流 → 生成文本Mapping → 手工选择文件或扫码构造路径 → ReadTransportMapping按同一开关选解析器 → 新建载具并注入制程 → 恢复码值/状态 → UI应用到载具槽位。不是后台自动同步数据库，也不是逐焊点完整备份。

## 保存何时触发

BondTask.SendAway在没有配置流道且设备未Stop时，若AutoSaveMapping开启则调用保存；随后设置“Mapping成功保存”提示和日志，清空BondSubSectionProgram.TransportUnit，设置NoMaterial，提示人工拿走，最后Stop。配置流道的分支只在此处发送允许传送信号，不能据此宣称每个自动出料都保存码值。

另有FrmTransportUnitMapping的手动保存按钮直接调用SaveMappingToLocal。AutoSaveMapping是生产调用条件；AutoSaveBondPositionComponentMapping是保存/读取的格式选择条件，二者不可混为一个开关。

## 文本格式与信息损失边界

文件路径由固定D盘目录、当前MachineConfigContext.RecipeName、载具SubstrateNumber和.txt组成。StreamWriter的append参数为false，同路径会覆盖；没有临时文件加替换机制。内容开头四行来自载具RecipeName、SubstrateLotNumber、SubstrateNumber、FaceType。目录配方与文件头配方来自不同对象，此方法没有校验一致性。

存在三种阵列分支：基板与模块均多阵列、仅基板多阵列、仅模块多阵列。每个分支继续写行数、列数、总数，再在索引7先插OK后插NG，最终第8行NG、第9行OK，第10行起为数据。NG按总数减成功数计算，包括未完成项，不等于只统计物理不良。两种IsMultiple均false时没有这些阵列分支，只保留四行元信息后写文件。

每个输出位置：module.IsFail()写X；否则System2已完成写module.BondPositions[0].BondPositionInfo.ComponentCode；否则写1。用空格拼接且未转义，码值X、1与控制标记冲突；空码、含空格码值需要专项验证。读取用Split，没有显式RemoveEmptyEntries参数。本轮不假设现场码值必然触发这些边界。

**导出仅取模块第一个焊点的码值，导入却把该位置码值赋给模块内每个焊点。** 因而不能把它作为所有焊点不同码值的无损往返格式。

## 导入及状态恢复

ReadTransportMapping(string)依据当前软件开关选择码值解析器，不从文件头识别版本。文件不存在提示并返回null；存在则ReadAllLines，新建TransportUnit，先注入S2和S1制程，再从前四行恢复载具信息。

阵列循环采用当前ProductConfiguration的行列数，从文件索引9开始取数据；不按文件记录的行列数重建循环，也没有在此比对配方、长度或格式版本。X禁用模块；仅基板多阵列分支的X禁用基板。值为1不进入完成赋值；其他值给模块全部焊点设置System1/System2完成并复制ComponentCode。所有分支最后返回载具。catch代码被注释，文件格式错误、索引越界或对象缺失可能向调用方传播。此处没有声明全软件都无异常处理。

手选路径读取成功后写TransportProgram.BondSubSectionProgram.TransportUnit并重建显示控件；扫码入口要求当前Transport非空，按输入ID拼路径，成功后写baseSubSectionProgram.TransportUnit。两者目标表达式不同，不能概括为所有入口同一槽位。取消文件选择返回null。扫码窗取消值、槽位具体绑定及权限门控后续核对。

## 失败传播

码值保存函数catch仅显示“保存失败”，返回类型void，不重抛也不返回失败状态。若此catch正常返回，BondTask仍执行其后的成功提示、清空载具和人工拿走流程。实际是否保存完整必须核对文件，不能只凭成功日志。

## 精确证据入口

在[源码阅读器](module-source-explorer.html)搜索codemap。除特别注明外，文件为trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs。

|ID|位置|
|---|---|
|codemap-send|BondSystem/Tasks/BondTask.cs:443–489|
|codemap-switch|TuService.cs:1385–1391|
|codemap-export-grid|1578–1739，三种阵列和标记|
|codemap-write|1741–1762，覆盖保存和catch|
|codemap-select|1769–1825，文件选择及解析器分流|
|codemap-read|1953–2079，重建/赋码/状态恢复|
|codemap-ui-read|Controls/Mapping/FrmTransportUnitMapping.cs:107–125|
|codemap-ui-save-id|同上:175–213|

复用uplookextra-code-call与uplookextra-code-field作为码值写入起点。快照包含行号并绑定源文件哈希。

## 仍需完成

- [ ] 用脱离设备的样本验证多阵列、单位置、保留标记、空值及多焊点不同码值往返。
- [ ] 展开TransportUnit构造、InjectSteps及完成/禁用方法的所有副作用。
- [ ] 核对Mapping窗口槽位绑定、扫码取消语义和运行期间权限。
- [ ] 现场真实文件与配方对应、历史格式兼容、磁盘写失败与覆盖策略验收。
- [ ] 按既定计划继续激光检测调度及外部硬件关闭契约；本专题不改变29组部分复核状态。
