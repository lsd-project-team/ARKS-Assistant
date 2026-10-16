# 本机MSBuild配置求值与编译项基准

本轮运行系统Framework64 MSBuild的只读自定义目标，求值16个项目的Debug/Release × AnyCPU/x86/x64。实际命令、退出码和日志哈希见[机器回执](msbuild-evaluation.json)。这不是Build、Restore或ResolveReferences，没有调用编译器、包安装、许可证编译或生产程序。

当前96组尝试：32组自定义目标成功、64组在到达输出目标之前失败。失败不能填写为“无编译项”；具体错误保留于日志。

## 当前环境与配置结论

- MSBuild：C:/Windows/Microsoft.NET/Framework64/v4.0.30319/MSBuild.exe；文件哈希已绑定，求值工具版本见每组properties。
- dotnet --list-sdks：退出码0，输出为空，本次未发现SDK。
- 项目默认Platform和显式配置组合不是同一概念。主工程Debug|AnyCPU实际PlatformTarget=x64；Release|AnyCPU实际AnyCPU。x86错误不是缺源代码，而是配置组合没有OutputPath。
- 解决方案把主工程Debug/Release的x64配置映射到项目Any CPU；直接传项目Platform=x64不等同通过解决方案构建。
- 此处HintPath存在性仍不等于MSBuild程序集解析结果；缺失HintPath可能另有GAC或其他搜索路径，未运行ResolveReferences确认。

## 求值矩阵

|项目|Debug AnyCPU|Release AnyCPU|Debug x86|Release x86|Debug x64|Release x64|
|---|---|---|---|---|---|
|trunk/AKRS.Calibration/AKRS.Calibration.csproj|12项 / AnyCPU|12项 / AnyCPU|失败(1)|失败(1)|失败(1)|失败(1)|
|trunk/Akrs.ChangeJson/Akrs.ChangeJson.csproj|12项 / x64|12项 / AnyCPU|失败(1)|失败(1)|失败(1)|失败(1)|
|trunk/AKRS.Galaxy.SoftKey/AKRS.Galaxy.SoftKey/AKRS.Galaxy.SoftKey.csproj|6项 / AnyCPU|6项 / AnyCPU|失败(1)|失败(1)|失败(1)|失败(1)|
|trunk/AKRS.Galaxy2.AutoFocusing/AKRS.Galaxy2.AutoFocusing.csproj|4项 / x64|4项 / AnyCPU|失败(1)|失败(1)|失败(1)|失败(1)|
|trunk/AKRS.Galaxy2.AxisCompensate/AKRS.Galaxy2.AxisCompensate.csproj|7项 / AnyCPU|7项 / AnyCPU|失败(1)|失败(1)|失败(1)|失败(1)|
|trunk/AKRS.Galaxy2.Component.TestDemo/AKRS.Galaxy2.RealtimeCurve.TestDemo.csproj|6项 / AnyCPU|6项 / AnyCPU|失败(1)|失败(1)|失败(1)|失败(1)|
|trunk/AKRS.Galaxy2.CoordinateSystems/AKRS.Galaxy2.CoordinateSystems.csproj|13项 / AnyCPU|13项 / AnyCPU|失败(1)|失败(1)|失败(1)|失败(1)|
|trunk/AKRS.Galaxy2.Dispense/AKRS.Galaxy2.Dispense.csproj|81项 / x64|81项 / 未指定|失败(1)|失败(1)|失败(1)|失败(1)|
|trunk/AKRS.Galaxy2.LogTest/AKRS.Galaxy2.LogTest.csproj|6项 / AnyCPU|6项 / AnyCPU|失败(1)|失败(1)|失败(1)|失败(1)|
|trunk/AKRS.Galaxy2.Machine/AKRS.Galaxy2.Machine.csproj|6项 / 未指定|6项 / 未指定|失败(1)|失败(1)|失败(1)|失败(1)|
|trunk/AKRS.Galaxy2.MachineSupport/AKRS.Galaxy2.MachineSupport.csproj|4项 / 未指定|4项 / 未指定|失败(1)|失败(1)|失败(1)|失败(1)|
|trunk/AKRS.Galaxy2.PR/AKRS.Galaxy2.PR.csproj|85项 / x64|85项 / AnyCPU|失败(1)|失败(1)|失败(1)|失败(1)|
|trunk/AKRS.Galaxy2.PR.Test/AKRS.Galaxy2.PR.Test.csproj|6项 / x64|6项 / AnyCPU|失败(1)|失败(1)|失败(1)|失败(1)|
|trunk/AKRS.Galaxy2.TeachTest/AKRS.Galaxy2.TeachTest.csproj|17项 / AnyCPU|17项 / AnyCPU|失败(1)|失败(1)|失败(1)|失败(1)|
|trunk/AKRS.ZX2200/AKRS.ZX2200.csproj|1137项 / x64|1137项 / AnyCPU|失败(1)|失败(1)|失败(1)|失败(1)|
|trunk/InterpolationMovementTest/InterpolationMovementTest.csproj|8项 / x64|8项 / AnyCPU|失败(1)|失败(1)|失败(1)|失败(1)|

