# ZX2200/Main：初始化、配方切换与生产调度

更新：2026-09-28。状态：部分复核。已涉及6个文件的指定方法范围，不代表76个文件全部阅读或主模块完整验收。沿实际调用补充既有八章自动工作主图，生产源码未修改。

## 工作步骤摘要

程序窗体加载先检查回零/离线条件，随后加载配置、执行数据调整、连接压力设备并启动后台线程。操作员可回零、新建或选择配方；切换配方先保存编号，再初始化各子系统程式节点和视觉方案。生产按钮另行调用Machine.Start，检查通过后设置Working，按配置和运行模式启动各工作任务。这里是调用发起顺序，不是机械动作串行完成顺序；任务内执行和信号握手见既有自动化章节。

## 入口和调用顺序

|阶段|源码实际行为|证据|
|---|---|---|
|窗体加载|AllAxisReset为false且非离线时禁用主界面并返回；否则DataLoad→ChangeData→参数界面委托赋值→ConnectBondhead→ConnectManometer→ChoseAllLight→StartBackGroundThread→确保导出目录。这里只确认调用，不证明设备连接成功。|[MainForm_Load 232–271](../../trunk/AKRS.ZX2200/Main/Controls/MainForm.cs#L232)|
|配置加载|WaferSub→Bond→TU→System1相关单例按代码顺序获取，末尾才设置PropertyChangeAop.InitSuccess=true。异常记录日志并弹窗，不重抛、不返回失败状态。若异常处理自身正常返回，调用方仍可继续ChangeData；没有加载事务或此处回滚。|[DataLoad 294–347](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs#L294)|
|回零按钮|直接调用AllAxisGoHome，按钮方法未使用其bool结果。方法先要求人工确认，按配置复位气缸、关闭补偿、发起滑动蘸胶回零，调用OneKeyHome；成功后OpenCompensate、AllAxisReset=true。取消、回零false或捕获异常返回false。本方法入口未清除旧AllAxisReset，不应把旧标记当成本次成功。|[按钮 531–535](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L531)；[回零 504–584](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L504)|
|加载配方|对话框OK且Recipe非null：设置RecipeID→SaveMachineConfig；旧配方为空或ID不同才ReLoadRecipe。相同ID仍保存编号但不重载。空Recipe弹出失败信息；OK分支尾部Dispose并触发后台界面刷新。|[BarBtLoad_ItemClick 804–839](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L804)|
|新建配方|创建对话框传入RecipeList和CopyOldRecipePR委托；OK且Recipe存在并同意切换才设置/保存ID，再按旧ID判断是否重载。通常返回路径最终Dispose、触发刷新并RecipeRepository.Save；异常可中断这些后续语句。复制委托内部已展开，见配方内部复核；文件helper和Clone等更下层尚待验证。|[BtNewProduct_ItemClick 320–361](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L320)|
|重建程式节点|ProductConfiguration→TransportProgram→BondProgram→System1Program→WaferSystemProgram→ProcessDomain，依次调用各自Init方法。六个方法均重设对应文件路径并将继承的 `instance` 设为 null；Wafer 初始化还先按 `IsClearStaticAdapter` 清理两种记忆状态。此顺序不等同于完整数据格式、清理或磁盘读取语义。|[InitProgramNodes 124–132](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L124)；[初始化专项复核](main-init-program-nodes-review.md)|
|重载视觉|先PrInitSuccess=false，禁用界面、显示提示、更新名称、清理dock、InitProgramNodes；然后才进入try。离线置成功后return，经finally恢复界面。在线关闭旧VmSolution→创建新方案→逐个查找PR并调用初始化；找不到的实体只记录日志，`InitVmProcedure` 异常也在内部吞掉，循环后仍置成功。`LoadDispensePr` 当前去除注释后无可执行语句。异常弹窗、日志并重抛，finally恢复提示和界面。|[ReLoadRecipe 137–203](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L137)；[PR专项复核](main-pr-reload-review.md)|
|开始生产|禁用界面；按配置提示确认配方，Cancel返回；关闭手动移动面板，退出单步，调用Start。catch调用Stop并弹窗，finally重新启用界面。Start内部检查false是普通return，不会因此进入按钮catch。|[BarItemStart_ItemClick 68–110](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L68)|
|启动任务|PrepareMachineReadyToStart为false返回；否则SetState(Working)。非补偿模式启动运输和供片；配置System1且非补偿时启动点胶。随后始终ActionNodesService.Init→BondTask.Start；滑动蘸胶、翻转按硬件配置且非补偿模式启动；最后检查并打开两类华夫真空。只描述此方法的条件，不扩展为所有模式的内部执行保证。|[Machine.Start 261–309](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L261)|
|保存及退出连接|DataSave按WaferSub、Bond、TU、System1和machine配置顺序逐项Save，异常日志/弹窗后返回，未回滚已保存项。ExitSoftware先调用DataSave再进入硬件关闭阶段；保存失败若被DataSave捕获，退出流程仍可能继续。|[DataSave 352–412](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs#L352)；[ExitSoftware局部 706–732](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L706)|

## 已证实的异常边界与待验证影响

- 配方编号在重载前已保存，重载异常路径未见恢复旧RecipeID。因此不能把编号保存成功当成配方所有模块初始化成功；恢复策略需单独验证。
- ReLoadRecipe的名称读取、dock清理、InitProgramNodes在try/finally之前。该范围抛出异常不会执行本方法后面的finally；界面恢复是否由更上层接管仍需追踪。
- 某个PR名称查找为空仅记录日志，`InitVmProcedure` 的异常也不会阻止循环；点胶加载方法当前为空操作，最终仍可 `PrInitSuccess=true`。该标记不能单独证明清单内每个PR都存在。
- DataLoad和DataSave是void并捕获异常；失败前已经产生的单例/文件副作用未在这些方法回滚。这里只指出控制流风险，未声称设备已发生故障。
- AllAxisGoHome成功日志不全是执行后状态验证；例如条件不满足时相关后续日志仍可出现。真正回零返回以OneKeyHome返回值及后续异常路径为准。
- BarItemRestart_ItemClick 117–119为空；不能把名称理解为已实现的自动重启。

## 输入、输出与外部边界

输入：操作员对话框结果、当前/目标RecipeID、运行模式、硬件配置、各Repository配置。可见输出：保存的配方上下文、初始化后的程式对象、视觉过程、PrInitSuccess/AllAxisReset/Working状态、任务启动请求、日志和界面提示。压力连接经ModbusService，视觉方案经VmSolution/PR包装，运动回零经HardwareRepositoryService。本轮没有验证这些外部实现、协议、超时或SDK版本，也未新增数据库/队列推断。文件格式与真实路径应继续追踪各Save/Init实现。

## 下一步与验收条件

1. 六个InitProgram方法和供片清理已展开；继续取得Singleton<T>实际实现，核实读取与迁移规则。
2. PR主清单、InitVmProcedure、LoadDispensePr空操作及CopyOldRecipePR已展开；Clone、同名策略和重建标记消费方已补深；继续清单子方法与窗口提交语义。
3. 继续Main其余文件及各入口调用方；补初始程序入口至MainForm的完整启动连接、权限和运行中切换限制，不能仅凭按钮方法宣称已阻止运行中切换。
4. 对照[启动限定范围复核](startup-semantic-revalidation.md)及[失败恢复限定范围复核](failure-recovery-semantic-revalidation.md)，展开任务内部顺序；不要将启动请求箭头解释为任务完成。
5. 最后完成依赖版本/构建、测试环境故障注入和设备验证；静态证据检查不替代这些验收。

独立模块台账：[状态与代表调用](module-review-status.md)。源码快照与哈希：[module-review-evidence.json](module-review-evidence.json)。


内部复核：[配方初始化、视觉异常与复制边界](recipe-initialization-source-review.md)。图候选尚有离线标签与节点净距诊断，未交付为已验收HTML；正文和精确源码证据可先用于交接。

## 停止恢复与料仓线程的交叉复核

已补普通停止、急停、继续、任务退出门控和报警关闭对料仓内部循环的影响。见[停止恢复影响矩阵](bin-stop-resume-source-review.md)。状态改变不代表全部线程退出，局部后台缩回Task未在退出检查列表中登记；并发路径和硬件接受条件仍待验证。

补充：[运行中编辑入口与两种启动差异](production-edit-gating-review.md)。

补充：[自动化入口矩阵：扫描、输送、单步与恢复](automation-entrypoint-matrix.md)。
