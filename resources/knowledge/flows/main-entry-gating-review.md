# 主程序入口与产品编辑门控复核

复核日期：2026-10-06。状态：`source-confirmed-partial`。证据登记见 [main-entry-gating-audit.json](main-entry-gating-audit.json)。本复核只读取当前 `trunk` 源码并记录哈希与行锚点，没有启动 `Program.Main`、`MainForm`、`Machine.Start`、硬件、VM 或设备。

## 入口顺序

`Program.Main` 在 `Program.cs:63` 标记 `[STAThread]`，于 `:68` 以 `Application.ProductName` 创建命名互斥体，并只在 `createNew` 分支进入初始化；重复打开分支在 `:260–265` 提示、等待后调用 `Environment.Exit(1)`。正常分支在 `:255–256` 构造 `MainForm` 并执行 `Application.Run(MainForm)`。

在线模式的 `Machine.GetInstance().InitPR()` 位于 `Program.cs:177`，随后 `HardwareRepositoryService.InitAllHardware(...)` 位于 `:180`。当前调用没有 `await`、`Wait` 或 `Result`。`Machine.Sustain.cs:116` 的 `InitPR` 返回 `Task`，并在 `:119` 使用 `Task.Run`，所以源码证据只证明 PR 初始化已排队，不能证明硬件初始化前 PR 已完成。

## 主窗体 Load 门

`MainForm_Load` 在 `MainForm.cs:234–238` 检查 `!AllAxisReset && !IsOffLineWork`；命中时禁用 `UcMainSystemTile` 并立即返回。通过该门后，才按顺序执行 `DataLoad`、`ChangeData`、参数初始化、两个压力表连接、灯光选择、`StartBackGroundThread`、测试目录准备和 Splash 关闭（`:240–270`）。因此窗体进入消息循环不等于主系统已完成回零或后台服务已启动。

## 编辑程式门控

`UcMainSystem.cs:368–390` 的 `BtEditProduct_ItemClick` 重新检查三项前置条件：设备正在工作、当前为 `DryCycle`、以及 `ProductConfiguration` 或 `RecipeName` 缺失。每项失败都弹出提示并返回。`UcMainSystem.UIState.cs:65`、`:181`、`:286` 分别记录运行、停止、暂停状态下 `BtEditProduct.Enabled` 的值：运行和暂停为 `false`，停止为 `true`。这说明按钮状态与点击处理器形成双层门控，但尚未覆盖权限层、所有事件来源或并发竞态。

## 两个启动入口的差异

普通启动 `UcMainSystem.cs:699–735` 在 `Machine.Start()` 前调用 `CloseAllDockPanel()`，会遍历并关闭当前 DockPanel。生产启动 `UcMainSystem.Production.cs:68–110` 只通过 `GetDockPanel("ucGuidMove")` 找到并关闭方向盘所在面板，然后调用 `Machine.Start()`；它没有调用 `CloseAllDockPanel()`。两个入口都在异常时调用 `Machine.Stop()`，并在 `finally` 恢复控件可用状态。

## 范围与后续

- 当前结论绑定审计脚本记录的源文件 SHA-256 和行号；源码漂移时应重新运行 `node .archify-work/register-main-entry-gating-audit.cjs`。
- 这组证据没有证明 `InitPR`、VM、硬件、权限服务或生产任务的运行时成功，也没有替代在线设备验收。
- 后续应继续核对权限实现、按钮事件路由、异步 PR 完成契约和启动异常后的资源回收。

## 可点击源码证据

- [Program.cs:63–70](../../trunk/AKRS.ZX2200/Program.cs#L63)
- [Program.cs:173–180](../../trunk/AKRS.ZX2200/Program.cs#L173)
- [Program.cs:255–269](../../trunk/AKRS.ZX2200/Program.cs#L255)
- [MainForm.cs:232–270](../../trunk/AKRS.ZX2200/Main/Controls/MainForm.cs#L232)
- [UcMainSystem.cs:368–390](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L368)
- [UcMainSystem.UIState.cs:34–65](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs#L34)
- [UcMainSystem.UIState.cs:150–181](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs#L150)
- [UcMainSystem.UIState.cs:256–286](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs#L256)
- [UcMainSystem.cs:699–751](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L699)
- [UcMainSystem.Production.cs:68–110](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L68)
- [Machine.Sustain.cs:112–121](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Sustain.cs#L112)
