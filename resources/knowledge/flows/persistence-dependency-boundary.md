# 配置持久化：外部依赖与证据边界

本文件由 scripts/build-persistence-boundary.cjs 生成。详解见 [失败路径复核](persistence-failure-boundary-review.md)；随仓库DLL的读取、单例与保存方法已另行[提取精确IL](persistence-save-contract-review.md)，后台线程服务见[调度与错误边界](background-task-contract-review.md)。

## 能证明与不能证明

本检查只证明本地文件摘要、词法声明搜索和已登记源码绑定未变化；另附的静态IL快照证明随仓库DLL方法体，不证明实际加载版本、磁盘运行行为或保存可靠性。DLL 随附 config 的存在不证明主程序采用其中配置。

## 本地依赖

|路径|存在|字节数|SHA-256|
|---|---|---:|---|
|trunk/AKRS.ZX2200/libs/AKRS.Galaxy2.Infrastructure.dll|true|135680|f75452133ba809255061210eafc861b576c0fe8b553a983575934fe3d19892eb|
|trunk/AKRS.ZX2200/libs/AKRS.Galaxy2.Infrastructure.pdb|true|474624|ef0dbb069e57ccbde57e1316228f5774d57b18d8ca552b75716505c87e6ddc64|
|trunk/AKRS.ZX2200/libs/AKRS.Galaxy2.Infrastructure.dll.config|true|759|13f3847e11b9076456059fd601bfccfbd004aa1d14c5c8e2478666ccb37901c2|
|trunk/AKRS.ZX2200/libs/AKRS.Galaxy2.BackgroundWorkThread.dll|true|11264|620cafdd6b50a6dccd42886307aa0c34e6e779e731c233f68dabc2331db19b77|
|trunk/AKRS.ZX2200/AKRS.ZX2200.csproj|true|237379|50509da43e7a02d8f59a04ce017ca65b56aa9b8e5116d603a3fbe076e1b2d3a5|
|trunk/AKRS.Galaxy2.MachineSupport/AKRS.Galaxy2.MachineSupport.csproj|true|3504|e20e2c7ff42a9c0566b2c6a3bf15da1698d6500ec395f6e07679d9a04cf2858b|

## 源码定义搜索

扫描 1436 个 C# 文件，排除 bin/obj/.git。词法结果不是语义解析。
- Singleton：0 个声明候选。在该扫描规则内未找到定义；不得补写内部行为。
- JsonFormatHelper：0 个声明候选。在该扫描规则内未找到定义；不得补写内部行为。
- BackgroundThreadService：0 个声明候选。在该扫描规则内未找到定义；不得补写内部行为。

## 已登记的调用方源码

- module-AKRS-Galaxy2-MachineSupport-MachineConfigContext: [trunk/AKRS.Galaxy2.MachineSupport/Config/MachineConfigContext.cs:1–87](../../trunk/AKRS.Galaxy2.MachineSupport/Config/MachineConfigContext.cs#L1)
- recipe-transport-init: [trunk/AKRS.ZX2200/TransportSystem/Models/TransportProgram.cs:63–75](../../trunk/AKRS.ZX2200/TransportSystem/Models/TransportProgram.cs#L63)
- binlayer-program: [trunk/AKRS.ZX2200/TransportSystem/Models/TransportProgram.cs:20–75](../../trunk/AKRS.ZX2200/TransportSystem/Models/TransportProgram.cs#L20)
- binconfig-base: [trunk/AKRS.ZX2200/Infrastructure/Models/BaseModels/BaseSettingRepository.cs:45–127](../../trunk/AKRS.ZX2200/Infrastructure/Models/BaseModels/BaseSettingRepository.cs#L45)
- editgate-refresh: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:271–303](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L271)

## 未解决的契约

- Actual loaded assembly/version and type ownership
- Bundled JSON read/null handling is captured in static IL; actual loaded helper and runtime error behavior remain unverified
- Filesystem guarantees, failed-write recovery and inter-process locking at runtime
- Bundled Singleton creation/GetInstance and Save are captured in static IL; actual loaded implementation remains unverified
- Bundled BackgroundThreadService scheduling/error method bodies are captured in static IL; actual loaded implementation, UI dispatch and runtime exceptions remain unverified

## 验证命令

`node scripts/build-persistence-boundary.cjs --check`

依赖或源码改变会使旧基准失效；须人工确认影响后才能重建基准，不能以重建代替语义复核。
