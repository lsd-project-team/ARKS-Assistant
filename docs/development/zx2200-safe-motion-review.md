# 安全运动与连续轨迹：源码复核

覆盖清单 10.01–10.06。沿 ZX2200 控制器、动作辅助方法、模块与本地固高工具读取，不执行设备动作。原件及引用库保持原样。此文供 Archify 固定已提交事实，原文件指纹及逐行范围另由 source-evidence.json 校验。

## 目标、软限位与普通安全分支

MoveToG0Pos(三维点) 先用 BondCoordinateSystem.BackConvertCoordinate 的一层逆变换求机械目标，再调用 MoveSafeBondXYZ；完整父链变换在 G0 专题说明。CameraMoveToG0Pos 先减 HeadToCameraOffset。双标量 MoveToG0Pos 则分别用 (X,0,X) 和 (0,Y,0) 取转换分量，不把它简化成同一个三维点重载。四维转换保留输入 T。

MoveSafeBondXYZ 读取当前机械 Z，先求安全高度，再 CheckSoftLimit，再 WaitSingleStep；单步拒绝直接 void return。当前 Z>=安全 Z 时，无论目标在安全高度哪侧，都先 XY 后目标 Z；当前低而目标不低时，先目标 Z 后 XY；两者都低时，先安全 Z、再 XY、最后目标 Z。XYZT 用同样分支，把水平组换成 XYT。XY 方法当前低时抬安全 Z、移动 XY 后恢复原 Z，高时直接 XY。NaN 等导致比较均不匹配的情况进入末尾异常，不概括成所有输入都有正常分支。

控制器未逐次检查 MoveZAxis 返回值，该方法可因单步拒绝返回 Abort；不能把每条后续 XY 都画成已确认 Z 成功之后才执行。模块的 XY 等方法另有离线与 IsReady 返回；void 返回也不统一代表实际完成。

依据：BondModuleController.MovementRelated.cs 49–180、186–313、393–466、762–893；BondModule.cs 386–441、449–497、780–863；BondHeadController.MovementRelated.cs 219–232。

## 安全高度与限位重载

安全高度以设备安全点或载具 G0 原点+产品 SafeHeight 为基础。S2 测高气缸打开且有点胶器时减焊头/点胶器 Z 差，否则加吸嘴测高偏移；再转回机械 Z。非工作状态的目标重载可改用设备安全 Z，跨静态 Waffle 区域时根据当前或目标 Y 提高到避让位 Z+吸嘴偏移。

二维、三维目标重载在覆盖与静态避让后检查最终安全高度限位；四维重载只在有载具的早期位置检查，后续覆盖/提高不再同样复查；无参数重载也没有相同的非工作覆盖。不要把重载合成一个完全相同的安全检查。模块四维 CheckSoftLimit 实际只查 XYZ，没有 T；二维只查 XY。双标量 Y 下限读取 GetSoftLimit，而其他部分多用 AxisSetPara。

依据：BondModuleController.cs 262–552；BondModule.cs 909–1015。

## 区域与场景选择

取片预移动先按配置检查翻转台交接位或回零位。重新取片走普通 XYZT 安全移动；其他按 AxisMoveMode 选择绝对动作或 Jump。绝对取片先等待安全 Z，再等待 XY 接近后发目标 Z，最后 WaitAxesArrival；静态 Waffle 覆盖专用安全高度，局部两段等待各有 10 秒判断。

Jump 取片按静态 Waffle、Bond 相机搜索或晶圆搜索组成不同过渡段：静态单段带高度检查，Bond 相机三段经过环光安全高度，其他经输送边缘两段或三段。固晶绝对动作等待安全 Z、XY 接近后发 Z，Jump 固晶依当前高度选择两段或三段。速度、加速度、前瞻参数由对应 ULM 配置与整机比例组成，不能把普通 MoveSafe 方法直接当成连续轨迹实现。

上视入口区分静态 Waffle、翻转台、晶圆与刮胶盘；绝对模式选择不同安全高度，插补模式分派不同 Jump 方法。翻转且校正前蘸胶、两点校正的路径会先抬高、发 BondDipFluxFinishSignal 并等待胶盘缩回，超过 5 秒抛异常。IPT 绝对移动与插补也分开；晶圆到 IPT 的插补使用四段，清嘴台配置和左右 IPT 改变过渡点。换嘴接口先到换嘴安全 Z 再 XY，另有自己的单步/离线门控。

依据：PickActionNode.MoveHelper.cs 61–125、135–336、660–781；BondActionNode.MoveHelper.cs 49–144、186–360；UpLookCorrectionActionNode.cs 619–766；SubstrateCameraCorrectionActionNode.MoveHelper.cs 51–106、114–309；BondModuleController.MovementRelated.cs 318–353；BondHeadController.MovementRelated.cs 71–90。

## 碰撞圆与路径工具

