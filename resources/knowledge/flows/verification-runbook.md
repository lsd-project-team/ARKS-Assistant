# ZX2200 Archify 验证手册

工作目录：`C:\Users\akrs\Documents\ChatGPT\archify`

## 一键验证

```powershell
node scripts/verify-all.cjs
./scripts/build-project-dependencies.ps1 -Check
node scripts/audit-diagram-structure.cjs --check --strict
```

成功标志：`verify-all: PASS`。

## 检查范围

- `verify-source-evidence.cjs`：源码路径、行号、片段、SHA-256、图节点引用。
- `build-traceability-ledger.cjs --check`：图数据、语义复核与统一台账。
- `test-ledger-guards.cjs`：基线和负例保护。
- `verify-startup-calls.cjs`：启动调用点数量与位置。
- `verify-completeness-report.cjs`：审计报告计数与台账一致。
- `git diff --check`：文档和脚本格式。

## 当前基线

- 89 个步骤
- 100 条流程关系
- 89 个历史节点登记，均待重新复核
- 62 条源码证据

## 浏览器检查

```powershell
node C:\Users\akrs\.agents\skills\archify\bin\archify.mjs visual-check docs/archify/index.html --json
```

当前环境没有 Chrome/Chromium 时，收据会明确标记 `status: skipped`；这不等于浏览器视口验证通过。

检查通过只代表列明的静态证据和结构检查通过，不代表全部业务语义、浏览器显示或设备运行验收通过。


## 配置状态与改名隔离验证（2026-09-28）

- `node scripts/test-mapping-constructor-state.cjs`：14项；使用生产结构体和枚举，撤回旧类替身导致的缺名异常结论。
- `node scripts/test-config-rename.cjs`：6项；OtherConfig/ProcessDomain改名原方法，Save为计数/异常替身。
- 两项已加入 `node scripts/verify-all.cjs`。需要Windows .NET Framework C#编译器；可用CSC_EXE指定路径。仅两个结构体构造器补 : this() 适配C#5，不修改生产源码。
- `node scripts/verify-mapping-recovery-browser.cjs` 和 `node scripts/verify-module-source-explorer-browser.cjs` 检查页面导航/精确片段，不能替代设备恢复验收。

设置提交：`node scripts/test-config-submit.cjs`，8项原方法隔离断言；仅空条件调用为C#5展开，其余Save/Start/UI均为受控替身。已加入verify-all，不涉及硬件或磁盘配置写入。

页面盘点：`node scripts/build-programming-page-inventory.cjs --check`，仅核对已定位切页方法的创建语句、主文件声明与Save词法候选。点胶列表：`node scripts/test-epoxy-list-save.cjs`，9项原方法隔离断言，不含真实UI/序列化/硬件。两项均已加入verify-all。

## 编程页面提交与输送配置校验（2026-09-28）

- `node scripts/test-transport-config-guard.cjs`：抽取五个子段校验、聚合方法和 UcInput.Confirm，编译运行32种整体有效性组合；配置/UI/保存为隔离替身，禁止视为设备验收。
- `node scripts/verify-programming-confirm-review.cjs`：校验20个 Confirm 主体与源码文件摘要、行区间，以及32项测试报告。
- `node scripts/verify-all.cjs`：已纳入以上两项，本轮完整执行通过。
- 本轮浏览器回执：`programming-confirm-browser-check.json`；只验证总入口导航、目标文件存在、无脚本错误及1440/850/390宽度无横向溢出，没有声称真实设备或全部图的视觉验收。
- 新专题入口：`programming-confirm-review.md`；结构化依据：`programming-confirm-review.json`。原552条关系/940段模块快照计数未增加；独立专题20个快照不要重复计入全工程完成率。

## 配置到生产启动门槛（2026-09-28）

