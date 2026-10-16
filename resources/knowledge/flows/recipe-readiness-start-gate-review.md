# 配方就绪到生产启动：标志、检查顺序与失败边界

本专题连接已完成的[配方加载与重载](recipe-switch-failure-review.md)、[配方切换时序图](recipe-switch-sequence.html)和[生产启动主链](production-start-readiness-review.md)。只分析当前trunk源码及原方法隔离检查，不执行设备、真实磁盘清理或视觉SDK。

## 先看结论

PrInitSuccess是共享布尔标志，不含RecipeID、PR清单或初始化代次。true仅让MachineInitSuccess继续检查磁盘和预热；最终还要经过安全门、工作状态、运动到安全位和各域环境检查。缺PR后仍置true，不等于缺PR必然能够投入生产，更不证明所有后续任务完成。

普通Start在视觉门控之前已经调用CleanFile、ResetMachineSignal、ReadyToLog和缺陷计数复位，具体到达哪些调用取决于更早的回零和任务门控。启动失败不是天然无副作用的只读检查。本文的副作用表示源码调用意图，未验证实际文件删除或现场信号效果。

## 标志的来源及消费

| 位置 | 实际行为 | 源码 |
| --- | --- | --- |
| Machine属性 | 自动属性默认false，没有关联配方身份或版本 | [Machine.Sustain.cs:37](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Sustain.cs#L37) |
| 启动入口 | 非OffLineWork时调用InitPR，不await或保存其返回Task，随后继续硬件初始化 | [Program.cs:173–183](../../trunk/AKRS.ZX2200/Program.cs#L173) |
| InitPR | Task.Run内关闭/创建视觉方案、获取PR名称；空名称跳过、找不到PR只记日志、Alg为空可跳过；末尾置true。异常提示并重抛到Task。方法入口没有先清false | [Machine.Sustain.cs:116–179](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Sustain.cs#L116) |
| ReLoadRecipe | 入口清false；六类程序初始化后，离线路径置true，在线在PR循环及LoadDispensePr之后置true；缺PR不阻止到达赋值 | [UcMainSystem.Production.cs:137–203](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L137) |
| MachineInitSuccess | 本轮具名引用清单中唯一直接读取门控：false弹窗并返回false，true继续后续检查 | [Machine.Operate.cs:408–444](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L408) |

上述“唯一”限定为当前trunk下C#文本中PrInitSuccess的具名引用，生成器记录所有命中与文件哈希；不包含反射、运行时委托动态绑定或DLL内部。初始化代次未绑定只说明不能用该标志单独证明当前RecipeID的模板齐备；未据此断言现场发生了竞态。

## 按真实入口展开检查顺序

1. [Start:261–309](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L261)先调用PrepareMachineReadyToStart，false立即返回。只有通过才设置Working，继续按模式和硬件配置发起生产任务；任务之间不是按机械完成时间串行执行。
2. [PrepareMachineReadyToStart:185–256](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L185)先CleanFile、ResetMachineSignal，再无条件检查AllAxisReset。失败到此返回；成功后ReadyToLog、IsAllowTaskClosed，然后逐项InitDefectCount，才调用MachineInitSuccess。
3. MachineInitSuccess内部依次检查：配置要求回零且未回零 → PR标志false → 磁盘容量不足 → 配置输送加热且加热开启且预热未完成。任一对应条件失败即返回false；均通过返回true。检查表达式短路，没有统一catch。
4. Prepare后续再检查安全门、IsWorking，按配置调用S1安全位、调用S2安全位，按顶针配置调用AbsoluteMove(0)，最后CheckOperatingEnvironment。该最后检查失败并不撤销前面的调用。各域实现继续见[域就绪复核](production-domain-readiness-review.md)。

重要区别：直接调用MachineInitSuccess时，IsAxisResetBeforeWork=false允许跳过其回零检查；但普通Start先进入Prepare，那里仍无条件要求AllAxisReset。不能从单独方法的选项推断正常生产入口可绕过总复位。

磁盘函数[IsDiskCapacitySufficient:186–209](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Sustain.cs#L186)读取C盘与D盘TotalFreeSpace并除以1024³，分别以小于10和200为失败条件。C盘失败不继续D盘；驱动器读取异常本函数没有catch。本文门控测试以替身返回/抛异常验证传播，不读取现场磁盘。

## 十六项原方法隔离检查

[测试脚本](../../scripts/test-recipe-readiness-gate.cjs)从当前源码提取完整MachineInitSuccess（408–444）和PrepareMachineReadyToStart（185–256）。仅将Prepare中一个无变量插值字符串改为普通字符串以兼容C#5；分支和调用顺序保持原样。[支架](../../scripts/recipe-readiness-gate-harness.cs.txt)替代配置、UI、文件、任务、仓库、运动及磁盘依赖，记录精确调用序列；不调用Start或真实设备。

| 场景 | 已核对结果 |
| --- | --- |
| 基础条件通过 | 仅调用磁盘检查，门控true |
| 要求回零但未回零 | 轴提示后false，不检查PR后的依赖 |
| PR=false | PR提示后false，不访问磁盘 |
| 直接门控、关闭回零选项且未回零 | 可通过直接门控；不能外推普通Start |
| 磁盘false | false，不访问加热状态 |
| 加热配置但未开启 | 即使预热false也通过此门控 |
| 加热开启且预热未完成 | 磁盘→加热→提示，false |
| 加热开启且预热完成 | 磁盘→加热，true |
| 磁盘检查抛异常 | 原异常向调用者传播 |
| 加热状态读取抛异常 | 原异常向调用者传播 |
| PR提示本身抛异常 | 原异常传播，而非正常false返回 |
| 同时未回零且PR=false | 优先轴提示，不到PR提示 |
| Prepare中回零选项关闭但未回零 | 清文件→复位信号→轴提示，false |
| Prepare中PR=false | 清文件→复位信号→ReadyToLog→任务门控→缺陷复位→PR提示，false |
| Prepare中任务尚未关闭 | 在缺陷复位和PR检查之前返回false |
| Prepare基础成功 | 到达S2安全位后才执行环境检查 |

每个场景同时核对PR与轴复位标志未被这两个方法改变。16项通过只证明所选输入及替身条件下的原方法行为，不证明所有配置组合、真实资源释放、工作线程状态或完整启动闭环。

## 已完成与尚待验证

- 已完成：标志写入/读取清单、加载与启动门控的连接、普通入口与独立检查选项差异、检查前副作用及异常传播的有界验证。
- 待验证：真实配方与视觉模板是否匹配；异步InitPR实际完成时间与后续切换之间是否存在重叠；现场门控UI可达性、磁盘/驱动异常、任务停止和生产运行。缺少现场证据时不标记这些项目已验收。
- 本专题复用现有生产任务、域检查和配方交互图，不重复计算业务覆盖，不修改生产源码，不把新的16项测试累加为模块完整验收数。

[源码快照与引用清单](recipe-readiness-start-gate-evidence.json) · [项目进度](project-plan-status.md) · [成果入口](index.html)
