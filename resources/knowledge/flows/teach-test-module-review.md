# 示教测试：类库入口与输送调整导航

更新：2026-09-28。部分复核；未执行程序或设备动作。

## 流程摘要与入口前提

项目声明 OutputType=Library、StartupObject 为空。因此 Program.Main 中 Application.Run(new FrmTUAdjustTeachTest()) 仅证明代码存在，不能当作默认可执行启动或已接入生产。若该窗体被实例化，构造函数建立两个步骤，显示首步骤说明并隐藏 Back/Done；用户 Next 前进至第二步，Back 返回，Done 或 Cancel 关闭。当前读取的点位采集、PR选择、坐标转换和配置赋值均为注释，不属于有效执行步骤。

入口证据：[项目:8](../../trunk/AKRS.Galaxy2.TeachTest/AKRS.Galaxy2.TeachTest.csproj#L8)、[启动对象:39](../../trunk/AKRS.Galaxy2.TeachTest/AKRS.Galaxy2.TeachTest.csproj#L39)、[Program:15](../../trunk/AKRS.Galaxy2.TeachTest/Program.cs#L15)。trunk 中该测试窗体的显式名称命中局限于自身和 Program；对 ZX2200 C#/csproj 的名称搜索未发现接入。这不是不存在反射调用的证明。

## 有效步骤和分支

|阶段|实际执行|源码|
|---|---|---|
|实例化|InitializeComponent → InitControl → 隐藏 Back/Done → 选中 TbiAdjust1；stepIndex 初始0、stepCount为2|[字段与构造:16–78](../../trunk/AKRS.Galaxy2.TeachTest/tests/FrmTUAdjustTeachTest.cs#L16)|
|建立步骤|两项 AssistantConfig：第一项 Next 选中 TbiAdjust2，Done 关闭；第二项 Back 选中 TbiAdjust1，Done 关闭，Next 回调为空|[InitControl:88](../../trunk/AKRS.Galaxy2.TeachTest/tests/FrmTUAdjustTeachTest.cs#L88)|
|Next|取当前列表项 → 调用 NextAction → stepIndex++ → SetUiControl|[213](../../trunk/AKRS.Galaxy2.TeachTest/tests/FrmTUAdjustTeachTest.cs#L213)|
|Back|取当前列表项 → 调用 BackAction → stepIndex-- → SetUiControl|[226](../../trunk/AKRS.Galaxy2.TeachTest/tests/FrmTUAdjustTeachTest.cs#L226)|
|UI刷新|读取显示标志，更新 Back/Next/Done、说明文本及说明可见性|[179](../../trunk/AKRS.Galaxy2.TeachTest/tests/FrmTUAdjustTeachTest.cs#L179)|
|Done|调用当前 DoneAction 后 stepIndex++；两项 DoneAction 的有效动作均是 Close|[239](../../trunk/AKRS.Galaxy2.TeachTest/tests/FrmTUAdjustTeachTest.cs#L239)|
|Cancel|直接 Close，无独立设备停止或回滚调用|[251](../../trunk/AKRS.Galaxy2.TeachTest/tests/FrmTUAdjustTeachTest.cs#L251)|

四按钮 Click 绑定见 [Designer:185](../../trunk/AKRS.Galaxy2.TeachTest/tests/FrmTUAdjustTeachTest.Designer.cs#L185)、[198](../../trunk/AKRS.Galaxy2.TeachTest/tests/FrmTUAdjustTeachTest.Designer.cs#L198)、[212](../../trunk/AKRS.Galaxy2.TeachTest/tests/FrmTUAdjustTeachTest.Designer.cs#L212)、[225](../../trunk/AKRS.Galaxy2.TeachTest/tests/FrmTUAdjustTeachTest.Designer.cs#L225)。

## 状态细节：不能仅靠标签画图

- 两个配置项的 Index 值为2和3，但处理函数按 stepIndex=0/1 取列表项，不用 Index 字段寻址；不能据2/3编造前置步骤。AssistantConfig 是显示标志、描述与三个 Action 的容器，见 [定义:28](../../trunk/AKRS.Galaxy2.TeachTest/AssistantConfig.cs#L28)、[赋值:87](../../trunk/AKRS.Galaxy2.TeachTest/AssistantConfig.cs#L87)。
- 第一项 IsShowDone=true，但构造函数强制隐藏 Done；从第二步返回后 SetUiControl 按第一项配置将 Done 显示。因此首屏与返回首步的按钮状态不同。
- 一点定位条件、读取坐标的 ChooseSystem、PR选择与定位配置赋值均被注释。界面文案包含 Teach-in/Move，不证明发生移动、测量或示教保存。
- 构造流程仅设置首步说明，不调用 SetUiControl(0)，不能用统一刷新规则替代真实初始状态。

## 输入输出、异常与外部依赖

该已读路径输入为用户导航按钮和内置步骤配置；输出是选中页签、说明、按钮可见性和窗口关闭。未见有效文件/数据库写入、消息队列、网络API、后台调度或硬件命令。项目仍声明 Infrastructure DLL 与 DevExpress 等依赖，见 [项目:41](../../trunk/AKRS.Galaxy2.TeachTest/AKRS.Galaxy2.TeachTest.csproj#L41)；声明不等于它们在此执行设备动作。

处理函数无局部 catch、重试、Action空值或索引范围检查；可见性是常规导航限制，而非方法级边界保护。没有动态测试，不宣称越界或异常必现。Done关闭不是点位数据已保存的完成状态，Cancel也不是生产设备的安全停止。

## 未完成范围

- 同项目还有 ModuleAdjust、ModulePosition、SubstrateAdjust、SubstratePosition、TUPosition 五类测试窗体，已在 Compile 项中定位，但其完整步骤未纳入本次复核。
- Properties、生成资源和 Designer 全部布局未语义验收；当前仅核实事件绑定。
- 实际加载方式、MSBuild条件求值、构建和导航行为未运行验收。
- 生产示教实现必须另以真实调用链核实，不能借这些测试占位代码补齐自动化图。