- `node scripts/test-process-start-gate.cjs`：原 ProcessDomain.CheckIsReady 的14项隔离测试；仅提示字符串做C#5适配，输入配置为显式构造替身，非真实机台运行。
- `node scripts/build-config-production-gates.cjs --check`：核对14个指定方法的文件摘要与原文、测试报告及确定性生成页面。
- `node scripts/verify-config-production-gates-browser.cjs`：从总入口实际点击到页面，核对全部14段带行号源码，验证搜索和1440/850/390窗口无页面横向溢出；结果见config-production-gates-browser-check.json。
- 前两项已纳入 `node scripts/verify-all.cjs`，本轮全流程通过。
- 面向工程师的入口：config-production-gates.html；说明：config-production-gates.md；结构化证据：config-production-gates.json。它是源码索引，不替换既有Archify自动化图，也不计为全工程/硬件验收。

### 启动门控下层扩展（同日后续）

- `node scripts/test-process-gate-composition.cjs`：9项对照测试，抽取ProcessDomain检查、真实S2ActionNodeController检查及启用步骤过滤属性；独立比较返回值，不等于完整Machine.Start联调。
- `node scripts/build-config-production-gates.cjs --check`：当前28段限定源码，包括属性与集合类型，不再仅指前一轮14个方法。验证两份报告（制程14项、两层门控9项）和原文摘要。
- `node scripts/verify-config-production-gates-browser.cjs`：当前28段逐字原文、FindAll搜索、实际入口跳转和三种窗口宽度均通过。
- `node scripts/verify-all.cjs`：已新增两层门控测试，本轮全部通过。
- 尚未声称：胶材有效期检查、数组Find扩展的具体实现、全部辅助状态形成、第三方持久化或设备运行均已完成。相似名称的旧System2ActionNodesService不得替代实际属性声明指向的S2ActionNodeController作为该启动路径证据。

## 2026-09-28 示教与S2预点胶增量

最新config-production-gates范围为46段（替代此前14/28段的当前数量）。复验：先运行node scripts/test-assistant-predispense-gates.cjs，再运行node scripts/build-config-production-gates.cjs及node scripts/verify-all.cjs，最后node scripts/verify-config-production-gates-browser.cjs。新增19项原方法隔离测试只覆盖状态和报警；不覆盖DoWork硬件执行。页面校验包含源码哈希/逐行内容及浏览器检索和窄屏布局，不等于整机验收。

## 2026-09-28 首轮与点位分配增量

当前配置生产索引扩展为53段（此前46为上一增量）。新增node scripts/test-s2-predispense-allocation.cjs，13项原方法隔离测试，已加入verify-all；其报告绑定原文件与片段哈希。首轮标志和主点胶调用者为静态复核，不计入13项点位测试。运行生成器、verify-all及源码页面浏览器检查后再交付。

## 2026-09-28 插补、检测和局部重试增量

源码索引当前62段；9段新证据为静态复核，未新增运行测试。专题时序图14条消息绑定证据JSON。node scripts/verify-s2-predispense-sequence.cjs检查源文件哈希、消息覆盖和最终Archify交付SHA，已加入verify-all。

Archify sequence交付通过9/9检查、0错误/0警告。用ARCHIFY_CHROME指向本机Edge执行visual-check，四种桌面尺寸通过；实际查看最终1440×900浅色及2048×1320深色截图，未见遮挡或越界。浏览器自动证据不等于源码语义或设备运行验收。回执保留specification/artifact的SHA与字节数；不要编辑生成HTML。

## 2026-09-28 节点重取、预处理与视觉副作用增量

当前专题75段精确源码；新增test-s2-node-selection.cjs的9项隔离检查，已加入verify-all。InitCurrentMessage仅计数替身，不是实际仓库初始化测试。EpoxyPretreatment、视觉报警事件和GuGao末尾为静态复核；SDK、设备与数据库未运行。

本轮verify-all通过；源码页75段逐行浏览器检查、搜索导航及1440/850/390宽度无溢出。更新Archify时序图终止副作用说明，14条消息保持源码映射，9/9 showcase检查且零错误警告；四桌面尺寸通过，最终1440浅色及2048深色截图已人工查看，未见遮挡。较小窗口中的图中文字可通过查看器缩放阅读。

## 2026-09-28 完整驱动指令构造增量

