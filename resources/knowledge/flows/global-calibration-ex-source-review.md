# Ex 全局标定：扫描、补偿验证与循环调度

复核日期：2026-09-28。范围为 `FrmGlobalCalibrationEx` 的扫描调度及其直接数据/异步依赖。它是独立窗口，不应并入自动生产的必经步骤。本文是源码结论，不代表设备运行、精度或安全验收。

## 工作流程摘要

准备扫描点和 PR/起点等配置 → 选择普通扫描或带补偿扫描、模拟或实际 → 启动按钮经 UIActionAsync 调度 → 每点先过暂停闸门、检查取消 → 可选温漂拍摄 → 运动/等待/PR → 更新点位及日志 → 扫描返回后恢复控件 → 触发完成事件；勾选循环时，完成事件延迟 500ms 再调用启动按钮。补偿区域由另外的按钮生成，不是普通扫描自动产生。

主要源码为 `trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs`；以下行号均指此文件，其他路径另注。

## 主入口与生命周期

- 574–624：未选择启动项时提示并返回。启动时创建已置位 ManualResetEvent 和 CancellationTokenSource，禁用模式/模拟/温漂配置控件。索引 0 调用 ScanPoints；其他选中索引调用 ScanPointsWithCompensation，分别 await；finally 恢复相关控件。
- 622：完成事件位于 try/finally **之后**。扫描正常返回才到这里，传播异常不会执行该事件；不要把 finally 恢复 UI 解释为任务成功。
- 1078–1091：暂停按钮 Reset 闸门，继续按钮 Set。暂停不会立即中断当前轴动作、PR 或 Delay。
- 1392–1396：停止按钮先 Set，再 Cancel；没有直接停轴，也没有关闭循环复选框。循环内看到取消是 break，而非抛出取消异常。因此，若正在执行的任务通过 break 正常返回，仍能触发完成事件；若 Task 在开始前取消等导致 await 抛异常，则不会触发。
- 1609–1637：复选框通过订阅/退订完成事件控制循环；处理器 Task.Run→Delay(500)→Invoke→BtnStartBoot_Click。没有在延迟后重查复选框、取消状态或关闭状态。由此可见，已派发的下一轮不能仅靠退订撤回；实际时序需运行验证。
- 227–249：关闭时依据启动按钮 Enabled 判断是否允许关闭；允许关闭且 isEdited 时询问是否 Save；运行中阻止关闭。不能以此证明不存在所有并发或关闭竞争。

## 四条扫描分支

| 模式 | 点位处理 | 保存和日志 | 源码 |
|---|---|---|---|
| 普通模拟 | 按 ScanData 顺序；暂停/取消检查；Delay；ScanAxisX/Y=AxisX/Y+随机[-.002,.002)偏移 | 每10点 FlushAsync；循环结束（包括取消 break）调用域 Save；本分支没有最后一次显式 Flush/finally | 659–704 |
| 普通实际 | 先移到界面起点 XYZ；逐点可选温漂拍摄→移动到 AxisX/Y→Delay→PR→像素转机械位置→更新 ScanAxisX/Y | 每10点刷新；正常循环退出后域 Save；循环区域的 finally 刷新日志。起点移动在该 try 外，不受这段 finally 覆盖 | 708–853 |
| 补偿模拟 | 逐点 Interpolate(AxisX,AxisY)；记录名义位置加补偿；已有 ScanAxis 均为0才以补偿后位置作日志替代值 | 每10点刷新；无分支末尾显式 Save 或最终 Flush；不执行真实运动 | 882–927 |
| 补偿实际 | 起点移动→温漂分支→Interpolate→移动到 AxisX/Y+compensation.X/Y→Delay→PR→更新 ScanAxisX/Y | 日志同时记录原始指令位置、补偿值和编码器；每10点/循环 finally 刷新；本分支无域 Save | 931–1069 |

