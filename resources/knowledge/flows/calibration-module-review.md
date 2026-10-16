# 标定系统：主调度、偏移标定与对焦边界

更新：2026-09-28。部分静态复核；不宣称所有标定算法或设备运行已验收。此文先给实际顺序，再列源码依据；不修改生产代码。

## 工作步骤摘要

主界面自动标定按钮 → 调用AllAxisGoHome → 按当前系统分流。System1启动点胶标定；其他系统进入StartAutoCalib：清空结果列表 → 人工清洁确认 → 安全Z/关真空 → 安装Touchdown确认 → 邦定标定 → 安全Z/关真空 → 更换BMC工具确认 → 邦头到相机偏移标定 → 上视标定 → 移到双相机位置并可选同标记标定 → 上视机械位置标定 → 安全Z及工具确认 → 晶圆台标定 → 晶圆多点标定 → 参数Save → UI结果窗口。

这是包含人工确认的串行流程，不是无人值守定时任务。子任务false即返回；同标记确认Cancel只跳过该子任务，其余所述确认Cancel会退出。System1并不执行这套System2串行任务。

## 启动、调用和完成状态

- [BtnStart_ItemClick：1338–1359](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L1338)：先调用AllAxisGoHome，再Task.Run；不检查回零返回值，Task没有在本事件中await、保存或设置异常延续。该事件内未见防重复点击或并发互斥，UI外层状态策略尚待核查。
- [AllAxisGoHome：504–584](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L504)：人工取消、OneKeyHome失败和catch均可返回false；成功才OpenCompensate并设置AllAxisReset=true。因此这个标定启动事件不能证明“回零成功后才启动”。
- [StartAutoCalib：2275–2403](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L2275)：子任务按摘要顺序同步调用，false立即return；最后才calibratePara.Save和MainForm.SendUiAction展示结果。外层无统一catch/finally/回滚，不能把中途退出称作全流程完成。各子标定算法还需逐一展开，本轮只确认其调度位置与返回值分支。
- [standalone calibration events：28–110](../../trunk/AKRS.ZX2200/CalibSystem/Controls/FrmStartup.cs#L28)：另有单独相机与偏移标定按钮，通过Task.Run执行；上视和偏移入口有工具确认。它们不能替代StartAutoCalib的全部前置步骤。
- [OnlyBondToCameraOffsetCaib / StartBondToCamCalibTask1：1817–1853](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1817)：单项OnlyBondToCameraOffsetCaib清空列表后调用bool子任务却忽略返回值，仍按当前参数生成结果、ShowDialog。因此“出现结果窗”不能证明该次偏移标定成功。

## 偏移标定中的对焦参数问题

- [offset pickup placement and focus：1855–1959](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1855)：取放标定片后，移动到玻璃标记左上位置，以startPos=基准Z+2、endPos=基准Z-3调用CalibController.AutoFocus。
- [AutoFocus：273–293](../../trunk/AKRS.ZX2200/CalibSystem/Services/CalibController.cs#L273)：Bond分支按(endPos,startPos)转交AutoFocusing.AutoFocus，其形参顺序是(pLimit,nLimit)，参见[AutoFocus coarse scan：215–257](../../trunk/AKRS.Galaxy2.AutoFocusing/Model/AutoFocusing.cs#L215)。因此实际pLimit=基准Z-3、nLimit=基准Z+2，distance=-1、pulse=-0.2；不能画成正常正向范围扫描。
- 若轴按命令同步到位并反馈一致，首个粗扫移动后下一步比较已经满足退出条件，粗扫可能只记录一个点；这是条件性源码推演，未实测运动行为。运动同步与限位属于外部Axis契约。
- 同一分发器的UpLook分支也传BondCamera；Dispense和Wafer分支为空。该分发器与BondHeadController中区分相机的另一套入口不同，不能混为同一实现。

## 偏移子任务的执行与判定

- [OnlyBondToCameraOffsetCaib / StartBondToCamCalibTask1：1817–1853](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1817)、[offset pickup placement and focus：1855–1959](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1855)：旋转至0、移动到玻璃拍照位置、定位/移向相机中心、更新位置，再根据偏移计算取放位置和参数，执行取放、对焦与标记定位。BondAction结果写入ret，本方法后续未见对ret的条件检查；不是所有失败都经该bool拦截。
- [LocatePosition：1013–1031](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1013)：按模板名取PREntity、Sleep2000、DoWork；非Success抛异常，成功强转AlgResult。没有本地重试或缺失实体检查，异常交给外层处理。
- [rotation repeat and coordinate save：1984–2119](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1984)：每次两轮、每轮0/-180两个角度取放并定位；由两中心差的一半调整BondRotateCenterToCamOffset。任一分量绝对值>0.003时count++并重来，count==2时直接进入下一阶段，不再次要求阈值达标。最多三批执行，不是“直到合格才继续”。
- 随后CreateCoordinateSystem、Init、Save、Refresh在子任务中间执行。后续失败并不能撤回已保存坐标；外层最终参数Save不是事务式提交。
- [offset check and return：2121–2269](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L2121)：后段使用分量<=0.004比较，没有取绝对值；即使条件不满足，step初值0也会触发break，step++无法由该路径到达。应理解为一轮检查而非可收敛的循环校正；大负偏差亦可能满足单边比较。
- 最后移动并取片，返回true；catch记录日志、弹窗并返回false，无统一回退动作。算法正常返回也不能证明误差达到规范阈值。

## 输入、输出、依赖与交接缺口

- 输入：当前系统选择、人工确认、CalibrateRunPara/BMCDevicePara、玻璃/BMC模板、轴反馈、相机定位。输出：内存参数、坐标系保存、副作用运动及结果列表/UI。所读路径无独立消息队列或远程API；通过控制器间接调用设备与视觉SDK。
- 待展开：点胶、邦定、上视、同标记、晶圆台和多点标定的完整数值算法、坐标系/参数持久化实现，以及按钮状态和停止/急停传播。
- 待验证：反向对焦参数意图、工具/安全联锁、未消费bool、单次校正和单边阈值是否符合工艺要求。本文是交接风险清单，不是授权自动改动设备逻辑。
- 专题图与现有主图整合尚待完成；编译、SDK行为与实机验收未执行。

## 相机子算法补充

已进一步复核[点胶与邦定相机的采样、拟合和保存](camera-calibration-source-review.md)。其余标定子算法继续保持待复核。

## 上视与晶圆子链补充

见[上视、同标记、晶圆和公共居中](uplook-wafer-calibration-source-review.md)，含顺序、结果保存、有限重试及上层忽略返回值的边界。