配置生产索引当前79段。GuGaoDrive.Interpolation的1098–1594行已完成限定静态复核；ObjectHelper.Clone的本地BinaryFormatter实现已定位，完整对象图复制仍未运行验收。时序图call-4补充准备、规划及指令循环源码映射，图形拓扑未改。

新增node scripts/test-gugao-command-loop.cjs：提取1430–1511原循环，11项断言通过。SDK、消息框、指针封送及输入类型为受控替身；不覆盖初始化、原生内存有效期、真实命令执行或硬件。临时C#编译运行有15秒上限且退出后清理测试文件。

本轮node scripts/verify-all.cjs退出0并输出PASS；node scripts/verify-config-production-gates-browser.cjs通过79段内容及导航搜索、1440/850/390宽度检查。新增证据均绑定原文件SHA和精确行段。生产源码未更改。下一步相机识别内部、实际上下文初始化和对象图边界，再推进剩余示教/持久化。

## 2026-09-28 视觉采集、算法分派与上下文增量

专题当前90段。新增控制器重试、VisionDefect服务、PREntity硬件执行/采集、EpoxyDetectAlg关键结果分支和上下文来源及项目引用证据。视觉子项目在trunk内并由ZX2200项目引用；未证明部署二进制身份或现场配方算法类型。

新增node scripts/test-vision-defect-retry.cjs，7项原循环隔离断言通过；日志调用为C#5兼容省略，其他服务/延时/上下文为替身。未运行实际光源、相机、VisionMaster/Halcon、存图或上下文初始化。PREntity文件按gb18030解码用于阅读，原始字节SHA仍校验，生产源码未转换编码或修改。

verify-all通过；浏览器首次检查因新增FindAll源码使旧单命中断言失效。现按证据算预期ID集合并与实际结果严格比较，重新检查通过90段逐行内容、总入口导航、搜索以及1440/850/390无溢出。时序图call-6补采集调用链来源，生成图本身未变。

下一步：剩余视觉辅助分派/流程文件、实际上下文场景和完整复制对象图，再衔接全部示教委托/持久化；设备、构建和实际配置验收仍未完成。

## 2026-09-28 视觉辅助与胶量模板增量

- `pwsh -NoProfile -File scripts/inspect-epoxy-template.ps1 -Check`：只读复核原始PRC归档、XML和13模块/15连接/92订阅。
- `node scripts/verify-epoxy-template.cjs`：检查模板到10图节点/9汇总边的完整映射、文件哈希及Archify生成与浏览器回执；纳入verify-all。
- 源码阅读器扩展至98段。本次未新增硬件或算法运行测试，既有隔离测试结论不扩大。
- 最终模板图1440×900浅色和2048×1320深色截图已审阅；分支按声明连接展示，脚本、条件值和实际配方仍明确未验证。

## 2026-09-28 S2上下文更新与复制对象图

- `node scripts/test-s2-context-update.cjs`：逐字抽取S2ActionNodeController.cs 930–974行；14项原方法隔离检查，涵盖对象引用绑定、缺失匹配、重复标识、局部字段残留和异常边界。夹具记录在scripts/s2-context-fixture.cs.txt，报告记录源码与夹具SHA256。
- 仓库替身、数据容器、启用过滤及提示计数器均在报告中披露。没有执行实际加载、Fody织入、任务循环或硬件。
- 已纳入verify-all及阅读器生成门控；源码阅读器扩至108段。序列化对象图仅为声明级复核，不计作真实配方克隆通过。

## 2026-09-28 预处理调用传播与数值边界

- `node scripts/test-epoxy-pretreatment.cjs`：抽取原EpoxyPretreatment、ObjectHelper.Clone、EpoxyApplicationLocation及真实胶型枚举，执行14项隔离检查。
- 最小胶型根对象和坐标类为替身；额外非序列化字段仅用于夹具故障注入，不是生产类成员。报告记录四处源码与夹具SHA256，不声明完整实际配方克隆已通过。
- 3个预处理入口、8个控制器调用点及S1/S2结果分派已静态复核。源码阅读器122段；统一验证包含新增测试、源码哈希、夹具哈希及页面生成一致性。
- 原方法数值边界不等于已证实现场可达；没有执行生产设备、试胶或保存按钮。