## 文件系统与编译项差异

Debug|AnyCPU：16个项目，1410个不重复Compile文件；文件系统基准1436个C#文件，差26个。Release|AnyCPU为1410个文件，两个集合相同。此集合是当前工具/导入条件下的编译前求值，不包含执行构建目标后可能动态添加的生成项。

以下文件当前未纳入Debug|AnyCPU Compile；保留源码分析记录，但不能据其存在证明在当前构建中运行，也不能凭未纳入就断定可删除：

- [trunk/AKRS.Galaxy2.Dispense/Properties/Resources.Designer.cs](../../trunk/AKRS.Galaxy2.Dispense/Properties/Resources.Designer.cs)
- [trunk/AKRS.Galaxy2.Machine/Services/MachineService.cs](../../trunk/AKRS.Galaxy2.Machine/Services/MachineService.cs)
- [trunk/AKRS.Galaxy2.PR/Models/TemplateConfigs/BaseTemplateConfig.cs](../../trunk/AKRS.Galaxy2.PR/Models/TemplateConfigs/BaseTemplateConfig.cs)
- [trunk/AKRS.Galaxy2.PR/Models/TemplateConfigs/PRTemplateConfig.cs](../../trunk/AKRS.Galaxy2.PR/Models/TemplateConfigs/PRTemplateConfig.cs)
- [trunk/AKRS.ZX2200/BondSystem/Controls/Setting/ProcessStep/FrmCreateProcessStep.cs](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/ProcessStep/FrmCreateProcessStep.cs)
- [trunk/AKRS.ZX2200/BondSystem/Controls/Setting/ProcessStep/FrmCreateProcessStep.Designer.cs](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/ProcessStep/FrmCreateProcessStep.Designer.cs)
- [trunk/AKRS.ZX2200/BondSystem/Controls/Setting/ProcessStep/UcProcessStepEdit.cs](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/ProcessStep/UcProcessStepEdit.cs)
- [trunk/AKRS.ZX2200/BondSystem/Controls/Setting/ProcessStep/UcProcessStepEdit.Designer.cs](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/ProcessStep/UcProcessStepEdit.Designer.cs)
- [trunk/AKRS.ZX2200/BondSystem/Services/System1ActionNodesService.cs](../../trunk/AKRS.ZX2200/BondSystem/Services/System1ActionNodesService.cs)
- [trunk/AKRS.ZX2200/Common.cs](../../trunk/AKRS.ZX2200/Common.cs)
- [trunk/AKRS.ZX2200/DispenseSystem/Services/System2ActionNodesService.cs](../../trunk/AKRS.ZX2200/DispenseSystem/Services/System2ActionNodesService.cs)
- [trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmChooseCamera.cs](../../trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmChooseCamera.cs)
- [trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmChooseCamera.Designer.cs](../../trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmChooseCamera.Designer.cs)
- [trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRotateCenterAccuracy.cs](../../trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRotateCenterAccuracy.cs)
- [trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRotateCenterAccuracy.Designer.cs](../../trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRotateCenterAccuracy.Designer.cs)
- [trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/InterpolationParamConfig.cs](../../trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/InterpolationParamConfig.cs)
- [trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/NLogTraceWriter.cs](../../trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/NLogTraceWriter.cs)
- [trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/SingleInterpolationParam.cs](../../trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/SingleInterpolationParam.cs)
- [trunk/AKRS.ZX2200/Main/Machine/Control/FrmChipFrictionSetting.cs](../../trunk/AKRS.ZX2200/Main/Machine/Control/FrmChipFrictionSetting.cs)
- [trunk/AKRS.ZX2200/Main/Machine/Control/FrmChipFrictionSetting.Designer.cs](../../trunk/AKRS.ZX2200/Main/Machine/Control/FrmChipFrictionSetting.Designer.cs)
- [trunk/AKRS.ZX2200/Main/Machine/Product/ProcessStep/ProcessStep.cs](../../trunk/AKRS.ZX2200/Main/Machine/Product/ProcessStep/ProcessStep.cs)
- [trunk/AKRS.ZX2200/Main/Machine/Product/ProcessStep/ProcessStepProgram.cs](../../trunk/AKRS.ZX2200/Main/Machine/Product/ProcessStep/ProcessStepProgram.cs)
- [trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ComponentsTeach/FrmComponentLocateUseInfo.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ComponentsTeach/FrmComponentLocateUseInfo.cs)
- [trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ComponentsTeach/FrmComponentLocateUseInfo.Designer.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ComponentsTeach/FrmComponentLocateUseInfo.Designer.cs)
- [trunk/InterpolationMovementTest/FrmTest.cs](../../trunk/InterpolationMovementTest/FrmTest.cs)
- [trunk/InterpolationMovementTest/FrmTest.Designer.cs](../../trunk/InterpolationMovementTest/FrmTest.Designer.cs)

