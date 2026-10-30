# 启动入口异常、Stop清理与配方界面保护

日期：2026-09-29。43项检查通过。纳入39份原成员片段（包括枚举、原构造、方法），原SystemProcess/ActionNodeMessage完整类和项目实际Singleton/JSON DLL；在上轮真实文件加载到启动排序脚手架上，新增两个原启动按钮、原Stop、原配方加载事件及六个原UI状态方法。生产源码未修改。

## 主要结论

两个启动按钮捕获Start抛出的异常后，都会先调用Stop再显示启动失败提示，finally恢复Enabled。因此上一轮直接调用Start后状态留在Working的结果，不可不加限定地套到这两个界面入口。Start正常返回（包括门控返回false）不会触发该catch。

原Stop并非不可失败：清消息框、报警、信号复位、要料输出或顶针真空任一替身抛异常，本测试中的停止状态已写入，剩余清理和启动失败提示被跳过；外部观察到的是Stop依赖异常，finally仍恢复主界面。真实线程是否结束、轴是否停稳，未由这些状态写入和替身调用证明。

原ChangeUiByState在普通Stop刷新中启用加载配方按钮。只有“状态Stop、主界面Enabled=false、提示文本恰为设备正在停止，请稍后”三条件同时满足，才先检查IsAllowTaskClosed。启动catch的finally把主界面设回Enabled=true，本受控样本随后刷新不会进入这条等待分支。

## 启动按钮场景（每个入口15项，共30项）

- 确认取消：恢复UI，不清单步模式，不调用Start或Stop。
- 正常确认：通过实际配置加载后的原启动和排序，两个入口最终恢复UI。工具栏关闭所有dock；Production只尝试关闭ucGuidMove。
- 准备阶段返回false：单步模式已清除，但不调用Stop，也不显示catch中的启动失败提示。
- dock操作抛异常：在调用Machine.Start前便进入原Stop。
- Wafer.Start替身抛异常：已调用Transport.Start；随后原Stop的清理完整执行，提示启动失败；Bond.Start未到达。
- Stop五个依赖逐点失败：异常向外传播并替代原启动异常，启动失败提示不执行，finally仍执行。
- Stop在状态之后失败，再刷新普通Stop界面：即使替身报告任务未关闭，也未查询该条件，配方按钮被启用。
- 错误提示自身异常：发生在Stop清理后，finally仍恢复UI。
- finally的Enabled=true setter异常：新异常传播，测试控件保持禁用；这是人为注入属性异常，非已证明的DevExpress现场行为。
- 最初Enabled=false setter异常：Production这句在try外，不进入Stop/finally；工具栏这句在try内，走Stop/finally。

另1项验证Production找不到ucGuidMove时仍可正常调用Start。5份代表调用轨迹保存在测试收据：两个入口各一份启动失败正常清理、一份Stop清理再失败，以及直接调用禁用配方事件的轨迹。

## 配方保护及UI刷新（12项）

1. 原运行、暂停刷新禁用加载配方按钮；停止刷新重新启用（3项）。正常用户点击仍受实际控件Enabled约束，未验证能通过UI点击被禁用按钮。
2. 测试直接调用原BarBtLoad_ItemClick，即使状态Working且对应按钮已禁用，仍执行保存与重载替身。原事件本身不检查工作状态或按钮Enabled（1项）。这是入口函数的行为边界，不是声称真实用户点击可以绕过控件。
3. 在ShowDialog替身回调中将状态由Stop改为Working，返回后事件未重查状态便保存和重载（1项）。仅证明该受控交错，尚未证明实际UI/任务存在相同交错。
4. 模态对话框Cancel保持旧ID，跳过显式Dispose，与已知入口测试一致（1项）；不据此宣称资源泄漏。
5. 停止提示特殊分支确实等待任务关闭，并在关闭后解除禁用、隐藏提示（2项）。普通Enabled=true的Stop刷新不查询任务关闭（1项）。
6. 原方法先更新记忆的machineState再写按钮；人为令BarBtLoad.Enabled setter失败会留下部分按钮已更新，同状态再次刷新不重试；经Stop→Working转换才重新应用（3项）。真实控件是否可能如此失败待原生UI验证。

## 与前一轮非正批次结论的区别

本轮故障样本使用正批次1及Wafer.Start等依赖异常，没有执行危险循环。两个入口能catch异常，不意味着能catch无限循环或自动恢复卡死。上轮MathHelper安全代理抛异常属于测试保护；不能据此把非正批次在实际程序里的表现描述为会被按钮catch并Stop。

## 原入口绑定与刷新调度

Designer把BarBtStart绑定BarItemStart_ItemClick、BtStart绑定BtStart_ItemClick、BarBtLoad绑定BarBtLoad_ItemClick；审计绑定具体行与源码哈希。UcMainSystem_Load通过BackgroundThreadService.RegisterTask注册刷新，在BeginInvoke回调内调用ChangeUiByState，然后ChangeUiByConfiguration及AutoLogOut。此调度路径仅静态确认，未执行真实消息循环或后台调度；外层加载事件catch不能被当成已验证能捕获随后异步委托异常。

## 原源码定位

| 文件 | 原成员 | 行号 |
|---|---|---|
| trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs | private void BtStart_ItemClick(object sender, ItemClickEventArgs e) | 699–736 |
| trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs | private void BarItemStart_ItemClick(object sender, ItemClickEventArgs e) | 68–110 |
| trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs | private void BarBtLoad_ItemClick(object sender, ItemClickEventArgs e) | 804–839 |
| trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs | public void Stop() | 347–378 |
| trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs | private void ChangeRunningUiState() | 34–145 |
| trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs | private void ChangePauseUiState() | 256–368 |
| trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs | private void ChangeStopUiState() | 150–251 |
| trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs | public void ChangeUiByState() | 382–420 |
| trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs | private void ChangeSingleStepUiState() | 373–377 |
| trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs | private void ChangeContinuousFeedingUiState() | 425–428 |

## 复现与边界

- node scripts/test-startup-entry.cjs
- node scripts/build-startup-entry-audit.cjs --check
- [43项测试与调用轨迹](startup-entry-test.json)；[源码/报告审计](startup-entry-audit.json)。
- UI控件、dock关闭、状态setter、报警、信号、物理I/O、任务Start内部、配方Save/ReLoad均为替身。没有重新执行完整视觉重载、真实切配方文件写入或生产线程终止。完整Stop状态/日志及真实信号另见[machine-stop-signal-review.md](machine-stop-signal-review.md)，不能无条件合并成现场端到端证明。
- 当前可确认界面层正常禁用和方法层缺少重查之间的区别。真实调用源、异步调度/消息循环、切配方与任务交错仍需验证；完整构建和设备闭环未验收，29个模块组继续部分复核。

后续已补[真实Task关闭门控](task-closure-review.md)：155项检查执行原IsAllowTaskClosed，覆盖16字段×8种真实Task状态，并接回启动和UI消费者。确认仅Running阻断；原Stop返回后受控Task仍Running，普通停止UI可启用配方按钮。任务体、原生UI和设备仍未验收。
