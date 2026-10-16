# 自动生产与编程编辑入口门控

2026-09-28。源码静态复核；未执行UI或设备。

## 已确认的执行顺序

1. 主界面 BtEditProduct_ItemClick 先用 IsWorking 拦截，再拒绝 DryCycle，最后检查 ProductConfiguration 与 RecipeName；通过后 ShowPanel 打开或复用编程窗口。IsWorking 仅判断 MachineState==Working。
2. ChangeRunningUiState 与 ChangePauseUiState 均将 BtEditProduct.Enabled=false；ChangeStopUiState 设为true。因此不能由点击处理器只检查Working，推断暂停时按钮可用。
3. 正常 BtStart_ItemClick 先禁用主控件，可选配方确认取消则返回；确认后 CloseAllDockPanel，退出单步，再调用 Machine.Start。异常时调用Stop并提示，finally恢复主控件Enabled。CloseAllDockPanel遍历面板快照调用Close，不证明第三方关闭不能取消或总能成功。
4. 编程树 Input/Output 依 LoadConfiguration==LoaderBin 创建 UcLoderSetting/UcUnloaderSetting，否则创建普通输入/输出控件；并非每种硬件配置都会进入料仓设置。

## 本轮仍待核查

本报告已核实状态刷新注册和两个按钮启动入口；补充快捷扫描、输送、单步与恢复见[自动化入口对照](automation-entrypoint-matrix.md)。剩余：权限叠加、关闭事件取消/异常、事件路由及运行中状态切换竞态。入口UI门控不等于持久化层事务或并发锁。

## 状态刷新与入口差异

- UcMainSystem_Load 注册后台任务，回调使用 BeginInvoke，先 ChangeUiByState、后 ChangeUiByConfiguration、再 AutoLogOut。RegisterTask 的尾参数为1、1000、false；本轮未找到其实现，不将它们直接解释成可保证的刷新周期。
- ChangeUiByState 仅在状态与缓存不同时选择 Working/Pause/Stop 的界面更新方法；停止提示存在且任务未关闭时提前return。这是异步界面刷新，不是与机器状态原子同步的编辑锁。
- Production按钮实际绑定 BarItemStart_ItemClick。它没有调用 CloseAllDockPanel，而是查找 ucGuidMove，只在找到时调用Close；随后退出单步并Start。不能将普通启动的全部关窗步骤套用到该入口。
- GuideMoveOpen/Close使用 ucGuideMove，Production查找使用 ucGuidMove，字符串不一致；GetDockPanel使用Controls.Find。此处登记为待验证的名称匹配问题，尚未证明实际窗口残留。
- ClosedPanel事件处理器移除并Dispose面板。第三方Close事件取消、浮动窗口归属、模态仓库窗口与生产启动的交互仍未运行验证。

## 工程师接手验收清单

|场景|源码预期 / 需要观察|状态|
|---|---|---|
|Working点击编辑|按钮在状态刷新后禁用；处理器还会直接拦截Working|静态已核实，UI未测试|
|Pause编辑|状态分发禁用按钮；点击处理器自身不拦截Pause|静态已核实，事件竞态未测试|
|Stop打开编程后普通启动|先请求关闭所有DockPanel，再Start|静态已核实，Close成功未保证|
|Stop打开编程后Production启动|只尝试关闭指定方向盘；编程面板后续状态待观察|静态差异已核实，运行未测试|
|启动确认取消/异常|取消退出且finally重新启用；异常调用Stop|静态已核实，异常注入未做|
|JSON保存与运行并发|入口门控不能替代文件事务/锁|外部库与并发验证待补|

## 精确源码入口

- editgate-entry: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:368–401](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L368)
- editgate-predicate: [trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.StateRelated.cs:25–46](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.StateRelated.cs#L25)
- editgate-refresh: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:271–303](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L271)
- editgate-dispatch: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs:382–420](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs#L382)
- editgate-running: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs:60–70](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs#L60)
- editgate-stop: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs:177–187](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs#L177)
- editgate-pause: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs:282–292](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs#L282)
- editgate-start: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:699–751](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L699)
- editgate-production: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs:68–110](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L68)
- editgate-panel: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:408–456](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L408)
- editgate-closed: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:464–468](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L464)
- editgate-editor: [trunk/AKRS.ZX2200/Infrastructure/Controls/Feature/EditProgram/UcEditProductProgram/UcEditProductProgramming.cs:490–550](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Feature/EditProgram/UcEditProductProgram/UcEditProductProgramming.cs#L490)
- editgate-bind-edit: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.designer.cs:560–565](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.designer.cs#L560)
- editgate-bind-production: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.designer.cs:700–706](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.designer.cs#L700)
- editgate-guide: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcmainSystem.Action.cs:190–225](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcmainSystem.Action.cs#L190)