晶圆带搜索 G0 移动先关顶针台真空，再判断离线；启用环限位时用目标 XY 与 WaferTableCenter 的平方距离判断，半径先转 long，边界相等通过。特定搜索模式先检查顶针准备高度，再转晶圆普通坐标、发 X/Y 指令并 WaitAxesArrival。该圆检查不是任意路径的全程避碰验证，也不检查 Z。

MotionPlanDomain 以四安全点的 XY 包围范围检查终点，按固定边顺序取首个交点；FindIntersection 在求直线交点后只检查起终线段的 X 范围，没有完整检查两条线段的 X/Y 参数范围。GetRadius 返回交点到终点的 XY 距离与 Z 差绝对值的较小值。GetMoveLine 生成两组各 11 点的折段/高度曲线，存在距离为零等未统一保护边界，不把它称为通用精确避障求解。

GetMoveParaByDistance 按 XY 距离分段返回 Acc/Dec/Jerk，没有发运动指令。当前主工程直接引用检索中 GetMoveLine 位于速度实验，GetRadius/GetMoveParaByDistance 未定位到直接调用，不将这些工具推定为所有生产动作的必经规划器。

依据：WaferTableController.cs 1426–1453、1504–1513、1710–1720；MotionPlanDomain.cs 58–164、175–255、265–325。

## 插补组与驱动边界

GetXY/XYZ/XYZTIpolGroup 明确转换为 ETELAxis 并建立/缓存 DsaIpolGroup，不是驱动自动探测接口。GetBondIpolAxis 按 IsBondAxisTSingleMove 选择 XYZ 或 XYZT，GetXYIpolAxis 只给 XY。实际 Pick/Bond/IPT Jump 根据首个驱动查所属 AxisCard，再调该卡 MotionController.ContinueInterpolationMove；无本地证据证明该外部接口一定转调同名 GuGaoDrive 静态工具。

本地 GuGaoDrive.ContinueInterpolationMove 使用 core=2、传入 list/group、轴号和 PulseEquivalent，配置轴/组、平滑、前瞻，逐段写绝对直线与非末段 blending。部分 rtn 累加、部分覆盖，不能当作每个 API 都即时独立通过。DataEnd do/while 在成功前持续尝试，没有本地统一超时；启动后监视 group.run 或 list.execute，超过 30 秒抛异常，finally 解组并禁用组。这个 finally 不是代码中显式的逐轴停止并确认到位。

PickContinueInterpolationMove 是另一辅助接口，core/list/group 固定为 2，固定组约束和前瞻参数。它的数据结束及运行状态循环没有前一接口的 30 秒检查；HighAccuracy 后续逐驱动调用 WaitInRealPosition。当前找到的直接调用在速度实验，不能因名称含 Pick 就标成生产取片所必用的实现。ETEL 测试方法用参数除 1000 后传 ipolLine，并调用 ipolWaitMovement；不同接口的单位/完成语义仍取决于实际驱动契约。

依据：BondModuleController.MovementRelated.cs 619–754、900–930；PickActionNode.MoveHelper.cs 308–324；BondActionNode.MoveHelper.cs 333–349；SubstrateCameraCorrectionActionNode.MoveHelper.cs 282–299；GuGaoDrive.cs 46–215、251–295、353–403、487–832、1600–2032；FrmSpeedImprovementExperiment.cs 166。

## 发令、到位、异常与停止

模块 XY/XYT/XYZT 先 SendAbsoluteMoveCommand 再调用 MotionService.WaitAxesArrival；无安全 XYZ 则先发 Z 并等待，再发 XY 并等待，不代表同时 XYZ 插补。MovePara 重载会就地乘速度比例，不是只读输入。Axis、MotionService 与各卡 SDK 的内部等待/超时实现未在此主程序源码中定位到对应定义，说明停在实有调用边界，不虚构全部硬件已到位。

T 单独运动时不进入 XYZ 插补组；部分 Jump 先开后台 T 任务，等待 Z 达某条件后才转 T，插补调用返回后再 Wait 该任务。取片与固晶/IPT 的局部条件及超时不同。部分提前返回或异常路径未统一 join 已启动的 T 任务，不能把调用失败理解为后台动作已结束。

普通 Stop 写状态、清对话、复位部分信号/输出并清检测计数，没有逐轴 StopMove 或统一等待所有 Task。EmergencyStop 另并行请求逐轴 StopMove(false,true)，再普通 Stop 并调用三个任务中止接口；该层没有显式统一 join 和物料恢复。暂停停止的完整状态说明继续链接恢复专题。

依据：BondModule.cs 449–497、552–630、780–863；BondHeadController.MovementRelated.cs 172–232；PickActionNode.MoveHelper.cs 149–201、315–336；BondActionNode.MoveHelper.cs 246–277、340–359；SubstrateCameraCorrectionActionNode.MoveHelper.cs 130–158、291–309；Machine.Operate.cs 347–402。
