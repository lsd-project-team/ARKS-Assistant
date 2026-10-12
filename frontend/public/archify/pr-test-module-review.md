# PR 测试入口：实体编辑、后台采图与关闭保存

更新：2026-09-28。状态：部分复核；未运行程序或初始化设备。

## 流程摘要

Program.Main 先调用 HardwareRepositoryService.InitAllHardware，再打开 Form1。用户点击唯一按钮后 EditPr("test2") 查找视觉实体：存在则复用，不存在则创建并加入仓库，再设置 XldModelAlg。随后以实体及 false 参数创建 FrmPREditor 并 ShowDialog。编辑器仍启动后台刷新任务，循环按连续采图开关和相机条件抓图；关闭时清除循环标志、保存仓库并释放部分对象。它是独立手动测试入口，不是自动生产调度器。

## 按实际调用追踪

|顺序|调用与分支|源码|
|---|---|---|
|1|Main 先初始化硬件，再 Run(Form1)；未见该入口局部 catch 或初始化返回值判断|[Program:17](../../trunk/AKRS.Galaxy2.PR.Test/Program.cs#L17)|
|2|构造函数初始化界面；按钮 Click 调用 EditPr 固定名称 test2|[Form1:22](../../trunk/AKRS.Galaxy2.PR.Test/Form1.cs#L22)、[事件:41](../../trunk/AKRS.Galaxy2.PR.Test/Form1.Designer.cs#L41)|
|3|仓库单例首次通过 JsonFormatHelper 读取 PathConfig.TemplateConfigRepositoryPath；返回 null 才新建仓库|[GetInstance:43](../../trunk/AKRS.Galaxy2.PR/Resipository/VisionEntityRepository.cs#L43)|
|4|Find 按 GetName 等值取首项；测试入口先强转 PREntity，再判断 null。若同名对象不是该类型，强转可能先失败|[Find:136](../../trunk/AKRS.Galaxy2.PR/Resipository/VisionEntityRepository.cs#L136)、[EditPr:51](../../trunk/AKRS.Galaxy2.PR.Test/Form1.cs#L51)|
|5|不存在则 new PREntity → AddVisionEntity → SetAlgFlowType(XldModelAlg)。添加只改内存列表，且会移除同名首项再添加，不等于已经持久化|[新建分支:59](../../trunk/AKRS.Galaxy2.PR.Test/Form1.cs#L59)、[Add:75](../../trunk/AKRS.Galaxy2.PR/Resipository/VisionEntityRepository.cs#L75)|
|6|new FrmPREditor(entity,false) → ShowDialog；测试函数未检查对话框结果|[Form1:70](../../trunk/AKRS.Galaxy2.PR.Test/Form1.cs#L70)|
|7|非空实体走 RefreshInterface，再 Task.Run(RealTimeRefreshImg)；isStartGrab 参数在该构造函数未参与条件判断，不能把 false 解释为禁止后台采图任务|[构造:103](../../trunk/AKRS.Galaxy2.PR/Controls/FrmPREditor.cs#L103)|
|8|while(isGrab)，仅 TSContinuous.Checked 且 camera 非空时 SnapShot；非空图像克隆后刷新算法控件；正常一轮 Sleep(300)|[刷新循环:128](../../trunk/AKRS.Galaxy2.PR/Controls/FrmPREditor.cs#L128)|
|9|FormClosing 设置 isGrab=false、关闭连续开关、取算法对象、保存仓库、释放图像及控件；未见等待后台任务结束|[关闭:475](../../trunk/AKRS.Galaxy2.PR/Controls/FrmPREditor.cs#L475)、[绑定:1055](../../trunk/AKRS.Galaxy2.PR/Controls/FrmPREditor.designer.cs#L1055)|

## 文件、错误和完成边界

仓库 Save 调用 SaveGenericObject 写 PathConfig.TemplateConfigRepositoryPath；文件存在时删除旧备份再复制当前文件到 DeviceDirPath 下的备份TemplateConfigRepository.json。catch 中提交 Error 日志，方法没有返回成功标志，因此调用返回不证明保存成功；备份是保存后的文件复制，不应声称保留了更新前版本。见 [Save:109](../../trunk/AKRS.Galaxy2.PR/Resipository/VisionEntityRepository.cs#L109)。

刷新循环没有局部异常处理或重试，Task 未在构造函数保存/await；异常可能终止刷新。关闭标志与资源释放之间未见等待任务退出，潜在并发问题需运行验证，不能静态判为必现。窗口关闭也不等于底层硬件被关闭：已读关闭方法未调用硬件全局释放。

Form1 声明 StartupPath/Settings/RecipeParams/RecipeID 路径属性，但 EditPr 没有消费这些属性；实际仓库读取走 PathConfig，不能把这组属性当作已证实的模板存储位置。

## 依赖与生产关系

[项目:1055](../../trunk/AKRS.Galaxy2.PR.Test/AKRS.Galaxy2.PR.Test.csproj#L1055)引用仓库中的 AKRS.Galaxy2.PR 项目，故编辑器和实体仓库可继续源码追踪。[165–172行](../../trunk/AKRS.Galaxy2.PR.Test/AKRS.Galaxy2.PR.Test.csproj#L165)以 DLL 形式引用 LogicHardware、MachineSupport 等。trunk C# 中未找到 HardwareRepositoryService 类定义；InitAllHardware 内部的配置、设备动作、顺序及失败策略仍是外部边界。不能因为项目名含 Test 就认为启动无设备副作用。

本次证明测试程序复用 PR 实现，未证明生产程序调用这个测试窗体。生产视觉链仍以 [视觉运行专题](vision-runtime-module-review.md) 的调用证据为准。

## 尚未完成

- 编辑器全部按钮、相机选择、光源控制、RefreshInterface 后续和算法构造/保存内部仍需复核；本次仅闭合入口、代表采图和关闭路径。
- PathConfig 的有效根目录、JSON助手异常策略、配置兼容性以及硬件初始化内部仍待验证。
- 项目完整构建依赖、生成资源、模态关闭并发与实际文件输出未运行验收。
- 未新建独立测试图，避免将辅助入口混入生产主图；源码关系先登记台账。
