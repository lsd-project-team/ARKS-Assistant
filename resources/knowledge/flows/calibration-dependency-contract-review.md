# 标定子调用：返回、异常、重试和清理

本专题连接[完整标定流程](bond-camera-calibration-review.md)与已存在的[安全运动审计](safe-motion-workflow-review.md)，不重复把已核验的运动分支当成新增实现。结论来自trunk；不代表设备运行验收。

## 视觉步骤和重试

1. 标定任务直接调用[CalibrateTask.LocatePosition:1013–1031](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1013)：仓库按名Find并转换PREntity → Sleep(2000) → DoWork → 执行枚举非Success抛ArgumentNullException → 转换并返回AlgResult。它没有检查返回对象的IsSuccess。
2. 居中辅助使用另一方法：[CalibController.LocatePosition:318–336](../../trunk/AKRS.ZX2200/CalibSystem/Services/CalibController.cs#L318)。结构相近但Sleep(200)，不是上面的两秒。Find返回null、错误对象类型、DoWork抛异常或AlgResult转换失败均无本地catch。
3. [LocateAndMoveToTargetPixel:161–210](../../trunk/AKRS.ZX2200/CalibSystem/Services/CalibController.cs#L161)以固定像素(1224,1024)为目标，retryCount<maxRetry时先定位并移动，再重新定位计算偏差。两分量绝对值均严格小于pixelTolerance才返回true；否则达到次数后提示并返回false。标定中的参数(1,2)代表最多两轮尝试，不是首次加两次重试。
4. [LocateAndMoveOnce及CalculatePixelDeviation:218–249](../../trunk/AKRS.ZX2200/CalibSystem/Services/CalibController.cs#L218)：首次结果null或IsSuccess=false会增加尝试计数；第二次结果失败则返回两个double.MaxValue，继续容差判断。异常则直接离开方法，不进入上述continue。若首次结果一直失败，最终偏差变量仍保持初值(0,0)，提示中的零偏差不能证明定位有效。
5. [标定调用:1846–1853](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1846)不检查居中bool，仍回读坐标并继续；后续左右Mark处也是独立调用，不把其false自动当作任务失败。异常才会进入标定外层catch。

## 运动返回与异常

[MoveSafeBondXY:436–467](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondModuleController.MovementRelated.cs#L436)先读取位置、计算安全高度、检查软限位，再等待单步。外层单步拒绝时void返回；低位分支调用安全Z、XY、原Z，但不消费Z包装的返回码。由此不能将方法正常返回当作所有动作已完成。XYZ等分支已有[原方法隔离验证](safe-motion-workflow-review.md)，本轮沿用其证据；异常向上中断后续语句，Abort/失败码与异常不是同一条路径。

## 取片和放片失败

[PickAction:97–109](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs#L97)及[BondAction:397–409](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs#L397)均在try之前读取速度和生成动作参数；此处异常不会经过各自方法里的catch/finally。

取片[337–387](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs#L337)有两类catch：NullReferenceException分支会请求顶针回准备位，力控模式还请求复位；一般异常分支的顶针回位代码已注释，仅力控模式请求复位。两分支均提示并throw；finally关闭力读取。清理、日志或提示自身抛异常可能替代原异常，不能保证清理完整。

放片[544–569](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs#L544)捕获后处理力控复位、提示并throw ex，finally关闭力读取，正常末尾return true。完整方法397–569中没有return false，因此“调用方忽略bool”不能转述成这个方法当前存在已证实的false返回路径；仍需区分更下层运动返回值与本方法异常。

取片的[顶针任务:213–237](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs#L213)仅CarrierWithWafer且非同步顶针时创建；[Wait(2000)超时:253–279](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs#L253)会尝试抬升/力控复位并返回false。但本标定方法使用CarrierWithWaffle及BMC，不能把这一超时出口画成其正常可达分支。原始取片调用类型见[1911–1912](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1911)与[2003–2006](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L2003)。

## 调用者可观察的结果

定位/运动/取放向外抛出的异常，若被[标定catch:2264–2268](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L2264)正常处理，将转成false；[外层结果展示](bond-camera-calibration-review.md)却不检查该值。居中false和运动void提前返回则不需要先经过catch，也可能继续流程。应分别展示这三类路径，不将所有失败统一画为“停止并恢复”。

后续补充：[取放参数服务分支与PR执行链](calibration-parameter-pr-review.md)已完成静态追踪，并连接既有视觉执行审计。尚未验收：各派生算法/SDK、参数真实配置与运行行为、厂商轴/相机契约、急停与并发关闭、真机清理效果；未修改生产源码。

## 验证资料

[原方法测试](../../scripts/test-calibration-pr-contract.cjs)分别提取两个LocatePosition原方法，各执行八项，共16项通过：成功对象返回、等待参数、IsSuccess=false仍返回、null结果仍返回、非成功执行枚举、模板缺失、结果类型错误、执行器抛异常。仓库、PR执行器及Thread.Sleep均为替身；200/2000只核对传入等待参数，不证明真实调度时长。未在此执行包含元组语法的像素重试方法，也未运行真实相机。

[源码证据快照](calibration-dependency-contract-evidence.json)保存当前报告哈希及所引原文，统一检查验证链接、原文漂移与16项行为测试。已知安全运动结果沿用既有独立测试，不重复计作本轮新测试。
