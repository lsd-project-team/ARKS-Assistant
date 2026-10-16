# 独立相机标定：入口、执行步骤与自动主链差异

复核日期：2026-09-28。范围仅为 `trunk` 中 `FrmStartup` 的 Only 相机入口及 `CalibrateTask` 四个实现；这是静态源码复核，不是设备运行或精度验收。生产源码未修改。

## 简明流程结论

四个按钮分别通过 `Task.Run` 启动独立方法，并非依次调用的自动生产步骤。点胶、邦定、晶圆主要执行网格采样；独立上视还包含取标定片、BMC 双标定位、放片、放后双标复测、重新取片、上视采样和旋转拟合。它们不能统一解释为自动标定主链的快捷包装。入口证据：`calib-standalone-ui`，`trunk/AKRS.ZX2200/CalibSystem/Controls/FrmStartup.cs:33–108`。

下文方法均位于 `trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs`。源码行号和证据 ID 配套登记在 `module-review-evidence.json`；既有自动主链见 `camera-calibration-source-review.md`、`uplook-wafer-calibration-source-review.md`。

## 四个入口的输出与差异

| 入口 | 实际步骤 | 本方法结果与保存边界 | 源码 |
|---|---|---|---|
| OnlyDispenseCameraCalib | 关闭测高气缸→移到配置拍照位→3×3 网格→每点移动、等待、固定“点胶标定模板”PR→Halcon 变换→结果窗口 | PR 非 Success 直接 return；没有把新矩阵赋给 DispenseHomMatTrans，没有 VM 坐标初始化/导出，没有测高和显式参数 Save；方法结尾也没有回网格中心 | 1073–1157；`only-dispense` |
| OnlyBondCameraCalib | 移到 BMC 拍照位→PR 居中→以内存实际位置更新中心→6×5 网格→逐点 XY/Z/PR→Halcon→回中心→窗口 | 网格间隔参数 .4/.3；自动 StartBond 的对应参数为 .1/.05。新矩阵赋给 BondHomMatTrans，但本方法无显式参数 Save、VM 初始化及 BMC 测高 | 1162–1252；`only-bond`；自动侧 `calib-bond-samples` |
| OnlyUpLookCameraCalib | 取片→BMC 双标定位→放片→放后双标复测→重新取片→6×5 上视网格→五角度旋转拟合→更新位置/偏移→Save→放回→调用位置子任务→窗口 | Halcon 结果用于展示，没有在本方法将新矩阵写入 UpLookHomMatTrans，也没有 VM 初始化；偏移 X/Y 实际执行减法。Save 在放回及位置子任务之前，不是全流程成功后的统一提交 | 1257–1707；`only-up-prepare` 至 `only-up-finish` |
| OnlyWaferCameraCaib | 邦头移开→晶圆左 Mark 到相机位→相机 Z→5×5 网格→逐点 PR→Halcon→晶圆台回起点→窗口 | 使用 WaferPRName；没有将新矩阵赋给晶圆转换参数，没有 VM 初始化、左右标记间距/G0 建立或显式 Save | 1712–1812；`only-wafer` |

“没有保存”均限定于被复核方法的显式调用，不能推导为整个程序永不保存。控制器、PR 和外部库仍可能具有其他副作用。

## 独立上视的完整主顺序

1. 清空展示列表，移到 GlassVisionMachinePos，GlassPRName 定位，使用 BondCameraCoordinateSystem 居中；再调用 LocateAndMoveToTargetPixel，但不检查其 bool。等待 5 秒、T 轴转 -180°，实际坐标加 BondRotateCenterToCamOffset，Z 设 0 后移动。1257–1285，`only-up-prepare`。
2. 用 BMC 参数组装取放片配置，距离模式、检测开关、WeakBlowProportion=1500；以 GlassPickZMachinePos 取片，随后抬至安全 Z。1289–1336，`only-up-prepare`。此处 PickAction 返回值未接收，不代表已确认取片成功。
3. 将 BMC 左上/右下标记机械位转 G0，以 BMC 拍照高度调用两次 BondCameraVision，再经 GetBondVisionResultPos 获取两个位置。中点加 HeadToCameraOffset 得到放片 XY。1338–1425，`only-up-bmc`。
4. 移到 G0 放片 XY；放片高度为 BMC MeasureHeightResult+1.7，抬起高度来自 GlassCenterCurVisionMachinePos.Z；执行 BondAction(BondOnBMC)。注意注释写标定片厚度 2，而实际表达式为 +1.7，本记录遵循代码表达式。1429–1469，`only-up-place`。
5. 用 GlassPRName 在左右两个位置再次拍照，各自 GetBondVisionResultPos；中点加 HeadToCameraOffset，移到中心，再调用 PickAction(BMC)；返回值未接收。1473–1557，`only-up-postbond`。
6. 移到配置上视位，以 UpLookPRName 定位、居中，用实际位置建立 6×5 网格。每点移动、等待 1 秒、LocatePosition，收集像素点；Halcon 的物理点为相对 curUpLookCenter 的计划网格位置。1559–1617，`only-up-grid`。没有用实测每点轴反馈替代计划点。
7. 回到上视位置，依次转 -180/-90/0/90/180°并定位；拟合像素圆心、移到该中心、记录 GlassUpLookVisionMachinePos；另一次机械点拟合的输出没有用于后续位置赋值。再次定位居中，计算位置差，从 BondRotateCenterToCamOffset 的 X/Y 减去差值，然后 Save。1619–1665，`only-up-rotate`。自动 StartUpLook 对应减偏移代码是注释，不能混同。
8. 抬安全 Z、移到玻璃位置加偏移、T 轴归 0，以 GlassPickZMachinePos+5 放回，BondAction(BondOnTU) 返回值未接收。生成展示结果，随后调用 StartUpLookMachinePosTask，bool 也未检查，最后打开结果窗口。1667–1707，`only-up-finish`。

