# 启动章节：外层控制流重新复核

日期：2026-09-28。本记录复核 `startup-workflow` 的 12 个节点与现有 10 条流程关系。验收对象是图上显示的外层控制流，不是所有被调用方法、所有配置组合或硬件运行。历史记录保留，新复核与历史登记分别计数。

## 简明流程

Main 单实例及前置检查 → 按非离线条件初始化 → 按配置请求开机回零 → 创建窗口并进入消息循环 → Load 事件门控与初始化 → 人工启动按钮 → Prepare 检查 → Working 状态 → 按配置顺序发起各任务。后台监控由通过门控的 Load 路径另外启动。

普通 Stop 与再次启动不是自动恢复链：图中“再次启动”明确表示人工事件。入口图是聚合视图；未展开的错误路径不能被理解成不存在。

## 节点对应的源码

|节点|源码证据与实际边界|
|---|---|
|entry|[Program.Main:65–172](../../trunk/AKRS.ZX2200/Program.cs#L65)：Mutex、磁盘、迁移提示、日志、辅助线程及可选授权。授权失败返回；重复实例分支见 [260–264](../../trunk/AKRS.ZX2200/Program.cs#L260)。|
|init|[173–248](../../trunk/AKRS.ZX2200/Program.cs#L173)：非离线才进 PR/硬件初始化块；catch 日志和弹窗而未直接退出。之后另有 Harmony 与视觉事件设置，不能承诺 catch 后绝不会发生其他异常。|
|home|[Main:250–256](../../trunk/AKRS.ZX2200/Program.cs#L250) 按配置调用回零且未检查返回值；[AllAxisGoHome:504–583](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L504) 中取消、回零失败或异常返回 false，只有成功末段开补偿并置 AllAxisReset。|
|form|[MainForm_Load:232–257](../../trunk/AKRS.ZX2200/Main/Controls/MainForm.cs#L232)：非离线且未回零会禁用主区域并立即返回；后续 DataLoad、仪器连接、选灯和后台启动仅在未提前返回且未被异常打断时执行。[Load 注册:310](../../trunk/AKRS.ZX2200/Main/Controls/MainForm.designer.cs#L310)。|
|operator / reject|[按钮注册:706](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.designer.cs#L706)；[处理器:68–109](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L68)。Cancel 在调用 Start 前返回，catch 调 Stop，finally 恢复控件；Prepare false 则在 Start 内返回。|
|checks|[Prepare:185–256](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L185) 有清文件、复位信号、安全位移动等副作用；[环境检查:89–127](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L89) 依次调用各域、产品、焊点及制程检查。内部自检与硬件反馈不在本次验收范围。|
|working|[Start:266–272](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L266)：Prepare true 后置 Working；[SetState:52–68](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.StateRelated.cs#L52) 赋状态并记录，非启动成功汇总。|
|dispatch|[Start:274–308](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L274)：输送、供晶、可选 S1、动作初始化、固晶、可选胶盘、可选翻转及真空检查；配置/补偿分支见源码。只是发起顺序，没有统一等待任务完成。|
|monitor|[662–699](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L662)：线程不存在或不存活时创建；ThreadFlag 循环内顺序调用各监控/存储入口，最后 Sleep(100)。不能声称固定周期为 100ms，也不能声称所有被调用函数都同步完成工作。|
|stop / restart|[Stop:347–378](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L347) 的局部清理与退出边界见 [停机复核](stop-cleanup-review.md)；再次点击重新触发原按钮处理器，不是 Stop 调用 Start。|

## 10 条关系的分类

|关系|分类|条件 / 注意事项|
|---|---|---|
|entry → init|条件控制流|只有通过前置检查且非离线才执行硬件初始化块。|
|init → home|顺序控制流|初始化块之后经过 Harmony/视觉事件设置，再到可选回零块；不是 InitPR 直接调用 AllAxisGoHome。|
|home → form|顺序与事件边界|Main 不检查回零返回值，继续创建窗口/Run；Load 由已注册事件触发。|
|form → operator|人工事件关系|界面初始化与用户操作的阅读顺序，不是 Load 自动调用生产启动。|
|operator → checks|直接调用链|确认通过后按钮调用 Start，Start 调 Prepare；取消路径见节点及本表说明。|
|checks → working|条件控制流|Prepare true；false 返回。|
|working → dispatch|顺序控制流|先置状态后发起各入口，不代表线程执行或完成顺序。|
|checks → reject|条件返回|Prepare false 导致 Start 返回；图上 reject 还聚合按钮 Cancel 的另一局部返回。|
|form → monitor|调用及线程启动|Load 未被回零门控/异常打断才调用；后台线程不存在或已退出才创建。|
|stop → restart|人工操作关系|表示可以再次请求启动并重新检查；不是自动重启，也不是保证重启通过。|

## 仍未完成

- 各域自检、驱动与第三方库全部内部语义；异步任务中的所有失败传播。
- 所有现场配置组合、设备动作完成/停止、构建与硬件运行验收。
- 其余历史图节点及其关系分批重新复核，最新计数见项目计划和台账。

结构化验收登记在 `semantic-revalidations.json`。节点说明、关系内容和源码哈希改变后，检查必须失败，要求重新人工语义复核；哈希检查本身不能证明语义正确。

## 本轮交付验证

- Archify showcase：9/9，0 错误、0 警告；正式 HTML 与 JSON 的 SHA-256/字节数保存在 startup-workflow.delivery.json。
- Edge 自动浏览器检查通过四个桌面视口；交付 HTML 哈希与浏览器回执一致。已查看 1440×900 浅色截图，条件标签和卡片未见遮挡。此视觉查看仅覆盖该截图，不替代全部交互测试。
- 整合页当前进度与复核登记进行数据一致性检查；内置浏览器拒绝 file 协议，未通过其他浏览器路径绕过，整合页本轮浏览器导航验收仍待完成。
- 新增 9 个复核漂移/拒绝负例，不执行设备程序。源码链接可定位性不等于本地阅读器一定支持 #L 跳转。
