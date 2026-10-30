# 相机与机械坐标标定：源码复核

覆盖清单 06.01–06.07。主程序、坐标工程、自动对焦工程保持只读。此文固定已读实现供 Archify 引用；原件指纹和逐行范围另存 source-evidence.json。图文解释当前行为，没有在设备上执行采点、取放标定片或更新现场参数。

## 入口与整机调度

主界面 BtnStart_ItemClick 先调用 AllAxisGoHome，未检查其 bool，再按 CurrentMachineSystem 排队 Task：S1 调 StartDispenseCalibTask，其他工位调 StartAutoCalib。事件没有等待 Task，也不接收点胶子任务 bool；发起任务与标定完成分开。

StartAutoCalib 清空结果列表，清洁确认后抬 Z、关真空，确认 Touchdown 后执行 Bond 相机标定。更换 BMC 吸嘴确认后，依次执行焊头到相机偏移、上视相机标定。随后可选同标记对齐：OK 执行，Cancel 仅跳过此步；之后仍做上视机械拍照位、确认工具、晶圆两标记间距、晶圆 N 点。所检查的必做子任务 false 或工具确认取消会 return；点胶标定不在这条 S2 主链中。全链到达末尾才 CalibrateRunPara.Save 并派发结果窗体。

依据：UcMainSystem.cs 1338–1358；CalibrateTask.cs 2275–2400。

## 点胶与 Bond 相机

点胶子任务收回测高气缸，按 3×3 点移动，用固定名称“点胶标定模板”采点，任一 DoWork 非 Success 直接 false。物理点为相对标定中心的 XY 差；创建 DispenseCameraCoordinateSystem（父 DispenseCoordinateSystem），Init、Save、Refresh 先执行，再求 Halcon 矩阵和测高。测高失败返回时，前面的坐标文件可能已更新；成功才记录实位/高度、回安全位、保存标定参数并收回气缸。

Bond 子任务先 BMC 测高并立即保存 BondDevicePara；记录相机到测高 Z 差。对中并调用像素校验，未检查后者 bool。再生成 6×5、X/Y 间距 0.1/0.05 的 30 点，采集 BmcPRName 结果；创建 BondCameraCoordinateSystem（父 BondCoordinateSystem），Init、Save、Refresh 后才求 Halcon 矩阵、回中心再校验、写结果列表并 true。不要沿旧“9点”注释推算实际点数。

GeneratePointList 按给定行列居中铺点、行外列内遍历；双间距重载分别使用 X/Y。NPointTrans 把两组 XY 传 VectorToHomMat2d，比例与旋转等来自后续 HomMat2dToAffinePar。VM 从属标定文件与 Halcon 矩阵是两条写入，不是一份结果的两个名称。

依据：CalibrateTask.cs 170–283、291–423；CalibService.cs 87–144、202–224。

## 上视、机械位置与晶圆

StartUpLookCalibTask 对中后按 6×5 采点，创建父为 BondCoordinateSystem 的上视从属坐标，明确 CameraStaticDown，Save/Refresh 后求 Halcon 矩阵。再按 −180、−90、0、90、180 五角度采像素点、拟圆并对中，更新 GlassUpLookVisionMachinePos。末段 bondOffset 的 XY 修正语句被注释；参数 Save 在放回标定片之前。放回 BondAction 的 bool 未检查，仍可写结果并 true。

StartUpLookMachinePosTask 使用 WaferLeftPRName、Bond 相机坐标对中后更新 UpLookMarkMachinePos，并加入结果列表；没有在该方法单独 Save。不要把上视物理相机的位置与上视像素坐标标定混为同一步。

StartWaferTableCalibTask 使用 Bond 相机分别对中晶圆台左右标记，写左右实位与“右−左”间距。StartWaferNPointCalibTask 则移动晶圆台与相机 Z，生成 5×5 点；创建父 WaferTableCoordinateSystem、CameraStaticUp 的晶圆相机从属坐标并 Save/Refresh。求 Halcon 矩阵、回中心、重识别右标记，计算右标记实位−两标记间距+焊头相机偏移，Save 标定参数后重建晶圆台普通坐标到 G0，再 Save/Refresh。末段回安全位并写结果列表。

依据：CalibrateTask.cs 486–686、694–717、725–786、794–1004；CalibService.cs 154–193。

## 焊头偏移与最后复核

