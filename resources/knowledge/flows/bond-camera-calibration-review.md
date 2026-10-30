# 焊头到相机偏移标定：完整方法流程

范围：CalibrateTask.OnlyBondToCameraOffsetCaib及StartBondToCamCalibTask1的顶层控制流。已读完整方法；硬件、视觉子调用不因此视为递归审计完成。本专题属于按钮触发的标定流程，不是每片产品必经的生产流程。

交互入口：[标定流程图](bond-camera-calibration-workflow.html) · [源码关系回执](bond-camera-calibration-diagram-status.json)。

## 工作流摘要

用户确认工具准备 → 后台任务 → 识别并取小标定片 → 放至BMC并对焦 → 双Mark定位 → 旋转中心修正（最多三轮）→ 创建、初始化并保存坐标系 → 两角度偏移检查（当前代码只执行一轮）→ 最后取标 → 返回bool → 外层生成结果窗口。任意被内层catch捕获的异常返回false；外层未以此阻止结果展示。保存发生在偏移检查和最终取标之前，不是结果窗口确认后的事务提交。

## 执行清单与源码

| 顺序 | 实际动作及条件 | 证据 |
| --- | --- | --- |
| 1 | BtnBondToCamera_Click提示准备工具，仅OK时Task.Run；外层清理结果列表 | [启动按钮:98–110](../../trunk/AKRS.ZX2200/CalibSystem/Controls/FrmStartup.cs#L98)、[外层:1817–1832](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1817) |
| 2 | T轴到0；移到小片视觉位置，用“小标定片模板”识别；移动到相机中心、指定像素，回读位置 | [1834–1853](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1834) |
| 3 | 根据现有偏移计算取标位置，设置取放参数、执行取片，计算BMC放片位置并放片 | [1855–1935](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1855) |
| 4 | 等待500ms，设置中心位置，移至左上Mark并对焦；回读Z，定位左右对角Mark，取均值更新中心和放片位置 | [1937–1982](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1937) |
| 5 | 每轮两次迭代，每次依次0°、−180°取放并识别双Mark；用两角度中心差的一半修正BondRotateCenterToCamOffset | [1984–2069](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1984) |
| 6 | count初值0，任何修正X或Y绝对值>0.003则count++并重做；count==2时直接离开重试段，不再检查本轮阈值 | [2071–2102](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L2071) |
| 7 | 用固定upPoint及当前BMC/偏移位置初始化BondCoordinateSystem；保存，再Refresh | [2106–2119](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L2106) |
| 8 | step=0进入偏移检查；0°时识别BMC并计算角度差；两个角度均取放标，识别玻璃/BMC双Mark并转机器坐标，记录中心差 | [2121–2228](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L2121) |
| 9 | 四个有符号偏移均<=0.004则break；即使不满足，step==0仍break，所以正常执行仅一轮，step++不可达 | [2230–2250](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L2230) |
| 10 | 移到最后取标位置，PickAction后return true；catch日志、消息后return false，没有finally回滚 | [2252–2270](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L2252) |
| 11 | 外层忽略bool，按当前偏移生成结果项并ShowDialog；确定和取消均Close并触发可选事件 | [1817–1832](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1817)、[结果按钮:51–66](../../trunk/AKRS.ZX2200/CalibSystem/Controls/FrmCalibResult.cs#L51) |

## 不能按注释推断的行为

- 旋转修正最多三轮，每轮四次角度取放，合计最多十二次；达到上限不代表阈值达标。此计数排除进入修正段前、后续偏移检查和最终取标，也以子调用正常返回为前提。
- 偏移检查比较的是有符号值，不是绝对误差；较大的负偏移也可能满足<=0.004。后续step>2里的修正代码已注释，且step==0直接退出，不能描绘为持续迭代校正。
- 多处BondAction返回值赋给ret但在本方法没有检查；进一步核对当前BondAction完整实现后，确认其正常返回true、失败抛异常，没有return false出口。不能将未检查bool本身描绘成已证实的放片false路径；详见[子调用失败契约](calibration-dependency-contract-review.md)。
- 对焦范围与局部异常边界见[对焦入口审计](autofocus-entry-review.md)。

## 保存与结果确认并非同一阶段

[CalibrateTask:105–110](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L105)定义同名MachineCoordinateSystem实例属性。因此任务中的Save调用应结合该属性解释；坐标类的[Save:86–89](../../trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/MachineCoordinateSystem.cs#L86)是实例方法，调用JsonFormatHelper.SaveGenericObject(instance,FilePath)。

[CreateCoordinateSystem:104–134](../../trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/MachineCoordinateSystem.cs#L104)正常情况下先删除同名坐标、创建新对象、加入集合并保存；调用方随后Init再保存，所以存在初始化前的中间保存。若上层G0不存在，则仅创建并保存G0后返回，不继续创建请求的BondCoordinateSystem；若后续Find也找不到BondCoordinateSystem，调用方Init会因空引用进入异常路径。上层不是G0且不存在则直接抛异常。

[文件路径:21–30](../../trunk/AKRS.Galaxy2.CoordinateSystems/StaticPara.cs#L21)默认是Application.StartupPath/Settings/DeviceParams/MachineCoordinateSystem/MachineCoordinateSystem.json；目录属性可修改，不能把默认值当成现场绝对路径。[Refresh:64–67](../../trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/MachineCoordinateSystem.cs#L64)仅把单例置null，下次[GetInstance/Load:33–59](../../trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/MachineCoordinateSystem.cs#L33)才从文件重载。

[项目引用:45–46](../../trunk/AKRS.Galaxy2.CoordinateSystems/AKRS.Galaxy2.CoordinateSystems.csproj#L45)指向随附Infrastructure DLL。JsonFormatHelper原始C#源码未找到，但[坐标保存证据衔接](calibration-coordinate-persistence-review.md)已核对项目HintPath与仓库随附Infrastructure DLL：对象helper采用临时文件及Replace/Move，具有特定catch范围，序列化错误回调可设置Handled。不能再把其实现整体列为未知；现场版本、磁盘原子性、并发写入和保存成功仍未验证。

结果窗体[初始化和绑定:19–43](../../trunk/AKRS.ZX2200/CalibSystem/Controls/FrmCalibResult.cs#L19)直接显示CalibCamScales、CalibTransResults；[确定/取消:51–66](../../trunk/AKRS.ZX2200/CalibSystem/Controls/FrmCalibResult.cs#L51)均关闭并触发CloseParentForm，没有本地保存、撤销或按成功标志筛选。按钮均有[Designer绑定:157–166](../../trunk/AKRS.ZX2200/CalibSystem/Controls/FrmCalibResult.Designer.cs#L157)。当前外层创建窗体处没有订阅CloseParentForm，不把其他调用者可能注册的事件行为归到本入口。

完整读取的StartBondToCamCalibTask1没有直接调用calibratePara.Save；运行参数字段变化与坐标系JSON保存是不同输出，不能说这条入口已持久化全部标定参数。此前保存不因后续偏移检查或最后取标异常而自动撤销。

## 尚待验证

验证资料：[完整方法与依赖源码快照](bond-camera-calibration-evidence.json)、[原方法隔离检查](../../scripts/test-calibration-result-flow.cjs)。三项检查已通过：内层返回true展示结果；返回false同样展示结果；内层向外抛异常则不创建结果窗口。外层方法原样提取，内层动作、结果对象与窗口为替身；这些检查不验证WinForms线程、标定算法精度或硬件动作。旋转重试上限、偏移检查单轮和保存先后顺序为静态源码结论，不冒充整机运行回执。

设备运行、真实配置与单位、视觉评分和各运动子调用的失败契约仍未验收。本文描述源码，不自动修复生产行为；本专题不增加模块完整验收数量。