## 2026-09-28 试胶提交与胶型名称解析

- `node scripts/test-epoxy-confirm.cjs`：11项检查；原Confirm仅等价改写一处空条件表达式，验证内存赋值顺序、两次保存委托和中断边界。
- `node scripts/test-epoxy-name-resolution.cjs`：7项检查；原Find无改写，验证缺失名称删除、索引跳过、对象引用复用及异常后的部分修改。
- 控件、仓库与Save使用替身；真实速度控件10–500、延迟上限5000已单独登记，故障注入不代表正常界面可达。没有真实写盘或设备执行。
- 两组均纳入verify-all；源码阅读器134段，生成检查绑定源码和夹具哈希。

## 手动试胶图与源码证据

`node scripts/verify-manual-epoxy-trial.cjs` 检查11节点/9关系源码片段及哈希、9项交付检查、四尺寸浏览器回执；`node scripts/build-manual-epoxy-trial-reader.cjs --check` 检查阅读器未漂移。已纳入 verify-all。静态映射和网页检查不验证机械运行。

`node scripts/verify-manual-epoxy-trial-browser.cjs` 验证总入口→源码阅读器→流程图、21个证据区块、搜索以及1440/850/390宽度无横向溢出。本轮 verify-all PASS；Archify deliver 9项通过，visual-check 四尺寸通过；实际查看1440浅色与2048深色截图。

## 预点胶板示教提交链

`node scripts/test-plate-teaching.cjs`：原始Save/Next/Done共16项隔离检查，使用参数/保存/UI替身，不执行设备程序集。
`node scripts/build-plate-teaching-review.cjs --check`：33段文件/行号/原文/SHA校验、生成页面一致性和测试源哈希校验；已纳入verify-all。
`node scripts/verify-plate-teaching-browser.cjs`：总入口、源码片段、搜索、响应式检查。

2026-09-28本轮结果：plate-teaching 16项通过；33段源码与源文件链接检查通过；1440/850/390宽度无横向溢出；verify-all PASS。实际WinForms事件、完整委托、外部保存和硬件仍未运行验收。

## 胶头与吸嘴示教状态专题（2026-09-28）

- `node scripts/test-tool-teaching.cjs`：6项原几何完成委托和按钮隔离检查，已通过。
- `node scripts/build-tool-teaching-review.cjs --check`：27段源码与测试来源一致性，已通过；这两项已加入verify-all。
- `node scripts/verify-tool-teaching-browser.cjs`：总入口导航、27段原文和源码文件链接、筛选、1440/850/390宽度检查，已通过。
- `node scripts/verify-all.cjs`：本轮完整回归通过。
- 已人工查看tool-teaching-source-review.png：完成按钮源码、行号和风险标题可读。
- 测试只执行隔离提取的控制流；拟合算法、保存、UI和设备均为替身，不能代表实际WinForms关闭时序、硬件安全或持久化验收。
- 接手先读tool-teaching-state-review.md，再在tool-teaching-source.html定位geometry-circle和geometry-button；生产代码尚未修改。

## 自动换嘴与示教取放（2026-09-28）

- `node scripts/test-nozzle-exchange.cjs`：14项原编排/示教包装隔离场景；下层机械/界面/检测/保存均为替身。
- `node scripts/build-nozzle-exchange-review.cjs --check`：29段原文、行号、SHA和测试来源。
- `node scripts/verify-nozzle-exchange-graph.cjs`：11节点/11关系源码映射及冻结规格/HTML/浏览器回执。以上三项已纳入verify-all。
- `node scripts/verify-nozzle-exchange-browser.cjs`：入口、29段原文与文件链接、搜索、1440/850/390宽度检查通过。
- Archify deliver为9项showcase检查、0错误/警告；visual-check四桌面尺寸通过。实际查看1440浅色与2048深色截图，独立记录visual-review.json。
- 生产源码没有修改。状态/成功语义与到位坐标风险列入nozzle-exchange-workflow-review.md；不代表硬件复现或修复。


