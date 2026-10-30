# 供晶章节源码复核

## 2026-09-29 换片与停止边界回填

主图保留12节点、15条聚合关系，把“异常后 Stop”改为“提示后请求停止”。门户换片节点区分ChangeTabletAuto返回false与其内部初始化false：后者按分支直接重试或重开向导，空跑不检查初始化bool。手动窗口先发布内存对象再保存/请求运动，取消或失败没有本地回滚；名称无效仍可能保留旧tempTablet。停止节点补充弹窗异常会跳过Stop，以及状态日志入队阻塞/失败可发生在已置Stop但尚未清理之间。两个节点和四条相邻关系的语义登记已回链六段新增源码，不增加主图业务步骤或宣称实机完成。

证据与执行范围：[初始化](wafer-start-init-review.md)、[外层换片16项检查](wafer-change-retry-review.md)、[手动窗口24项检查](manual-wafer-change-review.md)、[名称/网格23项检查](wafer-selection-review.md)、[日志队列与失败传播18项检查](state-queue-failure-review.md)。报告中的隔离范围分别保留，不能相加当作端到端验收。

新交付通过Showcase 9/9、0错误/警告；Edge四种桌面尺寸通过包含性检查。已查看1440×900浅色及2048×1320深色截图，主路径、节点与提示卡无遮挡；细小关系标签可使用缩放阅读。交付与浏览器回执分别见[交付记录](wafer-supply-workflow.delivery.json)、[浏览器记录](wafer-supply-workflow.visual-check.json)。下文旧交付记录保留历史范围。

更新：2026-09-28。范围：供晶主循环、需求/就绪信号、搜索模式分派和翻转包装；搜索算法、换片底层动作与硬件验收不能由主图代替。

## 工作流程摘要

1. WaferSubSystemTask.Start 在任务为空或非 Running 时 StartInit、清 PreviousNeedChipName、置 Working，并启动 LongRunning 任务。Start catch 只弹窗；AbortWaferSubThread 是空方法。
2. Dowork 等 IsBondNeedChipSignal，Wait=false 回到外层 WaitStart；单独 DryCycle 会延时后自行置需求。芯片名来自先写 SetCurrentNeedChipName 再 Set 需求的调用方，并非事件携带的消息队列。
3. 校验 GetCarriers 中存在名称，再从仓库获取配置。未知名称抛异常；当前 NullTablet 或与上次名称不同则置换片标志。
4. 需要换片时 ChangeTabletAuto；true/false 两条正常返回路径均写换片报警记录，false 再抛异常。方法直接抛异常时不保证写到同一记录收尾。
5. NextDie 按 Single、Nine、WaferMap、Box 分派。false 且需换片时：WaferMap、DryCycle、非 WaferTablet 回换片检查；普通晶圆进入人工选点。OK 回换片检查，Retry 校验范围、复位换片标志、置当前片 Good 并请求保存；其他返回最终抛搜晶失败。
6. 搜晶 true 后更新 PreviousNeedChipName，按载具与配置开/关取片前真空、可能延时，复位芯片需求，再 Set IsWaferAllowPickSignal。此为软件就绪发布，不是 S2 已取走。
7. 直取等待晶圆信号的条件还取决于 SearchCamera 与 StaticWaffle；翻转路线由 FlipTask 消费晶圆信号，再发 IsFlipTableAllowPickSignal，等待 IsBondPickSucceedSignal。
8. 普通循环继续等下一需求；单次搜索在发布就绪后 Stop。Dowork catch 先显示异常再 Stop，不是统一有界重试器。

## 翻转与预取的关键区别

FlipTask 先回零后循环。组件空则等待100ms；不使用翻转台时不走取片分支。已知组件但不使用翻转台的分支在此方法未见固定 Sleep，不能声称所有循环按固定周期调度。

