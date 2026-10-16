# 旧全局标定：单轴补偿、测试与记录

复核日期：2026-09-28。范围为 `FrmGlobalCalibration` 的 ScaleX/ScaleY、StageCalibrationTest、RecordData、BondCompensateRecordData，以及直接居中/驱动映射依赖。只有源码复核，没有设备执行或精度验收。

## 简明流程

主界面打开旧全局标定窗口 → Start 先 Save 再检查当前 Task → 根据选项调用单轴补偿、测试或记录方法 → 按各分支扫描、PR、计算和输出。ScaleX/ScaleY 的名字不能解释成一般的比例拟合：实际是重复测量误差并**逐轮累加补偿表**，保存文件并下载 ETEL 驱动。测试/记录则输出 Excel，不是自动判定合格。

以下未注明路径的行号均来自 `trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs`。主调度已在 `global-calibration-source-review.md` 登记，这里补其内部行为。

## 入口与执行顺序

154–221：Start 调用 Save；仅当 globalCalibrationTask 为 null 或 IsCompleted 才清 isStop、新建并启动 Task。选项索引0为 RecordData(999)，2为 ScaleX，3为 ScaleY，4为 StageCalibrationTest；7在 while(!isStop) 中顺序 RecordData(1)→BondCompensateRecordData(1)。它们不是自动生产的必经阶段。

228–238：Stop 设置 isStop，再根据 SelectedText 决定是否保存 AxisCompensateProgram；没有调用停轴或等待任务返回。索引7中若第一段在内部因停止返回，第二段仍被调用，其前置 MoveBondXYZ 在它自己的首次停止检查之前。不能把 Stop 当作立即撤销所有后续动作。

## 单轴补偿 X / Y

| 顺序 | X 分支（863–941） | Y 分支（947–1020） |
|---|---|---|
| 关闭现有单轴补偿 | CloseXOffset | CloseYOffset |
| 循环 | SpCycleTimes 轮，每轮 ColumnCount 点 | SpCycleTimes 轮，每轮 RowCount 点 |
| 点位 | 起点X+j×ColumnSpacing，固定起点Y | 固定起点X，起点Y+j×RowSpacing |
| 每点 | 检查 isStop→MoveXY→Delay→按 PrName 查模板→DoWork | 相同步骤 |
| PR失败 | 非Success直接 return | 非Success直接 return |
| 误差来源 | 选项0：x=(1224−CenterX)×SpinX；否则居中后用计划X−轴命令X | 选项0：y=−(1024−CenterY)×SpinY；否则居中后用计划Y−轴命令Y |
| 累积 | 第一轮 Add(x)，后续 result[j]+=x | 第一轮 Add(y)，后续 resultY[j]+=y |
| 每轮输出 | SaveMappingDataX(BondX,0,startX,result,X)→DownloadMapping(X轴,X) | SaveMappingDataX(BondY,1,startY,resultY,Y)→DownloadMapping(Y轴,Y) |
| 首轮之后 | 设置 isFirst=false，然后 OpenXOffset | 设置 isFirst=false，然后 OpenYOffset |

这不是取多轮均值。后续轮已启用首轮补偿，再把新的残差加到表中。方法本身没有包围全程的 finally 来恢复原补偿状态；首轮中途停止或 PR 失败会跳过重新启用。零轮也会先调用关闭补偿再不进入循环；是否允许输入零轮需另核控件约束。

Close/OpenXOffset、Close/OpenYOffset（508–575）均强制转换为 ETELAxis，调用 scaleMappingDeactivate/Activate 后 ResetError→ServoOn→GoHome。开关并非纯内存标志，它们会触发回零调用。没有在这些方法里检查 GoHome 的返回结果，也没有非 ETEL 分支。驱动回零等待语义仍待 SDK/设备确认。

## 映射文件与下载边界

`Infrastructure/Utils/ETelDrive.cs:204–282`：SaveMappingDataX 生成 ETEL 文本并覆盖 DeviceDirPath 下 X.txt/Y.txt。Origin 为 start/1000；Step size 固定为 `3.0e-3`，没有使用调用方配置的 ColumnSpacing/RowSpacing；Table size 为表长；Data unit factor 固定 -3；数值格式为4位小数。文件头中的日期、设备型号/序列号等为字面量，不能把它们作为当前设备身份或测量时间证据。