## 辅助视觉示教增量（2026-09-28）

- node scripts/test-vision-teaching.cjs：17项原方法隔离检查，真实默认MatchResult构造函数；其余硬件/标定/UI为替身。
- node scripts/build-vision-teaching-review.cjs --check：19段文件哈希、源码片段与测试回执一致性。PREntity原文件按GB18030解码。
- node scripts/verify-vision-teaching-browser.cjs：门户导航、原文行号、实际文件链接、搜索及三尺寸页面检查。
- 本轮不改生产源码，不把局部测试视为相机算法、对焦终止性或设备到位验收。


## 安全移动隔离验证（2026-09-28）

- node scripts/test-safe-motion.cjs：34项2D/3D/4D与4D本地限位原方法分支测试，编排中的外部运动/高度/限位/信号为替身。
- node scripts/build-safe-motion-review.cjs --check：16段源码及测试回执哈希。
- node scripts/verify-safe-motion-browser.cjs：统一入口、原文行号、文件链接、搜索与1440/850/390宽度检查。
- 不验证实际硬件到位、真实高度配置或线程竞争；不修改生产源码。

- node scripts/verify-safe-motion-graph.cjs：10节点/11关系逐一绑定16段源码ID，并比对四视口浏览器回执和交付HTML哈希。

## 2026-09-30：标记中心与换行

`node scripts/test-wafer-mark-center.cjs`执行76项断言；`node scripts/build-wafer-mark-center-audit.cjs --check`校验55方法、8属性、1枚举、三信号及专题7段源码。两项纳入verify-all。GetCurrentDieMarkCenterG0Pos仅直接探测，不宣称生产调用可达；真实SDK、落盘和设备仍未验收。

## 2026-09-30：原单颗位置生成

`node scripts/test-wafer-next-position.cjs`执行229项断言；`node scripts/build-wafer-next-position-audit.cjs --check`校验56方法、12属性、1枚举、3字段、三信号及专题15段源码。两项纳入verify-all，覆盖原GetNextPosition的首搜/八方向/探测/保存异常及消费者耗尽恢复。形状输入、点运算、SDK、落盘和设备仍未验收。

## 2026-09-30：范围与完整供晶Start

`node scripts/test-wafer-range-init.cjs`执行105项检查；`node scripts/build-wafer-range-init-audit.cjs --check`校验63方法、19属性、2枚举、3字段、三信号和21段专题源码（其中MainForm三段仅静态）。两项纳入verify-all。实际工作Task运行原消费者，双Start用初始化入口Barrier及串行UI替身提供交错，最后原Stop与线程Join。原生UI、上层完整启动/设备仍未验收。

## 2026-09-30：完整正常启动组合

`node scripts/test-normal-start-integration.cjs`执行175项检查；`node scripts/build-normal-start-integration-audit.cjs --check`校验67方法、19属性、2枚举、3字段、三信号和12段专题源码（UI两段仅静态）。两项纳入verify-all。完整原启动/准备包装/输送StartTask接真实供晶Task及原Stop，最后显式Stop和Join；准备帮助方法与输送/其他生产器仍为记录替身。

## 2026-09-30：原准备帮助方法

`node scripts/test-readiness-helpers.cjs`执行303项检查；`node scripts/build-readiness-helpers-audit.cjs --check`核验73方法、22属性、2枚举、3字段、23原信号初始化和38段专题源码（CleanFile一段仅静态）。两项纳入verify-all。原信号复位/关闭/日志/初始化/环境/容量包装接实际供晶Task，所有样本和消费者显式释放/Stop/Join。CleanFile仍为记录替身；域/容量/日志/加热目标、完整输送和UI/设备仍待验证。

## 2026-09-30：原UI启动与模式

`node scripts/test-ui-start-mode.cjs`执行262项检查；`node scripts/build-ui-start-mode-audit.cjs --check`核验80方法、28属性、2枚举、4字段、23信号契约及26段专题源码（Designer五段静态）。两个原按钮接完整准备/Stop与实际供晶Task，所有线程显式结束。静默/值变化/始终同步回调是可控测试契约，原生DevExpress派发和完整输送生产器仍待验收。

