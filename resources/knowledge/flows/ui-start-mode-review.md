# 原UI启动、工作模式与单步处理接入真实供晶Task

2026-09-30：262项受控断言通过。两个完整原启动处理方法、Dock查找/关闭、模式切换、单步和下一步处理，接入已验证的原准备帮助方法、Machine.Start、TransportDomain.StartTask、供晶Start/搜索/消费者及完整Stop。组合编译含80原方法、28属性、2枚举、4字段，共114原片段；这是编译范围，不能解释为所有方法与分支均执行。51份测试/依赖文件、23种信号初始化契约和5条Designer事件绑定可按来源哈希核验。

本轮直接执行原UI处理方法，控件、Dock集合、对话框及CheckedChanged派发为明确替身。不是原生WinForms/DevExpress事件可达性或现场验收；生产源码未修改。

## UI catch使启动失败进入原Stop

点胶Start、节点排序、BondStart、助焊、翻转或真空包装同步抛错时，两个原UI启动方法均进入catch，调用完整原Machine.Stop，再提示“启动失败”，最后恢复Enabled。真实供晶Task已经创建，本轮等待它在Stop状态下退出并Join工作线程，没有发允许取料。准备清理、日志、容量或环境依赖抛错时，也走同一UI catch，但供晶Task尚未创建。

这是[直接Machine.Start组合](normal-start-integration-review.md)的调用者边界：直接调用Machine.Start的下游异常会留下真实供晶Task与Working；调用原UI处理方法时，其catch执行Stop改变了结果。Stop方法本身没有Join，测试中的等待/Join是验证与资源收尾措施，不能解释为原按钮等待线程结束。

输送载具检查失败在内层调用Stop然后正常返回时，供晶Start仍重新写Working并创建真实Task；UI catch不会执行。发送新需料信号后仍能发允许取料。输送Init/MapMaterial异常被内层捕获，或供晶地图创建异常被供晶Start捕获并正常返回时，同样绕过UI catch；后者不创建供晶Task，但后续Bond调用仍发生且Working保留。

## 异常处理自身的失败

原Production处理方法先在try外写Enabled=false；该属性替身在此抛错时，不进入catch/finally，不调用Stop或恢复Enabled。顶部处理方法在try内禁用界面，相同故障会进入catch并恢复Enabled。此处是明确注入的属性故障，不声称现场控件会必然抛错。

UI catch中的Stop先执行SetState(Stop)，随后才清弹窗、设置报警、退出单步、复位需料和关闭真空。在原状态写入之前注入日志构造故障时，异常穿透catch、仍执行finally，真实供晶Task保持Working。若清弹窗或报警步骤抛错，Stop状态已写入，实际供晶Task仍会退出；错误提示可能尚未执行。错误提示自己抛错时，Stop已完成，finally仍恢复Enabled。

finally的Enabled=true替身抛错不会再次进入同一个catch。成功启动后发生该故障时，真实供晶Task继续运行且Working保留；取消后发生时没有创建任务。已捕获原启动异常并执行Stop后，finally故障会成为外层收到的异常，不能把原异常成功处理解释为最终按钮调用成功。

## 取消、Dock及模式

程式提示开启且返回Cancel时，经finally恢复Enabled；不关闭Dock、不退出单步、不执行准备清理或创建任务。提示关闭时，即使替身预置Cancel也不会读取它，仍进入正常启动。

Production按钮通过原GetDockPanel递归查找第一个包含ucGuidMove的面板，只关闭该面板；顶部按钮调用原CloseAllDockPanel，关闭全部面板。缺失目标返回null，重复目标取首个。CloseAll先ToList建立快照；测试让第一个Close替身清空现场集合，仍会依快照关闭第二个面板。实际控件关闭是否改变集合仍依现场SDK，测试只证明原遍历方式与显式集合行为组合。

五种具名工作模式及两个未知枚举值，均通过两个原UI按钮启动。原IsOffLineWork、IsDryCycle、IsCompensateWork、IsNormalWork从同一个MachineWorkMode派生。补偿模式跳过输送/供晶等任务而保留Bond调用；DryCycle走输送StartDryRun替身；离线、调试与未知模式在本启动包装中进入正常输送分支。所有非补偿场景均由实际供晶Task接收新需料并完成原消费者发许可。

原模式变更处理没有Stop/Pause/Working门控，直接拆箱EditValue赋枚举。三种状态下均可改模式；null或错误装箱类型抛错并保留旧值，装箱的int可按原枚举强制转换。该结果不证明界面下拉框会生成所有异常值，也不证明其他背景逻辑不会限制控件。

## 单步信号与派发契约

原Start先写IsSingleStepWork=false，再写切换控件Checked=false。原CheckedChanged回调在关闭单步时先设置真实System2SingleStepSignal，再修改标志和下一步按钮。原ResetMachineSignal不清除此事件，因此同步回调产生的事件可保留到准备完成之后。

两种按钮×初始Checked值×静默/值变化同步回调/始终同步回调，共12种显式控件契约验证其差异。静默或相同值且不派发回调时，Start仍清除模式，但下一步按钮的既有Enabled可保留；有回调时按钮更新并设置真实事件。本轮没有把任何一种替身契约认作真实DevExpress保证。

原下一步处理仅在单步标志为true时发事件，System2选中发System2，其余系统值（含未知枚举）发System1。关闭单步时真实事件若已释放，直接回调会在模式/按钮修改之前抛错；由Start间接触发时，Start前面的模式/Checked写入已发生，按钮旧值保留，再进入UI catch和Stop。不会回滚已发生的控件或模式变化。

## 复现与剩余项

`node scripts/test-ui-start-mode.cjs`执行262项唯一断言；`node scripts/build-ui-start-mode-audit.cjs --check`核验51份来源、114片段、23信号契约及5条Designer绑定；两项纳入统一回归。真实事件、原供晶LongRunning Task和实际消费者均运行；测试显式Stop并结束工作线程。多数成功矩阵以IsSearchOne=true替身控制执行一轮并由原Stop结束，另以IsSearchOne=false分别通过两个原UI按钮创建同一真实供晶Task，连续处理两个请求、两次发许可且保持Working，最后显式Stop/Join；不会把一轮收尾方式当作生产默认配置。

实际池生命周期、CleanFile清理、容量/域/加热/日志目标、安全移动、完整TransportTask.Start及其他生产器、配置/地图/点计算/视觉/标定/持久化/SDK仍为替身或待验收。原生UI线程派发和控件生命周期、现场DLL/配置、原项目构建与设备验收继续保留。全部29源组仍为partial，本专题不提高项目覆盖比例。

本轮回归修复：既有S2安全门暂停（37项）和输送暂停（32项）的事件消费断言存在观察同步不足，分别等待原任务相应阶段并检查真实事件句柄，避免用并发公开State推断事件消费；两项专项各连续三次通过。S1单步门控（33项）同类断言也改查真实句柄。原断言数量和生产方法均保留，失败日志保存。见[S2](s2-door-pause-review.md)、[输送](transport-pause-review.md)和[单步](single-step-door-review.md)观测修正；不扩大设备验收范围。