## 分支、重试与“完成”的含义

- BMC P1/P2 和放后 Glass P1/P2：BondCameraVision 返回 null 时弹 Retry/Abort/Ignore。Retry 通过 goto 重拍当前点，没有本地次数上限；Abort 抛异常；Ignore 构造新 MatchResult 后继续计算，不可称为定位成功。1350–1417、1473–1550，`only-up-bmc`、`only-up-postbond`。
- BMC 放片 bool=false：对话框实际只提供 Retry/Ignore。Retry 跳回 ReBond；Ignore 分支后仍执行 return，结束方法，**不会继续采样**。代码虽有 Abort case，但该对话框没有提供 Abort 按钮。1439–1469，`only-up-place`。
- 点胶/邦定网格 PR 非 Success：直接返回，不显示方法末尾结果窗口；上视/晶圆通过 LocatePosition 获取结果，该辅助方法对 PR 非 Success 抛异常。`only-dispense`、`only-bond`、`only-up-grid`、`only-wafer`、既有 `calib-locate`。
- 这些 Only 方法没有包围全流程的 catch/finally、取消令牌或统一回滚。入口 Task.Run 未在该按钮处理器捕获/await；这只是局部观察，不推导全程序没有异常处理或设备联锁。
- 上视位置展示项在调用 StartUpLookMachinePosTask **之前**从 UpLookMarkMachinePos 生成；保存也早于该子任务。子任务 false 仍可走到结果窗口。因此窗口出现不等于所有子步骤成功，也不证明最终位置已落盘。1695–1705，`only-up-finish`、既有 `calib-uplook-position`。

## 输入、输出及剩余缺口

输入：标定机械位置、PR 名称、采样距离、BMC 取放片参数、安全 Z、已有相机坐标系、机械/像素转换和偏移。输出：展示列表、邦定矩阵内存赋值、上视位置/偏移及提前 Save，以及设备运动/取放动作。此链没有直接展示网络服务或队列调用，不能由此排除下层驱动通信。

- 已复核：四个 Only 相机入口的局部流程、相对自动版本的差异、人工重试/忽略和显式写入顺序。
- 待复核：Ex 窗口、全局 Scale/Test/Record 其余算法，取放片下层完整故障恢复及各相机坐标系实际加载状态。
- 待运行验收：模板/硬件可用性、重复点击并发、保存文件实际内容、Ignored/false/异常下的安全终态和精度。
- 本文不把“方法已读”升级为整个 CalibSystem 或 ZX2200 完成，也不新增自动主链步骤。

## 可点击源码入口

- [calib-standalone-ui：standalone calibration events（28–110）](../../trunk/AKRS.ZX2200/CalibSystem/Controls/FrmStartup.cs#L28)
- [only-dispense：OnlyDispenseCameraCalib（1073–1157）](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1073)
- [only-bond：OnlyBondCameraCalib（1162–1252）](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1162)
- [only-up-prepare：OnlyUpLookCameraCalib preparation（1257–1336）](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1257)
- [only-up-bmc：OnlyUpLookCameraCalib BMC marks（1338–1425）](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1338)
- [only-up-place：OnlyUpLookCameraCalib placement retry（1429–1469）](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1429)
- [only-up-postbond：OnlyUpLookCameraCalib postbond（1473–1557）](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1473)
- [only-up-grid：OnlyUpLookCameraCalib grid（1559–1617）](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1559)
- [only-up-rotate：OnlyUpLookCameraCalib rotation（1619–1665）](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1619)
- [only-up-finish：OnlyUpLookCameraCalib finish（1667–1707）](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1667)
- [only-wafer：OnlyWaferCameraCaib（1712–1812）](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1712)