`ETelDrive.cs:54–69`：DownloadMapping 将同路径文件传给 scaleMappingDownload，使用 SCALE_MAPPING_MODE_ZERO_EDGE；只 catch DsaException，弹窗后正常返回。调用者随后仍可能 OpenXOffset/OpenYOffset，不能由“方法返回”证明下载成功。保存错误则包装并抛异常；转换类型等非 DsaException 也没有被该下载方法捕获。驱动端表内容、激活状态和单位正确性未验证。

## 公共居中循环

310–349：查模板→每轮等待200ms→DoWork；失败弹 Vision fail 后 void return；成功且像素距(1224,1024)两方向都小于0.1时返回，否则用当前轴命令位置及 SpinX/Y 计算校正，分别 AbsoluteMove X/Y，等待100ms并 goto RetryCommand。

该循环没有最大次数或 isStop 检查。PR失败和成功居中都通过同一个 void return 返回；Scale 和 Test 的调用方没有独立成功标志可消费。因此，居中返回不等于达到精度，Stop也不能在此循环内保证被观察。没有从 Sleep 推断轴已到位。

## StageCalibrationTest 实际测试步骤

670–736：清结果→居中→读取实际起点→循环 `j < ColumnCount−30`。每点先检查停止（清结果并 return），移到起点X+j×列间距、起点Y+5，再居中、读实际位置，再移到该位置X+50，等待后 PR。成功记录像素XY、前一个 point3D 的XY、计算偏移及两个0；失败抛异常。全部循环完成才导出 Excel 并清结果。

偏移公式 x=−(1224−CenterX)×SpinX×direct，y=(1024−CenterY)×SpinY×direct；direct 字段为1（85）。记录的 point3D 不是随后 +50 移动的目标，不能把该列直接解释为本次最终轴位置。ColumnCount≤30时循环无点，但前置居中已经发生，仍调用导出。没有通过/失败阈值汇总，也没有异常时导出部分结果的 finally。

## RecordData 与 BondCompensateRecordData

RecordData（743–817）：先清结果并 MoveBondXYZ 到 GlobalCalibrationDomain.StartPoint3D，查 PR，然后 count轮×RowCount×ColumnCount。每点检查 isStop→名义网格 MoveXY→Delay→DoWork；成功记像素、名义位置、轴实际位置。PR失败**不会退出**，而是记录1224/1024及99999.9999位置占位，继续扫描。每完成整轮才输出一个Excel并清列表，停止中途不写本轮未完成的记录。

BondCompensateRecordData（1527–1603）使用 BondCompensate 的起点/PR/行列数和间距，但等待时间仍取 GlobalCalibrationDomain.Delay；调用 GetBondCompensate，把返回点XY加到名义位置后移动，成功/失败占位与普通记录相同。每轮输出文件名多“固晶相机标定”后缀。

重要：既有 `cp-bond-return` 证据已经证明 BondCompensate.GetBondCompensate 在创建新 AKRSPoint3D 后无条件返回，后续插值不可达。此记录分支不能因此称为验证了有效的邦头二维插值；也不能与生产使用的 TransportUnitCompensate 混为一谈。新点默认值仍以实际类型定义为准。

## 二维补偿开关及 AutoScale

窗口 CloseStage（415–445）：ETEL轴走 ETelDrive.Close2DCompensate，其他轴类型走 GuGaoDrive.Close2DCompensate；之后先Y再X执行复位、使能、回零。OpenStage（450–503）：ETEL先关闭补偿、先X再Y回零，再 Open2DCompensate；GTAxis先关闭、先Y再X回零，再 GuGaoDrive.Open2DCompensate。其他轴类型在 OpenStage 中没有分支，和 CloseStage 的兜底行为不同。

ETelDrive.cs:292–329：Open2DCompensate 使用域 TextName 下载文件，忽略传入 fileName 参数，然后域 Save、stageMappingActivate。其双轴下载包装（27–46）同样吞掉 DsaException，仅弹窗；下载调用正常返回后仍执行保存/激活。Close2DCompensate 先禁用两个轴的单轴表，再判断并关闭二维表，不是只关二维表。

GuGaoDrive.cs:1017–1046：默认 pulseRatio=10000。StepX/Y 表达式先把间距强转 int **再乘** pulseRatio，而起点是乘完再转 int；因此小数间距会先被截断。AutoScale 为true时把两个网格维度各加20，再 SizeAutoExpend；1056–1085沿增大索引方向复制末行/末列/末角点，没有在这里移动补偿起点。这不是单轴 ScaleX/Y 的自动调用。

