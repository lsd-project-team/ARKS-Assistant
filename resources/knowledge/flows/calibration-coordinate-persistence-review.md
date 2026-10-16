# 标定坐标保存：源码与随附程序集的证据衔接

范围：偏移标定的MachineCoordinateSystem保存，不是所有标定参数保存。源码可定位到调用者和坐标类；JsonFormatHelper无原始C#源码，但已有当前仓库随附DLL的方法体证据。缺少源码不等于这段实现完全未知。

## 执行摘要

[标定方法](bond-camera-calibration-review.md)创建坐标时先保存，Init后再保存，再Refresh清除内存单例；随后继续偏移检查和取标。坐标类直接调用对象JSON helper；随附helper创建目录/必要时预创建目标，写同目录随机临时文件，再Replace或Move到目标。未通过最后复核或结果窗口取消，不会在该链中自动撤销已经发出的保存。

## 源码到二进制的绑定

1. [CalibrateTask:2107–2119](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L2107)：创建、查找、Init、Save、Refresh的顺序。
2. [MachineCoordinateSystem:86–89](../../trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/MachineCoordinateSystem.cs#L86)：SaveGenericObject(instance,FilePath)，参数是静态instance，不是this。本方法没有Singleton.Save的锁；不能因其他配置类继承Singleton就把其锁行为移植到这里。该类[声明:12](../../trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/MachineCoordinateSystem.cs#L12)的Singleton继承已注释。
3. [项目HintPath:45–46](../../trunk/AKRS.Galaxy2.CoordinateSystems/AKRS.Galaxy2.CoordinateSystems.csproj#L45)：引用ZX2200/libs/AKRS.Galaxy2.Infrastructure.dll，与[现有IL证据](persistence-save-binary-evidence.json)的assembly.path一致。当前文件SHA256为 `f75452133ba809255061210eafc861b576c0fe8b553a983575934fe3d19892eb`。这只是仓库引用和文件身份，不是现场加载证明。
4. [默认路径:21–30](../../trunk/AKRS.Galaxy2.CoordinateSystems/StaticPara.cs#L21)：Application.StartupPath/Settings/DeviceParams/MachineCoordinateSystem/MachineCoordinateSystem.json。CoordinateSystemPath可修改，不推定现场路径。

## 随附helper的实际步骤

以下位置来自机器可重提取的IL证据中 `methods.jsonSaveObject`，不是原始C#行号：

| 步骤 | IL位置 | 已确认边界 |
| --- | --- | --- |
| 取目录，必要时创建 | IL_0001–IL_002d | 位于主要catch之外 |
| 目标不存在时File.Create并Dispose | IL_002e–IL_0048 | 首次保存有预创建目标；不能声称失败一定保留“不存在”状态 |
| 随机临时名、创建流、序列化、WriteLine | IL_0049–IL_00cc | 写的是同目录临时文件；流释放有finally |
| 目标存在则Replace，否则Move | IL_00ed–IL_010e | Replace第三参数null，没有由此建立备份文件 |
| 异常后尝试删临时文件，再抛新Exception | IL_0113–IL_013c | 主要catch覆盖IL_0055–IL_0113；清临时文件异常被吞，新的异常只拼接原Message |

`methods.objectErrorCallback`在IL_001e设置ErrorContext.Handled=true，因此不能把“helper没有抛出异常”直接当成全部字段已完整序列化。没有执行磁盘故障注入，以上不证明文件系统的原子性、断电恢复、多文件事务或现场保存成功。

## 刷新与失败传播

[Refresh:64–67](../../trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/MachineCoordinateSystem.cs#L64)只将静态instance设null；[GetInstance/Load:33–59](../../trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/MachineCoordinateSystem.cs#L33)之后才重新读取并Init。保存接受静态instance意味着旧对象引用调用Save也不是自动保存它自身；Refresh后尚未重载时，该方法可向helper传null。这里只验证包装层传参，不声称正常标定顺序会主动触发此情形。

helper抛出的异常不会被坐标Save本地吞掉；在标定方法调用范围内可进入[catch:2264–2269](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L2264)。外层忽略false仍展示结果的问题已在[原方法检查](../../scripts/test-calibration-result-flow.cjs)验证。结果窗口出现不能替代落盘确认。

## 验证与缺口

- 随附DLL的九个方法已重新提取核对，沿用[原核验器](../../scripts/verify-persistence-save-contract.cjs)，不复制另一份容易漂移的IL。
- [坐标Save/Refresh包装检查](../../scripts/test-calibration-coordinate-save.cjs)使用原方法与记录型helper替身，覆盖静态实例传参、旧引用保存、Refresh后传null以及helper异常外抛；不操作真实配置文件。
- 仍缺：helper原始源码、现场DLL哈希与实际加载路径、JSON样本、序列化错误场景、磁盘失败/并发写入实验及设备复核。
- 本次关闭“未衔接已有二进制实现”的文档缺口，不将现场验收标成完成。
