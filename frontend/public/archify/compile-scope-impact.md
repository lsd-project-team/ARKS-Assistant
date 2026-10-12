# 非编译文件对现有源码结论的影响

适用于本机MSBuild求值的Debug/Release AnyCPU配置。依据[构建求值报告](msbuild-evaluation-review.md)，以下文件在两种配置下均未纳入Compile。源码快照仍证明文件内容，但不能据此证明这些方法参与当前产品构建或运行。构建目标动态生成项及其他环境须另行验证。

本表逐项匹配两个源码证据登记表的完整路径，以及模块reviewedFiles和关系中的证据ID。它不覆盖仅用类名描述的隐式引用，也不证明未命中的文件没有影响。

|文件|已登记证据|已复核模块|受影响代表关系数|
|---|---|---|---|
|trunk/AKRS.Galaxy2.Dispense/Properties/Resources.Designer.cs|无直接路径命中|无|0|
|trunk/AKRS.Galaxy2.Machine/Services/MachineService.cs|module-AKRS-Galaxy2-Machine-MachineService|AKRS.Galaxy2.Machine|0|
|trunk/AKRS.Galaxy2.PR/Models/TemplateConfigs/BaseTemplateConfig.cs|无直接路径命中|无|0|
|trunk/AKRS.Galaxy2.PR/Models/TemplateConfigs/PRTemplateConfig.cs|无直接路径命中|无|0|
|trunk/AKRS.ZX2200/BondSystem/Controls/Setting/ProcessStep/FrmCreateProcessStep.cs|无直接路径命中|无|0|
|trunk/AKRS.ZX2200/BondSystem/Controls/Setting/ProcessStep/FrmCreateProcessStep.Designer.cs|无直接路径命中|无|0|
|trunk/AKRS.ZX2200/BondSystem/Controls/Setting/ProcessStep/UcProcessStepEdit.cs|无直接路径命中|无|0|
|trunk/AKRS.ZX2200/BondSystem/Controls/Setting/ProcessStep/UcProcessStepEdit.Designer.cs|无直接路径命中|无|0|
|trunk/AKRS.ZX2200/BondSystem/Services/System1ActionNodesService.cs|无直接路径命中|无|0|
|trunk/AKRS.ZX2200/Common.cs|support-common|AKRS.ZX2200/Common.cs|0|
|trunk/AKRS.ZX2200/DispenseSystem/Services/System2ActionNodesService.cs|无直接路径命中|无|0|
|trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmChooseCamera.cs|无直接路径命中|无|0|
|trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmChooseCamera.Designer.cs|无直接路径命中|无|0|
|trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRotateCenterAccuracy.cs|无直接路径命中|无|0|
|trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRotateCenterAccuracy.Designer.cs|无直接路径命中|无|0|
|trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/InterpolationParamConfig.cs|无直接路径命中|无|0|
|trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/NLogTraceWriter.cs|无直接路径命中|无|0|
|trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/SingleInterpolationParam.cs|无直接路径命中|无|0|
|trunk/AKRS.ZX2200/Main/Machine/Control/FrmChipFrictionSetting.cs|无直接路径命中|无|0|
|trunk/AKRS.ZX2200/Main/Machine/Control/FrmChipFrictionSetting.Designer.cs|无直接路径命中|无|0|
|trunk/AKRS.ZX2200/Main/Machine/Product/ProcessStep/ProcessStep.cs|无直接路径命中|无|0|
|trunk/AKRS.ZX2200/Main/Machine/Product/ProcessStep/ProcessStepProgram.cs|无直接路径命中|无|0|
|trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ComponentsTeach/FrmComponentLocateUseInfo.cs|无直接路径命中|无|0|
|trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ComponentsTeach/FrmComponentLocateUseInfo.Designer.cs|无直接路径命中|无|0|
|trunk/InterpolationMovementTest/FrmTest.cs|无直接路径命中|无|0|
|trunk/InterpolationMovementTest/FrmTest.Designer.cs|无直接路径命中|无|0|

## 结论使用规则

- 上表命中的证据及关系仅作为仓库源码结构说明；当前配置的运行路径必须另找Compile内调用点和实现支撑。
- 未纳入编译不等于可删除；历史配置、外部项目和构建期间动态添加项尚未排除。
- 1436个文件是文件系统范围，1410个文件是此次编译前求值范围，不能用其中一个替代另一个。
- 模块仍维持部分复核，不因该核对提升完成状态。