实际扫描 PR 非 Success 在 835–838、1052–1055 **抛异常**，没有本地重试或占位继续，不能采用附近“直接返回”注释代替代码。已更新的内存点位不会由上述代码回滚；普通实际扫描异常会跳过循环后的域 Save，但仍尝试 finally 刷日志。日志实现的缓冲、自动落盘和失败保证需另核。

## 温漂、坐标与预测分支

- 开启温漂后，第一个点拍摄；以后按点数取余或 Stopwatch 超时拍摄。ScanPoints 中 748–771，带补偿中 972–995。点数间隔变量来自控件，方法内没有显式非零检查，界面约束仍需另核。
- VisionTpMark（860–872）将 UpLookMarkVisionPos1 转 G0，再调用 System2CommonVision，固定“温漂定位”/“上视温漂测试Mark”，然后 GetAxesPosOfMark。
- GetAxesPosOfMark（349–353）用当前三维实际位置及 MatchResult 执行 ConvertPixelToG0Pos，再 ConvertG0ToMachinePos，返回 XY。温漂拍摄后的扫描点走 MoveSafeBondXYZ 并重设硬件/灯光；其余点走 MoveXY。
- 普通实际扫描的 Predict 分支（824–830）只把结果写入“预测补偿值um”日志，未用于此处运动目标；带补偿扫描的运动补偿来自 BilinearCompensator，不是该预测器。
- 1640–1694：预测器初始化代码全部注释。Predict 在 predictor 为 null 时明确返回 (0,0)；关闭勾选直接 predictor.Dispose()，没有 null 判断。不能将此界面描述为已启用 ONNX 自动补偿。以上是可见字段/方法路径，不包含反射或外部注入证明。

## 配置与补偿区域

- 窗口 Save（290–301）从 UI 更新 StartPoint3D、ColumnSpacing、RowSpacing、PrName、Delay 后调用域 Save。启动处理器没有调用此窗口 Save；起点取 UI 值，而 Delay/PrName 等读取域对象，是否已同步应从具体配置操作追踪，不能假设启动即保存。
- GlobalCalibrationDomainEx 保存 ScanData、Compensator 等。ScanCompletedFlag 的实际定义是所有 ScanAxisX/Y 中等于0的值数量小于3，**不是本次运行已完成标志**；空列表也满足这个计数条件。
- 1098–1122：生成区域按钮先检查上述标志，弹窗口获取区域名/优先级，再将 ScanData 构造 BilinearCompensationRegion 并 AddRegion；这段没有显式 Save。数据充足性由后续构造检查，不能单靠标志认定数据齐全。

## 数据准备、导入和文件输出

1. 主界面 `UcMainSystem.cs:1723–1726` 的 BarBtnCalib2D_ItemClick 创建 Ex 窗口并 Show。Load（161–191）把间距、行列数、Delay、PR 名称绑定到域对象，加载起点和两个列表；“启动不调用 Save”不等于“UI 从不更新域对象”，Binding 的更新时机尚未沿下层确认。
2. 预定义点自动扫描（361–409）先询问确认，再经 UIActionAsync 执行4×4循环，调用 MoveBondXY→MoveToCameraCenter→读取实际 XY，最后 BeginInvoke 替换 ScanData 并 Save。外层 Y 移动后没有立即更新 currentPos，内层移动仍使用变量 currentPos.Y；这是可见指令顺序，不保证所得点构成理想4×4网格。提示也要求人工确认视觉高度。这个准备循环没有使用扫描任务的暂停/取消变量。
3. 根据预定义点生成（417–555）要求至少3点，以 WorldXY→AxisXY 拟合矩阵，将矩阵写入固定 D 盘文件，按四个象限扩展，再将所有点转成 AxisXY、替换列表并 Save。rowSpace 和 colSpace **都读取 SpRowSpacing**（459–460）。四个象限中任一行/列数为0会由 CalcAndFillQuadrant 抛异常；本地没有继续忽略该象限的分支。
4. 根据扫描点重建（1512–1601）另检查 ScanCompletedFlag，拟合输入改为 WorldXY→ScanAxisXY，其余扩展/赋值/Save 类似；colSpace 同样读取 SpRowSpacing（1559–1560）。不能将其误写为 X/Y 各用对应间距控件。
5. Sort 按钮（558–563）调用 GlobalCalibrationData.Sort 并替换内存列表；扫描循环本身沿列表原顺序，不自动调用这个按钮，也没有在该排序方法末尾显式 Save。排序算法内部仍待复核。
6. 导入（1403–1438）：选 JSON→ReadGenericList→非 null 时先 Save **旧配置**→替换内存 ScanData→刷新。该处理器未在替换之后 Save；错误弹窗。不等于新列表已持久化。
7. 导出（1446–1476）：SaveGenericList 保存选定路径；另以字符串 `Formatted_` 直接前缀完整 fileName 创建日志目标，逐项 AddData；没有在这段看到 CommitData/FlushAsync。格式化文件的路径和最终内容需验证，不能按注释宣称已成功生成 Excel。

