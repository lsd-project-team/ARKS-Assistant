# 输送章节：外层流程与交接关系重新复核

日期：2026-09-28。当前复核范围是输送图展示的任务入口、条件、信号和控制器返回分支；不代替硬件运行、驱动内部或所有参数组合验收。

## 已确认的启动和上料步骤

- [TransportDomain.StartTask:84–140](../../trunk/AKRS.ZX2200/TransportSystem/Models/TransportDomain.cs#L84)：未配置输送直接返回；先 Init，DryCycle 走 StartDryRun。普通模式检查现有料仓干涉，false 时 Stop 并返回；按配置复位要料、按反向搜索配置刷新载具，再 MapMaterial。**只有 LoadConfiguration==LoaderBin 才在这里同时启动 LoaderTask 和 UnloaderTask**，随后调用 TransportTask.Start。不能改写成由两个独立上下料配置分别启动两个料仓任务。
- [TransportTask:120–172](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L120)：Online 与 OnlineWithAutoLoader 另建送板机任务；PrepareFeeding 为 false 则等待。Success 清 PrepareFeeding，Abort 调 Stop；这里没有显式 Exception 分支。
- [TransferAutoLoaderToLoading:439–550](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L439)：入料段空才置要料、等待前端到料感应；到料后走皮带、关要料、停止皮带并保存有料状态。超过 5000ms 提供 Retry / Abort / Ignore；Ignore 的实际动作是 ContinuousFeeding=false 并返回 NoStart。循环中未直接检查 Stop/Pause；不能把超时退出和全局停止混同。
- [上料选择:181–418](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L181)：None 只处理点胶段已有料确认；非 LoaderBin 建皮带任务；LoaderBin 建料仓推料任务。两种任务均可能复用已有料而直接发来料信号。
- **未配置 S1 的皮带分支**在结果 switch 后发 AllowDispenseTransferToBondSignal，[293–295](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L293)，并非仅 Success 才发；料仓分支没有这条同位置旁路，不自行推断该组合必然可生产。
- [LoaderTask:55–129](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/LoaderTask.cs#L55)：先定位当前层、发 LoaderAllowPush；Wait AllowLoaderMove 后 MoveToNextPlaceLayer 再发允许推料。Abort 停机返回，其他未列出的结果可能继续发信号；不能概括成只在 Success 后放行。
- [UnloaderTask:56–127](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/UnloaderTask.cs#L56)：等待 AllowUnloaderMove 后仍调用 MoveToCurrentPlaceLayer，不能按名称假设直接调用 MoveToNextPlaceLayer。内部层号更新另需控制器证据。

## 下料分支与收尾

- **下料选择仍读取 LoadConfiguration**：[任务:605–726](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L605)。None 返回；非 LoaderBin 建等待区→出口皮带任务；LoaderBin 等 UnloaderAllowPush，再调用料仓传输。Online 或 OnlineWithAutoUnloader 才另建出口→收板机任务。因此普通 Belt 不能被画成必然等待下游要料。
- [等待区→皮带:1816–2054](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1816)：先检查等待区实际感应和软件有料；联机模式增加出口物料检查，仅 Online 再检查出口软件占用/传送状态。不能泛化成所有模式有完全相同的占用互锁。
- 上述控制器两处卡料 Retry 都回到 retry:1863，Abort 返回，Ignore 可继续迁移 TransportUnit、Refresh、清空等待区并保存状态。catch 只恢复等待区 SubSectionState，不是回滚所有先前动作或对象变更。
- [等待区→料仓:2063–2283](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L2063)：等待区实际/软件有料且未移动才继续。先传送，再按检测结果推杆回原/推料；推料失败 Retry 回到 RePush，其他卡料 Retry 回到 retry，Ignore 可能仍到软件收尾。推杆回原返回值在 2168–2170 被下一调用覆盖，没有独立判定。
- [料仓收尾:2241–2263](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L2241)：推杆回原、停等待区皮带、清等待区对象、更新两段状态，**AddCurPlaceLayer 后 Save**。随后任务 [703–709](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L703) 复位允许推料并发 AllowUnloaderMove。下料仓任务再定位“当前层”，不是没有层号递增。
- [出口→收板机:2292–2448](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L2292)：出口无料/传送中/下游不要料均 NoStart；否则等待出口感应出现，再等其消失。两次卡料 Retry 返回同一 retry 标签，**不会重新检查下游要料**；Abort 返回；Ignore 仍可清对象、置 NoMaterial/Ready、Save 并 Success。它没有前述进料控制器的 5000ms 计时条件，循环依赖 IsMoving。
- 该出口控制器 catch 返回 Exception，但对应任务 switch [743–757](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L743) 没有 Exception 分支，也没有 switch 后统一 Sleep；不能套用等待区→皮带任务的“Exception 调 Stop”行为。

## S1/S2 中段交接

此前已读的方法体和信号生产/消费位置见 [输送生产调用分析](transport-production-call-review.md)：S1 State 轮询与动作放行 → S1/S2 物料条件及 Wait → Success 发布 S2 来料 → Bond 消费与 SendAway → S2/等待区物料条件及 Wait。当前源码哈希需与快照一致才能复用这些复核。

这里的 Success 包含控制器内人工 Ignore 后的软件状态推进，不等于重新获得硬件到位证明。每片物料完成后任务继续等待下一片；本图的末端是局部交接收尾，不是全机任务终止。

## 尚未验收

- 料仓定位/推杆、运动驱动、所有传感器及 Save 底层实现；配置组合支持范围与设备运行。
- 历史图只表达主线及代表性进料报警，不穷举所有报警箭头；各局部 Retry/Ignore/Abort 以本记录和源码为准。
- 信号事件的底层自动复位行为、进程状态跨线程可见性及机械动作最终完成时间不可由此图保证。

## 图与台账本轮复核范围

本章 11 个节点完成其**展示的外层说明**复核，12 条现有关系完成分类；不代表这 11 个聚合节点囊括输送模块全部方法或报警支路。各节点的完整源码片段、路径/行号/文件哈希及说明指纹保存在门户和 semantic-revalidations.json，修改后需重新验收。

|关系|实际含义及源码依据|
|---|---|
|start → mode|普通模式经映射后调用 TransportTask.Start；DryCycle 分走模拟入口。TransportDomain:84–140。|
|mode → belt|LoadConfiguration 既不是 None 也不是 LoaderBin 的任务分支；是否额外在线进料还看 Online/OnlineWithAutoLoader。TransportTask:120–213。|
|mode → bin|LoaderBin 分支；定位与传输为两个任务间握手。TransportDomain:124–133、TransportTask:310–418。|
|belt → s1|TransferToDispense1FinishedSignal 的生产与消费，不是控制器直接调用 S1 工作方法。已有料也可发信号。TransportTask:224–295、DispenseWorkTask:221–263。|
|bin → s1|料仓传输 Success 或已有料复用发布同一来料信号；其他分支未必传料。TransportTask:327–415。|
|s1 → s2|S1 放行信号加两段物料条件；物料转送后任务发布 S2 来料。TransferDispenseToBond:1266–1524、任务:525–548。|
|s2 → wait|Bond SendAway 放行、控制器物料条件与等待；不是“主程序等待全部固晶线程结束”。BondTask:443–460、TransferBondToWaitingUnload:1531–1810。|
|wait → out|等待区软件/感应状态与后续传输任务的衔接，非同一函数顺序调用。控制器:1816–1859、2063–2100。|
|out → online|仅 Online / OnlineWithAutoUnloader 创建收板机交接任务；Belt 不自动进入该链路。TransportTask:726–765。|
|out → unloader|LoaderBin 任务 Wait UnloaderAllowPush 后调用传输，再复位并发移动许可。TransportTask:664–717。|
|belt → alarm|代表送板机到入料段的 5000ms 超时选择；不代表所有传输共用此计时。控制器:481–510。|
|alarm → belt|该处 Retry 跳回 Retry 标签，重新置要料并重建 Stopwatch；Abort/Ignore 是另外结果，不画成同一种重试。控制器:446–451、495–509。|

本图末端的联机出口交接与下料仓交接均是**一片物料的局部软件收尾**。载具迁移、Save、信号与物理到位分别解释，不能以图上节点的颜色或 Success 名称代替现场确认。

## 交付验证

- 本轮输送图通过 Archify showcase 的 9 项检查，0 错误/0 警告；JSON 与 HTML 哈希、字节数见 transport-workflow.delivery.json。
- Edge 自动浏览器检查通过，四个桌面视口与浅/深色截图回执见 transport-workflow.visual-check.json；交付与浏览器使用同一个 HTML 哈希。
- 已查看 1440×900 浅色截图，主线、分支与说明卡未见遮挡；该查看不等于所有交互功能验收。整合页本轮仍未额外执行浏览器导航验收。
- 仓库全套静态检查用于来源、图文/台账一致性与漂移保护，不执行生产设备程序。
