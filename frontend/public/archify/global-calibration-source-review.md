# 全局标定入口、扫描与补偿写入

更新：2026-09-28。限定源码复核，未运行硬件或修改生产代码。

[统一入口](index.html) · [自动标定主链](calibration-module-review.md) · [模块进度](module-review-status.md)

## 先区分入口

[主界面1706–1726](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L1706)：全局标定按钮创建FrmGlobalCalibration并Show；另一个按钮创建FrmGlobalCalibrationEx并Show。它们不是StartAutoCalib串行链的子步骤，Ex实现本轮尚未展开。

[FrmStartup独立相机按钮33–108](../../trunk/AKRS.ZX2200/CalibSystem/Controls/FrmStartup.cs#L33)通过Task.Run启动OnlyBondCameraCalib、OnlyUpLookCameraCalib、OnlyWaferCameraCaib、OnlyDispenseCameraCalib和OnlyBondToCameraOffsetCaib；上视与偏移先进行工具确认。这里只确认入口，不能用Start系列实现替代Only系列内部复核；后者仍有待展开部分。

## 全局窗口的实际调度

[启动及模式分发154–221](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L154)：点击Start先Save，即使已有任务运行也先保存UI参数；只有本窗口task为null或IsCompleted才清isStop并创建新Task。每次主界面Show会新建窗体，局部task检查不证明跨窗口互斥。

| SelectedIndex | 实际调用顺序 | 本轮覆盖 |
|---|---|---|
| 0 | RecordData(999) | 已追行列扫描、PR失败占位与Excel输出 |
| 1 | InitData → PreliminaryCompensationX → PreliminaryCompensationY → Mapping2DCalibration(999) | 已追初始化、两轮预补偿、扫描与分阶段写入 |
| 2 | ScaleX | 仅确认入口；算法待展开 |
| 3 | ScaleY | 仅确认入口；算法待展开 |
| 4 | StageCalibrationTest | 仅确认入口；算法待展开 |
| 5 | InitBondCompensateCalibration → BondCompensateCalibration(999) | 已追数组初始化、扫描、补偿累加与保存 |
| 6 | InitData → X预补偿 → Y预补偿 → InitBondCompensateCalibration → while(!isStop)：Mapping2DCalibration(1)、BondCompensateCalibration(1) | 已追组合调用；不具统一收敛阈值 |
| 7 | while(!isStop)：RecordData(1)、BondCompensateRecordData(1) | 已追分发及RecordData；后者内部待展开 |

999是传入迭代次数，不是精度验收标准。模式6/7持续迭代直到停止标志生效；这里未见总时限或整体异常收尾。其他SelectedIndex无匹配分支则方法结束。不能把task完成当成补偿合格。

## 模式1：初始化、预补偿和二维扫描

[InitData1026–1052](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L1026)：调用CloseStage → MoveBondXYZ到起点 → MoveToCameraCenter → Invoke回填实际XYZ → Save；清空X/Y映射列表，按行×列用0.0001初始化。关闭补偿与居中函数的完整内部行为尚待后续复核。

[X预补偿1060–1131](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L1060)固定两轮：仅首行实际移动/定位、累加X偏差，其他行复制首行对应X映射。[Y预补偿1137–1208](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L1137)也两轮：仅首列实际移动/定位、累加Y偏差，其他列复制本行首列Y映射。PR非Success均抛异常，每轮完成调用SaveData。没有根据残差迭代到收敛的判断。

[Mapping2DCalibration581–664](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L581)：先MoveBondXYZ到起点，再循环次数→行→列；每个点开始检查isStop。点位为起点加列距/行距，MoveXY → 延时 → 按PrName查找PREntity并DoWork。Success时按固定像素中心(1224,1024)、SpinX/SpinY及direct计算偏差，累加对应X/Y映射并记实际XY。非Success写入八个999占位且补偿加0，然后继续下一点；不是重试，也不是立即停止。每完整一轮SaveData。

本轮尚未追direct和SpinX/SpinY全部赋值来源，不能把公式系数解释为已校准的物理单位。成功数据行与失败占位行列数不同（10与8），导出消费者如何处理尚未验证。

## Z-XY补偿与数据记录

[InitBondCompensateCalibration1512–1520](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L1512)新建行×列double数组后Save。[BondCompensateCalibration1404–1504](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L1404)先移动/居中，以GetCmdPosition回填起点并Save，再扫描。每点先GetBondCompensate(X,Y)，把返回XY偏移加到目标进行MoveXY；PR成功后累加新误差，失败记录八个99999占位并加0，完整一轮SaveBondCompensateData。后续复核发现BondCompensate.GetBondCompensate入口无条件返回新点，后续插值不可达；不能将这个调用视为已使用存储数组。贴装实际消费的是另一套TransportUnitCompensate，详见[补偿到生产链路](compensation-production-source-review.md)。

[RecordData743–817](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L743)：清结果、移动起点、取PR实体，按行列扫描；成功记录像素中心、计划XY、实际XY；失败记录中心1224/1024、计划XY及实际位置占位99999.9999。注释称失败直接返回，但实际else添加记录后继续。每完整一轮在CreateFileByDate(全局标定)下写时间戳.xlsx并清结果。

## 输出与外部边界

[SaveData及关联方法1234–1300](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L1234)：

- ETEL：设置TextName=StageXY索引，SaveMappingData写本地，Sleep(100)，DownloadMapping，OpenStage；文件路径/驱动写入成功语义属于外部接口，未验证。
- 非ETEL：映射乘10000并强转int形成二维CompensateX/Y，写入GlobalCalibrationDomain并Save，随后OpenStage。不是保留全精度double；范围与溢出未作运行验证。
- 之后导出本轮Excel并清结果；Bond补偿导出带“固晶相机标定”的文件名后调用Save。硬件补偿变化、配置保存与Excel输出不是单一事务。

[Save355–382](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L355)将两套起点、网格间距/尺寸、PR名称和延时等UI值写入域对象，分别保存GlobalCalibrationDomain与BondCompensate。配置最终存储路径/原子性需继续追域与Singleton实现，不在本轮作保证。

[MoveXY825–858](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L825)：ETEL走插补组，设置绝对模式、速度0.05、加减速0.5、JerkTime=0.01，ipolLine传X/1000和Y/1000，ipolWaitMovement(100000)后ipolEnd；非ETEL调用BondModule.MoveBondXY。100000是外部API参数，不据此推断单位或完整超时语义；该包装没有finally保证异常时ipolEnd。

## 停止、异常与最终状态

[Stop228–238](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L228)只置isStop=true；如果SelectedText等于Z-XY则直接返回，否则保存AxisCompensateProgram。这里使用SelectedText，不是SelectedIndex，本轮不保证其与UI模式一致。该处理器没有取消Task、等待Task结束或直接逐轴停轴。

检查isStop主要位于点循环开始，不能打断正在执行的运动、延时、PR或保存。Mapping/Record/Bond扫描在检查前各有起点移动或初始化。模式1中预补偿因停止return后，外层仍会调用后续方法；模式6若停止发生在Mapping调用内，外层本次仍调用BondCompensateCalibration，它会先执行起点移动/居中/Save才进入点循环检查。以上为源码顺序，不是实机停止性能测试。

[关闭289–304](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L289)：任务未完成时阻止关窗并提示先Stop；完成后Dispose。IsCompleted也可能包含故障结束，代码没有在此检查IsFaulted或读取异常，所以允许关窗不是成功证明。

## 仍待完成

Only系列具体实现、FrmGlobalCalibrationEx、ScaleX/Y、StageCalibrationTest、BondCompensateRecordData、Open/CloseStage与居中细节、域文件/补偿插值/生产消费、PR和驱动契约、线程并发/异常恢复及设备精度验收。本文不宣称全局标定已完整覆盖；也未将这套独立工具混入原自动标定主链图。