配置文件：`ZX2200PathConfig.cs:354` 为 DeviceDirPath 下的 `GlobalCalibrationDomainEx.json`，由 GlobalCalibrationDomainEx 静态构造（18–26）指定。Singleton 保存实现仍属既有缺口。扫描 JSON 日志固定输出到 `D:\2025二维标定数据采集`，名称仅含 HHmmss；拟合矩阵使用固定文件名、OpenOrCreate，方法未显示目录创建或显式截断。上述是路径/调用事实，未在设备上验证目录、冲突或写入结果。

## 区域补偿如何进入运动

源码：`trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/BilinearCompensator.cs`。

- 43–58：构造要求至少4条，按四舍五入至6位的 WorldY 分组、WorldX 排序；网格键为 AxisXY，值为 ScanAxisXY−AxisXY。不会因为名为“补偿”自动改变符号：Ex 实际扫描把此插值结果**加到**名义位置（1000–1014）。
- 62–109：在相邻行/列的四边形单元内查找；找不到返回 false。119–143 的双线性计算用对角坐标构造分母，绝对值小于1e-10时抛异常。非规则网格精度及数据完整性不能由代码结构证明。
- 249–268：AddRegion 后按 Priority 降序排序。294–305：遍历首个 Contains 的区域并返回其插值；所有区域都不包含时明确返回 (0,0)，无警报。Contains（214–216）本身调用 TryInterpolate，因此选中区域会计算两次，异常可能发生在筛选阶段。
- 区域生成、排序与扫描是分开的人工入口；没有证据表明 Ex 生成区域会自动替换此前生产链使用的 TransportUnitCompensate。二者不得合并。

## 异步包装与硬件动作边界

`Infrastructure/Service/ControlService.cs:150–153,213,248–308`：Func<Task> 重载转 Delegate，进入公共静态 SemaphoreSlim(1,1) 包装；已占用时提示并返回，通过后禁用触发控件、等待 AsyncHelper.ExecuteAsync，通常再恢复控件并释放信号。外层 catch 是空的，控件恢复不在 finally，故不能声称任意异常都恢复按钮。该闸门仅覆盖使用此包装的动作，不能代表所有生产/Only任务互斥。

`Infrastructure/Utils/AsyncHelper.cs:18–38`：Func<Task> 分支真正 await 动作，catch 调用异常处理器、不再向上传播；包装的 HandleException 把异常消息交给 UI 弹窗。这不会使已经在异常处退出的 Ex 委托继续执行其后面的完成事件。

MoveXY（309–341）：ETEL 分支获取插补组，设置绝对坐标及速度/加减速等，x/y除1000后 ipolLine，再 ipolWaitMovement(100000)、ipolEnd；否则调用 BondModule.MoveBondXY。没有在本方法用 finally 保证 ipolEnd，也没把取消令牌传入这些硬件调用。参数100000的SDK具体时间语义与硬件停止保证需另核，不能直接当作已验证的超时策略。

