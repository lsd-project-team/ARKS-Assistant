# 项目声明依赖与缺失项

直接解析 csproj XML；未求值条件或 imports，不能等同运行时调用。

|项目|输出类型|框架|项目引用数|
|---|---|---|---:|
|trunk/AKRS.Calibration/AKRS.Calibration.csproj|Library|v4.8|0|
|trunk/Akrs.ChangeJson/Akrs.ChangeJson.csproj|WinExe|v4.8|0|
|trunk/AKRS.Galaxy.SoftKey/AKRS.Galaxy.SoftKey/AKRS.Galaxy.SoftKey.csproj|Exe|v4.8|0|
|trunk/AKRS.Galaxy2.AutoFocusing/AKRS.Galaxy2.AutoFocusing.csproj|Library|v4.8|0|
|trunk/AKRS.Galaxy2.AxisCompensate/AKRS.Galaxy2.AxisCompensate.csproj|Exe|v4.8|1|
|trunk/AKRS.Galaxy2.Component.TestDemo/AKRS.Galaxy2.RealtimeCurve.TestDemo.csproj|Library|v4.8|0|
|trunk/AKRS.Galaxy2.CoordinateSystems/AKRS.Galaxy2.CoordinateSystems.csproj|Library|v4.8|0|
|trunk/AKRS.Galaxy2.Dispense/AKRS.Galaxy2.Dispense.csproj|Library|v4.8|0|
|trunk/AKRS.Galaxy2.LogTest/AKRS.Galaxy2.LogTest.csproj|WinExe|v4.8|0|
|trunk/AKRS.Galaxy2.Machine/AKRS.Galaxy2.Machine.csproj|Library|v4.8|0|
|trunk/AKRS.Galaxy2.MachineSupport/AKRS.Galaxy2.MachineSupport.csproj|Library|v4.8|0|
|trunk/AKRS.Galaxy2.PR/AKRS.Galaxy2.PR.csproj|Library|v4.8|0|
|trunk/AKRS.Galaxy2.PR.Test/AKRS.Galaxy2.PR.Test.csproj|WinExe|v4.8|1|
|trunk/AKRS.Galaxy2.TeachTest/AKRS.Galaxy2.TeachTest.csproj|Library|v4.8|0|
|trunk/AKRS.ZX2200/AKRS.ZX2200.csproj|WinExe|v4.8|10|
|trunk/InterpolationMovementTest/InterpolationMovementTest.csproj|WinExe|v4.8|1|

## 项目引用明细

|声明位置|引用目标|文件状态|
|---|---|---|
|[trunk/AKRS.Galaxy2.AxisCompensate/AKRS.Galaxy2.AxisCompensate.csproj:68](../../trunk/AKRS.Galaxy2.AxisCompensate/AKRS.Galaxy2.AxisCompensate.csproj#L68)|trunk/AKRS.Galaxy2.MachineSupport/AKRS.Galaxy2.MachineSupport.csproj|存在；内部业务待复核|
|[trunk/AKRS.Galaxy2.PR.Test/AKRS.Galaxy2.PR.Test.csproj:1055](../../trunk/AKRS.Galaxy2.PR.Test/AKRS.Galaxy2.PR.Test.csproj#L1055)|trunk/AKRS.Galaxy2.PR/AKRS.Galaxy2.PR.csproj|存在；内部业务待复核|
|[trunk/AKRS.ZX2200/AKRS.ZX2200.csproj:4078](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L4078)|trunk/AKRS.Calibration/AKRS.Calibration.csproj|存在；内部业务待复核|
|[trunk/AKRS.ZX2200/AKRS.ZX2200.csproj:4082](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L4082)|trunk/AKRS.Galaxy.SoftKey/AKRS.Galaxy.SoftKey/AKRS.Galaxy.SoftKey.csproj|存在；内部业务待复核|
|[trunk/AKRS.ZX2200/AKRS.ZX2200.csproj:4086](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L4086)|trunk/AKRS.Galaxy2.AutoFocusing/AKRS.Galaxy2.AutoFocusing.csproj|存在；内部业务待复核|
|[trunk/AKRS.ZX2200/AKRS.ZX2200.csproj:4090](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L4090)|trunk/AKRS.Galaxy2.AxisCompensate/AKRS.Galaxy2.AxisCompensate.csproj|存在；内部业务待复核|
|[trunk/AKRS.ZX2200/AKRS.ZX2200.csproj:4094](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L4094)|trunk/AKRS.Galaxy2.CoordinateSystems/AKRS.Galaxy2.CoordinateSystems.csproj|存在；内部业务待复核|
|[trunk/AKRS.ZX2200/AKRS.ZX2200.csproj:4098](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L4098)|trunk/AKRS.Galaxy2.Dispense/AKRS.Galaxy2.Dispense.csproj|存在；内部业务待复核|
|[trunk/AKRS.ZX2200/AKRS.ZX2200.csproj:4102](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L4102)|trunk/AKRS.Galaxy2.MachineSupport/AKRS.Galaxy2.MachineSupport.csproj|存在；内部业务待复核|
|[trunk/AKRS.ZX2200/AKRS.ZX2200.csproj:4106](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L4106)|trunk/AKRS.Galaxy2.Machine/AKRS.Galaxy2.Machine.csproj|存在；内部业务待复核|
|[trunk/AKRS.ZX2200/AKRS.ZX2200.csproj:4110](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L4110)|trunk/AKRS.Galaxy2.Parameters/AKRS.Galaxy2.Parameters.csproj|缺失；不可推断实现|
|[trunk/AKRS.ZX2200/AKRS.ZX2200.csproj:4114](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L4114)|trunk/AKRS.Galaxy2.PR/AKRS.Galaxy2.PR.csproj|存在；内部业务待复核|
|[trunk/InterpolationMovementTest/InterpolationMovementTest.csproj:205](../../trunk/InterpolationMovementTest/InterpolationMovementTest.csproj#L205)|trunk/AKRS.ZX2200/AKRS.ZX2200.csproj|存在；内部业务待复核|