## 主工程未满足的引用条件

- 缺失项目：trunk/AKRS.Galaxy2.Parameters/AKRS.Galaxy2.Parameters.csproj
- 未找到HintPath：C:\Program Files\MATLAB\MATLAB Runtime\R2022b\toolbox\dotnetbuilder\bin\win64\netstandard2.0\MWArray.dll；本机解析为 C:/Program Files/MATLAB/MATLAB Runtime/R2022b/toolbox/dotnetbuilder/bin/win64/netstandard2.0/MWArray.dll
- 未找到HintPath：..\..\..\..\Platform\AKRS.Galaxy2\trunk\packages\System.Threading.Tasks.Dataflow.6.0.0\lib\netstandard2.0\System.Threading.Tasks.Dataflow.dll；本机解析为 C:/Users/akrs/Documents/Platform/AKRS.Galaxy2/trunk/packages/System.Threading.Tasks.Dataflow.6.0.0/lib/netstandard2.0/System.Threading.Tasks.Dataflow.dll
- 未找到HintPath：..\..\..\..\Program Files\VisionMaster4.3.0\Development\V4.x\ComControls\Assembly\VM.Controls.dll；本机解析为 C:/Users/akrs/Documents/Program Files/VisionMaster4.3.0/Development/V4.x/ComControls/Assembly/VM.Controls.dll
- 未找到HintPath：C:\Program Files (x86)\Reference Assemblies\Microsoft\Framework\.NETFramework\v4.8\System.dll；本机解析为 C:/Program Files (x86)/Reference Assemblies/Microsoft/Framework/.NETFramework/v4.8/System.dll
- 未找到HintPath：..\..\..\..\Program Files\VisionMaster4.3.0\Development\V4.x\ComControls\Assembly\VM.ModuleControl.dll；本机解析为 C:/Users/akrs/Documents/Program Files/VisionMaster4.3.0/Development/V4.x/ComControls/Assembly/VM.ModuleControl.dll

## 后续验收要求

1. 在匹配的Visual Studio/MSBuild与.NET Framework 4.8开发包环境补齐缺失项目及供应商依赖；不以替身程序集完成产品构建。
2. 使用解决方案声明的配置映射；主工程直接调用示例应使用 `/p:Configuration=Debug /p:Platform=AnyCPU`，不能沿用未经配置支持的x86建议。
3. 在该环境执行完整Build，检查引用实际解析路径、资源/许可证/AOP处理和输出架构，再进行软件启动及设备验收。
4. 对26个非Compile文件的已有结论添加配置范围；保留文件系统基准与编译项基准两种口径。

当前只完成构建前求值基准；整体模块、完整构建和设备运行未验收。