## 状态与待补事项

已核实 Ex 主入口、点位准备/重建、四条扫描分支、温漂/预测、区域插值、导入导出、暂停/取消/循环及异步包装。仍待核：中心对准/转换拟合的数值细节、列表排序及编辑分支、日志库和 Binding/Singleton 契约、循环取消时序、界面数值约束。全局旧窗口的 Scale/Test/Record 剩余算法也仍待展开。

这里只登记代表性调用与明确行范围，未把整个窗口或模块标记完成；外部相机/运动 SDK、设备停止终态、日志落盘、保存恢复和精度均待验证。

## 可点击源码证据

- [ex-entry：UcMainSystem.cs:1723–1727](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L1723)
- [ex-load：FrmGlobalCalibrationEx.cs:161–191](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L161)
- [ex-start：FrmGlobalCalibrationEx.cs:574–624](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L574)
- [ex-sim：FrmGlobalCalibrationEx.cs:659–704](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L659)
- [ex-scan-start：FrmGlobalCalibrationEx.cs:708–803](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L708)
- [ex-scan-end：FrmGlobalCalibrationEx.cs:803–853](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L803)
- [ex-td：FrmGlobalCalibrationEx.cs:860–872](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L860)
- [ex-comp-sim：FrmGlobalCalibrationEx.cs:882–927](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L882)
- [ex-comp-scan：FrmGlobalCalibrationEx.cs:931–1069](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L931)
- [ex-pause：FrmGlobalCalibrationEx.cs:1078–1091](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L1078)
- [ex-stop：FrmGlobalCalibrationEx.cs:1392–1396](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L1392)
- [ex-cycle：FrmGlobalCalibrationEx.cs:1609–1637](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L1609)
- [ex-close：FrmGlobalCalibrationEx.cs:227–249](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L227)
- [ex-predefine：FrmGlobalCalibrationEx.cs:361–409](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L361)
- [ex-grid：FrmGlobalCalibrationEx.cs:417–564](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L417)
- [ex-regrid：FrmGlobalCalibrationEx.cs:1512–1601](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L1512)
- [ex-files：FrmGlobalCalibrationEx.cs:1403–1476](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L1403)
- [ex-region：FrmGlobalCalibrationEx.cs:1098–1122](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L1098)
- [ex-predict：FrmGlobalCalibrationEx.cs:1640–1694](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L1640)
- [ex-domain：GlobalCalibrationDomainEx.cs:18–88](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/GlobalCalibrationDomainEx.cs#L18)
- [ex-path：ZX2200PathConfig.cs:350–354](../../trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs#L350)
- [ex-map：BilinearCompensator.cs:43–89](../../trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/BilinearCompensator.cs#L43)
- [ex-interp：BilinearCompensator.cs:98–184](../../trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/BilinearCompensator.cs#L98)
- [ex-priority：BilinearCompensator.cs:209–305](../../trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/BilinearCompensator.cs#L209)
- [ex-ui-wrapper：ControlService.cs:248–308](../../trunk/AKRS.ZX2200/Infrastructure/Service/ControlService.cs#L248)
- [ex-ui-overload：ControlService.cs:150–154](../../trunk/AKRS.ZX2200/Infrastructure/Service/ControlService.cs#L150)
- [ex-ui-signal：ControlService.cs:213–213](../../trunk/AKRS.ZX2200/Infrastructure/Service/ControlService.cs#L213)
- [ex-async：AsyncHelper.cs:18–38](../../trunk/AKRS.ZX2200/Infrastructure/Utils/AsyncHelper.cs#L18)
- [ex-move：FrmGlobalCalibrationEx.cs:309–353](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L309)
- [ex-save：FrmGlobalCalibrationEx.cs:290–301](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs#L290)