StartBondToCamCalibTask1 先转 T=0，以“小标定片模板”初定位，再用 GlassPRName 校验；按现有偏移取片、放到 BMC、对焦并读取对角标记。取放使用 Distance 模式；部分 PickAction/BondAction 返回值没有门控后续采点，不把它们标成统一成功检查。

旋转修正每次进行两轮 0/−180 取放与双点定位，以两个中心之差的一半修正 BondRotateCenterToCamOffset。任一分量绝对值大于 0.003 则增加 count、清列表并重试；count==2 时本轮计算后直接进入后段，不再按该阈值拒绝。随后以固定 G0 参照点 (200,−300,100) 及 BMC/偏移构造 BondCoordinateSystem，Save/Refresh 在最终复核之前。

最终复核再用两角度的玻璃/BMC 中心差；源码判断四个带符号分量 <=0.004，没有 Abs。step 初值 0，容差未满足也在 step==0 时 break，未形成注释所暗示的持续修正。之后再次取片并 true。因此 true 不证明所有绝对偏差小于阈值；之前的参数、坐标与物理动作也没有统一回滚。

可选 StartBondToCamBySameMarkTask 以 Bond/上视识别值和固定像素中心求对齐位置，再写 XY 偏移及 BondCamUpLookCamMachinePos；此方法不独立 Save。

依据：CalibrateTask.cs 1834–2268、431–477。

## 公共对中、目标像素与对焦

MoveToCamCenter 为 Bond、UpLook、Dispense、Wafer 选择轴和坐标名，调用相机从属坐标的一层 ForwardConvertCoordinate，并加当前轴命令位置，直接 AbsoluteMove；此服务本地没有另一个显式 Wait 到位调用。GetMachinePosByPixelPos 则接收调用方传入的当前位置作同类相加；它不是设备完整父链 G0 转换。

LocateAndMoveToTargetPixel 固定目标 (1224,1024)，每轮定位并移动，再重新定位算 X/Y 各分量偏差，均严格小于 pixelTolerance 才 true；最多 maxRetry 轮。失败定位或超限继续，最终提示并 false；下层 LocatePosition 的异常不在这里捕获。CalibrateTask 多处直接调用而未检查 bool。MoveWaferAndEjectorZ 当前空实现返回 true，不能画成执行过两个 Z 动作。

CalibController.AutoFocus 只有 Bond、UpLook 分支有调用，而且两者实际都传 BondCamera 与 BondHead.AxisZ，参数为 endPos、startPos；Dispense/Wafer 分支为空。引用 AutoFocusing.AutoFocus 先粗扫清晰度并返回最大评分位置，再以脉冲变向/减半做六轮式细调；本地没有统一循环超时、范围有效性检查或显式等待到位。成像、清晰度工具和驱动仍属运行边界，不按注释推定已对上视物理相机单独调焦。

依据：CalibController.cs 133–293、318–335；CalibService.cs 33–76；AutoFocusing.cs 215–311、371–392。

## 独立方法与文件边界

OnlyDispenseCameraCalib、OnlyBondCameraCalib、OnlyWaferCameraCaib 与整机子任务不等价：点胶主要生成报告；Bond 使用 0.4/0.3 间距并写内存矩阵，晶圆主要显示结果，它们没有对应整机子任务中的完整 VM 坐标建立和保存链。当前主菜单直接引用的是 S1/S2 主入口，不把未定位到直接调用的 Only 方法放进必经主链。

OnlyUpLookCameraCalib 另有取放片、各点 Retry/Abort/Ignore 分支；视觉 Ignore 可创建默认匹配值继续，放片失败后的 Ignore 仍走该分支末尾 return。它以当前中心采 6×5 点、做像素及物理拟圆、减去 XY bondOffset 并 Save；不同于整机上视子任务中被注释的 XY 修正。最后调用上视机械位方法而未接收 bool。OnlyBondToCameraOffsetCaib 也不接收偏移任务 bool，仍显示结果。

CalibrateRunPara 继承外部 Singleton，FilePath 为设备目录 CalibratePara.json；本仓库只证明 Save 调用与先后，不声称外部序列化和落盘持久性已实测。坐标 JSON 与 .iwcal 的实现统一见 G0。FrmCalibResult 只绑定两个结果列表；OK 与 Cancel 都关闭窗口并通知父窗体，没有在此回滚、应用或保存标定参数。

依据：CalibrateTask.cs 1073–1251、1257–1706、1712–1830；CalibrateRunPara.cs 15–23；ZX2200PathConfig.cs 235；FrmCalibResult.cs 19–65。
