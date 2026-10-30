# 偏移标定：双入口、启动与退出边界

范围：同一个 `OnlyBondToCameraOffsetCaib` 方法的两个具名调用入口及其局部生命周期。源码静态复核，不代表整机互锁或真实并发执行验收。

## 工作流摘要

主界面“Bond偏移”，或者“测试辅助功能”打开的 FrmStartup → 工具准备确认 → OK 时获取 CalibrateTask 实例并提交 Task.Run → 内层标定 → 外层结果显示。取消确认只跳过本次提交；本地入口未持有任务句柄、传入取消令牌或等待任务完成。

## 入口与源码

| 入口 | 绑定与实际调用 | 边界 |
| --- | --- | --- |
| 主界面 Bond偏移 | [Designer:968–974](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.designer.cs#L968) → [Diagnosis:119–131](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Diagnosis.cs#L119) | OK 后 Task.Run，返回的 Task 未保存 |
| 测试辅助窗口 | [主界面绑定:931–937](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.designer.cs#L931) → [创建窗口:1400–1404](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L1400) → [按钮绑定:89–97](../../trunk/AKRS.ZX2200/CalibSystem/Controls/FrmStartup.Designer.cs#L89) → [处理方法:98–110](../../trunk/AKRS.ZX2200/CalibSystem/Controls/FrmStartup.cs#L98) | 每次创建新窗口并 Show；本段未检查已存在窗口 |

这两条边已经在源码中找到，不能将测试窗口当成唯一入口。菜单是否对特定用户可见、是否受到外部权限或机器状态限制，不能仅凭 Designer 绑定认定。

## 重复启动、共享结果与取消

两个处理方法都没有本地 busy 标志、按钮禁用、锁、排队串行控制、await/Wait 或 continuation。连续两次 OK 会在处理方法层提交两次请求；这不等于已证明底层设备会同时运动，也不等于已测得数据竞争。

[CalibrateTask:44](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L44)继承 Singleton；[结果字段:149–159](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L149)是实例 List 属性；[外层方法:1817–1832](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1817)每次先 Clear，再运行内层、Add 并打开结果窗口。若两个调用得到同一实例并交叠，这些清空和添加作用于同一组集合；这是需要受控验收的交叠风险，不宣称已经发生。Singleton 基类的运行行为未在本专题替身检查中验证。

确认框 Cancel 只是不执行本次 Task.Run，不能画成对既有任务的撤销边。[FrmStartup Dispose:14–21](../../trunk/AKRS.ZX2200/CalibSystem/Controls/FrmStartup.Designer.cs#L14)仅释放 components 并调用 base.Dispose，没有连接到任务取消的代码。对已提交任务的机器停止和底层轴中断应分别追踪，不把窗口关闭等同于安全停机。

## 异常观察与结果窗口

`CalibrateTask.GetInstance()`在构造提交参数时调用，处理方法本身没有 catch；因此获取实例或提交时抛出的异常与已启动委托内部异常是不同阶段。Task.Run 的真实调度器行为未由替身测试验证。

[Program:97–105](../../trunk/AKRS.ZX2200/Program.cs#L97)注册 Application.ThreadException 与 AppDomain.UnhandledException；[处理方法:281–296](../../trunk/AKRS.ZX2200/Program.cs#L281)仅展示消息。trunk 的 C# 文本检索未找到 UnobservedTaskException 订阅。不能把现有两个注册当成这些未持有 Task 的异常必然被观察、提示或恢复的证据；依赖 DLL 中行为也未排除。

外层方法直接 ShowDialog/Dispose，当前方法中未见 Invoke 切回主界面。这里只记录调用位置，不能据此断言实际运行一定触发跨线程异常。内层 false 仍展示结果、异常逸出则跳过结果显示，见[完整方法报告](bond-camera-calibration-review.md)和[既有隔离检查](../../scripts/test-calibration-result-flow.cjs)。

## 验证与剩余项

[入口替身检查](../../scripts/test-calibration-task-entry.cjs)原样提取两个事件方法，以可记录的提交器替换 Task.Run，验证每条入口的取消不提交、OK 提交但尚不执行、再次 OK 再次提交、获取实例异常外抛。它不创建真实 WinForms、线程池或设备，不证明真实并发安全。

停止覆盖已补充：[界面停轴、机器停止与任务清单](calibration-stop-coverage-review.md)。已确认标定任务未登记在恢复界面的生产任务清单中；静态调用分析不等于实际停机验收。

剩余：现场菜单权限与可见性、重复任务互锁、SDK调用串行化、窗口线程模型、关窗后后台生命周期、机器停止能否中断每个标定子步骤。当前不修改生产源码，不增加模块完整验收数量。