GuGaoDrive.cs:897–1008：写核心2的X/Y补偿表及使能参数，累计SDK返回值，合计为0返回true，否则false。窗口 OpenStage 没有消费此bool；因此窗口调用返回不等于驱动配置成功。Close2DCompensate（839–887）在累计值非0时抛异常。SDK各返回码意义及累加作为成功判据是否可靠尚未验证。

## Excel 结果真正写到哪里

`Infrastructure/Utils/FileHelper.cs:104–130`：CreateFileByDate(全局标定) 构造并创建 `D:\全局标定\当前配方名\年\月\日` 目录（年/月/日字符串带中文后缀）。配方名取 MachineConfigContext.CurrentRecipe.RecipeName，目录不可用或配方为空的恢复未在此处理。

`FileHelper.cs:30–61`：使用 ExcelPackage，选择首工作表或新建 sheet，设前10列宽度15，把列表逐项写入，从A1开始，不加表头/单位，再 Save、Dispose。异常时没有 finally 保证 Dispose；也没有在此生成成功/失败汇总。接手者需按各记录分支的列序解释数值和99999.9999占位，不能把占位当实际测量。文件头文字和单位说明应由交付分析补充，不能假设工作簿自带。

## 输入输出与剩余验收

输入包括模式、循环次数、起点、行列数/间距、Delay、PR模板、像素比例和驱动类型；输出包括驱动补偿开关/回零/下载、X/Y文本表及 FileHelper 保存的 Excel。此调用链未出现直接网络 API 或队列调用；下层运动/视觉通信不在此结论范围内。

已补到源码内的 FileHelper 保存、二维OpenStage/CloseStage、AutoScale扩展。待补：配置约束/单位正确性、外部SDK返回值及回零等待契约、故障时补偿恢复、实测文件质量与设备验收；其他标定窗口和工具仍须按模块清单推进。已覆盖上述代表方法不等于整个 CalibSystem 或全项目验收。

## 可点击源码证据

- [sr-scale-x：FrmGlobalCalibration.cs:863–942](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L863)
- [sr-scale-y：FrmGlobalCalibration.cs:947–1021](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L947)
- [sr-offset：FrmGlobalCalibration.cs:508–575](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L508)
- [sr-center：FrmGlobalCalibration.cs:310–349](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L310)
- [sr-test：FrmGlobalCalibration.cs:670–736](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L670)
- [sr-record：FrmGlobalCalibration.cs:743–817](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L743)
- [sr-bond-record：FrmGlobalCalibration.cs:1527–1603](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L1527)
- [sr-direct：FrmGlobalCalibration.cs:80–85](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L80)
- [sr-stage：FrmGlobalCalibration.cs:415–503](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L415)
- [sr-etel-file：ETelDrive.cs:204–282](../../trunk/AKRS.ZX2200/Infrastructure/Utils/ETelDrive.cs#L204)
- [sr-etel-download：ETelDrive.cs:54–69](../../trunk/AKRS.ZX2200/Infrastructure/Utils/ETelDrive.cs#L54)
- [sr-etel-download-2d：ETelDrive.cs:27–46](../../trunk/AKRS.ZX2200/Infrastructure/Utils/ETelDrive.cs#L27)
- [sr-etel-stage：ETelDrive.cs:292–329](../../trunk/AKRS.ZX2200/Infrastructure/Utils/ETelDrive.cs#L292)
- [sr-gt-close：GuGaoDrive.cs:839–887](../../trunk/AKRS.ZX2200/Infrastructure/Utils/GuGaoDrive.cs#L839)
- [sr-gt-open：GuGaoDrive.cs:897–1008](../../trunk/AKRS.ZX2200/Infrastructure/Utils/GuGaoDrive.cs#L897)
- [sr-gt-params：GuGaoDrive.cs:1017–1046](../../trunk/AKRS.ZX2200/Infrastructure/Utils/GuGaoDrive.cs#L1017)
- [sr-gt-expand：GuGaoDrive.cs:1056–1085](../../trunk/AKRS.ZX2200/Infrastructure/Utils/GuGaoDrive.cs#L1056)
- [sr-excel：FileHelper.cs:30–61](../../trunk/AKRS.ZX2200/Infrastructure/Utils/FileHelper.cs#L30)
- [sr-directory：FileHelper.cs:104–130](../../trunk/AKRS.ZX2200/Infrastructure/Utils/FileHelper.cs#L104)
- [gc-dispatch：FrmGlobalCalibration.cs:154–221](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L154)
- [gc-stop：FrmGlobalCalibration.cs:228–238](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L228)
- [cp-bond-return：BondCompensate.cs:23–86](../../trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/BondCompensate.cs#L23)
