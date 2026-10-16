# 上视、同标记、晶圆标定与居中闭环

更新：2026-09-28。接续[标定主调度](calibration-module-review.md)和[点胶/邦定相机](camera-calibration-source-review.md)。以下为源码静态分析，设备、SDK契约、真实配方和标定精度未运行验收。

## 执行步骤摘要

- 上视：玻璃模板定位/居中 → 6×5采样 → 保存CameraStaticDown类型的VM相机坐标 → Halcon矩阵 → 五角度旋转采样并拟合圆心 → 居中、记录旋转中心 → 保存参数 → 放回标定片 → 追加结果。
- 同标记：移动到双相机位置 → 分别定位两模板 → 邦定相机居中 → 用上视结果和固定像素中心换算 → 覆写邦头到相机XY偏移及双相机位置 → 返回；本方法没有Save。
- 晶圆间距：晶圆台准备位 → 邦定相机定位并居中左/右标记 → 读取实际XY → 保存内存中的右减左差值 → 追加结果。
- 晶圆多点：邦头移开 → 晶圆台与相机Z就位 → 5×5采样 → 保存CameraStaticUp类型的VM相机坐标 → Halcon矩阵 → 晶圆相机左标记居中 → 邦定相机右标记居中 → 计算坐标基准并保存参数 → 创建晶圆台G0坐标/保存 → 移开邦头、Z安全、相机Z归0 → 追加结果。

## 上视与同标记：数据和副作用

- [StartUpLookCalibTask sampling 486–560](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L486)：UpLookPRName、UpLookCalibDistance与当前玻璃位置生成30个计划点，逐点MoveSafeBondXYZ、Sleep1000、LocatePosition。注释“12点/9点”不能代表实际数量；采样物理坐标为计划点减中心。
- UpLookCameraCoordinateSystem依赖BondCoordinateSystem，Init(realPoints,imgPoints,CameraStaticDown)后Save/Refresh，随后计算UpLookHomMatTrans。两种变换输出分别保存，不能假定一致。
- [StartUpLookCalibTask rotation center 562–608](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L562)：T角顺序为-180、-90、0、90、180；五次定位形成像素点集，[FitCircle 154–194](../../trunk/AKRS.ZX2200/CalibSystem/Services/CalibService.cs#L154)用Halcon algebraic圆拟合，X取Col、Y取Row。未以半径或拟合残差做本地验收；±180是否重复物理方向取决于轴/工装，不替代码去重。
- 拟合圆心居中后更新GlassUpLookVisionMachinePos.X/Y；再定位居中并计算bondOffset，但修改BondRotateCenterToCamOffset的两行被注释，不能画为“自动用bondOffset修正偏移”。
- [StartUpLookCalibTask placement and result 610–687](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L610)：参数Save在放片之前；BondAction返回值未消费，若仅返回false而未抛异常，仍会追加结果并返回true。异常catch记日志/弹窗/false，无本地统一恢复或回滚。
- [StartBondToCamBySameMarkTask 431–478](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L431)：模板固定为BondCamUpLookCamAlign-Bond和BondCamUpLookCamAlign；上视结果在邦定居中运动之前取得，运动之后仍复用该结果。以(1224,1024)构造中心点换算，计算curBondCamCenterPos+curMarkUpLookPos-upLookCameraCenterPos；偏移为GlassUpLookVisionMachinePos减该位置并覆写XY。数据时序和坐标物理解释需实测核查。
- [StartUpLookMachinePosTask 694–718](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L694)：名称“上视相机位置”不表示用上视相机拍照；实际使用WaferLeftPRName及CamCoordinateType.Bond居中，更新UpLookMarkMachinePos后仅追加结果。

## 晶圆：间距与多点不是同一步

- [StartWaferTableCalibTask 725–787](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L725)：左标记取WaferTableLeftMarkBCVisionMachinePos，右标记取WaferTableRightMarkVisionMachinePos；通过邦定相机居中后读取轴实际XY。WaferTableMarksDistance是(rightX-leftX,rightY-leftY)向量，不是欧氏长度。此方法无Save。
- [StartWaferNPointCalibTask sampling 794–904](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L794)：明确5×5=25点，使用WaferPRName；imgPoints.Z填相机标定Z，realPoints.Z为0，XY仍为计划点相对位移。WaferCameraCoordinateSystem在此先依赖WaferTableCoordinateSystem并保存；后者后续才重新创建，故首次初始化是否已有父坐标需按配置核实。
- [StartWaferNPointCalibTask frame and completion 907–1005](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L907)：左标记居中后更新WCVision位置；后段测高代码整体被注释，不能列为实际执行步骤。再以WaferTableRightMarkBCVisionMachinePos定位右标记，注意它与间距步骤的RightMarkVisionMachinePos是不同属性。
- BondHeadRotateCenterInWC = 右标记BC位置 - 左右标记间距 + 邦头到相机偏移。先calibratePara.Save，再将此点经BondCoordinateSystem.ForwardConvertCoordinate转换，建立WaferTableCoordinateSystem相对G0的General坐标并Save/Refresh。
- 末尾移开邦头、邦头Z安全及MoveWaferCameraZ(0)只在正常路径执行；catch仅日志/弹窗/false。失败可能发生在任意阶段保存之后，并无整体事务。

## 公共居中：有限尝试不等同收敛通过

- [LocateAndMoveToTargetPixel and helpers 161–249](../../trunk/AKRS.ZX2200/CalibSystem/Services/CalibController.cs#L161)：目标固定(1224,1024)。每轮先定位并移动，再重新定位计算X/Y偏差；两分量绝对值都严格小于pixelTolerance才true。所读任务调用参数均为1像素、maxRetry=2；最多两轮尝试，不是首次加两次重试，也不是欧氏误差。
- 超限弹出信息框然后返回false；这些上视/晶圆任务调用均未判断此bool，随后仍更新位置、计算和保存。提示框本身不是失败退出。若每次初次定位都返回null/IsSuccess=false，finalDelta保留初值0，末尾弹窗可显示0偏差但结果为false。
- [LocatePosition 318–336](../../trunk/AKRS.ZX2200/CalibSystem/Services/CalibController.cs#L318)：DoWork非Success直接throw；居中循环没有catch，因此这类异常不会被maxRetry包住，而是向标定子任务catch传播。null/IsSuccess=false与异常是不同路径。
- [GetMachinePosByPixelPos / MoveToCamCenterCoo 33–77](../../trunk/AKRS.ZX2200/CalibSystem/Services/CalibService.cs#L33)：像素结果经指定DependentCoordinateSystem.ForwardConvertCoordinate；坐标返回值加curAxisPoint。实际居中运动使用GetCmdPosition加变换偏移，依次AbsoluteMove X、Y，没有在该包装中显式等待或同步插补。底层Axis契约尚未确认。

## 交接未完成项

- 固定像素中心与真实相机分辨率、模板绑定硬件、世界坐标单位/符号、不同右标记属性的示教来源。
- 为什么忽略居中bool、上视放片bool、是否需要工艺阈值；本文记录行为，不自动更改生产逻辑。
- 居中/测高/轴等待、急停和取消的全栈传播，首次坐标建立条件、SDK与文件保存恢复、并发入口。
- 公共主流程与本轮子步骤已经有源码依据，仍需同步Archify专题图并验证可交互溯源；不能以文档新增数当作全项目完成。