## 2026-09-30：完整原输送Start

`node scripts/test-transport-producer.cjs`执行870项检查；`node scripts/build-transport-producer-audit.cjs --check`核验81方法、31属性、4枚举、13字段、23信号契约及30段专题快照。完整656行Start以真实Task.Run接原UI/准备/Stop和真实供晶Task。显式命名/控制器屏障确定调度，所有Task身份保留并等待；不Join池线程。Provider标志和区段声明为原文，完整控制器/SDK、原生UI/设备仍待验收。

## 2026-09-30：原Bond控制器接完整生产器

`node scripts/test-transport-bond-integration.cjs`执行310项检查；`node scripts/build-transport-bond-integration-audit.cjs --check`核验87方法、39属性、6枚举、13字段、23信号契约和46段专题快照。原TransferBondToWaitingUnload及原解夹/双皮带/基础轴包装接完整九任务生产器、UI/准备/真实供晶Task与完整Stop，两条子Task由原WaitAll等待。其他八传输和驱动/传感器/程序/日志/SDK为替身，原生UI、原项目构建和设备仍待验收。

## 2026-09-30：原等待区到出料皮带

`node scripts/test-transport-waiting-integration.cjs`执行1076项检查；`node scripts/build-transport-waiting-integration-audit.cjs --check`核验105方法、42属性、6枚举、13字段、23信号契约和67段专题快照。`node scripts/build-transport-sdk-predicates.cjs --check`核验SDK五方法体/参数/Moving字段及两DLL哈希，只做静态检查。真实父Task 5/6组成Bond到等待区到出料皮带；其余七传输、SDK/控件/程序边界仍为替身或待完成。详见[专项报告](transport-waiting-integration-review.md)。

## 2026-09-30：原等待区到出料Bin

`node scripts/test-transport-bin-integration.cjs`执行578项；`node scripts/build-transport-bin-integration-audit.cjs --check`核验111方法、50属性、6枚举、13字段、23信号契约和81段专题快照。`node scripts/build-transport-bin-sdk.cjs --check`静态核验六AbsoluteMove重载/执行器、可选参数、SDK枚举和两DLL哈希；不执行SDK。实际第五/第七Task组成Bond到等待区到Bin链，其他六传输、原生UI/SDK与设备仍待验收。详见[专项报告](transport-bin-integration-review.md)。

## 2026-09-30：原出料皮带到收板机

`node scripts/test-transport-auto-unloader-integration.cjs`执行287项；`node scripts/build-transport-auto-unloader-integration-audit.cjs --check`核验114方法、53属性、6枚举、13字段、23信号契约和87段专题快照。`node scripts/build-transport-auto-unloader-sdk.cjs --check`静态核验GetInputValue/执行器无参数bool签名、IL与两DLL哈希，不执行SDK。三实际父Task组成Bond到等待区到出料区到收板机链；原第九父Task忽略Exception已验证，其余五传输、原生UI/SDK与设备仍待验收。详见[专项报告](transport-auto-unloader-integration-review.md)。

## 2026-09-30：原点胶到Bond

`node scripts/test-transport-dispense-bond-integration.cjs`执行184项；`node scripts/build-transport-dispense-bond-integration-audit.cjs --check`核验132方法、57属性、8枚举、13字段、23信号契约和111段专题快照。`node scripts/build-transport-dispense-relative-sdk.cjs --check`静态核验四方法、HighAccuracy默认参数及两DLL哈希，不执行SDK。实际点胶/Bond/等待区/收板机父任务形成连续链，构造函数/OpenVacuum仍为替身；其他四传输、原生UI/SDK/设备待验收。详见[专项报告](transport-dispense-bond-integration-review.md)。

## 2026-09-30：原点胶1到点胶2

`node scripts/test-transport-dispense12-integration.cjs`执行276项；`node scripts/build-transport-dispense12-integration-audit.cjs --check`核验136方法、65属性、8枚举、14字段、23信号契约和124段专题快照。沿用RelativeMove静态四方法契约；没有SDK执行。实际五阶段连续链、坐标/标志部分提交和重复事件被验证，构造/Refresh/坐标SDK与原生验收仍待完成。详见[专项报告](transport-dispense12-integration-review.md)。

