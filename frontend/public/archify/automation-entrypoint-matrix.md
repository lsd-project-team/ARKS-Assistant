# 自动化入口对照：生产、扫描、输送、单步与恢复

2026-09-28。基于trunk的静态调用复核；状态进入Working不等于完整生产调度已经启动。未运行设备或UI。

## 入口与执行顺序

|入口|入口检查与执行顺序|是否调用Machine.Start|结束或限制|
|---|---|---|---|
|普通启动BtStart|可选配方确认 → CloseAllDockPanel → 退出单步 → Start|是|异常Stop，finally恢复Enabled；见production-edit-gating-review.md|
|Production的BarBtStart|可选配方确认 → 尝试关闭ucGuidMove → 退出单步 → Start|是|不请求关闭全部面板；见production-edit-gating-review.md|
|继续按钮（两个按钮共用）|BtContinue_ItemClick → Continue → 安全门配置分支 → SetState(Working)|否|无门配置直接改状态；有门且未关闭只提示；有门且已关闭设置两个IsFirstDispense标志后改状态|
|Shift+F4（窗口KeyDown）|IsVisionScanIsReady → 检查visionTask.Status==Running → 创建新Task(VisionScan)并Start|否|扫描函数自行设置Working；不是Start的完整前置检查和任务调度|
|Shift+F1（窗口KeyDown）|SubstrateIndex → 四个Task.Run先全部发起，再等待|否|并行输送子任务，不是四段串行执行；细分控制器仍有自身条件|
|F9（窗口KeyDown）|单步开启时按CurrentMachineSystem发S2或S1信号|否|是释放单步等待，不新建任务|
|Shift+F9（窗口KeyDown）|先经过F9发送分支，再在Shift分支切换单步开关|否|若原本单步开启，本处理器代码顺序为先发送、后关闭；实际按键路由待验证|
|全局F9 / Shift+F9|RegisterHotKey → WM_HOTKEY → 发S2信号 / 切换单步开关|否|全局发送固定S2，不按当前系统选择；RegisterHotKey返回值未检查|

## Shift+F4扫描的真实步骤

1. 父窗体KeyPreview=true，订阅UcMainSystem_KeyDown；要求ModifierKeys恰好等于Shift才进入F4分支，不应画成任意F4或全局扫描热键。
2. 前提：MachineInitSuccess为true；非Working且非Pause；当前TU存在；IsAssistantSucceed为true。提示文字虽然说状态不是Stop，但实际条件并非严格IsStop。
3. 重入检查只排除TaskStatus.Running；首次调用还会先创建一个未Start的Task，再重新赋值为新Task并启动。未见本方法互斥锁、等待旧任务或检查全部未终止状态。可能竞态需运行验证，不能宣称已经重入。
4. VisionScan先SetState(Working)，再次获取TU。系统2：设置偏移；非Divide时定位TU；再ObjectVision(TU)，然后逐Substrate、Module、BondPosition调用ObjectVision。各层对象自身Disable时跳过该对象定位，但循环仍继续遍历后代，不是整棵子树自动剪枝。
5. 系统1：设置偏移；非Divide时先MatterVision(TU)；按IsTuInDispense1选后段或前段索引，前段还执行System1MoveDistance；非Divide随后用全部基板索引覆盖列表；再按基板→模组→焊位定位，对象自身Disable则跳过该对象定位。
6. 两条分支在多处WaitStart检查：Stop返回false，Pause循环等待；返回false即离开扫描方法，不执行末尾完成提示。正常遍历结束才Stop并提示扫描完成。不能把提前退出或异常统一画到成功完成节点。
7. 扫描方法没有局部try/catch/finally；抛错后的任务观察、清理、机器状态恢复不能由此保证。视觉方法的结果在这些调用处未显式判定，完成提示证明走到末尾，不证明所有识别成功。

## 信号与并发边界

- WaitStart的暂停while退出后直接return true，没有第二次Stop检查；状态变化时序需要隔离验证，不能仅凭方法名承诺原子暂停/停止屏障。
- Continue不重新创建已经结束的visionTask或生产任务；恢复状态与任务重新启动是两件事。
- 快捷输送外层未调用IsVisionScanIsReady、Machine.Start或CloseAllDockPanel；不能据外层缺检查就断言底层没有互锁。
- 窗口KeyDown与全局WM_HOTKEY是两条事件入口；是否同一次按键双重触发、按键被哪条路径消费，需真实Windows消息验证。

## 待工程师验证

- Shift+F4在WaitingToRun窗口重复触发、扫描抛错、扫描中Stop/Pause/Continue。
- Disabled父对象下仍有启用子对象时的实际扫描意图，及系统1非分段时System1MoveDistance的影响。
- Shift+F1四任务异常、Wait传播与其他任务继续运行的行为。
- S1选中时全局F9、窗口F9、Shift+F9的实际信号接收路径和全局热键注册失败。
- 扫描/快捷输送对已打开编程窗口的影响；本轮只证明调用路径差异，未证明设备风险发生。


## 精确源码证据
- entry-keybind: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:235–243](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L235)
- entry-keydown: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.ShortcutKeys.cs:45–120](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.ShortcutKeys.cs#L45)
- entry-scan-ready: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.ShortcutKeys.cs:282–311](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.ShortcutKeys.cs#L282)
- entry-scan-s2: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.ShortcutKeys.cs:126–196](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.ShortcutKeys.cs#L126)
- entry-scan-s1: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.ShortcutKeys.cs:197–276](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.ShortcutKeys.cs#L197)
- entry-index: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.ShortcutKeys.cs:316–331](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.ShortcutKeys.cs#L316)
- entry-hotregister: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.HotKeyManage.cs:68–86](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.HotKeyManage.cs#L68)
- entry-hotproc: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.HotKeyManage.cs:92–120](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.HotKeyManage.cs#L92)
- entry-continue-ui: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:846–849](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L846)
- entry-continue-core: [trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:323–342](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L323)
- entry-continue-bind1: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.designer.cs:731–736](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.designer.cs#L731)
- entry-continue-bind2: [trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.designer.cs:2829–2834](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.designer.cs#L2829)
- entry-waitstart: [trunk/AKRS.Galaxy2.Machine/Models/Signal.cs:202–228](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L202)