翻转工具无芯片时等晶圆可取，再调用 FlipChipAction 或 DryRun。Success 置工具有料；Exception/Abort 对晶圆执行顶针准备吹气后 return，此方法该分支没有显式 Stop。NoStart 跳回等待晶圆；未列出的返回值无 default，可能继续发布翻转可取。工具已有料则跳过新一次取料直接发布可取。

notifyWafer 回调另起 Task.Run：检查 T 位置超过避让阈值后，读取下一组件名是否非空，但实际写入需求的是 component.Name；不是直接把 nextComponentName 发给晶圆。超过10000ms弹窗：Ignore 重启计时继续等，Abort Stop 并退出；循环另检查 Stop。该回调任务没有统一 catch/await，本轮不推断异常会自动使主线程停止。

FlipTask.DoWork 没有 try/finally：只有自然离开外层循环才走末尾 FlipTableGoHome；中途 return 或异常不保证回零。Start 也只用 null/非 Running 门控，返回 true 不证明动作完成。

直取 WaitAllowBondPickSignal：StaticWaffle 避让分支循环调用 Wait(100)，必要时移动避让位并 Pause，Stop 返回 Abort；其他非翻转仅 WaferCamera 或 StaticWaffle 才等晶圆信号，最终仍 WaitStart。Signal.Wait(int) 实现不是按形参保证等待100ms，参见已有信号复核。

## 源码入口