## 2026-09-30：原入料皮带与Unit生命周期

`node scripts/test-transport-loading-belt-integration.cjs`执行252项；`node scripts/build-transport-loading-belt-integration-audit.cjs --check`核验156方法、94属性、10枚举、15字段、23信号契约和176段专题快照。`node scripts/build-transport-loading-output-sdk.cjs --check`核验Electric输出两个方法/一个仓库DLL静态契约；没有SDK执行。实际六阶段链、原Refresh、构造配置副作用与失败部分状态被验证，子实体/服务/SDK及原生验收仍待完成。详见[专项报告](transport-loading-belt-integration-review.md)。

## 2026-09-30：原送板机与真实超时

`node scripts/test-transport-auto-loader-integration.cjs`执行238项；`node scripts/build-transport-auto-loader-integration-audit.cjs --check`核验159方法、95属性、10枚举、15字段、23信号契约和180段专题快照。沿用Sensor无参bool与Electric必需bool/void静态契约；没有SDK执行。原Stopwatch及5秒阈值、七阶段链、第一父线程Ignore后再次要料、部分HasMaterial/Unit/Save已受控验证，服务/SDK和原生验收仍待完成。详见[专项报告](transport-auto-loader-integration-review.md)。

## 2026-10-01：原料仓推杆及真实子任务

`node scripts/test-transport-loader-bin-integration.cjs`执行288项；`node scripts/build-transport-loader-bin-integration-audit.cjs --check`核验173方法、103属性、10枚举、16字段、23信号契约和203段专题快照。`node scripts/build-transport-loader-bin-sdk.cjs --check`核对9个SDK方法/2仓库DLL的静态契约，未执行SDK。原10秒Stopwatch/Task.Wait、五阶段料仓链、卡料Ignore提前发布、未等待子任务、NoStart保留许可后恢复上料和异常部分提交已受控验证；真实服务/生命周期/SDK及原生/设备验收仍待完成。详见[专项报告](transport-loader-bin-integration-review.md)。

## 2026-10-01：原启动载具检查、记忆、真空与计时日志

`node scripts/test-transport-carrier-map-integration.cjs`执行1355项；`node scripts/build-transport-carrier-map-integration-audit.cjs --check`核验191方法、122属性、11枚举、17字段、23信号契约和242段专题快照。`node scripts/build-transport-carrier-map-log-sdk.cjs --check`核对2个日志Post方法和1个仓库DLL的元数据，未执行SDK。`node scripts/build-transport-unit-services-next-evidence.cjs --check`绑定19段尚未运行集成的实体/服务/程式/模块源码。载具记忆、真空通道差异、真实计时、异常分层、Stop/Pause后提交与两条UI搜索载具五阶段链已受控验证。正式回归与阅读器收尾另见当前验证回执；整体工程/原生/设备验收仍待完成。

## 2026-10-01：实体树、TuService与五子任务初始化

`node scripts/test-transport-unit-services-integration.cjs`运行1011项；`node scripts/build-transport-unit-services-integration-audit.cjs --check`绑定149显式依赖与38仅片段文件、391段原源码和291段阅读器快照。`node scripts/build-transport-unit-services-sdk.cjs --check`核对2个仓库DLL的6方法元数据，SDK未运行。`node scripts/build-transport-unit-lifecycle-next-evidence.cjs --check`核对14段尚未运行的坐标/产品/异形配置/程式源码。旧19段接续文件仍描述载具1355项冻结范围，本轮审计逐段证明已纳入；两套检查数量分开。统一回归与浏览器收尾另行登记。

1011项当前统一回归已实际退出0并PASS，阅读器四宽度通过，见[验证回执](transport-unit-services-integration-verification.json)。后续原坐标113项与产品/异形配置29项独立探针及其来源审计已通过；未登记为当前阅读器专题或加入1011项回归，见[准备进度](coordinate-product-lifecycle-preparation-progress.json)。
