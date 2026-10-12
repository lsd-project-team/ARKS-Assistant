# 后台安全门、激光与温度监控：原方法及线程边界

日期：2026-09-29。89项方法/线程检查以及9个独立Framework进程异常场景通过。测试程序集纳入46份原成员片段，本轮新增完整原StartCheckSafeDoorTask、StartLaserEncoderCheckTask、LaserEncoderCheck、Pause、BackgroundTemperatureAlarm和StartBackGroundThread；纳入不等于全部方法分支覆盖。

## 安全门

12组配置×Working/Pause/Stop×门开关组合直接执行原安全门方法和原Pause。只有配置启用、Working且门开时变为Pause，其余保持原状态。每组另确认受控Running固晶Task仍运行，没有Stop清理。门重新关闭不会由此方法自动恢复Working，恢复代码已注释。

门传感器读取和状态setter是替身；此处证明调用门控与状态赋值意图，不证明物理轴停止或生产任务响应Pause。

## 激光检查及消息顺序

| 受控输入 | 原返回/监控结果 | Abort消息响应 |
|---|---|---|
| 环境传感器不良 | 先提示，再返回false，外层调用Stop | 调用ExitSoftware替身，返回后仍false |
| 算法异常 | 先提示，再返回false，外层调用Stop | 同上 |
| 光强不是3 | 提示后返回true，外层不调用Stop | 调用ExitSoftware替身；若返回，则仍true |
| 传感器读取抛异常 | catch提示通讯异常，返回false，外层调用Stop | catch中的对话框结果没有被用于退出 |

8组异常类型×OK/Abort组合均确认受控Task继续Running；ExitSoftware仅记录调用后返回，未执行产品退出、保存或进程终止，因此不能据此推断实际退出后的运行状态。

额外验证：正常返回true；未配置仍先查询硬件；配置启用但硬件返回null也直接true。硬件查询位于try之外，查询异常跳过本地通讯提示和Stop。第一次提示自身抛错会转到通讯提示；通讯提示再次抛错则向外传播，Stop尚未调用。Stop清理再失败会留下部分停止状态。

原StartLaserEncoderCheckTask末尾只有Task.Delay(100)，没有await/Wait；不将其当作同步100ms等待。完整后台循环另有Thread.Sleep(100)，实际循环耗时还包含前面各项工作。

## 温度报警与预热

24组配置×三状态×加热开关×报警组合确认：只有配置启用、Working、加热开启且Alarm为true才Stop并弹温度提示。与激光不同，温度提示发生在Stop清理之后；之后仍继续加热完成/预热记账。Stop或提示异常都会截断相应后续工作。

原预热判断使用(DateTime.Now - HeatingCompleteTime).Minutes，而非TotalMinutes。阈值10分钟时，受控已过5、15、65、75、125分钟分别得到false、true、false、true、false；阈值60、已过90分钟仍false。测试时间另留5秒余量，并非精密时钟或所有时间值证明。完成标志已置true后，即使加热关闭也不会由本方法清除。

这些配置值是隔离测试输入，没有修改现场预热参数。当前源码事实不表示现场配置一定允许60分钟阈值；其UI/持久化允许范围需另行核对。

## 原后台线程

直接执行原StartBackGroundThread，以最后一个服务替身在第一轮结束时将ThreadFlag设false，确保有界运行和Join回收。确认服务依次执行：安全门、激光、自动登出、温度、耗材、信号、视觉存图、统计保存。另验证ThreadFlag初始false不执行循环体、存活线程抑制重复启动、已结束线程可以重新创建、线程名称和后台属性。未覆盖并发同时调用启动方法的竞争。

在最小独立Framework可执行程序中，9处故障注入分别覆盖Pause状态写入、激光查找、通讯提示、自动登出、温度读取、耗材、信号、视觉与统计服务。每个子进程均记录故障点后UnhandledException，随后非零退出；后续服务没有执行。原循环没有被添加try/catch。

独立程序只加载测试程序集与随项目DLL，不是产品EXE；这是原调用链在该宿主策略下的传播证据，不声称产品宿主或现场进程必定以相同方式退出。传感器、弹窗、轴状态、业务服务和自动登出/退出内部实现仍为替身；无真实设备操作。主界面MainForm中启动后台线程的直接调用位置单独绑定源码哈希。

## 构成与复现

- 安全门12组×门控/任务保持：24项。
- 激光8组×状态/退出处理：16项；激光额外边界：8项。
- 温度报警配置矩阵：24项；预热及异常顺序：11项。
- 原后台线程生命周期与顺序：6项。合计89项，50条结构化观测。
- 另有9个隔离进程故障场景，退出码及逐项调用序列保存在回执。

运行`node scripts/test-background-monitor.cjs`；审计`node scripts/build-background-monitor-audit.cjs --check`。原源码、脚手架、真实Singleton/JSON程序集及独立宿主均绑定SHA256。生产源码不变。

前置材料：[急停按钮](emergency-entry-review.md)、[Stop与Abort](emergency-abort-review.md)、[真实Task关闭门控](task-closure-review.md)。29组保持部分复核；后续继续传感器真实读取、预热参数入口、生产任务Pause响应及现场宿主策略，不以本轮测试替代完整构建或设备安全验收。