- [供晶 Dowork](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L64)：64–384。
- [启动与空 Abort](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1373)：1373–1458。
- [搜索分派](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L335)：335–355。
- [需求首发](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs#L55)：55–101。
- [取晶等待选择](../../trunk/AKRS.ZX2200/BondSystem/Models/Parameter/System2RunTimeProvider.cs#L337)：337–406。
- [翻转主循环与异步预取](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs#L57)：57–276。
- [直取预发需求条件](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs#L633)：633–671。
- [换片模式与向导已有复核](carrier-change-review.md)。
- [Single 搜晶与握手已有复核](wafer-bond-handshake-review.md)。

## 四种搜索的实际边界

|模式|已核实的外层流程|退出与限制|
|---|---|---|
|Single|位置生成→定位判定→跳过循环→取晶中心；详见已有握手复核|局部候选位置最多50次不等于整个流程最多50次；视觉、人工重试另有循环|
|Nine|首次中心或上方候选优先；随后按行方向选左右/斜向候选，再尝试记忆的下一行、T点、最大行起点；AnalyseDies 检查范围并定位|RecurCount > RecurLimit（50）才抛 PickRefEnd；捕获后置需换片、料片 Bad、保存并返回 false。记忆候选耗尽也会 StartInitNine 后直接 false，不可把每个 false 都视为同一种换片原因|
|WaferMap|GetNextPositionInfoAndForwardTo→移动→AnalyseDie→设置物理坐标；跳板或跳过时继续循环；再移到取晶中心|不支持双点、MultipleSearch、非定位搜索。NoApproachableChip 可先补取选中类型的参考晶粒；结束或 PickRefEnd 置换片标志、Bad、保存并 Unlock 后 false；找不到路径抛异常|
|Box|跳过非 Good 槽位；StandardSearch 下可双点或单点；StaticWaffle 单点分支直接用槽位与相对偏移；跳过时更新索引并请求保存|无下一槽位置需换片、当前盒 Bad 并 false；MultipleSearch/非定位抛异常；正常循环末尾 StopSearch，再移动取晶中心并 true|

源码：[Nine 39–386](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchNine.cs#L39)、[RecurLimit 874–879](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchNine.cs#L874)、[Map 46–196](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchMapping.cs#L46)、[Box 48–208](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchDieBox.cs#L48)。

Box 的 AsyncSave 通过 MainForm.SendUiAction 请求 WaferSubDevicePara.Save，不能据方法名认定文件在返回前已经持久化。地图加载、参考点、预取与保存见 [地图运行复核](wafer-map-runtime-review.md)。Nine 的 CalculateDiesPosition、墨点和候选标记几何算法本轮没有全量语义验收。

## 图中十五条关系的含义

|关系 ID|类型|源码依据与限定|
|---|---|---|
|need-valid|顺序控制流|Dowork 80–123：需求等待成功后校验名称|
|valid-change|条件控制流|115–134：存在名称；空片或名称变化置换片标志，再检查|
|change-search|条件控制流|134–162：不需换片时继续 NextDie|
|change-replace|条件控制流|134–149：标志为真才调用 ChangeTabletAuto|
|replace-search|条件返回|140–162：ChangeTabletAuto 返回 true 后记录再搜索；不是所有向导关闭均成功|
|search-found|直接调用链|Dowork 162→Block.NextDie 335–355，返回 bool；抛异常跳 catch|
|found-ready|条件控制流|162、256–324：仅 true 才进入后续真空等准备并清需求、置就绪|
|found-retry|条件控制流|165–247：false 且需换片；Map/DryCycle/非晶圆回换片检查，其余人工选点|
|retry-change|条件控制流|169–247：直接 goto，或人工 OK，或 Retry 通过范围验证后 goto；取消等返回不走此边|
|found-stop|条件控制流|252→375–383：失败未走恢复跳转则抛异常；catch 弹窗后 Stop|
|valid-stop|条件控制流|123→375–383：未知名称抛异常；并非验证函数直接调用 Stop|
|ready-route|信号交接|322–324、WaitAllowBondPickSignal 337–406 与 FlipTask 101：生产者和等待者分属任务，不是串行调用|
|route-pick|条件控制流|WaitAllowBondPickSignal 339–403；PickActionNode 206–212 在非补偿工作时调用，实际等待还受相机/StaticWaffle 条件限制|
|route-flip|信号交接|FlipTask 93–103 消费晶圆事件；S2 的389–391等待翻转事件|
|flip-pick|信号交接|FlipTask 236发布；S2 等待成功并通过 WaitStart 后继续。翻转失败/退出不保证到达发布|

图保留一颗供晶需求的主路径，catch 同样接收换片、搜索和准备阶段异常；这些聚合异常没有全部展开成重复箭头。到达“S2 接续”不是整机生产完成。

## S2 接续的证据与范围

[PickActionNode.cs 206–212](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs#L206) 确认非补偿运行才调用等待包装；[333–343](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs#L333) 确认 Pick 成功清翻转工具有料标志。

[470–498](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs#L470) 再检查 WaitStart：直取通过 Task.Run 在非补偿工作时调用 SendSignalToWaferTable；翻转另起 Task.Run 调用 SendSignalToFlipTable。此处确认调用关系，不把任务启动当作其通知已成功完成；翻转通知内部的安全位置等待与全部取晶恢复分支留在取晶章节验收。

## 当前缺失与验收范围

本章复核对象是12个现有图节点和15条聚合关系，以及上述搜索包装分支；不代表整个供晶子系统、所有调用传递层级或现场运行已经验收。运动/视觉/地图 SDK 内部、全部信号生产者、Nine 几何算法、线程竞态、数据库实际写入和硬件安全需继续验证。源码缺失的实现停在接口边界，不补写推测。

## 本轮交付验收

- 供晶正式规格与 HTML 已通过 Archify deliver：9项检查，0错误、0警告。详见 wafer-supply-workflow.delivery.json。
- Edge 自动浏览器检查通过，覆盖回执中的桌面尺寸与明暗主题；截图、溢出和控件边界记录见 wafer-supply-workflow.visual-check.json。此检查不证明业务流程在硬件上运行正确。
- 已实际查看 wafer-supply-workflow.visual-check.1440x900.light.png：主链、恢复支路、信号区及提示卡可辨认，未见文字遮挡；标签较小，细节可用页面缩放查看。本次图像审查仅覆盖该截图，不冒充所有视口的人工验收。
- 门户与正式图的节点标签、15条边一致，交付哈希匹配；verify-all 的13项任务通过。整合门户实际导航仍未完成本轮浏览器验收。
- 当前登记45/89节点、49/100关系；其余44节点、51关系待逐条复核，不是全项目完成率。
