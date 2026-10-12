# 自动对焦入口与标定参数审计

验证：原方法替身测试三项通过——正向范围恒定评分共23次采样，反向范围共19次，采图失败在移动后向外抛出。前两项分别是5/1次粗扫与18次细扫；18仅是恒定评分情景，不是生产上限。未连接真实设备或运行WinForms。见[测试脚本](../../scripts/test-autofocus-range.cjs)和[源码快照及报告哈希](autofocus-entry-evidence.json)。

## 工作流摘要

已确认三类入口：人工晶圆辅助、按当前系统分派的辅助对焦、按钮确认后启动的焊头到相机偏移标定。它们不能合并成一条必经生产链。这里补齐入口与局部算法调用；不表示完整标定任务、所有界面或实际设备已验收。

| 入口 | 源码执行顺序 | 退出边界 |
| --- | --- | --- |
| 晶圆XY示教按钮 | [Designer:346](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/EjectionsTeach/FrmXYPositionTeach.Designer.cs#L346) → [处理器:467–486](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/EjectionsTeach/FrmXYPositionTeach.cs#L467)禁用按钮 → WaferTableController.Autofocus | 同步调用；catch显示消息，finally恢复按钮，未证明轴安全回位 |
| 顶针标定辅助按钮 | [Designer:242](../../trunk/AKRS.ZX2200/SupportFeature/Calibrate/FrmEjectionCaliTeach.Designer.cs#L242) → [处理器:416–442](../../trunk/AKRS.ZX2200/SupportFeature/Calibrate/FrmEjectionCaliTeach.cs#L416)检查IsUseWaferCameraAssistantEjectCenter | true走同步晶圆路径；false走BondCamera异步辅助 |
| 传送单元共用辅助 | [TUAssistantHelper:602–615](../../trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Assistant/TUAssistantHelper.cs#L602)按CurrentMachineSystem分派 | System1走DispenseController，其余走BondHeadController/BondCamera；本包装无catch |
| 焊头到相机偏移标定按钮 | [Designer:97](../../trunk/AKRS.ZX2200/CalibSystem/Controls/FrmStartup.Designer.cs#L97) → [处理器:98–110](../../trunk/AKRS.ZX2200/CalibSystem/Controls/FrmStartup.cs#L98)工具准备确认 → 仅OK时Task.Run → OnlyBondToCameraOffsetCaib → StartBondToCamCalibTask1 | 取消不启动该Task；此处未等待Task完成，不等于每次生产必经步骤 |

## 输入、算法与输出

[WaferTableController:1197–1202](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L1197)读取WaferTableLeftMarkWCVisionMachinePos.Z作为temp，使用晶圆相机和WaferCameraAxisZ，向AutoFocus传入pLimit=temp+5、nLimit=temp−5。该包装不写数据库或队列；主要输出是轴位置变化。

[标定任务:1937–1956](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1937)放片后等待、更新中心点、移动到左上Mark位置，再调用CalibController.AutoFocus(Bond,Z+2,Z−3)；返回后读取真实Z并更新中心点Z，随后执行PR定位与移动。这是局部调用顺序，不是整段标定的完整审计。

[CalibController:273–293](../../trunk/AKRS.ZX2200/CalibSystem/Services/CalibController.cs#L273)依次把endPos、startPos传给pLimit、nLimit，因此上述调用实际变为pLimit=Z−3、nLimit=Z+2。UpLook分支也使用BondCamera与BondHead.AxisZ；Dispense、Wafer分支为空。相机选择是否符合设计意图需要工程师确认。

[AutoFocus:215–312](../../trunk/AKRS.Galaxy2.AutoFocusing/Model/AutoFocusing.cs#L215)先移到nLimit，计算distance=(pLimit−nLimit)/5；每次先移动、采图评分，再检查当前位置+distance>pLimit。标定反向参数使distance=−1：从Z+2移到Z+1采第一个样本后，下一点Z>Z−3，粗扫立即退出。因此该输入不会完成通常正向范围的五点粗扫。随后仍进入细扫，方向和步长随评分变化；T==6且出现非上升评分才退出，没有固定总采样上限。

该方法无catch/finally，硬件调用异常向外传播；返回void而非焦点质量或成功标志。正常返回和按钮恢复均不能替代焦点质量验收。相机、轴控制和评分SDK是外部运行依赖。

## 异常与完成状态

[BondHeadController:1050–1085](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs#L1050)在try之外转换并禁用按钮，然后Task.Run；工作线程try调用AutoFocus并Invoke更新界面，catch显示消息，finally再次Invoke恢复按钮。Task仅保存在局部变量，未返回或等待；finally的Invoke无第二层catch，也未见窗体关闭检查。这里没有硬件复位操作。

[外层标定:1817–1832](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1817)调用StartBondToCamCalibTask1却不检查其bool返回值，之后仍生成结果项并显示结果窗口。[内层入口:1834](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1834)有try，[尾部:2258–2270](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L2258)捕获异常并返回false。因此内层正常返回false时，外层不会据此阻止结果展示；catch内部再次异常另当别论。窗口出现不能认定标定成功。

## 完成范围与缺口

- 已核对：上述按钮绑定、条件分支、参数传递、局部顺序和异常边界。
- 待核对：所有辅助窗体可达性、完整标定及保存分支、运行参数与单位、运动限位、急停/关闭/并发、实际焦点质量。
- 未修改生产源码；不扩大既有模块完整验收数量。源码风险应先由工程师确认意图，再另行实施修复。
- 统一入口：[成果首页](index.html)；总进度：[项目计划](project-plan-status.md)。
