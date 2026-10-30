# ZX2200 项目计划与当前进度

流程图整理增量（2026-10-08）：总目录 [flowchart-catalog.html](flowchart-catalog.html) 已更新为 64 个条目、61 份 Archify 源规格、64 个 HTML；本轮新增 S1 Working 暂停/继续/停止、S1 停止/重启/返工、权限与编辑门控、TransportTask 启动与返回码、S2 任务入口首步故障、StatisticsService 日志生产与持久化、S2 动作节点执行边界、Machine.Start 启动就绪与任务调用链、急停/Stop/任务关闭边界、任务关闭门控、搜晶模式与停止门控、自动换片三路 Retry、输送暂停/Stop 与状态提交、换片名称选择与保存一致性、S1 胶检结果与 Retry/异常传播、S1 点胶 Abort/Fail 与 finally 刷新、S1 胶检重做上下文、S1 分段交互 Pause/Stop、S1 步骤提前提交与关闭查询 19 张专题图，均通过 showcase 9/9、0 错误/警告并绑定对应源码复核文档。当前环境没有 Chrome/Chromium，新增图的自动视觉检查仅生成 skipped 收据；不把它们计入 27 份浏览器视觉证据。该增量扩大已复核范围，但不改变下方整体构建、设备和 29 个源码分组仍未完成的结论。

当前构建进度：[原工程实际Build及复跑](native-msbuild-build-review.md)已定位失败；本轮在隔离源码镜像中用官方 Roslyn/.NET 4.8 引用程序集完成 [AKRS.Calibration](official-net48-calibration-build-review.md)、[AKRS.Galaxy2.LogTest](official-net48-logtest-build-review.md)、带 `MachineSupport` 项目引用的 [AKRS.Galaxy2.AxisCompensate](official-net48-axiscompensate-build-review.md)、[AKRS.Galaxy2.CoordinateSystems](official-net48-coordinate-build-review.md)、[AKRS.Galaxy2.Machine](official-net48-machine-build-review.md)、[AKRS.Galaxy2.AutoFocusing](official-net48-autofocusing-build-review.md)、[AKRS.Galaxy.SoftKey](official-net48-softkey-build-review.md)、[AKRS.Galaxy2.TeachTest](official-net48-teachtest-build-review.md) 和独立 [AKRS.Galaxy2.MachineSupport](official-net48-machinesupport-build-review.md) 构建，均退出码 0；[Akrs.ChangeJson](official-net48-changejson-build-review.md)、[InterpolationMovementTest](official-net48-interpolation-build-review.md)、[AKRS.Galaxy2.PR.Test](official-net48-prtest-build-review.md)、[AKRS.Galaxy2.RealtimeCurve.TestDemo](official-net48-realtimecurve-build-review.md)、[AKRS.Galaxy2.Dispense](official-net48-dispense-build-review.md) 和 [AKRS.ZX2200](official-net48-zx2200-build-review.md) 则分别定位到许可证工具、缺失程序集、项目闭包、DevExpress `.resx`/资源许可证以及主项目闭包阻塞，失败证据已保留；使用原工程已有厂商输入重跑 [Akrs.ChangeJson](official-net48-changejson-zxvendor-build-review.md)、[PR.Test](official-net48-prtest-zxvendor-build-review.md)、[RealtimeCurve](official-net48-realtimecurve-zxvendor-build-review.md)、[Dispense](official-net48-dispense-zxvendor-build-review.md)、[InterpolationMovementTest](official-net48-interpolation-zxvendor-build-review.md) 和主 [AKRS.ZX2200](official-net48-zx2200-zxvendor-build-review.md) 后，缺失程序集和资源错误均已消除；主闭包最终只剩 Dispense/PR 两个逻辑上的 `LC.exe` 许可证编译前置条件（日志出现4次重复摘要），退出码仍为1。完整构建/部署未验收，整体目标未完成。

依赖审计脚本的编码与运行环境已核验：[依赖审计记录](dependency-audit-verification.md)；`pwsh 7.6.5` 下 16 个项目的 806 条外部声明和 13 条项目引用可重放，声明层缺失与未求值范围仍保留。

项目引用缺口已进一步定位：[ZX2200 缺失 Parameters 项目](missing-parameters-project-review.md)；`AKRS.ZX2200.csproj:4110` 指向不存在的 `AKRS.Galaxy2.Parameters.csproj`，相邻 58 个源文件仅作材料证据，未合成项目文件。

在隔离主项目候选中移除该陈旧 `ProjectReference` 后重新构建，仍保持程序集缺失 0，最终只剩 Dispense/PR 的两个逻辑 `LC.exe` 许可证前置条件：[Parameters 引用隔离修复](official-net48-zx2200-parameters-repair-review.md)。因此该引用需要清理，但不是当前主闭包失败根因；生产工程未修改。

原始源码产物闭包已在隔离候选中修复并复核：[16 项依赖/API 闭包修复](original-source-artifact-reference-closure-repair-review.md)；将 `WindowsFormsApp1` 对 ZX2200 的版本身份候选替换后，16 项产物的 254 个 AssemblyRef、15 条产物间边全部解析，缺失和身份不一致均为 0。该结果不替代联合 MSBuild、资源许可证、部署或运行时验收。

Main 的程式节点初始化已继续展开：[六个初始化方法复核](main-init-program-nodes-review.md)确认入口顺序、六次 Singleton 实例重置、六个配方文件名及 Wafer 记忆清理分支；只读元数据还确认了 `Singleton<T>` 的静态字段和 `GetInstance/Load` 接口，JSON 读取、实际配方与运行中重载仍待验收。

Main 的 PR 重载路径已继续展开：[PR 清单与复制复核](main-pr-reload-review.md)确认缺失或初始化失败的 PR 不会阻止 `PrInitSuccess`，`LoadDispensePr` 当前为空操作，复制流程会复制 `.prc`、克隆实体并加入仓库但不检查复制返回值；真实 VM、配方 PR 文件和设备仍待验收。

配方重建与生产任务入口又补了一条源码锚定：[配方域重建复核](recipe-domain-reconstruction-review.md)确认同一 `RecipeID` 的选择会保存配置但跳过 `ReLoadRecipe`，新配方按六域固定顺序重置单例；在线/离线 PR 分支、晶圆记忆清理，以及 `Machine.Start` 到输送载具检查和任务启动的顺序已登记。该轮只读源码哈希审计，实际 VM、UI、SQL、设备、完整生产循环和原工程构建仍未验收。

模块复核登记修复后，嵌入式源码阅读器已重新生成并通过 `--check`：[阅读器漂移修复](module-source-explorer-repair.md)；29 个模块、552 条关系、940 段证据已重新绑定。

当前原生增量：[原Program.Main离线首次启动及退出](native-program-main-entry-review.md)通过，两轮41项，来源台账19106；在线／部署及客户区布局未验收，整体目标未完成。

前序原生增量：[原主窗口合成截图及裁切](native-mainform-layout-review.md)完成复现，四轮47项，来源台账18705；客户区布局未验收，整体目标未完成。

前序原生增量：[原正常监控与消费者](native-monitor-consumer-startup-review.md)通过，两轮40项，来源台账18295，在线／SQL／整UI范围保留，整体目标未完成。

前序原生增量：[原退出与存活消费者](native-exit-consumer-pending-review.md)通过，两轮25项，来源台账17846，实际未写完图片及SQL范围保留，整体目标未完成。

前序原生增量：[原关闭保存及真实退出](native-mainform-close-save-review.md)通过，两轮60项，来源台账14818，失败仍退出和未保存项边界保留，整体目标未完成。

前序原生增量：[原PR初始化任务失败边界](native-pr-init-boundary-review.md)通过，两轮31项，来源台账14446，成功VM与关闭保存链待验收，整体目标未完成。

前序原生增量：[原主窗体加载与SDK刷新](native-mainform-context-review.md)通过，两轮40项，来源台账14205，监控与整窗体布局边界保留，整体目标未完成。

前序原生增量：[原新建配方、拷贝及切换确认](native-recipe-create-copy-review.md)通过，两轮163项，来源台账13651，原SDK失败与调度差异保留，整体目标未完成。

前序原生增量：[原配方模态对话框](native-recipe-dialog-events-review.md)通过，两轮89项，来源台账12916，独立SDK刷新异常保留，整体目标未完成。

前序原生增量：[原界面停止与任务关闭恢复](native-ui-stop-recovery-review.md)通过，两轮572项，来源台账12534，整体目标未完成。

前序原生增量：[原界面离线配方重载](native-recipe-ui-reload-review.md)通过，两轮48项，来源台账12379，整体目标未完成。

前序原生增量：[运行中原任务程式重载](native-recipe-live-reload-review.md)通过，两轮93项，来源台账11965，整体目标未完成。

前序原生增量：[原输送配置与整机生产环境组合](native-transport-environment-review.md)通过，两轮3141项，来源台账11799，整体目标未完成。

前序原生增量：[原进出料握手与异常循环](native-inout-handshake-review.md)通过，两轮550项，来源台账11622，整体目标未完成。

前序原生增量：[原料仓握手与实际编辑配置聚合](native-bin-handshake-readiness-review.md)通过，两轮834项，来源台账11474，整体目标未完成。

前序原生增量：[原Loader/Unloader入口与保存顺序](native-loader-unloader-entry-review.md)通过，两轮773项，来源台账11381，整体目标未完成。

前序原生增量：[原晶圆/传输任务入口](native-wafer-transport-entry-review.md)通过，两轮660项，来源台账11165，整体目标未完成。

前序原生增量：[原Flip/Slide入口及状态日志顺序](native-aux-task-entry-review.md)通过，两轮487项、106原任务/轮；来源台账10974，整体目标未完成。

前序原生增量：[原S2任务入口及首步故障](native-s2-task-entry-review.md)通过，两轮497项、122原任务/轮；来源台账10857，整体目标未完成。

前序原生增量：[原任务关闭与S1真实结局](native-machine-task-closure-review.md)通过，两轮310项、256状态夹具矩阵及8实际Task/轮；来源台账10761，整体目标未完成。

前序原生增量：[原整机环境及初始化门](native-machine-environment-review.md)通过，两轮123项、六层首失败顺序与真实信号复位；来源台账10685，整体目标未完成。

前序原生增量：[原载具力控与点位就绪](native-carrier-readiness-review.md)通过，两轮100项、真实载具计划/JSON、力控/点位门；来源台账10544，整体目标未完成。

前序原生增量：[原S2就绪检查](native-s2-readiness-review.md)通过，两轮56项、完整离线就绪与Option.Count检查缺口；来源台账10455，整体目标未完成。

前序原生增量：[原检测配置持久化与就绪](native-inspection-readiness-review.md)通过，两轮108项、12重载配置/就绪矩阵及3原胶检DoWork，来源台账10344；完整启动/业务/设备仍待验收。

前序原生增量：[原S1完整胶检节点](native-s1-defect-outcomes-review.md)通过，两轮109项、每轮15次完整胶检DoWork及3真实Task，模式缺口/异常传播与原结果映射已核验，来源台账10250；完整业务/重试/设备仍待验收。

前序原生增量：[原S1停止与返工恢复](native-s1-stop-recovery-review.md)通过，两轮51项、每轮6真实Task、原Stop释放等待与重启/返工部分重置已核验，来源台账10164；完整业务/重试/设备仍待验收。

前序原生增量：[原S1点胶步骤提前提交](native-s1-step-commit-review.md)通过，两轮85项、4真实Task及12点胶/6预点胶调用每轮，来源台账10096；完整业务/重试/设备仍待验收。

前序原生增量：[原S1 Working任务循环](native-s1-task-loop-review.md)通过，两轮126项、13真实Task/317次动作尝试每轮，来源台账10006；完整业务/重试/设备仍待验收。

前序原生增量：[34种注册节点前置条件](native-node-preconditions-review.md)已通过，两轮584项/每轮544次条件调用及一次Pick离线DoWork，来源台账9836；完整任务链仍待验收。

前序原生增量：[组件配方与全部34注册接收者选择](native-recipe-action-selection-review.md)已通过，两轮31655项、5888消息/轮、原Interactive五次短DoWork，来源台账9734；其他节点与生产Task未执行。

前序原生增量：[准确S1/S2消息到节点实例选择](native-action-selection-review.md)已通过，两轮5655项、848消息/轮、26种实际接收者，最新来源台账9659；节点DoWork/生产Task未执行。

前序原生增量：[算法实例选择与类型属性差异](native-algorithm-selection-review.md)已复现并核验，两轮163项、65个对象/轮，最新来源台账9609；FindModel/VM/完整任务未执行。

已验收的阅读器：[完整源码与虚/接口候选阅读器](module-source-explorer-dispatch.html)已通过全量来源与浏览器核验。17518处原调用、675集合/3257候选行可浏览；阅读器候选接入已完成。最新[进度](dispatch-source-reader-progress.json)登记9513个来源绑定，运行时实例/配置、完整业务和构建/设备验收仍待完成。下列历史记录保留各轮当时范围，整体目标未完成。

## 最新增量：原产品初始化接完整启动与实体输送

原产品声明增量：1328项受控检查通过，原1303项名称/顺序/表达式原样重跑，新增25项默认配置/实体/两条UI检查。8段原产品初始化及正确编辑枚举、另6段静态构造/异形根声明接完整组合；512记录/511唯一源码含269方法、198属性、19枚举、24字段、2结构体与23信号契约。原产品字段/替身名称已替换，默认普通空焊点树与异形Z20根、默认未教拒绝及已教启动共同验证。真实SDK Singleton/JSON、完整配置/AOP/PR/VM/动作与原构建/部署/原生UI/设备仍待完成。 见[专项报告](transport-product-declarations-integration-review.md)与[进度](transport-product-declarations-integration-progress.json)。专项及来源审计通过；统一回归与四宽度阅读器均通过；见[1328项验证回执](transport-product-declarations-integration-verification.json)。当前40专题、3817段专题快照。旧192输入保持原哈希，新组合197输入。独立原生产品36项/两份SDK为不同运行范围，不相加认定覆盖。整体16工程、29组、1436个C#文件与13项要求仍未完成。


后续完整焊点原生准备：[23个完整原文件与实际产品/焊点JSON](bond-config-native-source-progress.json)，两份DLL各56项相同断言通过（原36项保留、新20项，112次执行），见[专项报告](bond-config-native-source-review.md)。原完整SingleBondPositionConfig替换原生探针中的焊点适配器。早期无效曝光值可丢失焊点记录并使空列表汇总通过；不兼容Name对象则令实际产品ReadGenericObject返回null，真实Singleton恢复空焊点/未教TU默认产品，焊点汇总通过但TU拒绝。该数据准备未加入1328统一回归或40专题/3817快照；Fody/外部依赖/完整启动SDK组合与原工程构建/部署/原生UI/设备仍待完成。

后续完整组合原生准备：[Framework1328与实际SDK启动58项](transport-full-framework-sdk-progress.json)及[专项报告](transport-full-framework-sdk-review.md)已完成独立验证。完整受控1328项在原生CLR中执行，名称/顺序相同；实际SDK分支在两份DLL独立进程中各58项通过（116次执行），原产品/仓库对象与列表实际Save/Load接两条原启动入口、单叶实体、五次回零和真实供晶Task。512记录/511唯一源码正文保留，来源审计绑定269输入。SDK分支仅执行58项，旧1328项在该分支只编译；完整原配置/焊点类组成、点类型、Fody/AOP/PR/VM/动作/设备边界仍有适配器。该准备不加入已冻结1328统一回归或40专题/3817快照；原工程构建/部署/原生UI/设备与全目标仍待完成。

后续完整原配置SDK准备：[37个完整原文件、实际SDK与原启动142项](transport-whole-config-sdk-progress.json)及[专项报告](transport-whole-config-sdk-review.md)通过，两份DLL各142项（284次执行、每份28次原启动调用），重新编译产物哈希一致。原产品直接继承SDK单例/保存，完整原仓库直接调用SDK JSON，AOP/状态/信息/坐标/辅助实现接同一组合；移除48个重建声明，512原提取正文保持，新增8段实体成员。已教TU下，非法曝光导致焊点记录丢失后，空焊点列表在两条原启动方法中继续启动；非法Name回退未教默认产品则拒绝。缺陷证据未等同实际窗口/部署/设备验收，生产源码未改。独立142项不加入冻结1328统一回归或40专题/3817快照；完整原实体/检测剩余声明、Fody/外部依赖、原构建/部署/原生UI/设备继续待办。

后续完整原实体/检测SDK准备：[45个完整原文件与实际SDK187项](transport-whole-entity-sdk-progress.json)及[专项报告](transport-whole-entity-sdk-review.md)通过，两份DLL各187项（原142项名称/顺序保留、新45项，374次执行，每份34次原启动调用），重编译产物哈希一致。五层实体、完整PostBondInspection/AdjustConfig/BondEnum替换8个重建声明及坐标包装器；512段既有正文与上一轮8段实体成员保持原样。完整状态递归、信息清理、补偿访问、三位舍入阈值/检测频率及背崩Able/UnAble/null经实际SDK保存重载后的两条原启动入口已验证；未完成或null背崩示教在任务启动前拦截。307输入冻结，生产源码未改；派生探针的旧夹具兼容迁移不修改冻结1328，旧1328在本分支仅编译。本独立187项不加入正式1328或40专题/3817快照。以上准备的剩余范围以本段为准：下一步原S1/S2动作控制器InjectSteps与步骤模型，再推进完整动作/PR/校准/导出、Fody/外部依赖、原工程/部署/原生UI/设备。16工程、29组、1436个C#文件及13项要求仍未完成。

后续完整原动作控制器SDK准备：[54个完整原文件与实际SDK278项](transport-whole-action-sdk-progress.json)及[专项报告](transport-whole-action-sdk-review.md)通过，两份DLL各278项（原187项名称/顺序保持、新91项，556次执行，每份40次原启动调用），重编译产物哈希一致。完整S1/S2控制器、流程/步骤/系统/产品域及动作基础/信息/消息替换三个流程/注入夹具；512段既有正文与8段实体成员保持原样。实际流程Save/Load/改名、禁用/重复/追加注入、原自动生成及两控制器各八种排序已验证；禁用且Index无效仍经两条原启动入口拦截。null步骤名、null功能标记和空计划的原就绪行为已登记，完整域/SelfCheck关联仍待验收。确定性文件锁验证保存失败时保留数据/清理临时文件/解锁恢复；两次意外File.Replace失败日志保留，唯一根因和精确失败DLL证据有限。331输入冻结，生产源码未改；本独立278项不加入冻结1328或40专题/3817快照。以上准备的剩余以本段为准：下一步完整动作目录/实际节点、完整域就绪/相对贴片/重做及IO稳定性，再推进PR/校准/测量、Fody/外部依赖、原工程/部署/原生UI/设备。16工程、29组、1436个C#文件及13项要求仍未完成。

后续原目录初始化核验：[5个完整原文件/两份SDK各119项](catalog-init-sdk-progress.json)及[报告](catalog-init-sdk-review.md)通过（238次放置、重编译产物哈希一致、86输入冻结）。原S1/S2目录分别注册15/19项；三次Init使四个分层列表从3项增至9项，重复相同节点引用；任一分层列表null会在总列表刷新后异常并留下部分追加。37个具体节点的构造/DoWork仍为拒绝执行边界，仅验收目录构造/Init，不证明生产发生重复调用。完整节点组合保持122个完整原文件、123单元、53真实引用；[最终编译失败记录](whole-node-source-compile-progress.json)保留642条错误/真实exit1及183输入快照，未运行，不以目录专项代替完整节点验收。生产源码及既有54文件/278项、冻结1328、40专题/3817快照未改，计数不相加。以上后续准备的剩余以本段为准：继续实际域/控制器/配方依赖和类型遮蔽，核验原节点非设备分支、完整就绪/SelfCheck、PR/校准/测量、IO稳定性及原工程/Fody/部署/UI/设备；16工程/29组/1436文件/13项整体仍未完成。

本轮继续保留正式 642 错误基线，同时在隔离源码组合中推进到 v120：177 个源码输入、70 个引用，错误降至 448；v120 加入 SlideFluxer、ForceTorque、SearchChip/PickRefEnd 和 RtuConnectConfig 的真实源码，退出码仍为 1，DLL 未验收。该候选只更新隔离进度，不替换正式失败基线，也不计入 119/278/1328 或专题快照。

v120 依赖闭包继续做了 10 个小型真实源逐个追加探针；没有候选降低 448 个错误，`IPTController` 与 `EpoxyMaterialProgram` 仅保持原错误数，其余候选上升到 449–461 个错误。候选产物均保留为失败日志，不纳入整节点或正式回归；后续应转向仍未完成的完整域/生产组合、构建织入、部署和设备边界，而不是把这些候选当作可接受构建。

后续完整原源码编译准备：[主程序1137份与PR SDK85份原源码](full-original-source-build-progress.json)及[报告](full-original-source-build-review.md)通过直接编译，共1222份原源码、2个工程；没有源码筛选、改写或程序集内夹具，重编译产物哈希一致，1465项输入冻结。独立原生61项覆盖载具就绪、取片/贴片参数与机器默认值，保留载具构造空Flip/名称覆盖及非法枚举就绪证据。依赖SDK同版本不同API已核对，重编译完整PR后解决主程序最后两条错误。首次厂商元数据预读失败保留，按需加载通过不等于厂商运行库验收。旧122文件/642错误快照原样保留，1328/278/119及40专题/3817快照不加计数。本次未运行MSBuild、资源或Fody/PostSharp织入，缺失Parameters项目、原目录/具体节点构造/DoWork、主入口/UI/设备仍待验收。以上后续剩余以本段为准：推进其余14工程/214份源码及原域/动作、PR/校准/测量、IO稳定性、构建资源/织入与原生UI/设备；16工程/29组/1436文件/13项整体仍未完成。

后续16工程原始编译项核验：[全部1410份原Compile项](all-project-source-build-progress.json)及[报告](all-project-source-build-review.md)通过独立源码发射；新增14工程/188份源码真实退出码均0、重编译14个产物哈希一致。文件系统1436份中26份未纳入原编译配置，逐文件哈希已登记。新增484项冻结输入和父1465项分开绑定；原源码未改、程序集内无夹具。新增产物只编译，61项父非设备检查不增加；1328/278/119、旧122文件/642错误与40专题/3817快照保持。依赖仍含缓存元数据，尚未统一换成本次新产物，不等同16工程联合构建；缺失Parameters和targeting pack、资源/织入/MSBuild、原生UI/设备仍待验收。以上后续剩余以本段为准：核验全部新源码产物之间的依赖/API一致性，再推进原域/动作、PR/校准/测量、IO稳定性及原工程/部署/运行；29组/13项整体仍未完成。

后续新源码产物引用兼容准备：[16工程1410项与原生98项](fresh-project-dependencies-progress.json)及[报告](fresh-project-dependencies-review.md)通过。130处源码工程元数据引用放置（含闭包，115处换路径）全部换成新原源码产物，原ProjectReference口径不变；16个产物重放哈希一致。15个与上轮产物一致，插补测试改绑主程序1.2.0.0→1.5.0.0，方法指令/局部类型未变。独立原生61项模型与37项轴数值检查名称/顺序保持，移除3个SDK/路径测试声明，实际5个源码程序集加载位置核验通过；退化拟合约1.4e31/NaN/Infinity及空/共线圆拟合NaN记录保持。新增103项冻结输入绑定父1949项。生产源码、1328/278/119、旧122文件/642错误和40专题/3817快照保持；未执行程序入口/Load/Save/UI/视觉流程/设备。本次是元数据引用兼容准备，缺失Parameters/targeting pack、MSBuild资源/织入与完整运行仍待验收。以上后续剩余以本段为准：原坐标几何/VM边界、原域/具体动作、PR/校准/测量、IO稳定性与资源/织入构建；29组/13项整体仍未完成。

后续完整原坐标原生核验：[13份完整原源码/124项几何检查](coordinate-native-source-progress.json)及[报告](coordinate-native-source-review.md)通过编译与原生重放；实际SDK点/TransformTool无替身，范围含普通/从属层级、XYZ修正/弧度、null/NaN及限时父级环观察（含3项测试线程控制，不据100ms推断永久不终止）。正确UTF8解码使旧输入162份元数据预读通过，明确早期Unicode路径误读原因；旧失败快照保持。5项真实VM/标定尝试失败，真实exit1重放一致：MVD_Algorithm.dll及所需MVDSDK.VMControls.BaseInterface加载缺口；列表引用/null在Save失败前已提交，隔离目录无标定文件。现有VMControls.BaseInterface名称/公钥不同，不能直接替代。新增36项冻结绑定父2052项；生产源码、1410项/98项、1328/278/119及40专题/3817快照保持，计数不相加。以上后续剩余以本段为准：资源/织入构建与匹配的SDK运行依赖，原域/具体动作、PR/校准/测量、IO稳定性及部署/UI/设备；29组/13项整体仍未完成。

后续原工程资源准备：[16工程388个原资源/1498个数据项](project-resources-progress.json)及[报告](project-resources-review.md)通过。实际MSBuild仅评估Debug|AnyCPU资源名称，原生Framework序列化全部388个.resx，真实DevExpress21.2.7身份匹配；保持1410份原Compile源码，16个隔离产物嵌入387个中性资源，另生成1个版本1.5.0.0/cs卫星程序集。17个产物原生回读全部流字节哈希及1498个键/类型，重放序列化、编译、回读真实exit0且哈希一致；cs命名分类本身不证明窗口故障。新增1090项冻结输入绑定父2088项，共3178项；早期三处工具脚本失败保留并限定证据。1498不是业务断言，原1410/98/124、1328/278/119、旧122文件失败与40专题/3817快照保持，生产源码未改。5个声明licenses.licx尚未编译，Win32图标/清单/版本、targeting pack、完整MSBuild/restore与Fody/PostSharp织入未验收；未执行主入口/UI/轴/相机/设备。以上后续剩余以本段为准：许可证/织入与匹配SDK依赖、完整域/具体动作、PR/校准/测量、IO稳定性及原工程部署/UI/设备；16工程/29组/1436文件/13项整体仍未完成。

后续原许可证/现有织入包失败定位：[5个实际LC目标与2个Fody兼容性目标](license-weaving-probe-progress.json)及[报告](license-weaving-probe-review.md)保留真实失败。5个原工程实际CompileLicxFiles均exit1/MSB3086，SdkToolsPath及目标查询的注册表位置未找到LC.exe，无许可证输出；20条/12种许可控件仅核验真实DevExpress21.2.7元数据，不证明许可证有效。Main/PR隔离副本导入现有Fody6.0.5.targets均被MSBuild16门槛拒绝，目标报告15为默认属性，不代表安装MSBuild15；未绕过守卫/执行WeavingTask，副本未变。该诊断不同于既有NuGet记录的Fody6.6.4原流水线。复跑7个失败结果相同、元数据一致，新增37项冻结绑定父3178项，共3215项；记录器/证据审计exit0不能当构建通过。父388资源/1498项验收保持，生产源码未改，业务计数及历史冻结保持。以上后续剩余以本段为准：匹配构建/厂商运行依赖，以及可独立推进的完整域/具体动作、PR/校准/测量、IO稳定性、原部署/UI/设备；16工程/29组/1436文件/13项整体仍未完成。

后续完整原程式就绪/仓库原生核验：[1137源码Main与实际SDK58项](native-program-readiness-progress.json)及[报告](native-program-readiness-review.md)通过；16个资源版源码程序集物理绑定核对，宿主启动目录自然隔离原PathConfig，不替换路径/单例/仓库/程序类型。实际NozzleShelfProgram在两个OnBondHead槽位仍true，Option.Find.Count最多1；取工具方法却异常。完整Bond.SelfCheck使用实际点Equals，零坐标上/下视拍照点均放行，选下视时null上视点仍先异常。PostBondProgram删除相邻失效名时跳过未完成项，连续就绪true→false；3个原仓库实际SDK保存/重载，锁定失败保留旧字节、解锁恢复。固定测试数据时间后重编译EXE及58项/3JSON哈希重放一致，44项新增冻结绑定父3215项，共3259项；首轮两处测试属性名错误、宿主启动失败与30项后Equals假设失败限定证据保留。此58项不同于历史SDK58，不合并1328/278/119/98/124或40专题3817；生产源码未改，未执行原入口/UI/PR算法/具体节点DoWork/轴/相机/设备或织入，旧LC/Fody/VM失败保持。本隔离结果不证明现场事故。以上后续剩余以本段为准：完整域/动作、就绪负分支、PR/校准/测量、IO稳定性、匹配构建与运行依赖、原部署/UI/设备；16工程/29组/1436文件/13项整体仍未完成。

后续完整原动作/域原生核验：[251项完整控制器与目录](native-action-controller-progress.json)及[报告](native-action-controller-review.md)通过；37个原始具体节点、S1/S2两个完整域由实际SDK单例构造，16个源码资源程序集物理绑定。公开Init各8组合形成16份53消息排程，独立核对遍历/交错次序；真实普通TransportUnit构造树接两个控制器步骤注入。原宿主启动目录自然隔离配置，硬件/环形限位文件运行前不存在且实际硬件仓库前后为空，未编译具体节点替身。返工只重置首个重复消息且后项异常保留前项修改；相对排序重建视觉消息丢失Finished，缺失后续步骤时已移除前项；两个步骤注入保留已删除工序的旧键。返工/相对/Finish的私有普通消息状态用反射检查/注入，没有替换路径/单例/类型或未初始化对象。251项、产物和只读IL重放一致，33新增冻结绑定父3259项，共3292项；首次25条宿主编译错误原证据保留。原源码未改，不合并1328/278/目录119/原生58/98/124或40专题3817；原入口、具体DoWork、硬件/UI/织入尚未执行，旧LC/Fody/VM失败保持。以上后续剩余以本段为准：完整启动/输送域与当前消息衔接、具体动作及暂停停止/下层算法、就绪负分支、PR/校准/测量、IO稳定性、匹配构建依赖及原部署/UI/设备；16工程/29组/1436文件/13项整体仍未完成。

后续完整输送上下文/离线原节点核验：[180项原生检查](native-transport-context-progress.json)及[报告](native-transport-context-review.md)通过；完整输送域/程式/控制器/模组构造接5载台8模组，两个真实2×2×2实体树由原载台入口创建。S1/S2公开GetNext/Finish各遍历53消息共106次，8种原始识别节点执行30次正常离线DoWork及2次回调异常尝试，共32次；条件门控、实体标记、状态与回调顺序核对。实际硬件仓库为空，关闭输送/料仓Start门控不创建Task，未运行在线识别/设备。S2前置消息和耗尽后保留较低层实体缓存，当前消息为空时步骤名getter异常；ChangeName参数只映射节点，实体仍按内部消息刷新。原输送JSON真实Save/Load按JsonIgnore排除运行态、重载替换单例，5个子控制器的基类载台缓存仍旧，固晶派生getter读新单例，形成新旧引用；旧对象Save实际保存新静态单例。这里只读反射，不注入私有当前消息；未推断全部派生动作使用旧缓存或生产入口一定发生失配。180项/EXE/JSON/IL重放一致，30新增冻结绑定父3292项，共3322项；首轮4条宿主编译错误保留。原源码未改，不合并251/1328/278/目录119/58/98/124或40专题3817，旧LC/Fody/VM失败保持。以上后续剩余以本段为准：真实配方重载/重建合同、节点选择后的完整任务异常与退出、在线具体动作及下层算法、就绪负分支、PR/校准/测量、IO稳定性、匹配构建依赖和原部署/UI/设备；16工程/29组/1436文件/13项整体仍未完成。

后续原始任务/配方初始化核验：[100项原生检查](native-recipe-task-lifecycle-progress.json)及[报告](native-recipe-task-lifecycle-review.md)通过。直接原Signal线程复现Pause睡眠期间切Stop仍返回true，属于可发生的调度路径；撤下业务暂停任务释放测试，防止沿原while进入设备动作。原业务任务只在Stop启动6个，5正常结束/1原Init空步骤故障；Enable=false仍Start、S1排程重建、S2十字段重置而保留排程、完成/故障重启及无任务/完成任务Abort行为核对，运行中Abort未原生验证。原生产页面InitProgramNodes以无this读取的原IL/open delegate调用，未构造UcMainSystem；6单例/路径切换但5基类载台引用、S2消息/实体缓存仍旧。晶圆清理真实Save，true/false静态盒标记区别、独占保存异常导致前4组切新而晶圆/工序旧、内存部分提交/原磁盘保持与解锁恢复复现；ReLoadRecipe调用在try/finally外仅IL推断UI异常恢复边界，完整UI未运行。宿主/38方法IL精确重放，实际晶圆JSON仅2处原DateTime.Now字段动态，其余解析内容一致，原文件字节不相同。54新冻结+3322父=3376；早期11/85失败、2原空载具弹窗宿主终止(-1)、IL检查失败均保留，95断言子序列保留。原源码未改，各180/251/1328/278/119/58/98/124和40专题3817分开，LC/Fody/VM失败保持。以上后续剩余以本段为准：任务暂停/退出及真实配方入口重建调用、其他等待/异常链、在线节点/下层算法、就绪负分支、PR/校准/测量、IO稳定性、匹配构建/部署/UI/设备；16工程/29组/1436文件/13项整体仍未完成。

后续原始机器停止/急停核验：[70项原生检查](native-machine-stop-progress.json)及[报告](native-machine-stop-review.md)通过。完整Machine Stop/Pause/Continue/EmergencyStop在真实空硬件仓库/轴表、OffLineWork与空报警表运行；未执行轴停止或电气/门控动作。S1原Start在Stop下运行100000原步骤Init，真实Running任务被原急停Dispose拒绝后继续完成Init/Stop退出；空Task急停空引用，已完成/故障Task允许Dispose。原闭合判定采16/15槽，S1配置false可漏掉仍Running的真实任务，Faulted被接受closed。实际原容量500日志队列在SetState先提交状态后Add满槽阻塞，后续信号/计数清理延迟，TryTake释放后恢复；CompleteAdding显式故障使状态提交而清理中断，同态重试绕过日志恢复，不推断现场队列已满/关闭。原Online上游方法无离线门控，空Electric失败后部分清理提交；安全门配置true缺Sensor在Continue状态变更前失败。原Start IL确认S2 Init先于BondTask.Start，但完整生产Start/设备循环/数据库保存线程未执行。宿主/完整运行/55原方法IL/固定仓库JSON重放一致；42新增冻结+3376父=3418。初始核验脚本误判foreach finally及==比较而失败，原冻结脚本不改，accepted检查精确更正两守卫，35原绑定保留加7项，失败记录保持，65原断言子序列保留。各70/100/180/251/1328/278/119/58/98/124和40专题3817分开，LC/Fody/VM失败保持。以上后续剩余以本段为准：数据库消费者/停止上层调用、生产配方重建入口、其他等待/异常链、在线节点/下层算法、就绪负分支、PR/校准/测量、IO稳定性、匹配构建/部署/UI/设备；16工程/29组/1436文件/13项整体仍未完成。

后续原始数据库保存线程核验：[原生30项正常生命周期与12项完成队列子进程检查](native-db-saver-progress.json)及[报告](native-db-saver-review.md)完成，8个共同标签共34不同断言，均独立于此前70/100/180/251/58与正式1328。原StartSaveThread创建真实后台消费者，原容量500队列中阻塞生产者被释放，507个未知CLR对象被消费而非入库；20次顺序启动保留同一线程，公开ThreadFlag=false不停止原消费者。DBService原Lazy保持未创建，SQL连接/四种已识别Insert分支/建表清理均未执行。完成空队列显式隔离故障使原Take未捕获InvalidOperationException，UnhandledException事件证明原线程/isTerminating与原栈，原生子进程实际退出3762504530（有符号-532462766）；外层记录器0不是子进程成功。CLR stderr的Exception.ToString失败提示保留，格式化根因未查明。正常返回仍存活后台线程不等于优雅停机。19原方法IL进一步确认监控调用先后、DB Insert catch记录无回队重试、取消按钮禁用界面后直接Stop无本地保护、两个Start catch中的Stop异常仍处于Enabled恢复finally范围、ExitSoftware无排空/Join而Environment.Exit(0)；这些UI/SQL/整段监控/原退出方法仅静态核验。EXE/完整正常结果/异常事件/进程退出/IL重放一致；43新增冻结+3418父=3461，首次测试路径失败、两次stderr守卫失败及引号命令失败均保留。本段为最新剩余：已识别数据库日志与SQL错误、原SaveEntity去重/背压、其他队列/等待/异常链、配方生产重建、在线下层/就绪/PR/校准/测量/IO、完整构建部署及真实UI设备；16工程/29组/1436文件/13项整体仍未完成。

后续原始操作日志生产者核验：[60项完整原SaveEntity/手动AOP原生检查](native-statistics-producer-progress.json)及[报告](native-statistics-producer-review.md)通过。消息仅和上一成功入队文本比较，忽略操作者；初始null抑制、后续null接受、空值/大小写/空白及非连续重复边界已验证。SDK原Trace InFile=0在日志数据库2/4分支前返回，实际SDK dbInitializationAttempted=false与主DB Lazy未创建；原SDK广播公开TryReceive只读观察，没有替换Queue/广播/SDK或私有状态写入。原容量500队列满时Trace已经Post，而lastMessage/活动时间尚未提交；公开TryTake后成功，新实体排在499普通输入后。同样成功消息绕过满/封闭集合；新消息Add失败仍Post，失败文本未提交、再次重试继续Post。真实两普通调用线程在满集合窗口通过相同旧消息门控，释放2槽后队列内2个相同文本不同操作者的原实体，去重并发缺口可重放，不估计现场频率。手动原AOP OnException只有通用异常文本，连续不同原异常细节被去重；封闭集合时异常记录方法本身InvalidOperationException。手动调用不是自动拦截/织入，UI/权限方法未运行，LC/Fody失败保持。EXE/完整运行JSON/34原方法IL重放一致，真实日期仅检查关系未序列化，实体竞态顺序未强制。30新增冻结+3461父=3491；本60与父消费者30/12、机器70、任务100、输送180、动作251、正式1328等计数独立。本段为最新剩余：图片队列/消费者、其他等待/异常退出链、已识别真实数据库日志与SQL故障、生产配方重建、在线下层/就绪/PR/校准/测量/IO、匹配完整构建/部署及真实UI设备；16工程/29组/1436文件/13项整体仍未完成。

后续原始图片队列核验及源码编码缺口：[41正常/12关闭生产者/10、8、9故障进程检查](native-vision-image-queue-progress.json)和[报告](native-vision-image-queue-review.md)完成，共56不同断言。实际无界原队列、Bitmap同一引用和普通公开入队路径，原Save写BMP并Dispose，独立头/像素/真实文件证据重放；调用者入队后修改像素会进入实际文件，JPG后缀仍BMP。原生产者对null/非法路径/关闭队列catch返回并Error InFileAndUI3记录，原Bitmap不释放；SDK/main DB未初始化。异步Save失败不受生产者catch保护：缺少文件名子目录的原生产者先正常返回，原消费者GDI+异常时Bitmap仍可读/后续队列项保留；同一对象两次入队，首次成功Dispose、第二次ArgumentException；空队列CompleteAdding导致Take InvalidOperation。3原后台故障进程均实际退出3762504530（有符号-532462766），外层0仅记录预期故障。ThreadFlag=false不停止消费者，正常Main返回后台线程仍活，不是优雅关闭。16源码程序集18286方法体只读扫描6调用/委托位点、8委托字段位点、23选定原IL，确认Program.Main注册PREntity.SaveLocateImageAction、PR Excute三分支Invoke，注释直接调用不能判未接通；整个启动/相机/算法/实验UI未运行。62先冻结+26重放=88新增，3491父+88=3579，首次Error模式守卫17后失败保持。**本段同时记录实质新缺口：PREntity.cs严格UTF8失败、CP936可读，当前冻结默认UTF8 ReadAllText编译PR路径含U+FFFD而非源CP936中文；同编译宿主923替代字符、Framework918计数差异保留，实际IL目录损坏确认。旧编译成功/哈希一致不证明全源码字符串保真，原csc/MSBuild/部署编码仍未验收；测试VisionService本文件有效UTF8。** 以上为最新优先顺序：全仓库编码审计、原工具链解码核对、另名保真源码编译/重放与阅读器展示审计；再继续其他等待/异常链、真实SQL日志/故障、配方重建、在线下层/就绪/PR/校准/测量/IO、完整构建/部署/真实UI设备。此前本轮分进程/60/30+12/70/100/180/251/1328等计数不相加，16工程/29组/1436文件/13项整体仍未完成。

后续源码编码保真核验（本段更新上一阶段编码待办）：[1436原始字节/1410Compile/16工程三轮48次编译](source-encoding-fidelity-progress.json)和[报告](source-encoding-fidelity-review.md)已通过。1427 UTF8 BOM、2无BOM UTF8、7无BOM CP936候选全部严格解码和原字节往返；实际Roslyn流解码1436文本哈希匹配，本机ANSI936与4种实际csc探针均保留中文原值，但原部署工具链/整体MSBuild未识别。7个旧默认UTF8文本不同，其中6编译，68字符串/插值词法变化均PR；新另名编译不改源字节/编译项，bound/replay各130源码工程元数据引用、16程序集哈希均重放一致，15与旧产物相同，仅PR变化。18286方法体逐指令/异常范围比较仅59处PR ldstr变化，其余所检项目一致，不宣称全ABI/自定义属性/资源等价。旧损坏PR编译/资源/阅读器与1328/历史sourceEncodingFidelityGap指针保留；新[保真阅读器](module-source-explorer-encoding-preserving.html)修复12既有PR中文快照，29模块552关系940基础/40专题3817保持，Edge实测4757显示/搜索/点击/深链与4尺寸通过。317新增冻结+3579父=3896，旧失败和本轮探针/检查器准备失败保留，不添加业务断言计数。**当前原始字节解码、另名raw-source编译/重放和阅读器展示已完成；下一优先项是另名源码资源程序集保真迁移及代表原生宿主重放，然后继续等待/异常链、SQL/配方/在线下层、完整构建部署与真实UI设备。** 本轮没有资源迁移、旧宿主使用新程序集重放、原整体Build/部署、PR相机VM/SQL/设备运行；16工程/29组/1436文件/13项仍未完成。

后续保真源码资源与原生宿主迁移（本段完成上一阶段资源待办）：[16工程1410Compile/388资源1498条目/1文化卫星](encoding-preserving-resources-progress.json)和[报告](encoding-preserving-resources-review.md)已通过。最终三轮17程序集共51实际编译0，bound/replay各130源码工程元数据引用已指向本轮资源产物；17哈希一致，仅PR相对旧资源产物变化，18286方法体比较59中文ldstr恢复/其他所检指令异常范围一致。两个Framework进程实际物理绑定17、逐流字节SHA/键与类型对应验证388/1498并匹配冻结基线。8组冻结Probe字节不变，新的primary-final/replay-final根目录重放26进程：18正常0，8故障3762504530；58/251/180/100/70/30/60/41及关闭12/故障12、10、8、9原标签/范围保持，不新增业务断言。各16源码程序集物理绑定新资源路径，完整输出语义匹配仅规范化根/程序集位置，wafer原JSON仅2个CreateTime动态字段，原BMP字节/像素保持。初候选51编译/26运行可兼容但引用替换0的守卫失败，整套保存后重编译与全新根重放；3资源读回准备失败、猜测日志路径/名称排序守卫失败均保留。1217新增冻结+3896父=5113。**原始解码、保真源码编译/资源嵌入和代表原生重放迁移现已完成，后续采用本轮runtimeMap；继续真实业务Working/Pause/异常退出、生产配方与启动、SQL持久化、PR/校准/测量/IO下层及完整构建部署/真实UI设备。** 旧源码/编译器/程序集/阅读器与原stage resourcesMigrated=false指针仍是历史证据，正式1328/40专题3817不改写。既有fixture边界保留（251已有工作消息私有写入、60手动AOP等）；本轮没有整体MSBuild/许可证/weaving/部署/相机VM/SQL/设备验收，16工程/29组/1436文件/13项整体仍未完成。

## 历史增量：原检测仓库接完整启动与输送

原检测仓库增量：1303项受控检查通过，原1209项重跑并按原列表/加载迁移12个运行断言（7静态位置、4个名称），另执行44项两条UI与50项仓库。498记录/497唯一源码含268方法、186属性、18枚举、24字段、2结构体及23信号契约。原单例/Load/Find/过滤/配方/Save/PR增删顺序接完整实体/坐标/供晶/五阶段链；历史字典与读取钩子已移除。真实JSON/产品单例/AOP/PR/VM/动作及构建/部署/原生UI/设备仍待完成。 见[专项报告](transport-inspection-repository-integration-review.md)与[进度](transport-inspection-repository-integration-progress.json)。专项、来源审计、统一回归与四宽度阅读器均通过；见[1303项收尾回执](transport-inspection-repository-integration-verification.json)。当前39专题、3405段专题快照。此前19段仓库接续及10段BaseDsSetting已编译，旧180正式/186准备输入保持原哈希。历史50/44准备已在同一1303 Run执行，不额外相加；下一步[8段原产品声明及正确编辑枚举](transport-product-config-declarations-next-evidence.json)。另已完成两份DLL各26项真实JSON/单例SDK数据验证，见[SDK准备](inspection-repository-json-sdk-progress.json)；合成数据类型尚未接原产品/配置。整体16工程、29组、1436个C#文件与13项要求仍未完成。


后续原生数据准备：[六个完整原源码文件与真实JSON SDK](inspection-repository-native-source-progress.json)，两份DLL各27项相同断言通过（54次放置）。现有Roslyn以明确Framework引用编译隔离测试DLL，原仓库/助手状态/默认值与真实SDK共同执行；非法背崩枚举可保留Forbidden并通过，非法焊后枚举保留UnAble并拒绝，不兼容Name对象可丢弃记录。原产品声明/Fody织入/实际PR/原工程构建/部署/原生UI/设备仍待完成；此准备在本1303项统一回归及专题计数范围外。

后续产品原生数据准备：[22个完整原源码文件、原产品默认值与真实SDK Singleton/JSON](product-config-native-source-progress.json)，两份DLL各36项相同断言通过（72次执行），见[专项报告](product-config-native-source-review.md)。8段原产品声明/正确编辑枚举在完整原文件内编译，原目标类型new语法保留；实际产品就绪、Init/Clear/Save、原配置/仓库与检测状态共同执行。无效SafeHeight数字字符串放在JSON前部可截断后续示教状态读取而拒绝，放在末尾则保留已读Able并通过。此准备未迁移到完整启动/实体组合，未加入1303回归或39专题/3405快照；Fody/外部依赖/原工程构建/部署/原生UI/设备仍待完成。

## 历史增量：原焊点与检测自身汇总接完整组合

原焊点/检测自身汇总增量：1209项受控检查通过，原1144项按原名称顺序重跑，同一Run另执行20项两条UI与45项汇总。469记录/468唯一源码含251方法、177属性、17枚举、22字段、2结构体及23信号契约。健康Setup/Grid显式已教；原默认未教、null与空列表、检测标志和实际状态差异接原实体/坐标/供晶/五阶段链。真实仓库/单例/VM/动作/SDK及构建/部署/原生UI/设备仍待完成。 见[专项报告](transport-inspection-readiness-integration-review.md)及[进度](transport-inspection-readiness-integration-progress.json)。专项、来源审计、统一回归与四宽度阅读器均通过；见[1209项收尾回执](transport-inspection-readiness-integration-verification.json)。当前38专题、3007段专题快照。此前20段接续全部编译并执行整套1144旧断言，旧171个正式输入与176个准备输入保持原哈希。下一步[19段原检测仓库与基础仓库](transport-inspection-repository-next-evidence.json)。历史准备45/20项已在本1209组合执行，不再次相加认定覆盖。整体16工程、29组、1436个C#文件与13项要求仍未完成。


接续准备：[原检测仓库50项与两条原UI44项验证](inspection-repository-preparation-progress.json)及来源审计通过；19段原仓库接续和10段BaseDsSetting成员已经参与准备编译。44项准备探针仅编译旧1209项；另行建立的[完整仓库1303项分支](transport-inspection-repository-integration-checkpoint.json)已执行旧1209项及44/50新增项，七个静态断言位置对应12个运行断言按原列表/加载迁移，四个名称改变。分支专项及来源检查点通过，正式专题登记和独立统一回归待完成；不计入本次1209项统一回归或阅读器专题计数。

## 历史增量：真实示教汇总接完整启动与输送

真实示教汇总增量：1144项受控检查通过，原1031项全部重跑并迁移六个断言，另执行20项两条UI及93项汇总检查。449条提取记录对应448段唯一源码，含242方法、166属性、17枚举、22字段、2结构体及23信号契约。原16状态与异形递归/检测查找接完整实体、坐标和五阶段链；Save异常提前到准备阶段，UI Stop且未启动供晶，缓存重试可绕过仍失败的Save。焊点/检测对象自身汇总、仓库/单例/VM/动作/SDK及构建/部署/原生UI/设备仍待完成。 见[专项报告](transport-teaching-integration-review.md)。专项、来源审计、统一回归与四宽度阅读器均已通过。此前29段示教接续全部编译，并执行整套旧断言；下一步[20段焊点与检测自身汇总](transport-inspection-readiness-next-evidence.json)。旧160个正式输入和165个准备输入保持原哈希；各历史套件不相加认定覆盖。整体16工程、29组、1436个C#文件与13项要求仍未完成。


收尾回执：[1144项统一回归及阅读器验证](transport-teaching-integration-verification.json)。当前37专题、2638段专题快照。下一项原焊点与检测自身汇总的独立45项和20项两条原UI准备验证及来源审计通过，见[准备进度](bond-inspection-readiness-preparation-progress.json)；旧1144项尚未迁移重跑，不计入本次1144项统一回归。

## 历史增量：原坐标计算、产品配置与异形缓存

原坐标/产品生命周期增量：1031项受控检查通过（包含此前1011项断言及20项组合检查），420条提取记录对应419段唯一源码，含237方法、143属性、16枚举、22字段、2结构体、23信号契约。三个原坐标文件、产品/异形缓存/程式生命周期接实体树、两条UI、真实供晶Task与五阶段输送。旋转和偏移世界坐标、刷新失败旧父链、保存失败缓存重试已验证。示教汇总、VM校准、原单例加载/保存、动作/SDK及构建/部署/原生UI/设备仍待完成。 见[专项报告](transport-coordinate-product-integration-review.md)。专项、来源审计、统一回归与四宽度阅读器均已通过。此前14段生命周期接续已编译进本组合；下一步[29段真实示教汇总及依赖](transport-teaching-next-evidence.json)。旧1011专项的149个输入保持原哈希，独立1355和113/29准备探针不计作新增覆盖。整体16工程、29组、1436个C#文件与13项要求仍未完成。

收尾回执：[1031项统一回归及阅读器验证](transport-coordinate-product-integration-verification.json)。当前36专题、2289段专题快照。下一项真实示教汇总的独立93项和20项两条原UI准备验证及来源审计通过，29段接续已准备，见[准备进度](transport-teaching-lifecycle-preparation-progress.json)；旧1031项断言尚未迁移重跑，不计入本次1031项统一回归。

## 历史增量：实体树、TuService与五子任务初始化

实体/TuService及五子任务增量：1011项独立受控检查通过，391条提取记录（390段唯一源码）含213方法、140属性、14枚举、22字段、2结构体、23信号契约；普通/异形树、状态屏蔽、坐标异常前缀、原五Task/WaitAll及两条UI的29节点五阶段连续链已验证。坐标变换/产品/异形配置/动作/单例/SDK与原构建/部署/原生UI/设备仍待完成。 见[专项报告](transport-unit-services-integration-review.md)。专项、来源审计、统一回归与四宽度阅读器均已通过。35专题、1969段专题快照；此前载具1355项为独立冻结套件，本轮1011项不可与其相加认定覆盖。下一步14段坐标/产品/异形配置/程式生命周期。整体29组与13项要求仍未完成。

收尾回执：[1011项统一回归与四宽度阅读器验证](transport-unit-services-integration-verification.json)。下一轮14段接续已由独立探针准备：原坐标113项、产品/异形配置29项及来源审计通过，见[准备进度](coordinate-product-lifecycle-preparation-progress.json)。两套独立检查尚未接入实体/输送组合，不计入本次1011项统一回归。

## 历史增量：启动载具映射、真空/日志与五阶段连续输送

原启动载具检查/MapMaterial、Bond与点胶搜索/记忆/真空及原计时日志接九条输送、完整生产器、两条UI和真实供晶Task/Stop，1355项受控检查通过，含191方法、122属性、11枚举、17字段和23信号契约。记忆矩阵、真空输出/检测通道差异、真实计时、SDK返回忽略、Stop/Pause后提交、域catch后继续供晶与嵌套失败后UI Stop、搜索载具五阶段输送链已验证；实际服务/实体/生命周期/SDK及构建/配置/DLL/原生UI/设备仍待完成。 详见[专项报告](transport-carrier-map-integration-review.md)。专项运行、来源审计、统一回归与四宽度阅读器验证通过。下一步19段原实体/TuService/程式/模块生命周期，再继续原构建与配置/DLL、原生UI和设备验收。历史增量中的待办以本段最新范围为准。

收尾验证（2026-10-01）：1355项专项、来源审计、统一回归PASS且实际退出码0；阅读器1600/1440/850/390宽度通过且无页面错误。见[集成验证回执](transport-carrier-map-integration-verification.json)。现有34专题、1678段专题快照；载具检查/映射/搜索/真空/日志及九条输送已受控组合，19段真实实体/服务/程式/模块源码继续待运行集成。实际SDK日志、原工程构建、部署配置/DLL、原生UI和设备验收未完成。

## 历史增量：原料仓推杆子任务与五阶段连续链

原料仓到点胶、推杆/入料/参数与真实10秒子Task接完整生产器、两条UI及真实供晶Task/Stop，288项检查通过，含173方法、103属性、10枚举、16字段和23信号契约。九条输送均已受控编译，五阶段料仓链、卡料Ignore无物料却发布、未等待子Task、Home返回覆盖、NoStart保留许可后恢复上料、Stop/Pause后提交及子任务故障部分提交已验证；载具检查/MapMaterial/日志、真实服务/生命周期/SDK及构建/原生UI/设备仍待完成。 详见[专项报告](transport-loader-bin-integration-review.md)。专项运行、来源审计、统一回归与四宽度阅读器验证均通过。下一步启动载具检查/MapMaterial、Bond与点胶MapBelt/SearchBelt及Provider计时日志，再继续真实服务/产品/程序/池/域/SDK和构建/配置/DLL/原生UI/设备验收。历史增量中的待办以本段最新范围为准。

收尾验证（2026-10-01）：288项检查及来源审计通过；统一回归PASS、实际退出码0；阅读器1600/1440/850/390宽度通过且无页面错误。见[集成验证回执](transport-loader-bin-integration-verification.json)。现有33专题、1436段专题快照；九条输送均已接受控组合，22段启动载具检查/物料比对/计时日志接续源码中10段在本轮冻结的验收范围外。推杆SDK9方法/2仓库DLL静态核对已计入本次统一回归，未执行SDK。整体工程及原生/设备验收尚未完成。

历史检查点（2026-10-01）：载具映射226项基线、1178项中间验证与1292项分支检查已冻结保留，未计入此前料仓288项回归；当前载具映射1355项和正式来源专题范围见首段。

## 历史增量：原送板机超时与七阶段连续链

原送板机到入料段、前端物料getter/读取及真实5秒超时接完整生产器、两条UI和真实供晶Task/Stop，238项检查通过，含159方法、95属性、10枚举、15字段和23信号契约。七阶段连续链、连续两次真实超时、Ignore后第一父线程再次要料、Stop/Pause后提交、构造/Save部分状态及程式替换受控验证；剩余料仓到点胶、服务/SDK及原构建/原生UI/设备验收待完成。 详见[专项报告](transport-auto-loader-integration-review.md)。专项运行、来源审计、统一回归与四宽度阅读器验证均通过。下一步最后一条原料仓到点胶、推杆/入料口/原参数、第三父Task和真实10秒子任务，再继续载具检查/MapMaterial、真实服务/产品/程序/池/域/SDK和构建/配置/DLL/原生UI/设备验收。

收尾验证（2026-09-30）：238项检查与来源审计通过；统一回归PASS、退出码0；阅读器1600/1440/850/390宽度通过且无页面错误。见[集成验证回执](transport-auto-loader-integration-verification.json)。现有32专题、1233段专题快照。最后一条原料仓到点胶、推杆/入料口/第三父任务/真实10秒子任务的22段见[接续证据](transport-loader-bin-next-evidence.json)。另已独立核对推杆SDK9方法/2仓库DLL静态契约，未计作本次统一回归新增项，原料仓运行集成仍待完成。整体工程及原生/设备验收尚未完成。

## 历史增量：原入料皮带与单元生命周期及六阶段链

原入料皮带到点胶1、原轴/物料/参数/SMEMA及Unit构造/Init/Refresh接完整生产器、两条UI与真实供晶Task/Stop，252项检查通过，含156方法、94属性、10枚举、15字段及23信号契约。六阶段连续链、两种Ignore区别、Refresh部分别名提交、异常返回后父任务继续、Stop输出故障与阵列/异形配置副作用已受控验证；坐标/子实体/服务/SDK和其他两入料、构建及原生UI/设备仍待验收。 详见[专项报告](transport-loading-belt-integration-review.md)。专项运行、来源审计、统一回归与四宽度阅读器验证均通过。下一步原自动送板机到入料段、前端传感器/真实5秒超时及第一父Task，再继续料仓到点胶、载具检查/MapMaterial、真实服务/产品/程序/池/域/SDK和构建/配置/DLL/原生UI/设备验收。

收尾验证（2026-09-30）：252项检查和来源审计通过；统一回归PASS、退出码0；阅读器1600/1440/850/390宽度通过且无页面错误。见[集成验证回执](transport-loading-belt-integration-verification.json)。现有31专题、1053段专题快照。下一项原送板机到入料段/前端传感器/真实5秒超时及第一父任务的11段见[接续证据](transport-auto-loader-next-evidence.json)。整体工程及原生/设备验收尚未完成。

## 历史增量：原点胶1到点胶2及五阶段连续链

原点胶1到点胶2、Clamp/同步皮带、Unit偏移/cast及配置/信息声明接完整生产器/UI/真实供晶Task/Stop，276项检查通过，含136方法、65属性、8枚举、14字段和23信号契约。五阶段连续链、重复许可累计偏移、Stop后提交、晚期坐标/标志故障及域/程式替换已受控验证；构造/Refresh/坐标SDK、其他三入料与原生UI/设备继续待验收。 详见[专项报告](transport-dispense12-integration-review.md)。专项运行、来源审计、统一回归与四宽度阅读器验证均通过。下一步原入料皮带到点胶1、原传感器/参数/getter/皮带/需料与Unit构造/Init/Refresh，再继续其他入料、载具检查/MapMaterial、真实产品/程序/池/域/SDK和构建/配置/DLL/原生UI/设备验收。

收尾验证（2026-09-30）：276项检查与来源审计通过；统一回归PASS、退出码0；阅读器1600/1440/850/390宽度通过且无页面错误。见[集成验证回执](transport-dispense12-integration-verification.json)。现有30专题、877段专题快照。下一项原入料皮带到点胶1/硬件/参数/需料与Unit构造/Init/Refresh的20段见[接续证据](transport-loading-belt-next-evidence.json)。整体工程与现场验收尚未完成。

## 历史增量：原点胶到Bond及完整四阶段连续链

原点胶到Bond及气缸/夹紧/同步皮带接完整生产器、两条UI和真实供晶Task/Stop，184项检查通过，含132方法、57属性、8枚举、13字段及23信号契约。四阶段连续链、子任务Stop后提交、父任务忽略Exception且不发布本次完成事件、卡料及Unit部分提交已受控验证；其他四传输与原生UI/SDK/设备继续待验收。 详见[专项报告](transport-dispense-bond-integration-review.md)。专项运行、来源审计、统一回归与四宽度阅读器验证均通过。下一步原点胶1到点胶2、点胶Clamp/同步皮带、Unit坐标偏移及预点胶标志，再继续其他入料、载具检查/MapMaterial、程序/池/域/SDK和构建/配置/DLL/原生UI/设备验收。

收尾验证（2026-09-30）：184项检查与来源审计通过；统一回归PASS、退出码0；阅读器1600/1440/850/390宽度通过且无页面错误。见[集成验证回执](transport-dispense-bond-integration-verification.json)。现有29专题、753段专题快照。下一项原点胶1到点胶2/Clamp/同步皮带/Unit坐标及预点胶标志的11段见[接续证据](transport-dispense12-next-evidence.json)。整体工程与现场验收尚未完成。

## 历史增量：原出料皮带到收板机接完整生产器

原出料皮带到收板机、SMEMA和硬件getter接完整生产器/UI/准备/真实供晶Task/Stop及原Bond/等待区链，287项检查通过，含114方法、53属性、6枚举、13字段和23信号契约。实际第九Task、三阶段连续传输、两类卡料、停止后动作、动态硬件及被忽略的Exception返回已受控验证；其他五传输及原生UI/SDK/设备仍待验收。 详见[专项报告](transport-auto-unloader-integration-review.md)。专项测试、来源审计、统一回归与四种宽度阅读器验证均通过。下一步原点胶到Bond及气缸/夹紧/同步皮带链，再继续其余入料/点胶传输、载具检查/MapMaterial、程序/池/域/SDK、构建与配置/DLL、原生UI和设备验收。

收尾验证（2026-09-30）：287项检查与来源审计通过；统一回归PASS、退出码0，阅读器1600/1440/850/390宽度通过且无页面错误。见[集成验证回执](transport-auto-unloader-integration-verification.json)。原收板机/SMEMA/硬件getter链已受控验证；下一项点胶到Bond/气缸/夹紧/同步皮带及第五父Task的19段见[点胶到Bond接续证据](transport-dispense-bond-next-evidence.json)，仅Success分支发布完成事件，需验证Exception返回时未Stop且不发布的区别。

## 历史增量：原等待区到出料Bin接完整生产器

原等待区到出料Bin、缩回/推料/层号及模组/参数包装接完整生产器/UI/准备/真实供晶Task/Stop与原Bond，578项检查通过，含111方法、50属性、6枚举、13字段和23信号契约。实际Bin信号、SDK默认参数、三类重试、停止后发布、层号与部分提交/嵌套异常已受控验证；其他六传输及原生UI/SDK/设备仍待验收。 详见[专项报告](transport-bin-integration-review.md)。专项测试、来源审计、统一回归与四种宽度阅读器验证均通过。下一步原出料皮带到收板机及SMEMA要料链，再继续其余入料/点胶传输、载具检查/MapMaterial、程序/池/域/SDK、构建与配置/DLL、原生UI和设备验收。

收尾验证（2026-09-30）：578项检查与来源审计通过；统一回归PASS、退出码0，阅读器1600/1440/850/390宽度通过且无页面错误。见[集成验证回执](transport-bin-integration-verification.json)。原Bin传输/推杆/层号链已受控验证；下一项原出料皮带到收板机/SMEMA及第九父Task的10段见[收板机接续证据](transport-auto-unloader-next-evidence.json)。其父任务没有Exception返回分支，需继续验证。

## 历史增量：原等待区到出料皮带接完整生产器

原等待区到出料皮带、共用运动/停止/有料包装接原Bond与完整生产器/UI/准备/真实供晶Task/Stop，1076项检查通过，含105方法、42属性、6枚举、13字段和23信号契约。配置门控、真实连续两阶段传输、停止后动作、卡料重试和部分提交/异常已受控验证；其余七传输、原生UI/SDK/设备仍待验收。 详见[专项报告](transport-waiting-integration-review.md)。专项测试、来源审计、统一回归与四种宽度阅读器验证均通过。下一步原等待区到出料Bin及LoaderBin路径，再继续其余传输、载具检查/MapMaterial、程序/池/域/SDK、构建与配置/DLL、原生UI和设备验收。

收尾验证（2026-09-30）：1076项检查与来源审计通过；统一回归PASS、退出码0，阅读器1600/1440/850/390宽度通过且无页面错误。见[集成验证回执](transport-waiting-integration-verification.json)。原等待区到出料皮带及共用包装已受控验证；下一项原等待区到出料Bin/LoaderBin路径及推杆/层号链15段见[Bin接续证据](transport-bin-next-evidence.json)，其余六传输见[其余接续证据](transport-waiting-next-evidence.json)。

## 历史增量：原Bond到等待区控制器接完整生产器

原Bond到等待区传输/解夹/双皮带与基础轴链已接完整生产器、原UI/准备和真实供晶Task，310项检查通过，含87方法、39属性、6枚举、13字段和23信号契约。实际子Task/WaitAll、暂停/停止后的动作、部分提交及异步catch失败已受控验证；其他八传输、原生UI/SDK和设备仍待验收。 详见[专项报告](transport-bond-integration-review.md)。专项测试、来源审计、统一回归与四种宽度阅读器验证均通过。下一步原等待区到出料皮带控制器及共用运动/传感器包装，再继续其他传输、载具检查/MapMaterial、程序/池/域/SDK、构建与配置/DLL、原生UI和设备验收。

收尾验证（2026-09-30）：310项检查与来源审计通过；统一回归PASS、退出码0，阅读器1600/1440/850/390宽度通过且无页面错误。见[集成验证回执](transport-bond-integration-verification.json)。下一项八原传输及共用运动/停止/有料包装共25段固化于[等待区控制器接续证据](transport-waiting-next-evidence.json)；原Bond模组HasMaterialInModule直接抛NotImplementedException，下一轮保留并验证。

## 历史增量：完整原输送Start与九个真实Task

完整原输送Start及九Task字段接入UI/真实供晶Task的870项检查通过，含81方法、31属性、4枚举、13字段和23信号契约。六配置、九槽位八Task状态、全部返回码、暂停与停止后成功发布、异步异常已受控验证；完整传输控制器、原生UI/SDK和设备仍待验收。 详见[专项报告](transport-producer-review.md)。专项测试、来源审计、统一回归与四种宽度阅读器验证均通过。下一步原Bond到等待区传输/轴/解夹链接完整生产器，再继续其他原传输控制器、池/域/SDK及原项目构建、配置/DLL、原生UI和设备验收。

收尾验证（2026-09-30）：870项检查与来源审计通过；统一回归PASS、退出码0，阅读器1600/1440/850/390宽度通过且无页面错误。见[集成验证回执](transport-producer-verification.json)。下一项九原控制器传输、载具检查/MapMaterial/日志及已编译Provider/区段声明共16段固化于[控制器接续证据](transport-controller-next-evidence.json)。

## 历史增量：原UI启动、模式与单步接真实供晶Task

原UI启动、Dock/模式/单步处理接真实供晶Task的262项检查通过，含80原方法、28属性、2枚举、4字段及23信号契约。原UI catch同步失败执行Stop、内部正常返回失败绕过catch、Enabled/Stop/finally故障及单步回调保留事件已验证。原生控件派发、完整输送生产器、池/域/SDK和设备仍待验收。 详见[专项报告](ui-start-mode-review.md)。专项测试、来源审计、统一回归与四种宽度阅读器验证均通过。下一步完整TransportTask.Start、真实池/域/SDK及现场配置/DLL、原生UI/构建与设备验收。

收尾验证（2026-09-30）：262项检查与来源审计通过；统一回归PASS、退出码0，阅读器1600/1440/850/390宽度通过且无页面错误。见[集成验证回执](ui-start-mode-verification.json)。下一项完整输送Start及九字段、包装/控制器共14段原代码已固化于[完整输送生产器接续证据](transport-producer-next-evidence.json)。

## 历史增量：原准备帮助方法与真实信号/任务关闭

原准备帮助方法接入完整启动与真实供晶Task的303项检查通过，含73原方法、22属性、2枚举、3字段、23信号初始化契约。Running关闭拒绝前仍清除真实需料/取料事件；16槽位八状态、复位部分失败、环境/磁盘/预热门控及新请求处理已验证。清理、域/容量/SDK、完整输送生产器和原生UI/设备仍待验证。 详见[专项报告](readiness-helpers-review.md)。专项测试、来源审计、统一回归与四种宽度阅读器验证均通过。下一步实际UI启动/模式入口、完整TransportTask.Start、真实池/域/SDK及现场配置/DLL、构建与设备验收。

收尾验证（2026-09-30）：303项检查与来源审计通过；统一回归PASS、退出码0，阅读器1600/1440/850/390宽度通过且无页面错误。见[集成验证回执](readiness-helpers-verification.json)。下一项的14段UI启动/模式及完整输送生产器原成员、5条Designer事件绑定已固化于[UI启动与模式接续证据](ui-start-mode-next-evidence.json)。

## 历史增量：完整正常启动接入真实供晶Task

完整Machine.Start、准备包装和TransportDomain.StartTask接入真实供晶Task的175项检查通过，含67原方法、19属性、2枚举、3字段。输送内部Stop被供晶Start重写Working、输送catch后继续启动及下游同步异常保留真实供晶任务并发许可已验证。真实准备帮助方法、完整输送生产器、UI入口/SDK/设备仍待验证。 详见[专项报告](normal-start-integration-review.md)。专项测试、来源审计、统一回归与四种宽度阅读器验证均通过。下一步真实准备帮助方法、完整TransportTask.Start及实际UI启动/模式入口，以及现场配置/DLL、构建与设备验收。

收尾验证（2026-09-30）：175项检查与来源审计通过；统一回归PASS、退出码0，阅读器1600/1440/850/390宽度通过且无页面错误。见[集成验证回执](normal-start-integration-verification.json)。下一项的9段准备帮助方法、完整输送生产器及UI入口原代码已固化于[准备帮助方法接续证据](readiness-helpers-next-evidence.json)。

## 历史增量：原载具范围、完整搜索初始化与供晶Start

原载具范围表达式、完整搜索初始化及供晶Start的105项检查通过，含63方法、19属性、2枚举、3字段。配置替换保留旧步距、失败地图重试跳过生命周期、完整原Stop在初始化中被Start重写Working已验证；串行UI替身下两个实际消费者Task启动并经原Stop退出。实际UI入口/SDK/设备仍未验收。 详见[专项报告](wafer-range-init-review.md)。专项测试、来源审计、统一回归与四种宽度阅读器验证均通过。下一步完整Machine.Start、TransportDomain.StartTask、实际模式切换/启动入口，以及现场配置/DLL、构建与设备验收。

收尾验证（2026-09-30）：105项检查与来源审计通过；统一回归PASS、退出码0，阅读器1600/1440/850/390宽度通过且无页面错误。见[集成验证回执](wafer-range-init-integration-verification.json)。下一项的8段完整启动及UI入口原代码已固化于[正常启动接续证据](normal-start-integration-next-evidence.json)。

## 历史增量：原单颗位置生成与边界探测

原GetNextPosition及行列间距/间隔配置的229项受控断言通过，含56原方法、12属性、1枚举与3字段。八方向探测、原50次耗尽、保存失败保留步距/方向、首搜状态及耗尽后换片失败/人工Retry消费者链已验证。首次搜索不判范围；SDK、现场配置/保存和设备仍未验收。 详见[专项报告](wafer-next-position-review.md)。专项测试、来源审计、统一回归与四种宽度阅读器验证均通过。下一步原载具范围配置/初始化、实际SDK与完整正常启动并发。

收尾验证（2026-09-30）：229项检查与来源审计通过；统一回归PASS、退出码0，阅读器1600/1440/850/390宽度通过且无页面错误。见[集成验证回执](wafer-next-position-integration-verification.json)。下一项的13段原范围/初始化代码已固化于[范围配置待验证证据](wafer-range-init-next-evidence.json)。

## 历史增量：原标记中心与搜索终点换行

原标记中心与搜索终点换行的76项受控断言通过，含55原方法、8属性、1枚举。八种方向与保存/运动失败的部分状态保留已验证，原AnalyseDie调用与消费者Stop接入；Pause/Stop连续模式仍到达XY。当前标记中心仅直接探测，具名调用为注释。SDK/保存/设备仍未验收。 详见[专项报告](wafer-mark-center-review.md)。专项测试、来源审计、统一回归与四种宽度阅读器验证均通过。下一步原GetNextPosition、实际SDK与完整正常启动并发。

收尾验证（2026-09-30）：76项检查与来源审计通过；统一回归PASS、退出码0，阅读器1600/1440/850/390宽度通过且无页面错误。见[集成验证回执](wafer-mark-center-integration-verification.json)。下一项的8段原代码及配置表达式已固化于[位置生成待验证证据](wafer-next-position-next-evidence.json)。

## 历史增量：原晶圆台位置与墨点处理

原墨点两重载及晶圆台位置属性接入后，51个原方法、7个属性的131项受控断言通过。数量区间含边界；异常可跳过图像释放；晶圆台XY顺序读取非原子快照。首次读位置时Stop，Nine仍可移动并发许可，Single/Mapping拦截；Box本配置路径未触发位置读取。实际SDK、标定、图像与硬件仍为替身，非设备验收。 详见[专项报告](wafer-blob-position-review.md)。专项测试、来源审计、全量回归和页面验证均通过。

收尾验证（2026-09-30）：131项检查与来源审计通过；统一回归PASS、退出码0，阅读器四种宽度检查通过且无页面错误。见[集成验证回执](wafer-blob-position-integration-verification.json)。

## 历史增量：原Bond坐标与重复定位

原Bond坐标读取/转换和重复定位循环接入后，49个原方法与3属性的99项受控断言通过。XY读取命令位置、Z读取编码器位置，依次读取非原子快照；精度比较包含等号，Retry重置次数，失败后OK访问null结果并由消费者捕获停止。校正期间Stop仍可继续XY；实际轴、标定SDK和硬件仍为替身，非设备验收。 详见[专项报告](wafer-position-accuracy-review.md)。下一步原晶圆台位置与墨点/图像处理、实际SDK/驱动，并继续完整启动并发、配置/DLL、构建与设备验收。

收尾验证（2026-09-29）：99项检查与来源审计通过；统一回归PASS、退出码0，阅读器四种宽度检查通过且无页面错误。见[集成验证回执](wafer-position-accuracy-integration-verification.json)。

## 历史增量：原相机避让与Bond到位门控

原真空策略、晶圆相机避让及Bond三维到位判断接入后，43个原方法与3属性的174项受控断言通过。相机避让阈值相等仍阻塞，Bond各轴误差严格小于0.2；位置读取中Stop而判断放行时，算法仍可执行，Nine供晶仍可继续发许可。实际坐标读取、视觉SDK、到位标志及硬件仍为替身，非设备验收。 详见[专项报告](wafer-camera-clearance-review.md)。下一步原Bond坐标获取与重复定位、实际SDK和驱动，并继续启动并发、配置/DLL、构建与设备验收。

收尾验证（2026-09-29）：174项检查与来源审计通过；统一回归PASS、退出码0，阅读器四种宽度检查通过且无页面错误。见[集成验证回执](wafer-camera-clearance-integration-verification.json)。

## 历史增量：完整原视觉采集与相机等待

完整原MatchResult(string,bool,bool)采集接入后，40个原方法与3属性的112项受控断言通过。离线/空跑返回单个相机中心；晶圆相机等待超过8秒仅日志后继续，放行时不检查Stop，Bond相机等待先查Stop；算法异常不自动收真空或撤销对称移动。真实SDK、相机避让谓词、真空策略与图像存储仍为替身，非设备验收。 详见[专项报告](wafer-vision-acquisition-review.md)。下一步继续原真空策略、相机避让与Bond位置判断、重复定位及实际SDK，并完成启动并发、配置/DLL、构建与设备验收。

收尾验证（2026-09-29）：112项检查与来源审计通过；统一回归PASS、退出码0，阅读器四种宽度检查通过且无页面错误。见[集成验证回执](wafer-vision-acquisition-integration-verification.json)。

## 历史增量：原视觉分析与停止分派

原AnalyseDie、GetOffsetWorld及两个匹配分派包装接入后，39个原方法与3属性的118项受控断言通过。Single、Mapping、Box在匹配中Stop后经StopSearch拦截取料；Nine成功路径仍可在Stop状态调用最终XY并发许可。相机中心绑定原表达式；采集、重复定位、标定变换和驱动SDK仍为替身，非设备验收。 详见[专项报告](wafer-vision-control-review.md)。下一步接入完整原视觉采集包装，继续真实SDK、完整启动与并发、配置/DLL、构建及设备验收。

收尾验证（2026-09-29）：118项检查与来源审计通过；统一回归PASS、退出码0，阅读器四种宽度检查通过且无页面错误。见[集成验证回执](wafer-vision-control-integration-verification.json)。

## 历史增量：原九宫格几何与目标点限位

原九宫格重置/分配、距离、墨点包装、范围与坐标包装、目标点限位接入后，35个原方法与3属性的180项断言通过。等距按分支优先，重复分配改变后续最近点；离线多结果可在中心已写后越界。墨点异常可能跳过图像释放；Nine匹配中Stop后仍可XY并发许可。视觉/图像/驱动SDK仍为替身，非设备验收。 详见[专项报告](wafer-geometry-review.md)。下一步接入原AnalyseDie重试/跳过/报警及真实标定包装，继续完整启动与并发、实际驱动、配置/DLL、完整构建与设备验收；29组保持部分复核。

收尾验证（2026-09-29）：180项检查与来源审计通过；统一回归PASS、退出码0，阅读器四种宽度检查通过且无页面错误。见[集成验证回执](wafer-geometry-integration-verification.json)。

## 历史增量：原安全门控与回零路径

原换针台位置检查、台面当前位置碰撞检查、安全位移动及银行轴属性接入后，26个原方法与3属性的135项受控断言通过。未匹配或空换针槽数组不拒绝；碰撞半径转整数，超界OK继续；安全位跳过台面检查，特定离线分支仍调用回零。原StopSearch停止后执行安全位与回零，异常可先于停止提示抛出。轴SDK、视觉等仍为替身，非设备验收。 详见[专项报告](wafer-safety-guards-review.md)。下一步继续目标点环限位、原视觉/九宫格计算、实际驱动到位契约及完整启动与并发；真实配置/DLL、构建和设备验收未完成，29组保持部分复核。

收尾验证（2026-09-29）：135项检查与来源审计通过；统一回归PASS、退出码0，阅读器四种宽度检查通过且无页面错误。见[集成验证回执](wafer-safety-guards-integration-verification.json)。

## 历史增量：原顶针就绪与预顶移动

原顶针就绪检查、预顶移动、两种Z移动重载、载具获取与Z位置属性接入后，23个原方法与2属性的110项受控断言通过。阈值相等可提示但不移动；连续Pause/Stop及预存单步事件仍可放行Z，无事件等待可由原Stop取消。预顶中Stop后仍可调用XY，九宫格路径仍可发许可。驱动与碰撞检查等仍为替身，非设备验收。 详见[专项报告](wafer-eject-ready-review.md)。下一步继续原碰撞/安全位置检查、实际驱动到位契约、原视觉/九宫格计算、完整启动与并发；配置/DLL、完整构建及现场验收未完成，29组保持部分复核。

收尾验证（2026-09-29）：110项检查与来源审计通过；统一回归PASS、退出码0，阅读器四种宽度检查通过且无页面错误。见[集成验证回执](wafer-eject-ready-integration-verification.json)。

## 历史增量：原Stop与供晶动作链

完整原Stop、SetState、停止报警和IsStop接入供晶动作链后，18个原方法与1属性的172项受控断言通过。正常Stop取消单步等待；早期清理失败保留单步开关，后续事件仍可放行轴接口。已发取料许可不撤回，X接口内Stop后仍调用Y。硬件、视觉和存储仍为替身，非设备验收。 详见[专项报告](wafer-stop-chain-review.md)。下一步继续原视觉/九宫格计算、驱动/顶针就绪检查、模式分派与完整启动；真实配置/DLL、构建、并发与设备验收仍待完成，29组保持部分复核。

收尾验证（2026-09-29）：172项检查与来源审计通过；统一回归PASS、退出码0，阅读器四种宽度检查通过且无页面错误。见[集成验证回执](wafer-stop-chain-integration-verification.json)。

## 历史增量：原取料动作链与台面单步门控

原取料移动、补偿、位置记忆、换料判断、台面控制器及单步控制接入后，14个原方法与1属性的210项受控断言通过，绑定3个原信号。连续模式及带单步许可的Pause/Stop可到达轴命令接口；离线先关真空，位置保存失败保留内存值。驱动/视觉和Machine.Stop仍为替身，未完成设备验收。 详见[专项报告](wafer-action-gates-review.md)。下一步接入原视觉分析、九宫格计算、原Stop与下层轴/就绪门控；完整启动、构建、配置/DLL、真实并发和设备验收仍待完成，29组保持部分复核。

收尾验证（2026-09-29）：210项检查与来源审计通过；统一回归PASS、退出码0，阅读器四种宽度检查通过且无页面错误。见[集成验证回执](wafer-action-gates-integration-verification.json)。

## 历史增量：四种原搜晶与停止门控

完整供晶消费者与四种原搜晶、NextDie、AnalyseDies、StopSearch共8个原方法及1属性的172项受控断言通过。九宫格先检查Stop，Single/Mapping/非静态Box先调用搜索动作接口再检查；耗尽可提前返回，成功路径门控后变Stop仍可发送许可。底层视觉/几何/动作和Machine.Stop仍为替身，不代表设备验收。 详见[专项报告](wafer-search-gates-review.md)。下一步接入下层视觉/动作门控、原Stop及模式分派；完整构建、正常启动、真实并发、配置/DLL与设备验收仍待完成，29组保持部分复核。

收尾验证（2026-09-29）：172项检查与来源审计通过；统一回归PASS、退出码0，阅读器四种宽度检查通过且无页面错误。见[集成验证回执](wafer-search-gates-integration-verification.json)。

## 历史增量：完整供晶消费者与取料许可

完整原供晶Dowork、IsNeedChange及完整Signal的212项受控断言通过，绑定ManualReset需料和AutoReset许可声明。进入等待后Pause及接收后Stop均可继续搜晶接口并放行；真实事件故障区分请求清除与许可发送，后续异常不撤回许可。搜晶、动作、Stop和持久化仍为替身，非设备验收。 详见[专项报告](wafer-consumer-pause-review.md)。下一步接入原Block搜晶及下层动作门控、原Stop和模式分派；完整正常启动、现场配置/DLL及设备验收仍待完成，29组保持部分复核。

收尾验证（2026-09-29）：212项检查与来源审计通过；统一回归PASS、退出码0，阅读器四种宽度检查通过且无页面错误。见[集成验证回执](wafer-consumer-pause-integration-verification.json)。

## 历史增量：完整空跑启动与任务保护

完整原StartDryRun、正常启动保护块及完整Signal的115项受控断言通过，另绑定四个原信号构造。8种Task状态仅Running被保留；空跑前置初始化不受Pause/Stop门控，重复启动仍替换材料。进入等待后Pause可消费放行；完成信号早于材料构造。未证明生产并发启动、原生UI或设备验收。 详见[专项报告](dry-run-task-review.md)。下一步继续供晶消费者、完整正常启动与实际并发，以及现场配置和加载DLL；29组保持部分复核。

收尾验证（2026-09-29）：115项检查与来源审计通过；统一回归PASS、退出码0，阅读器四种宽度检查通过且无页面错误。见[集成验证回执](dry-run-task-integration-verification.json)。

## 历史增量：外层输送任务循环与异常

9个原方法、1段原外层任务委托及完整Signal的52项受控检查通过。Success和NoStart继续循环，Abort与Exception调用原Stop；外层catch可结束任务但保留Working，Stop异常可留下部分清理。入口与循环间Pause恢复已验证。仅原委托，不含完整Start、原生UI或设备验收。 详见[专项报告](outer-transport-task-review.md)。下一步核对任务去重/重启、空跑与供晶消费者，以及实际配置和加载DLL；29组保持部分复核。

收尾验证（2026-09-29）：52项检查与来源审计通过；统一回归PASS、退出码0，阅读器四种宽度检查通过且无页面错误。见[集成验证回执](outer-transport-task-integration-verification.json)。

## 历史增量：轴初始化切面与返回值消费

9个原方法的84项受控断言及6个DLL方法的12项只读检查通过。轴返回失败码被原模块忽略，固定完成传感器下仍提交材料；抛异常则中断。初始化切面可预设Success短路，仓库状态bool不等于机器Pause/Stop。未执行真实Axis或驱动。 详见[专项报告](axis-return-transfer-review.md)。下一步接入外层输送返回值处理、核实仓库状态属性与实际DLL版本，并继续空跑与供晶消费者；29组保持部分复核。

收尾验证（2026-09-29）：84项检查与来源审计通过；统一回归PASS、退出码0，最终阅读器四种宽度检查通过且无页面错误。见[集成验证回执](axis-return-transfer-integration-verification.json)。

## 历史增量：原夹爪终止与输送轴命令

9个原方法、完整Signal原类与46项受控检查通过。四种夹爪模式报警Abort执行原Stop后以void返回，父输送仍在Stop下调用两段轴接口并提交材料。五处Stop依赖异常则阻断后续轴命令；缺失皮带设置先提示后在轴包装入口失败。轴、I/O及保存为替身，不证明实机运动。 详见[专项报告](transport-unclamp-stop-review.md)。下一步接入外层输送返回值处理及实际轴驱动门控，并继续空跑与供晶消费者；29组保持部分复核。

收尾验证（2026-09-29）：46项检查与来源审计通过；统一回归PASS、退出码0，最终阅读器四种宽度检查通过且无页面错误。见[集成验证回执](transport-unclamp-stop-integration-verification.json)。

## 历史增量：固晶放行下游输送暂停

完整原输送方法和Signal原类的32项受控检查通过。进入事件等待后的Pause仍可接收放行并调用气缸、皮带及材料提交；入口Pause会阻塞。Wait返回后改变状态不重新门控，保存异常保留已转移材料。动作、状态存储和保存为替身，非原Stop或设备验收。 详见[专项报告](transport-pause-review.md)。下一步接入外层输送返回值处理、原Stop及下层驱动门控，并继续空跑与供晶消费者；29组保持部分复核。

收尾验证（2026-09-29）：32项检查与来源审计通过；统一回归PASS、退出码0，最终阅读器四种宽度检查通过且无页面错误。见[集成验证回执](transport-pause-integration-verification.json)。

## 历史增量：S2固晶循环门控暂停

17个原方法、完整Signal原类与37项受控检查通过。S2五个阶段暂停恢复已验证；进入来料等待后Pause仍可消费事件，收尾SendAway仅由Stop阻止。S2单步后WaitStart阻止预点胶。真实线程和事件配合服务/驱动替身，非产品宿主或设备验收。 详见[专项报告](s2-door-pause-review.md)。下一步继续输送、供晶暂停集成及放行信号下游消费者；29组保持部分复核。

收尾验证（2026-09-29）：37项检查与来源审计通过；统一回归PASS、退出码0，最终阅读器四种宽度检查通过且无页面错误。见[集成验证回执](s2-door-pause-integration-verification.json)。

## 历史增量：单步门控及原界面事件

17个原方法、完整Signal原类与33项受控检查通过。原单步按钮不重查Pause或Stop，单步事件可放行预点胶但后续WaitStart拦住插补；原退出单步先发送系统2事件，发送失败会保留单步开启。真实线程和事件配合控件/驱动替身，非原生UI或设备验收。 详见[专项报告](single-step-door-review.md)。下一步继续S2、输送、供晶暂停集成与原生UI及快捷键分派边界；29组保持部分复核。

收尾验证（2026-09-29）：33项检查与来源审计通过；统一回归PASS、退出码0，最终阅读器四种宽度检查通过且无页面错误。见[集成验证回执](single-step-door-integration-verification.json)。

## 历史增量：安全门到完整点胶循环暂停

门控接入真实Signal及完整原S1任务循环：15个原方法、28项受控检查通过。四处屏障验证暂停恢复及原Stop；插补成功返回后仍可提交完成状态，下一信号检查才阻塞。驱动及服务为替身，非现场机械停止验收。 详见[专项报告](door-task-pause-review.md)。下一步继续单步等待门控响应及S2、输送、供晶各自的暂停检查点；29组保持部分复核。

收尾验证（2026-09-29）：28项检查与来源审计通过；统一回归PASS、退出码0，最终阅读器四种宽度检查通过且无页面错误。见[集成验证回执](door-task-pause-integration-verification.json)。

## 历史增量：安全门到来料等待暂停

安全门到点胶来料等待：8个原方法、16项受控检查通过；暂停阻止等待阶段预点胶，但切换Stop先调用预点胶，动作中暂停再恢复可重复调用。驱动及动作体为替身，非完整生产任务或设备验收。 详见[专项报告](safe-door-pause-review.md)。已找到既有完整Signal原类测试，下一步将门控接入真实Signal及完整S1任务场景，继续动作内部暂停检查；29组保持部分复核。

收尾验证（2026-09-29）：16项检查与来源审计通过；统一回归PASS、退出码0，最终阅读器四种宽度检查通过且无页面错误。见[集成验证回执](safe-door-pause-integration-verification.json)。

## 历史增量：预热保存与产品异常宿主

预热设置与全局异常处理：61项检查及10个独立异常进程通过；真实保存重读确认分钟分量计时与完成标志保留。原异常处理器仅提示。非完整产品宿主或设备验收。 详见[专项报告](heating-host-review.md)。已登记统一回归，29组继续部分复核；完整构建、原生UI、生产并发及设备验收未完成。

收尾验证（2026-09-29）：模块证据与统一回归登记完成，阅读器重建完成；verify-all退出码0、PASS，四种宽度浏览器检查通过且无页面错误。见[集成验证回执](heating-host-integration-verification.json)。下一步补安全门到任务暂停的链路：原IsSafeDoorClosed读取“门控”Sensor；点胶GetInputSignal在预点胶前后检查IsPause，现有S1测试将IsPause固定为false，尚不能证明暂停响应，生产中的Signal.WaitStart行为也需继续核实。

## 历史增量：安全门、激光、温度与后台线程

89项方法/线程检查与9个独立Framework异常进程通过。原安全门仅改变Pause；激光环境/算法失败先提示后Stop，光强异常提示后仍可能true；温度先Stop后提示，预热用Minutes分量。原后台循环已验证有界顺序、存活去重与结束重启，9个故障点在独立宿主中中断后续服务并非零退出。详见[后台监控报告](background-monitor-review.md)。46份原成员纳入程序集不等于全部分支覆盖；真实设备、产品宿主退出策略、完整构建及生产并发未验收，29组保持部分复核。

## 历史增量：实际界面急停入口与机器方法区分

27项检查通过，原急停按钮事件只Parallel停轴，不调用Machine.EmergencyStop、Stop或Abort；原UI在Working/Pause禁用按钮，Stop启用。直接调用并非点击禁用控件；受控任务及机器状态保持，异常直接传播，另验证同步等待及Machine方法对照。1436份C#文本中EmergencyStop精确方法词元仅有定义，不能排除反射或外部调用。详见[急停入口报告](emergency-entry-review.md)。45份成员纳入程序集不等于全分支覆盖；原生UI、真实驱动、安全电路与生产并发尚未验收，29组保持部分复核。

## 历史增量：急停与三个Abort真实Task验证

87项检查通过，执行原EmergencyStop、Stop与三个Abort，覆盖八种真实Task状态。点胶Abort仅Dispose，五种未完成状态抛异常并截断后续Abort；固晶和供晶Abort不终止受控任务。另核对S1关闭配置仍调用、轴异常与六处Stop失败中断。详见[急停报告](emergency-abort-review.md)。轴命令、状态和业务任务体为替身，非物理急停或设备验收；生产源码未修改，完整构建、生产并发及原生UI仍待验收，29组继续部分复核。

## 历史增量：真实Task关闭门控与消费者

155项检查通过，直接执行原IsAllowTaskClosed，覆盖16字段×8种真实Task状态。仅Running阻断；Created、WaitingForActivation、WaitingToRun及WaitingForChildrenToComplete未完成时仍放行。已接回原启动准备、停止提示UI及Stop，确认状态Stop不代表受控Task结束；另验证配置排除、引用替换及容器异常。详见[任务关闭报告](task-closure-review.md)。生产任务体、实际并发、原生UI、完整构建与设备仍未验收，29组继续部分复核。

## 历史增量：启动入口异常与配方界面保护

43项集成检查通过，新增两个原启动事件、原Stop、原配方事件及六个UI状态方法，绑定3处Designer事件。确认启动异常被按钮捕获后调用Stop；Stop清理再失败时finally仍恢复界面，普通Stop刷新不检查任务关闭而可启用配方按钮。正常运行/暂停UI确实禁用加载按钮；原事件直接调用没有工作状态重查。详见[入口与配方保护报告](startup-entry-review.md)。控件、I/O、任务内部和配方重载仍为替身，未证明真实消息循环交错、线程终止或现场互斥；完整构建与设备未验收，29组继续部分复核。

## 历史增量：真实配置到启动及排序的有界集成

实际Singleton/JSON DLL、29份原成员片段、原SystemProcess与ActionNodeMessage的63项集成检查通过。8种非正批次在明确替身条件下通过原门控到达分批代理；此时已设Working并调用Transport/Wafer/S1的Start，尚未调用Bond。另覆盖8种正常排序、前置门控失败、启动异常、空步骤和未知模式。详见[启动集成报告](startup-config-review.md)。代理在危险循环前主动停止，生产线程与设备未运行；完整依赖、入口异常承接、原生UI、并发和构建仍待验收，29组保持部分复核。

## 历史增量：真实Singleton文件加载与保存

项目Singleton/JSON帮助器DLL、完整SystemProcess及原重置方法的27项Framework临时文件检查通过。真实加载接受开启批次的0、保存重读保留负数；确认缓存不随磁盘自动刷新、旧实例Save保存静态缓存、清缓存后Save写null，以及锁文件失败保留旧磁盘值。详见[单例文件报告](singleton-load-review.md)。派生包装器不含完整生产门控，真实任务/并发构建及设备未验收，29组保持部分复核。

## 历史增量：批次数输入与JSON加载边界

四个原界面方法、两份原枚举、完整SystemProcess及项目Newtonsoft DLL的32项Framework检查通过。界面声明下限1，但原事件不独立校验；真实JSON可保留0/负数及未知模式，保存异常不回滚内存。指定生产门控未引用批次数，仍未证明实际Singleton加载到排序的完整生产可达性，未执行无限循环。详见[批次数报告](cycle-config-review.md)。原生UI、文件加载、并发构建与设备未验收；29组保持部分复核。

## 历史增量：动作控制器初始化、排序与筛选

33个原方法及完整ActionNodeMessage的80项隔离检查通过，含16种模式组合的生产动作次序、翻转沾胶顺序、分段分批、异形/禁用筛选和相对贴片重排。确认空初始化缓存保留、上层禁用不级联下层动作及异常后部分队列变更。非正批次潜在无限循环仅作源码推导，配置可达性待查。详见[排序报告](action-sort-review.md)。真实配置和任务联合运行、并发构建及设备未验收，29组保持部分复核。

## 历史增量：真实动作控制器与载具构造链

17个原方法/构造函数及完整ActionNodeMessage的51项隔离检查通过。确认消息推进、S2特殊节点重复保护、上下文缓存与步骤字典边界；正常载具有参构造重新注入S2及S1步骤。详见[动作控制器报告](action-controller-review.md)。控制器初始化排序/过滤、完整任务联合运行、真实配置几何、并发构建与设备未验收；生产源码不变，29组保持部分复核。

## 历史增量：S2生产任务、报警与人工上下料集成

13个原方法及完整Signal/枚举59项检查通过，实际串联S2任务、来料/送走、点胶节点、安全Z和Stop。确认两种Retry路径、直接Fail完成动作、Ignore未写焊点标记、停止后收尾、先注入旧对象再重建以及人工保存/提示失败边界。详见[S2任务报告](s2-task-integration-review.md)。真实动作服务、补偿/插补、UI文件、并发构建与设备尚未验收，生产源码不变，29组保持部分复核。

## 历史增量：真实Stop与事件信号接入S1失败链

11个原方法及完整Signal/枚举源码60项检查通过，使用真实EventWaitHandle；S1失败路径已进入原Stop、状态及报警包装。复现日志/报警异常中断清理、需晶事件释放失败、计数部分更新，以及WaitStart读取交错与定时等待State不同步。详见[停止信号报告](machine-stop-signal-review.md)。日志队列、状态存储和硬件仍为替身，真实并发、构建与设备未验收，29组保持部分复核。

## 历史增量：S1任务与点胶节点真实方法串联

六个完整原方法30项同步集成隔离检查通过，实际执行任务循环、入料等待、节点门控/执行、安全移动与单步包装。复现失败恢复安全Z异常截断后续Stop、回调异常穿出任务、入料失败退出及放行门槛。详见[S1任务集成报告](s1-task-integration-review.md)。动作服务、停止内部、信号并发、完整控制器与硬件仍为边界；生产源码不变，29组保持部分复核。

## 历史增量：点胶节点失败传播与安全位置

六个完整原方法68项隔离检查通过：两套DoWork、安全移动及单步域包装。确认非成功结果转Alarm、回调异常覆盖返回、完成标记早于统计、安全移动异常及关闭单步后旁路信号等待；另静态串联S1/S2生产任务分派和Machine.Stop。详见[节点失败传播报告](dispense-node-failure-review.md)。完整控制器/调度器未端到端运行，物理阀状态和设备仍未验收，生产源码不变，29组保持部分复核。

## 历史增量：完整GuGao插补初始化与异常退出

完整原Interpolation方法及点配置类的79项隔离检查通过：9项正常顺序、22处初始化非零返回、37处SDK异常和11项边界。确认错误码覆盖、空数据仍启动、null点在使能后失败，以及外层catch丢失异常原因且不补跑剩余SDK清理。两套控制器异常出口另作静态核对。详见[完整驱动报告](dispense-driver-lifecycle-review.md)。SDK全部为替身；完整控制器、全局停止保护、部署与设备仍未验收，生产源码不变，29组继续部分复核。

## 历史增量：S1/S2点胶驱动字段消费

三个精确原片段和完整点配置类的29项隔离检查通过，复现ETEL减速度取Acc、GuGao起点参数/目标点坐标与IO队列、错误码覆盖和持续等待边界。S1/S2调用点静态核对完成。详见[驱动复核报告](dispense-driver-consumption-review.md)。无硬件调用；完整初始化、控制器外层清理、SDK指针与设备仍未验收，29组保持部分复核，生产源码不变。

## 历史增量：Framework真实克隆与点胶预处理

五份完整原类和四个精确原方法在本机.NET Framework下30项检查通过，使用原BinaryFormatter克隆，验证对象图隔离、内部别名、基类数据和事件排除，以及归一化、旋转、速度倍率和非有限数边界。发现前置空曲线影响极值初始化、负百分比及后置旋转可留下非法输出。详见[预处理报告](dispense-pretreatment-review.md)。未运行Fody织入、原生UI、控制器或设备；生产源码不变，29组继续部分复核。

## 历史增量：上层编辑确认与业务配置往返

九份完整原类和六个精确原方法的31项隔离检查通过。确认EndSpeed丢失、Dec被Acc覆盖、坐标及参数转换、失败后取消不回滚、合理性getter改写数据、NaN和末点校验边界，以及Confirm双保存调用的部分提交。详见[编辑桥接报告](dispense-editor-bridge-review.md)。原生UI、真实持久化与克隆、全部生产字段消费和部署仍未验收；生产源码不变，29组继续部分复核。

## 历史增量：真实SXml模板保存与回读

七份完整原类配合仓库AKRS.Base.dll的22项真实临时文件检查通过：小数坐标、八项工艺字段和图像矩阵往返；复现测高标志丢失、缺图模板读回失败、旧图复用和XML锁定时图片先写入。详见[模板往返报告](dispense-pattern-roundtrip-review.md)。跨区域与全部异常、原生UI、部署兼容性、完整构建及设备仍未验收；29组继续部分复核，生产源码不变。

## 历史增量：背景图变换与鼠标状态

40个原始类文件及23个原方法/属性的39项隔离检查通过。确认平移Move/Up的Y符号不同、松开不沿用轴锁定、旋转重入保留holding、两个重置菜单均清除全部矩阵，以及重建失败后的部分提交。详见[背景图报告](dispense-background-edit-review.md)。实际位图重建、原生UI、SXml文件回读、完整构建及设备仍未验收；生产源码不变，29组继续部分复核。

## 历史增量：参数编辑、批量应用与端点往返

31个原方法/属性配合真实Curve与DataTable的38项隔离检查通过。确认单行解析后一次提交、全曲线批量清零高度补偿和测高标志、当前曲线批量依赖值变更回调，以及端点表修改未自动写回曲线。详见[参数往返报告](dispense-parameter-roundtrip-review.md)。原生编辑提交与选择时序、文件回读、背景动作、完整构建及设备仍未验收；生产源码不变，29组继续部分复核。

## 历史增量：模式切换、取消与表格刷新

23个原控件/表单方法配合原处理器的34项集成隔离检查通过。确认同一ActionChanged事件前后双通知、SetMode失败后的同模式重试跳过、绘制退出双重短曲线清理，以及删除索引与表格刷新事件顺序相关。详见[生命周期报告](dispense-mode-lifecycle-review.md)。原生SelectionChanged时序、参数往返、背景动作、完整构建和设备仍未验收；生产源码未修改，29组保持部分复核。

## 历史增量：旋转、平移及选择交互

三个完整原处理器的34项隔离检查通过，覆盖鼠标按钮、修饰键、异常重试与选择高亮；复现旋转后缓存命中边界未刷新和全局X符号影响旋转方向。详见[变换选择报告](dispense-transform-select-review.md)。生产源码未修改；真实模式取消链、表格往返、背景动作、UI、完整构建和设备仍待完成，29组继续部分复核。

## 历史增量：追加、移动及绘制动作

三个完整原处理器的24项隔离序列通过，复现重叠吸附、缓存末点缩放未刷新、右键未结束移动、退出不撤销坐标，以及追加/绘制事件与重绘顺序差异。详见[动作报告](dispense-draw-edit-review.md)。控件模式切换和表格事件仅静态核对，旋转平移选择、真实UI、完整构建及设备仍待完成；29组保持部分复核。

## 历史增量：插点、删点与缩放鼠标序列

三个完整原处理器及基类的27项隔离序列通过。复现吸附点与事件坐标不一致、删点候选跨失败/未命中保留、右键缩放、坐标原点相关比例和失败重试差异；另核对控件分派与表单订阅。详见[鼠标报告](dispense-mouse-edit-review.md)。真实UI、宿主清空事件副作用、其余动作及产品构建仍待完成，29组保持部分复核。

## 历史增量：点胶曲线原类几何

十一份完整原始源码的30项检查通过，使用真实System.Drawing矩阵覆盖旋转、缩放、距离、命中与删点。复现零长度距离NaN、矩形边缘不对称、中间段删除空操作和回调部分更新；确认控件包装方法在变换成功后刷新实际坐标，避免误报漏刷新。详见[曲线报告](dispense-curve-geometry-review.md)。鼠标状态机、全域数值稳定性、完整构建和设备验收仍待完成，29组保持部分复核。

## 历史增量：点胶模板删除管理

两类完整原始管理窗口的20项临时文件隔离检查通过，核对8处Designer事件绑定。复现背景图锁定时模板已删除而列表保留、全部删除先清空界面、快照遗留与临时文件清理差异。详见[删除报告](dispense-repository-delete-review.md)。图像索引仅在List替身下验证，真实控件、曲线与鼠标处理、完整产品及现场验收仍待完成。29组保持部分复核。

## 历史增量：高阶与大坐标补偿矩阵

完成[108组拟合矩阵](axis-fit-scale-review.md)，包括直线、正弦和峰形人工曲线及31/32点阶数切换。所有组返回系数，但部分非线性大坐标样本有明显误差；记录原幅度检查接受0.5修正而真实误差约0.690211的具体样本。六项实验行为断言与报告哈希检查已加入统一回归，不能算生产精度验收。源码及设备配置未修改，整体仍部分复核。
## 历史增量：轴补偿原类数值验证

完整五个补偿原类配合项目指定net48 MathNet程序集的37项隔离检查通过，覆盖开关/幅度边界、NaN/Infinity、同名替换、不等长与空样本、两重载范围差异、分段原值返回及私有圆拟合。退化拟合可不抛出而写入极大或非有限系数；同名重复项可使旧项继续生效。详见[补偿报告](axis-compensate-module-review.md)与[回执](axis-numeric-test.json)。仅替换配置单例和路径，不加载/保存生产配置或运动；完整构建、运行版本与设备验收仍未完成。
## 历史增量：四类示教窗口原类验证

ModuleAdjust、SubstrateAdjust、ModulePosition和TUPosition完整原类35项隔离检查通过，确认输入异常先后顺序、不同Done返回值、关闭后的索引更新及注入Close异常的状态保留。与SubstratePosition已有20项合计55项；[报告与边界](teach-test-navigation-review.md)已更新。测试复用原主类，Designer、控件与输入为替身，原产品源码不变；真实UI/设备/完整构建仍未验收，29组仍部分复核。下一步回到模块剩余缺口，区分本地可完成证据与需要现场环境的验收。
## 历史增量：示教输入失败原类验证

SubstratePosition完整原类及AssistantConfig的20项隔离检查通过，复现三类列数解析失败后的页签/索引不一致，并验证合法重试、最终行数失败不关闭、原点跳步及隐藏处理器越界。详见[示教导航报告](teach-test-navigation-review.md)与[测试回执](substrate-navigation-test.json)。原产品源码未修改；控件和输入为替身，真实UI、设备、保存和产品构建未验收。下一步继续其余窗口的输入与关闭差异以及剩余模块缺口，29组仍部分复核。


## 历史增量：其余五类示教测试导航

已完整读取Module/Substrate调整、Module/Substrate/TU位置五个测试主类，并核对22处Designer事件绑定。[步骤及输入失败顺序](teach-test-navigation-review.md)区分有效导航/输入与注释中的采点保存，记录原点跳步和不同Done关闭结果。十份源码快照已绑定；真实UI、输入框和产品构建未运行验收。

## 历史增量：资源图片解码

134条外部资源引用已分型检查：111条Bitmap均经System.Drawing解码并绘制到内存图像；23条SVG仅作安全XML结构检查，未调用DevExpress渲染器。原文件保持不变，[逐项结果与验收限制](resource-images-review.md)已登记并纳入回归。产品嵌入、DPI/视觉效果及实际运行仍待验收。

## 历史增量：资源内部文件引用

已解析388份项目声明的RESX，核对134条ResXFileRef目标，当前均存在；记录资源文件与目标文件哈希、原始引用和行号。[资源内部引用报告](resx-references-review.md)纳入统一回归。没有执行嵌入对象反序列化或资源编译，图像解码、控件许可和运行加载仍未验收。

## 历史增量：16项目资源文件声明核对

已检查623条资源/内容/None声明，32条字面路径缺失：31条为Dispense项目残留的.svn元数据，1条为迁移项目packages.config。没有把历史版本控制条目算作生产资源缺失；原声明、条件与元数据已存入[资源材料核对](project-assets-review.md)。存在性核对纳入统一回归，仍不能替代MSBuild资源/许可证生成与产品构建。

## 历史增量：迁移资源与配置材料

已用XML解析排除模板注释，确认三份resx无数据项、仅一个设计器元数据，Settings为空；核对DevExpress许可及程序集声明，发现项目声明的packages.config缺失。[资源与配置报告](changejson-assets-review.md)及哈希回执纳入统一检查。资源编译、许可生成和完整产品构建仍未验收。

## 历史增量：迁移文件辅助类

已读取34个公开方法/重载，7项原类临时文件验证通过；确认短写残留、移动目标误建目录、目录清理部分删除和进程当前目录变化。项目内未发现具名调用，按钮直接使用File；[辅助类报告](changejson-files-review.md)保持两条路径分开。真实构建、动态调用与完整输入验收仍未完成。

## 历史增量：迁移双任务旧快照覆盖

原方法隔离检查扩至9项。用真实Task及事件闸门控制同一窗口的两个任务：先暂停第一任务于读取后，替换映射项让第二任务成功写入，再恢复第一任务；实读确认旧快照覆盖第二次结果，且两任务都正常结束。[步骤和限制](change-json-module-review.md)。此项补足一种确定交错，真实WinForms时序及其余并发尚未验收。

## 历史增量：迁移按钮临时文件失败验证

完整BtUpdateJson_Click原方法8项检查通过，使用真实Task与临时文件，覆盖格式零匹配、缺失/同名映射、第二文件读取失败、Invoke失败、列表变化及文件锁写入失败。确认逐文件部分提交和提示先于写入的边界；真实UI和多任务覆盖尚未验证。结果已回填[模块报告](change-json-module-review.md)，模块仍部分复核。

## 历史增量：迁移工具反射辅助类原方法验证

完整ReflectionHelper原源码7项隔离检查通过：属性复制int/string样本保持旧值，两种CreateInstance对缺失类型分别抛异常或返回null，私有构造和类型不兼容边界已验证。仅发现本文件具名声明，尚无生产调用证据。[契约与测试范围](changejson-reflection-review.md)。测试纳入统一回归；迁移文件写入、并发、UI及完整构建仍未验收。

## 历史增量：非编译源码对已有结论的影响

后续同步：配置边界已写入Common声明报告和机器框架报告正文，三个受影响模块的报告哈希已更新，源码阅读器已重建并通过真实Edge的全部快照、深链接和四种宽度检查。构建说明中的可执行示例已改为AnyCPU。

已逐项核对26个未纳入Debug/Release AnyCPU Compile的文件与两套源码登记表、模块reviewedFiles和代表关系。命中2段快照：Common.cs声明和MachineService空类；未命中直接绑定的代表执行关系。已在交接说明中限定其用途，详见[影响表](compile-scope-impact.md)。此核对不覆盖仅凭类名描述的隐式引用，也不替代完整构建；29组仍部分复核。

## 历史增量：MSBuild实际求值与编译项范围

完成[本机配置求值](msbuild-evaluation-review.md)：16项目×Debug/Release×AnyCPU/x86/x64共96组，32组AnyCPU成功，64组直接平台组合因OutputPath未配置失败。得到1410个Compile文件，比1436文件系统基准少26个，保留双口径；主工程Debug|AnyCPU实际目标x64。更正历史x86构建建议，记录缺失项目和HintPath。只读求值不等于完整构建，SDK/厂商依赖与设备运行仍未验收。下一步将非编译项边界落实到已有结论，并继续其余模块。

## 历史增量：换片图与语义台账同步

已将换片重试、窗口部分提交和日志队列停止边界回填[供晶交互图](wafer-supply-workflow.html)及门户：保留12节点/15关系，停止节点改为“提示后请求停止”。两个节点、四条相邻关系回链六段新增源码，主图总步骤/关系仍为89/101。Showcase交付9/9、零错误/警告，四种桌面尺寸通过浏览器检查，浅色小屏和深色大屏截图已审查。同步校验纳入统一回归。该清单项完成限定范围图文同步，不增加模块完整验收；接下来继续剩余模块缺口及真实依赖条件。

## 历史增量：换片名称与网格状态一致性

完成[名称/网格复核](wafer-selection-review.md)：23项原方法受控检查通过，确认无效名称保留旧临时对象、Save不重新验证名称，适配器创建失败可留下临时对象与网格不同步；槽位状态先赋值再初始化，失败无本地回滚。16段快照接入后为17个专题、212段快照。控件事件为显式测试调用，真实DevExpress生命周期、配置/存储和设备尚未验收。下一步同步换片图与语义台账；29组仍部分复核。

## 历史增量：手动换片窗口初始化与提交

完成[手动换片窗口复核](manual-wafer-change-review.md)：五个原方法24项隔离检查通过，覆盖初始化取消/停止状态异常、先发布共享引用再保存/移动、部分提交后Abort和关闭清理二次异常。Designer三处事件绑定已固化；9段快照接入后为16个专题、196段专题快照。真实UI、深拷贝、配置持久化及运动SDK仍未验收，29组仍部分复核。下一步继续名称/网格事件一致性及换片图与语义台账同步。

## 历史增量：完整自动换片外层与停止检查点

完成[换片重试复核](wafer-change-retry-review.md)：完整ChangeTabletAuto原方法16项受控检查通过，覆盖三种false重试、异常逸出、入口Stop及重试中Stop、选层和传感器失败前缀。补充手动换片窗口构造调用InitControl/ShowDialog和按Working分派异常的静态证据。5段快照接入后为15个专题、187段快照；业务初始化、UI和硬件仍为替身，29组仍部分复核。剩余窗口InitControl/完成提交、设备取消与图形语义同步需继续完成。

## 历史增量：状态日志队列与换片失败传播

完成[停止日志与供晶失败边界](state-queue-failure-review.md)：18项受控检查通过，原SetState/Stop配合真实容量500队列，确认状态已Stop但入队阻塞/失败时后续清理未执行；供晶catch先弹窗后Stop，二次异常影响任务结束状态。另验证空跑分支忽略初始化false，初始化异常保留先写的Good槽位状态。12段证据接入后为14个专题、182段快照。运行环境为内置.NET，UI/硬件为替身，非完整换片或现场Framework验收；29组仍部分复核。后续继续换片重试的停止观察点和未闭合模块内部关系，并核销已由新证据覆盖的旧缺口。

## 历史增量：五类启动门控与供晶并发重现

完成[重复启动与状态交错验证](task-start-concurrency-review.md)：五个原Start方法对null及全部8种TaskStatus的45项受控检查，加供晶双调用竞争和停止状态交错，共47项通过。使用真实.NET Task，旧WaitingToRun任务引用被替换后仍可执行；供晶两个并发调用均可通过检查并创建工作Task。业务循环、UI和状态服务为替身，未证明现场频率或完整Stop安全性。7段源码证据接入后为13个专题、170段专题快照；29组仍部分复核。下一步补状态日志队列失败和换片故障传播，真实配置、SDK与设备验收仍未完成。

## 历史增量：供晶初始化失败与重试残留

完成[供晶启动初始化复核](wafer-start-init-review.md)：9项原方法替身检查通过，9段源码证据接入统一阅读器。确认初始化异常被供晶Start弹窗catch处理，正常返回后外层调度可继续；搜索标志先修改，窗口引用在CreateForm/Show/Hide前赋值，失败后再次初始化会跳过非null引用。九点重置及换片调用另行保留依赖边界。当前12个专题、163段专题快照；29组仍部分复核、0组完整验收。下一步追WaitingToRun重复启动、Start/Stop并发和换片入口故障传播；真实UI、线程退出、配置与设备未验收。

## 历史增量：启动调度顺序与同步异常传播

完成[任务启动顺序及失败边界报告](production-start-launch-review.md)：原Machine.Start通过30项替身隔离检查，覆盖普通/补偿模式下16种配置组合、准备检查返回/异常、10处同步失败截断与两类正常返回边界。补充三个具名调用点的静态恢复差异及7段源码证据。统一阅读器现为11个专题、154段专题快照；模块完整验收数量不变。真实线程退出、并发启动和设备安全状态仍未验收。

## 历史增量：焊后反馈证据完成统一接入

已将[焊后反馈专题](postbond-feedback-source-review.md)的31段源码快照接入统一阅读器，补上此前报告绑定和换行格式差异。当前为10个专题、147段专题快照，独立于29组模块、552条代表关系和940段模块快照统计。新增规范化原文、源文件与片段哈希的拒绝检查；浏览器验证报告链接和全部专题原文。此增量完善交接追溯，不新增业务覆盖，也不替代设备验收。

### 此前增量：专题证据接入统一源码阅读器

9个独立专题、116段经过报告哈希和源码原文核对的快照已接入[模块源码阅读器](module-source-explorer.html)，支持模块筛选、检索、报告回链和证据深链接。原模块台账29组、552条代表关系、940段快照独立统计，未提升业务覆盖或完整验收状态。另一格式的postbond专题仍待适配，页面已披露。详见[工程师交接说明](source-explorer-handoff.md)。

## 历史增量：统一目标达成与覆盖口径

已将[源码覆盖审计](source-coverage-audit.md)改为从当前台账生成：修正旧88/102/21口径为现有89步骤、101关系、89条语义登记，并按13项原始目标列出状态、证据与未证明部分。16项目、29分组、1436个排除bin/obj的C#文件，与专题全树扫描分开统计。新增机器可读审计与漂移检查，未扩大业务覆盖，也未把模块升级为完整验收。

## 历史增量：配方就绪到生产启动门控

完成[就绪标志与普通启动入口复核](recipe-readiness-start-gate-review.md)：扫描1452个C#文件，固化6处具名标志引用和8段源码快照。原MachineInitSuccess及PrepareMachineReadyToStart的16项隔离检查通过，明确启动门控前清文件/信号与缺陷复位的顺序、回零选项的内外层差异，以及磁盘/预热异常传播。PR标志true不等于整个启动通过。真实SDK、配置和设备闭环仍未验收；29组完整验收数量不变。

## 历史增量：配方切换时序图与逐条溯源

完成[配方加载→重载时序图](recipe-switch-sequence.html)：6个参与者、11条关系，每条绑定源码，配套报告19段源码快照；复用入口7项和重载10项隔离检查。覆盖同ID跳过、程序初始化、在线/离线与异常恢复。九项图检查、四种尺寸及浅深色截图复核通过。当前仍为专题内部复核阶段；29组模块完整验收数量不变，真实配方、SDK与设备闭环未验收。

## 历史增量：配方重载内部就绪与恢复矩阵

在[配方切换报告](recipe-switch-failure-review.md)中补充ReLoadRecipe十项隔离检查：在线/离线、缺PR、try前dock及Init异常、旧视觉关闭/新方案创建/名称枚举/算法初始化异常。确认缺PR仍可置就绪，离线仍先Init，try前失败不执行本方法finally；try内所测异常恢复界面并重抛。与入口七项检查共同纳入统一回归；依赖为替身，不计作真实视觉或生产验收。

## 历史增量：配方加载结果与路径重置边界

完成[配方加载失败矩阵](recipe-switch-failure-review.md)：七项原入口替身检查确认同ID保存但不重载、保存与重载异常保留新内存ID且跳过后续清理。六类程序逐项重置路径/实例，供片清理异常可留下部分重置状态；重载try之前的异常不由其finally恢复界面。检查和源码快照纳入统一回归。真实配置文件、SDK及现场恢复未验收，29组仍部分复核。

## 历史增量：坐标保存与既有DLL证据衔接

完成[坐标保存依赖回链](calibration-coordinate-persistence-review.md)：核对项目HintPath、随附DLL哈希与对象保存IL，修正此前将保存实现整体列为未知的表述。坐标类Save不继承Singleton.Save锁，传入静态instance；原Save/Refresh方法4项隔离检查通过。7段源码快照绑定既有二进制证据，原标定报告保留12段锚点。现场DLL、磁盘失败及设备验收未完成，29组仍部分复核。

## 历史增量：标定停止覆盖与任务清单

已补齐[停止路径与标定覆盖](calibration-stop-coverage-review.md)：界面急停只遍历停轴，与Machine.EmergencyStop定义不同；普通停止后的界面恢复只检查登记的生产任务，该标定Task未纳入。关闭单步可能在不同检查点得到不同结果，不能统一标成取消。15段源码快照纳入统一核验，复用已有停止清理及安全移动测试；实体急停、驱动与真实标定停止效果仍需验收，29组模块完整验收数量不变。

## 历史增量：标定双入口与任务生命周期

已补齐[双入口、重复启动和取消边界](calibration-task-lifecycle-review.md)：确认主界面Bond偏移与测试窗口指向同一方法，两处未持有Task或设置本地重复启动门禁；取消确认不等于取消已提交任务。12段源码快照与两个原方法的8项替身检查纳入统一核验。共享集合交叠风险、真实线程行为、现场权限及停机效果尚未运行验收，不增加29组模块的完整验收数量。

## 历史增量：标定交互图与源码边关系

已交付[标定交互图](bond-camera-calibration-workflow.html)：11个节点、12条关系逐条绑定源码。展示人工确认、最多三轮修正、先保存后复核、false仍展示及异常逸出。Archify九项检查、四种窗口尺寸检查通过，浅色与深色截图已审查。当前完成该专题的静态梳理和可视化；29组模块仍为部分复核，设备与SDK验收未完成。

## 历史增量：取放参数来源与标定PR执行链

已完成[参数服务分支和PR执行衔接](calibration-parameter-pr-review.md)：标定CarrierWithWaffle/BMC选用普通取片字段，BondOnBMC选用普通放片字段；区分吸嘴真空与平台真空，列出IPT/FlipTable对照分支、默认值和空参数边界。标定无参PR调用与已有光源、算法、结果显示、存图链连通，避免重复建设视觉审计。13个源码锚点快照接入统一检查，本轮为静态复核；真实配置、算法SDK与设备运行未验收，模块完整验收数量不变。

## 历史增量：标定视觉、运动和取放失败契约

已补齐[标定子调用的返回/异常/清理边界](calibration-dependency-contract-review.md)，复用现有安全运动验证，确认像素居中false与抛异常不走同一条路径；两个LocatePosition方法16项原方法替身检查通过。取放参数生成位于各自try外，清理仍可能再次抛异常；当前BondAction没有false出口。晶圆异步顶针超时不能直接套到CarrierWithWaffle/BMC标定链。15个源码锚点快照和新测试纳入统一检查；PR执行器、参数服务及设备实际清理效果尚待验收，模块完整验收数量不变。

## 历史增量：焊头到相机偏移标定完整顶层流程

已梳理[标定方法完整步骤与保存链](bond-camera-calibration-review.md)：按钮确认、取放/识别、最多三轮旋转修正、中途坐标保存、实际单轮偏移检查、最终取标及结果展示。原外层方法三项替身检查通过，确认false仍展示结果、异常向外抛出则停止展示；确定/取消均不执行本地回滚。12段去重快照覆盖完整顶层方法及保存/界面依赖，纳入统一核验。Infrastructure JSON写入实现仅有DLL引用，持久化原子性与现场成功未验证；运动视觉子调用、其他标定入口和设备验收仍待推进。29组模块完整验收数量不变。

## 历史增量：对焦入口、标定参数与失败出口

已补齐[对焦入口审计](autofocus-entry-review.md)：晶圆同步按钮、系统分派辅助、标定确认后Task启动。标定范围经包装后反向，粗扫仅取一个样本；原方法三项替身检查通过。内层标定返回false未被外层检查，结果展示不能代表成功。15个源码锚点快照与报告哈希已纳入统一核验。完整标定、全部窗口可达性和实际设备验收仍待完成；29组仍为部分复核，不新增完整验收数量。

## 历史增量：自动对焦的三种可选算法

已补齐[DoFocusing / New / New2 的步骤与边界](autofocus-alternatives-review.md)：三阶段拟合、下降判定、共享实例字段和退出次序均对应源码。New/New2原方法的8项受控检查通过；[回执](autofocus-alternatives-test.json)包含原文哈希和全trunk五处具名引用。当前未找到这三种方法的具名生产调用，不能混入既有AutoFocus主链；其中两种方法复用已停止实例时先绝对移动再跳过采样。旧三阶段算法仅静态分析，SDK、真实轴和焦点质量未测试。作为独立专题缩小模块缺口，不增加既有552条模块关系/940段快照计数，29组仍为部分复核。

## 最新完成：焊后反馈专题交互图（2026-09-29）

已交付[焊后反馈与补偿失败路径图](postbond-feedback-workflow.html)，使用 Archify workflow v2，保留全部 11 节点、11 关系，按结果/UI、后续生产、失败处理三个通道排布。此前连线冲突已解决，Showcase 9/9、0 错误/警告；四种桌面尺寸通过浏览器包含性与可读性检查，最终浅色小屏和深色大屏截图已目视复核。入口已接入首页。[交付回执及逐关系源码映射](postbond-feedback-diagram-status.json)绑定最终 JSON/HTML 哈希与现有 31 段证据；[浏览器回执](postbond-feedback-workflow.visual-check.json)保持独立。此项图表交付完成，不表示 WinForms、数据库、故障恢复或设备动作已运行验收；模块完整验收范围不变。

## 历史增量：补偿失败的二次异常与任务门控（2026-09-29）

已检查 BondTask 整个 DoWork、Start 的 Task 包装和 Machine.Stop：节点错误日志/消息/WorkStop 或任务停止指令若再次抛异常，当前两层任务调用没有兜底捕获，不能保证进入或完成 Exception 停止分支；机器先置 Stop 再做后续处理，也不能用状态代替清理完成。再次启动两处任务门控只拒绝 Running，不明确拒绝 Faulted。报告关联现有全源码异步异常审计，证据扩展至 31 段，避免重复建设审计。[失败传播及未验证项](postbond-feedback-source-review.md)。生产故障注入、真实设备状态、部署依赖仍待验证；本增量未修改生产源码，模块完整验收数量不变。

## 历史增量：焊后新入口与补偿异常停止链（2026-09-29）

已从 Designer 绑定追到 `BtPostBondDataNew_ItemClick → ShowForm<FrmPostBondData> → Load 订阅`，补齐新数据窗体的静态入口；旧曲线窗体处理器绑定仍未确认。补偿异常追到 `BondActionNode.DoWork` 的捕获、错误返回与 finally，再到 `BondTask` 的 Exception 分支：停止机器→请求焊头安全位→按配置请求胶盘回位→退出本次任务方法，不走自动 Retry。见[入口和失败处理说明](postbond-feedback-source-review.md)与[24 段原文证据](postbond-feedback-evidence.json)。仅完成静态调用链，日志/窗口/回调二次异常及设备真实停止效果仍未验证；不扩大 29 组部分复核、0 组完整验收的范围。

## 历史增量：焊后补偿原方法边界验证（2026-09-29）

对原始 `GetPostCompensation` 方法完成 18 项受控检查，方法体不改写，使用真实 LINQ；[场景结论](postbond-feedback-source-review.md)与[源码快照及测试回执](postbond-compensation-test.json)可直接追溯。确认 X/Y 分别筛选、严格排除绝对值 50、筛选为空时抛异常，以及清空后缺样本返回默认点、补足后恢复计算。还覆盖 double 类型参考次数的小数截断与异常参数输入；这些测试不证明 UI 接受异常参数，也不证明外层异常恢复或设备实际动作。统一入口 `node scripts/verify-all.cjs` 已纳入此项。当前仍为 29 组部分复核、0 组完整验收；剩余优先项为窗体入口可达性、外层异常处理、真实配置和运行样本、关闭/并发行为。

## 历史增量：焊后结果返回界面与生产补偿（2026-09-29）

新增[焊后反馈链](postbond-feedback-source-review.md)及[16 段源码快照、6 处委托引用](postbond-feedback-evidence.json)：数据库入队→默认内存缓存→窗体 Task/Invoke→共享列表显示，以及共享数据被后续贴装坐标计算读取。已区分两窗体的异常/关闭边界、全字典清空对补偿取样的影响。主界面存在曲线窗口处理器体，但当前静态搜索未找到其显式事件绑定，不宣称现场入口已确认。仍为 29 组部分复核、0 组完整验收；下一步核对入口可达性、配置样本及回调并发/补偿空样本边界。

## 历史增量：数据库消费原方法隔离验证（2026-09-29）

对 `DBService.Insert` 与 `StatisticsService.SaveEntityToDb` 完成 11 项受控检查，并纳入 `verify-all`。[分析及场景表](async-persistence-ingress-review.md)与[含原方法快照的回执](async-db-consumer-test.json)明确：常规写入异常由 Insert 捕获并记录日志，已取出的记录不重试，后项可继续；日志本身抛异常才会继续逸出这一边界。温补未匹配分派也以受控类型场景复现。SqlSugar、实体及日志使用测试替身，尚未验证真实数据库、并发线程与现场数据；项目仍为 29 组部分复核、0 组完整验收。下一步优先补真实依赖和样本条件下的持久化验收，并继续统计结果回到业务/UI 的调用链。

## 历史增量：异步保存入口与温补分派缺口（2026-09-29）

已追踪图片及数据库进程内队列的生产者→入队→后台消费→文件或数据库输出：11 个源码文件哈希、27 个精确行锚点、5 处直接 `.Add`。图片通过 PR 委托进入无显式容量队列；数据库队列容量 500，仅对四种实体作 `Insert` 分派。两处温补结果被构造成独立的 `TemperatureCompensationEntity` 并经 `SaveDataToDb(object)` 入队，但当前 `SaveEntityToDb` 无此类型或默认分支；若该对象被取出，按当前源码不会在此消费者写库。见[队列链路与缺口](async-persistence-ingress-review.md)及[可再生证据](async-persistence-ingress.json)。这是源码分派结论，未验证现场是否丢数据。

正常关窗的 `ExitSoftware` 直接保存/关硬件后 `Environment.Exit(0)`，没有显式排空或等待两条队列；主界面刷新 DLL 也未见在此路径先置 `ThreadFlag=false` 或 Join。[异步保存交互图](async-persistence-dataflow.html)已按图片/数据库两条路径分层交付，[Archify 规格](async-persistence-dataflow.archify.json)通过 Showcase 9/9、0 警告；[浏览器回执](async-persistence-dataflow.visual-check.json)显示四个桌面视口、浅/深截图均通过。静态图验收不代表设备或数据落盘验收。仍为 29 组部分复核、0 组完整验收；后续需核对现场实际加载版本、真实配置/配方与数据库样本，并在隔离环境复核写入和退出边界。

## 历史增量：主界面后台刷新调度契约

沿 `UcMainSystem_Load` 的任务注册与四处激活调用追到随仓库 `BackgroundWorkThread.dll`：静态 IL 固化 14 个方法、DLL 哈希及三个源码文件哈希。注册参数为优先级 1、间隔 1000 ms、周期型（`SingleExecuteState=false`）；服务每 20 ms 扫描任务，但刷新 Action 仍经间隔门控，再用 `BeginInvoke` 排入 UI。单次激活仅置布尔标志，不绕开此周期任务的时间门控。任务同步异常的 catch 与 UI 委托随后执行的异常不属同一边界。[交互时序图](background-task-sequence.html)、[调度/失败路径](background-task-contract-review.md)与[机器证据](background-task-binary-evidence.json)可供工程师追溯。

此结论只适用于随仓库 DLL 静态实现；现场加载版本、实际 UI 时序、并发和退出时任务回收未验。29 个分组仍部分复核、0 组完整验收，继续遵循源码链路→真实依赖材料→隔离验证→设备验收的顺序。

## 历史增量：编程页覆盖与配方读取契约

已完成 32 种编程树页面类型的限定入口盘点：20 种直连 Confirm 页面、4 种非接口事件页、8 种展示/配置页。4 种事件页的 17 个方法、22 次直接 Save 已映射到目标类型；8 种展示/配置页的本地事件、绑定及保存调用有独立证据。此覆盖仅指页面主类与 Designer 的指定入口，不等于继承控件、第三方绑定或全部运行行为验收。

配方切换的六种程序重置顺序已对齐源码；随仓库 Infrastructure DLL 的 9 个单例、JSON 读写及保存相关方法已登记静态 IL 与 SHA-256，区分缺文件、读取失败、空列表、默认实例和异常传播。证据见[页面盘点](programming-display-pages.md)、[非接口保存目标](noninterface-save-targets.md)、[配方重载](recipe-initialization-source-review.md)、[持久化 IL](persistence-save-contract-review.md)与[失败边界](persistence-failure-boundary-review.md)。

当前仍处于第 2–3 阶段：29 组部分复核、0 组完整验收。本地 `dotnet --info` 仅列出运行时、没有 SDK，命令搜索未找到 MSBuild，尚未尝试也不能宣称完整解决方案构建通过。下一步核对现场实际加载的 DLL/配置/配方样本，在隔离目录验证失败路径，并继续剩余模块及调用关系；完整构建和设备验收未完成。

## 历史增量：安全移动门控与返回值

已将2D安全XY、3D安全XYZ、4D安全XYZT与Z单步包装、4D限位纳入34项原方法隔离检查；新增16段独立源码阅读器。核实各高度分支、Z返回Abort/Fail后续行为、二维恢复原Z、四维T透传及本地T限位缺口。调用继续并不证明物理运动。

[步骤与失败语义](safe-motion-workflow-review.md) · [源码阅读器](safe-motion-source.html) · [交互图](safe-motion.html) · [测试回执](safe-motion-test.json)。阅读器入口/原文/链接/搜索及三尺寸检查通过。下一步继续其他运动入口与可获得的外部等待/持久化契约；真实配置、完整构建和硬件验收仍未完成。整体维持29组部分复核、0组完整验收。


## 历史增量：辅助视觉示教与运动门控

已追踪共享模板→上视识别/重试→坐标换算→距离/单步门控→XY下发，并单独复核后台对焦。新增19段可追溯源码、17项原方法隔离检查；搜索与对焦相机差异、按轴距离检查、空值与异常重试差异、细搜退出边界均记录。

[步骤与待复核风险](vision-teaching-workflow-review.md) · [源码阅读器](vision-teaching-source.html) · [测试回执](vision-teaching-test.json)。当前仍处于第2–3阶段局部补齐：29组部分复核，0组完整验收；外部运动等待/持久化契约、完整构建、真实配置/配方及硬件验收未完成。


## 历史增量：自动换嘴与示教取放

已追踪换嘴入口→逻辑/物理检测→放回旧嘴→定位取新嘴→回原→状态保存，并补齐示教人工/自动包装。新增29段独立源码证据、14项原编排/包装隔离检查，Archify交互图11节点/11关系。记录回原返回未检查、示教放回取消/false被吞及到位Y/Z分量不一致的待复核风险。

[工作步骤与风险](nozzle-exchange-workflow-review.md) · [可搜索源码](nozzle-exchange-source.html) · [交互图](nozzle-exchange.html) · [测试回执](nozzle-exchange-test.json)。Archify交付9项通过，四尺寸浏览器检查与两主题端点截图人工查看通过；阅读器29段原文/文件链接和三尺寸检查通过，本轮verify-all通过。

这属于第2–3阶段局部链路补齐，不增加全局完整验收组数：29组部分复核、0组完整验收。真实机械取放仅静态复核，测试未执行硬件；下一步继续辅助视觉示教、运动互锁与外部持久化契约，完整构建/真实配方/设备验收仍未完成。

## 历史增量：胶头与吸嘴示教状态

已补齐S1/S2胶头步骤、吸嘴高度/对准/几何完成委托、产品编程调用者及直接状态消费条件。新增27段源码和6项原几何委托/按钮隔离测试，源码一致性、页面导航/搜索/三宽度及verify-all均通过；记录拟合失败返回后外层仍标记完成的风险。生产源码未修改。

[步骤、风险与未验收项](tool-teaching-state-review.md) · [带行号源码](tool-teaching-source.html) · [隔离测试](tool-teaching-test.json)。

本轮为限定源码复核，不是全项目完成：仍处于第2–3阶段，29组部分复核、0组完整验收。下一步继续剩余示教/辅助视觉委托和持久化契约；随后完整构建、真实配方及硬件验收。

更新：2026-09-28。目标：从 trunk 源码建立工程师可追溯的框架、模块、业务链路和自动工作步骤说明，明确缺失项。图表是阅读入口，不是业务覆盖证明。

## 历史增量：预点胶板示教提交链

已追踪S1/S2手动页入口、三步向导、测高包装、保存宿主、取消与关闭清理、板位初始化及IsReady消费方。新增33段独立源码证据，另有16项原始Save/Next/Done隔离检查通过。已区分S1对话框正常返回后的调用方清理、S2测高Ret未检查与异常重试、保存委托前写完成标志的边界。

[步骤与失败边界](plate-teaching-workflow-review.md) · [可搜索源码](plate-teaching-source.html) · [测试回执](plate-teaching-test.json)。该专题没有新增自动生产主图覆盖率；33段不计入134段配置索引或552条代表关系。验收：33段原文/源文件链接、搜索及1440/850/390宽度检查通过，verify-all通过。

当前仍处于第2–3阶段。下一步为胶头/吸嘴及剩余示教委托、外部保存/重载类型契约；完整构建、实际配方和硬件运行仍待验收。29组部分复核、0组完整验收。

## 上一增量：手动试胶门控与源码图

已完成两个按钮处理器的限定静态复核：普通试胶、预点胶板试胶，区分 S1/S2 门控、逐层定位测高、预点胶返回未检查、插补返回分派及异常边界。新增 Archify 工作流 11 节点 / 9 关系，逐项绑定原文件、行号、源码快照及 SHA-256；不计入原有 134 段专题索引或全局 552 条代表关系。

[试胶流程图](manual-epoxy-trial.html) · [节点与源码](manual-epoxy-trial-source.html) · [执行步骤和限制](manual-epoxy-trial-summary.md)。这只是静态源码专题完成，未验证真实胶头、视觉与运动执行。验收：Archify 9项检查通过，四尺寸浏览器检查通过；11节点/9关系源码绑定、阅读器导航搜索及 verify-all 均通过。

下一步：剩余示教入口与保存/重载委托，逐步补齐工程构建与真实配方材料。总体仍处于第2–3阶段；29组部分复核、0组完整验收。

## 上一增量：试胶提交与名称解析

已补齐试胶前Confirm、对象引用来源、设备胶型库与产品程式路径；新增11项提交隔离测试和7项名称解析隔离测试。确认两次Save的中断边界，以及读取胶型列表会删改名称并可能跳过相邻项。源码阅读器现134段。[完整链路与限制](config-production-gates.md)、[提交测试](epoxy-confirm-test.json)、[名称解析测试](epoxy-name-resolution-test.json)。

当前继续第2–3阶段：试胶前置门控本轮已补齐；下一步剩余示教委托与可获得的持久化依赖类型证据。真实写盘/恢复、完整构建、实际配方与设备验收仍未完成；整体29组仍部分复核、0组完整验收。

## 历史增量：预处理调用与失败传播

已逐一核对3个直接预处理入口及8个控制器调用点，区分自动生产、普通试胶和预点胶板试胶；新增14项原方法隔离测试。源码索引现134段。S1非Success停机与S2 Alarm三选项不能合并，预点胶板试胶未检查Fail返回也已登记。[完整证据与限制](config-production-gates.md)、[测试结果](epoxy-pretreatment-test.json)。

试胶入口Confirm与名称解析已在后续增量完成局部复核；其他示教委托及外部持久化继续推进；完整生产对象克隆、Fody织入、构建与真实运行仍未验收。

## 历史增量：S2上下文与复制对象图

已确认实际主链使用S2ActionNodeController；新增原方法14项隔离检查，验证匹配缺失、重复标识、旧字段残留及异常传播。补齐胶型、点位、两层基类与PropertyChanged事件的序列化声明；这是源码对象图，不是实际配方克隆验收。[源码与场景说明](config-production-gates.md)、[测试结果](s2-context-update-test.json)。

该轮后续已推进预处理调用传播与14项隔离测试；真实配方对象类型仍待验收，继续其余示教委托、外部持久化及构建运行验证。整体29组仍部分复核、0组完整验收。

## 历史增量：视觉辅助与胶量模板

已复核灯光/相机设置、硬件绑定、图像输入及视觉流程加载，提取默认胶量模板13个模块、15条连接、92条订阅；Archify展示10个节点（四种匹配合并），全部连接可溯源。详见[模板流程图](epoxy-template.workflow.html)、[原始结构](epoxy-template-structure.json)和[图与证据映射](epoxy-template.evidence.json)。仅证明仓库模板的声明结构，分支取值、脚本内部代码、实际配方覆盖与VisionMaster运行尚未验收。

## 最新专题增量：配置与生产启动门槛

当前完成到：配置提交→配方重载→生产启动门控→代表性示教状态形成→S2预点胶触发和DoWork执行→首轮标志与点位分配→插补/检测外层及Alarm局部重试。并补充节点重取、图形预处理、视觉报警副作用及驱动结束边界。并补充胶后视觉采集/服务分派、胶量算法关键分支与上下文来源。单页现收录134段限定源码；制程14项、两层门控9项、示教/预点胶报警19项、点位分配13项、节点选择9项、驱动指令循环11项、视觉重试7项、上下文更新14项、复制/预处理14项隔离测试。DoWork与IsDispense仅静态复核，未计入19项执行测试。

成果入口：[可搜索源码页面](config-production-gates.html) / [完整说明与源码直达](config-production-gates.md)。原证据继续保留在同一页。新增[S2预点胶与重试Archify时序图](s2-predispense-retry.sequence.html)，14条消息逐条绑定源码。插补/检测及重试为静态复核，不计作硬件运行测试。

下一步顺序：①上下文局部更新已完成14项隔离检查，复制对象图已完成声明级复核；复制/预处理入口传播及14项隔离检查已补齐，真实配方对象类型仍待验收；视觉辅助调用与胶量默认模板结构已完成限定静态复核；本轮采集到FindModel分派及上下文更新已完成限定静态复核；GuGao完整方法及本地Clone机制已静态展开，SDK与实际配置复制仍未运行验收；②全部示教委托和外部持久化；③构建、认证配置材料、硬件运行验收。直接Retry的节点重取已用9项隔离测试核实；视觉终止按钮会先调用Stop，不能把检测返回值忽略误读为没有停机副作用。驱动SDK实际行为仍待验证。

边界：新增片段属于独立专题，不计入既有552条代表关系/940段模块快照；29组仍部分复核、0组完整验收。未完成全工程业务解析，也未证明真实保存/加载成功。

## 上一专题增量：编程配置提交

已复核20类直接接口页面的 Confirm 与指定保存委托，新增32种输送配置组合的原方法隔离验证。详见 [逐页提交与失败边界](programming-confirm-review.md)。这是独立专题证据，不计入既有552条代表关系 / 940段模块快照，也不提升29组的完整验收状态。当前继续第2–3阶段；下一步衔接保存、重新加载与真实生产启动门槛。

## 当前阶段

正在进行第 2–3 阶段：工程基准已建立，已有8章自动化主图的限定范围外层控制流已逐条复核，继续推进模块内部调用与专题缺口。尚未完成全工程业务解析；不提供缺少验收分母的完成百分比。

|顺序|工作包|状态|现有成果 / 下一验收条件|
|---|---|---|---|
|1|源码范围和文件清单|基准已完成|16 个项目、29 个文件分组、1436 个 C# 文件；含 Designer，排除 bin/obj；不是编译项覆盖率|
|2|项目声明依赖与源码解码|源码与实际Build失败边界已验收；安装输入清单已解析，完整部署待完成|原SetupZX2200.vdproj只读识别465 File项/393存在/72缺失/195依赖；.NET4.7.2 LaunchCondition、ProjectOutput为空及解决方案未选Build.0已绑定，未生成安装包|
|3|模块职责、入口及边界|原正常监控自动启动消费者与重启边界已补证，完整链待验收|原MainForm.Load自动Start监控，原循环自动Start两个消费者；顺序启动守卫和false标志结束范围已实测|
|4|自动生产启动调用链|原Program.Main离线首次入口与真实关闭已运行，在线完整链待验收|STA主线程1的原版本／身份保存、Harmony／PR委托、Application.Run及原Load监控／消费者启动通过；宿主ProductName配置夹具，原EXE部署及设备启动待验收|
|5|输送与任务消息衔接|重载保留五运行Task及异常退出已补证，物理握手待完成|四行各5个原输送Task等待许可，2原Stop、2调度夹具Faulted；push未确认move、没有TU提交|
|6|配方、参数与配置衔接|原退出保存范围与遗漏已复现|产品及晶圆公开修改已落盘；RecipeList与ProcessDomain内存修改在退出保存链中遗漏|
|7|工序排序、动作执行及重工|原任务状态与界面恢复集成已补证，完整循环与Retry待验收|256公开持有者行225恢复31等待，其中129恢复Task未完成；另1实际S1Task公开回调故意Faulted，原节点主体未通过|
|8|视觉、运动、补偿和标定|原纯路径预处理/力控与补偿边界已补证，设备成功待验收|原三策略纯克隆归一化/旋转/数值51检查，物理动作未执行；真正控制器保存clone仅静态IL。力控46检查和JSON/两表导出、S2前提证据保持；真实相机/轴/贴片/清零/闭环成功未完成|
|9|运行数据、文件、数据库与外部服务|原监控自动消费者和真实文件释放通过，SQL待验收|16图／轮全部BMP保存及Dispose；500普通对象取走不创建SQL；停止监控后消费者仍活，前轮积压退出证据保留|
|10|图与源码证据统一|完整静态候选浏览保持，文档实例与SDK原生容器已实测；全动态解析待验收|17518原调用／675集合3257行、295目标360方法1053类型候选仍可浏览；实际MainForm的MF／PostAction、QueryControl1次、DocumentContainer和首页原生移窗已绑定，完整实例／配置／泛型解析仍待完成|
|11|自动更新与回归检查|原Program入口两轮41项与34绑定通过；全目标未完成|365声明246源278IL／9程序集；401新增+18705=19106，旧1328独立|
|12|界面交互与异常反馈|原入口版本提示与客户区裁切矩阵已实测；目标设备布局与异常插桩仍未验收|Program.Main入口保留六PNG；新增两轮×6客户区尺寸，观察1536×793文档1920×999，右384/下206，AutoScroll=false、96DPI；没有修复生产界面，原异常处理器回调未插桩|
|13|工程师交接验收|完整匿名源码页与候选浏览交接保持，29组仍partial|离线页保留1436文件／5411快照654提示／2458匿名视图；本轮主窗体裁切有原生图、原Designer及IL复现，目标设备布局、实例配置／动态／在线设备／VM／SQL／完整Build及部署需继续，整体目标未完成|

## 当前确认的缺失与限制

- 原ReDispense在Dictionary.Keys枚举中写回，Framework实际首步提交后InvalidOperation；原排序同一步点胶/胶检互斥，单独消息重做缺配对。见[native-s1-rework-context-review.md](native-s1-rework-context-review.md)；原整Retry动作/任务未执行，映射选择是公开测试委托。

- 原点胶离线step在单步等待前提交，实际Abort/Fail后仍true；任务nonSuccess早退不做最终Finish。原finally调用未赋值UI刷新会Faulted，见[native-s1-return-gates-review.md](native-s1-return-gates-review.md)。这是离线原行为与公开回调同步验证，未证明物理点胶或Retry完整路径。

- 原分段交互 Wait 返回 false 被丢弃仍 Success；已进入完成等待后暂停仍消费 Set，下一层暂停门才阻塞。已在真实启用离线 S1 任务验证；完成由测试产生，物理转移/点胶未执行，见[native-s1-segment-interaction-review.md](native-s1-segment-interaction-review.md)。

- 原来料/入口边界已验证：S1仅重置State，底层事件仍可消费；原S2 Enable=false也执行前置吸嘴架运动，空硬件下Task Faulted而设备仍Working。Compensate模式Stop可在状态提交后因缺失输出异常。见[native-task-input-gates-review.md](native-task-input-gates-review.md)；未证明重复实物生产或完整在线停机。

- 原S1原生业务边界已复现：Pause→Stop的WaitStart睡眠释放窗口可准入下一离线身份动作；原公开动作回调异常使Task Faulted但观察时Machine仍Working。见[native-s1-working-pause-review.md](native-s1-working-pause-review.md)。同步/异常由fixture回调注入，在线轴行为未复现；生产源码未修改。

- P1静态风险待验证：取片压力采集的正常停止调用被注释，采集循环共用标志且无直接Stop检查；可能持续采集或延迟导出，未运行复现。见 [取晶复核](pickup-semantic-revalidation.md)。

- 主工程引用的 `trunk/AKRS.Galaxy2.Parameters/AKRS.Galaxy2.Parameters.csproj` 不存在；不能补写其内部行为。
- 89 个历史节点中，8章全部 89 个已完成限定范围的外层控制流复核；101 条现有关系已分类复核。分类包含人工操作与事件关系，不可全称直接调用。
- 文件快照与哈希匹配只证明证据未漂移，不证明图中解释正确。
- 未运行硬件控制程序，不能从静态代码推出现场设备一定继续运动或一定停止。
- 历史报告可能保留旧计数和过度完成表述；进度以本清单、当前台账及逐方法复核记录为准，后续持续清理。

## 后续执行顺序与验收标准

1. 完成自动生产：逐一展开任务入口和循环，记录触发、步骤、分支、信号、退出和异常；每条关系附调用点及被调用方法证据。
2. 扩展模块表：为每个源码分组填写职责、实际入口、依赖、输入输出、关联业务和未确认项；不可根据目录名猜职责。
3. 补齐专题链路：配置配方、动作调度、视觉运动、数据持久化、维护标定；缺失实现明确停在边界。
4. 同步 Archify 与入口：在流程摘要核实后更新图，将直接调用、并发信号、条件关系和人工操作明确区分。
5. 完成交接验证：复跑自动检查、实际浏览页面、检查源码导航；单列构建/运行尚未验证的部分。

## 成果与证据入口

- [整合页面](index.html)
- [源码分组基准](source-module-inventory.md)
- [项目依赖及缺失项](project-dependency-baseline.md)
- [自动生产启动方法复核](production-start-callchain-review.md)
- [步骤与关系台账](automation-traceability.md)
- [结构化直接调用证据](callsite-evidence.json)
- [验证手册](verification-runbook.md)

- [输送与 S1/S2 交接复核](transport-production-call-review.md)：本轮新增的静态方法体分析与异常处理差异。

- [供晶与取晶握手复核](wafer-bond-handshake-review.md)：已追踪直取/翻转主握手、异步预取与局部退出；Single 搜晶和自动换片外层已有补充复核；Nine/Box/Map 搜索外层已补至供晶章节；底层算法、动作及其他发信号分支待展开。

- 搜晶进度：已确认 NextDie 按 SearchMode 分派，展开 Single 外层控制流（换料返回、定位模式限制、跳过循环）；Nine/Box/Map 外层已补至供晶复核，视觉和几何底层仍待复核。见供晶握手记录。

- 单颗搜索进一步复核：位置生成、局部 50 次探测边界、StopSearch 已停止检查及取晶中心移动入口已读；视觉判定与自动换片外层已有补充复核；底层算法和动作待核实。

- AnalyseDie 外层视觉判定已复核：墨点、多次定位、空晶跳过、人工重新定位/提前换片；底层视觉算法仍待展开。

- [自动换片控制流复核](carrier-change-review.md)：已核实料库/无料库、复用/人工换片、窗口实际显示入口和初始化重试；已补齐普通晶圆初始化外层模式对照、Block 状态契约及向导完成回调；地图运行外层已另文复核；地图库内部、底层动作及图表同步待完成。

- [地图运行源码复核](wafer-map-runtime-review.md)：已连接本地地图加载、参考点/起点寻路调用、普通搜晶/参考晶粒补取、取晶后刷新与保存请求；已定位 UI Invoke 调度。地图库实现与实际异步完成状态未验证。

- [料库换片动作复核](magazine-transfer-review.md)：选层、放旧料/取新料、夹片传感器重试、局部升降互锁及状态保存已展开；发现 SlotScan(index) 检测段不可达、部分无料检查可直接返回。气缸重载、到位反馈差异、热吹输出/保持及单步门控已补至该文第6–7节；Sensor/运动驱动内部、停机兜底与现场验收仍待完成。

- [停机与任务退出复核](stop-cleanup-review.md)：普通停止、急停、任务 Abort 实现、重启状态门控及退出软件前段已核实；空 Abort 和仅 Dispose 不代表任务退出。外围状态监控、驱动实际停止、异常时热吹关闭保证仍待验证。上述新增结论尚待同步到图与语义台账，不能据此宣称全项目完成。

- [普通停止流程图](stop-cleanup-workflow.html)：新增 7 节点专题图，已按 Stop 方法顺序复核，9 项 Archify 检查通过；独立于待复核的历史 89 节点台账，不混算覆盖率。

- [启动章节语义复核](startup-semantic-revalidation.md)：12 个节点与 10 条关系按当前源码重新核实，已同步图规范、门户和台账；加入说明/关系/源码范围漂移检查。此为限定外层范围验收，不代表全工程或设备验收。

- [输送章节语义复核](transport-semantic-revalidation.md)：11 个节点、12 条关系已按任务、物料、信号及控制器结果重新核实；修正下料共用上料配置、料仓层号更新、Ignore 推进状态、Exception 处理差异。底层控制器/驱动和现场运行仍未全部验收。

- [S1 配方与动作源码复核](dispense-semantic-revalidation.md)：任务循环、八种排序、代表动作、检测重做与异常边界已读源码；新版图已通过布局/浏览器检查并同步门户；本章 10 节点与 12 关系完成限定外层验收。

- [S1 定位、测高与识别](s1-action-behavior-review.md)：其余 11 个动作包装及共用业务方法、禁用传播已核实。新增定位 bool 被忽略、测高重试保留读数的静态分支说明，未宣称设备故障已复现。

## 阶段记录：供晶主图同步

供晶12节点、15关系已完成限定范围源码复核，新增10段证据；该阶段结束时累计45/89节点、49/100关系。这是已有主图范围的复核数量，不是全项目完成率。

[供晶源码复核](wafer-supply-semantic-revalidation.md) · [供晶交互图](wafer-supply-workflow.html)。下一步按顺序复核 Bond 任务调度、取晶与贴片动作，然后收口失败恢复。

供晶正式图通过 Archify 9项检查（0错误/0警告）、Edge 多视口检查，并已查看1440×900浅色截图。整合门户导航尚未完成本轮实际浏览器验收；构建、硬件运行仍未验证。

## 阶段记录：Bond 调度主图同步

已复核 Bond 调度12节点、15关系，新增8段源码快照；该阶段结束时累计57/89节点、64/100关系，剩余32节点、36关系。此分母只覆盖已有主图，不是全工程完成率。

[Bond 源码复核](bonding-semantic-revalidation.md) · [Bond 交互图](bonding-workflow.html)。已核实外层调度、编排分派、消息状态、配方后处理及胶盘并发；八种排序每层循环和具体动作内部仍待深入。下一阶段：取晶→贴片→失败恢复。

正式图通过 Archify 9项检查（0错误/0警告）与 Edge 浏览器布局检查，1440×900浅色截图已实际查看。整合门户实际导航、编译和设备运行仍未验收。

## 阶段记录：取晶与漏晶恢复主图已同步

本轮完成10节点、13关系的限定范围复核，新增10段源码证据；当前累计67/89节点、77/100关系，剩余22节点、23关系。此分母只覆盖已有主图，不是全工程完成率。

[取晶源码复核](pickup-semantic-revalidation.md) · [取晶交互图](pickup-workflow.html)。已展开重检/重取/下一颗差异、静态华夫盒定位、DryCycle、异步通知、压力/LVDT记录与顶针包装。具体运动轨迹、SDK、现场运行待验证。下一步：贴片动作→失败恢复，然后继续模块与专题缺失项。

图通过Archify九项检查（0错误/0警告）及Edge布局检查，1440×900浅色截图已查看。整合门户导航、完整构建和硬件运行仍未验收。


## 阶段记录：贴片动作主图已同步

本轮完成10节点、11关系的限定范围复核，新增10段源码证据；当前累计77/89节点、88/100关系，剩余失败恢复章节12节点、12关系。这个分母只覆盖已有主图，不是全工程完成率。

[贴片源码复核](bond-action-semantic-revalidation.md) · [贴片交互图](bond-action-workflow.html)。已核实ReBond与重新取贴、胶印Fail转换、位置组合与运动包装、压力文件、人工观察Stop和步骤完成标记。底层轨迹、补偿算法、统计全链路、SDK与实机尚未验收。

图表九项检查与Edge桌面检查通过，已目视1440×900浅色截图；统一门户的完整交互导航未重新完成浏览器验收。下一步：失败恢复主图，然后继续29个分组的模块职责、内部调用和专题缺口，最后进行构建/运行及交接验收。


## 阶段记录：八章自动工作主图的限定范围复核完成

完成失败恢复12节点、13关系及9段新增证据；本轮明确增加S2 Alarm直接重做当前动作的独立箭头，关系分母由100调整为101。累计89/89节点、101/101关系，门户158段源码证据。以上仅是已有八章主图的验收范围，绝不是1436个C#文件或全项目业务的完成率。

[失败恢复源码复核](failure-recovery-semantic-revalidation.md) · [失败恢复交互图](failure-recovery-workflow.html)。图中区分动作Retry和报警Retry、Ignore完成标记、门与Continue、普通Stop与急停请求、检查点退出边界。

两张本轮图均经Archify九项检查、Edge桌面自动检查、1440×900浅色截图目视审阅；修复了恢复图中重试与停止路线重叠。统一门户完整导航、构建与设备运行仍未验收。

### 下一阶段顺序及完成条件

1. 模块清单逐组验收：沿现有29个文件分组补职责、入口、调用方/被调用方、配置/状态、缺失依赖和对应代码。完成条件是每组明确已读范围与未读范围，不用文件数量冒充语义覆盖。
2. 自动化内部补深：运动轨迹、位置/视觉补偿、点胶/取贴下层包装、所有等待点与后台温度/耗材/传感器处理。每条补链同时更新源码锚点和异常路径。
3. 数据与外部依赖：配方加载保存、统计队列、数据库和文件、设备SDK边界；记录实际格式、线程与失败处理，未提供实现明确标缺失。
4. 工程可复现与交接：依赖/构建环境核验、静态检查回归、门户导航/源码溯源验收、测试环境运行。设备验证单列，不以静态图通过替代。


## 最新推进：模块级复核已建立，先核实机器框架

[模块级进度与调用清单](module-review-status.md) · [机器框架内部源码复核](machine-framework-module-review.md)。29个文件分组全部有明确状态；Machine和MachineSupport两组已读9个行为源码文件、2个元数据文件，登记12条代表关系、21段独立源码快照，仍标部分复核；其余27组待逐组复核。

已明确：ZX2200 Machine不继承BaseMachine；MachineService为空；SignalList只登记12/23个信号；配置读取失败可能返回null；框架源码项目与DLL引用需要版本核验。上述行为均附代码入口，外部实现及运行影响不凭源码注释推断。

新增模块证据/结论/文档漂移检查，并接入verify-all；它验证证据一致性，不代替人工语义或运行验收。下一组：ZX2200/Main，优先初始化→配方选择/加载→生产调度连接点，再沿依赖展开。


## 最新推进：Main初始化、配方与生产发起

[Main源码复核](main-module-review.md)：新增5个文件的指定方法范围、10条代表关系、12段源码快照。模块级累计3组部分复核、26组待逐组复核，22条代表关系、33段快照；无模块完整验收。八章主图89节点/101关系仍是限定范围，不代表全工程完成率。

已核实ID先保存再重载、程式节点初始化位于重载try/finally之外、单个PR缺失只日志后继续、DataLoad/DataSave捕获异常后可继续，以及生产任务启动分支。生产源码未修改。下一步展开六个InitProgram方法、PR加载和复制的文件/缓存/失败状态；构建、实机及门户完整导航仍待验收。


## 最新推进：六个初始化与视觉加载/复制已展开

[配方内部复核](recipe-initialization-source-review.md)：新增18段源码快照、7条代表关系；模块台账累计29条代表关系、51段证据。3组部分复核/26组待逐组复核口径不变：本轮跨模块追踪不冒充全部模块验收。

已明确五个初始化只改路径清实例，供片初始化会修改记忆并通过标志方法调用Save；点胶模板加载为空操作；视觉初始化内部捕获异常后上层仍可置成功；复制临时路径恢复不在finally。没有修改生产源码。

配方初始化新图候选存在离线路由净距诊断，尚未交付/浏览器验收。下一步继续下层Clone、同名处理与重建标记消费方，解决图布局；Singleton<T>、文件复制helper真实实现以及构建和实机验证仍待补齐。


## 最新推进：视觉复制与供片重建纳入模块台账

[视觉模块](vision-recipe-module-review.md)和[供片重建模块](wafer-rebuild-module-review.md)已建立限定范围说明。当前5组部分复核、24组待逐组复核；43条代表关系登记、65段独立源码快照。代表关系按模块登记，可能描述同一条跨模块调用，不是全项目唯一调用计数。

已核实克隆的临时JSON/null返回、首个同名替换、视觉保存异常吞掉、供片检查和槽位窗口两个重建入口、实体/槽位递归更新与本地SingletonJson保存包装。生产源码未改。下一步PR清单子方法、槽位构造及窗口提交/取消行为，再推进其余模块。

配方初始化新图仍未通过：离线边显式标签与节点净距冲突，尚未交付HTML或浏览器验收。既有主图和本轮源码文档/证据验收口径分开。构建、SDK及实机仍待验收。


## 最新推进：窗口提交与视觉清单分支复核

模块台账为5组部分复核、24组待逐组复核，51条代表关系登记、83段独立源码快照。关系登记可能跨模块重复，不是全局唯一调用数。

已核实槽位填充/行操作当场保存、数组直接赋值、关闭方法仅释放映射控件；补齐蛇形孔位构造与载盘/顶针/贴后/吸嘴/定位PR清单。定位清单未添加P4，贴后Find会移除缺失名称，这些静态现象的实际运行影响尚未验收。

下一步：TransportUnitSystem与BondSystem逐组职责和内部调用；再补视觉执行、数据和外部依赖。配方初始化候选图仍因净距诊断未交付；不影响已审查文档的证据记录。构建、SDK、实机及统一门户完整交互仍待验收。


## 最新推进：传输单元实体、注入与交接

6组部分复核、23组待逐组复核；59条代表关系登记、100段独立模块证据。新增[传输单元模块说明](transport-unit-module-review.md)，不改变既有八章主图计数。

明确载具模型与硬件搬运调度的边界；已追踪配置→构造→常规/异形坐标→ModifyMatter→S2/S1步骤注入→偏移及跨台Refresh。注入只补步骤字典，ModifyMatter异常会清配置并保存，可能继续构造；影响需运行复现。

下一步优先BondSystem模块职责与内部调用；TransportUnitSystem下层构造、视觉/Mapping以及真实存储调用继续列缺口。生产源码未修改，静态一致性检查不替代构建和实机。


## 最新推进：贴装领域自检与设备副作用

7组部分复核、22组待逐组复核，68条代表关系登记、116段独立模块证据；新增[贴装模块说明](bond-system-module-review.md)。代表关系登记不是全局唯一调用计数，指定方法范围不代表整文件验收。

已核实配方力值/延时/相机点位条件、动作步骤检查、吸嘴架与焊头检查、清吸嘴名保存、抛料和任务入口。自检可能开真空、改记忆或抛料；硬件检查前7槽且是非对称判定，抛料终态检测被注释，均需设备环境验证实际影响。

下一步将TransportSystem与DispenseSystem模块职责、状态交接和内部依赖对齐已有主流程专题，再继续补偿/换嘴/视觉与数据外部依赖。配方初始化候选图布局、完整门户交互、构建及实机仍待验收；生产源码未改。


## 最新推进：传输任务与点胶双入口

9组部分复核、20组待逐组复核；81条代表关系登记、140段独立模块证据。新增[传输模块](transport-system-module-review.md)与[点胶模块](dispense-system-module-review.md)，不改变八章主图的限定覆盖口径。

核实传输任务模式分派、IsAlive与料仓任务集合不一致、分段传输实际气缸/皮带调用、清记忆后仍需人工取走载具；核实点胶准备检查、来料等待和生产动作两个预点胶入口、首次/周期触发、失败收尾和挤胶分支。设备效果及参数相关风险仍待复现，不用静态检查冒充实机结论。

下一步补预点胶GetEpoxy/胶后检测与底层阀包装，完成当前自动工作链的输入输出闭环；随后按模块清单继续视觉、运动、统计/数据与外部依赖。配方初始化候选图布局、完整门户交互、构建和实机仍待验收。

## 2026-09-28：预点胶下层链路补充

- 已补：点位预留/保存、胶后检测返回、人工选择结果、导出异常和胶阀/压力包装。
- 当前模块登记：9组部分复核、20组待逐组复核；86条代表关系、148段独立源码快照；不代表完整覆盖。
- 新发现：检测返回码未被预点胶上层判断；导出使用null焊点可在本地catch后仍返回Success；空跑判断晚于检测移动/照明。详见点胶模块复核文档。
- 下一步：视觉与运动模块边界，再推进统计/数据和外部依赖；构建、设备验证、配方初始化候选图布局问题仍未完成。

## 2026-09-28：视觉服务执行链

- 新增Infrastructure视觉服务限定复核，补深PR硬件执行及存图边界。
- 当前10组部分复核、19组待逐组复核；94条关系、159段独立模块证据。
- 已确认启动委托→内存队列→后台存图链；缺失PR判空顺序、结果赋值时机和写盘异常需测试。
- 下一步：派生视觉算法与坐标/运动，随后统计/数据与外部依赖；没有完整模块或设备验收。

## 2026-09-28：胶量算法与坐标转换

- 已补EpoxyDetectAlg实际分支、VM输入/结果、工厂和算法切换；新增CoordinateSystems限定复核。
- 当前11组部分复核、18组待逐组复核；104条代表关系、176段模块证据。
- 明确普通父链遍历与从属两层转换差异；VM逆向不支持、固定像素中心及图像输入失败后继续均列入验证缺口。
- 下一步追点胶机械目标到运动模块/驱动的执行、失败和停止；其他视觉算法仍待覆盖。

## 2026-09-28：点胶运动至驱动边界

- 已补机械目标、安全高度分支、Z/XY/XYZ包装、到位等待调用及普通停止/急停差异。
- 当前仍11组部分复核、18组待逐组复核；109条关系、185段模块源码证据。
- 确认真正MotionService/Axis未找到本地C#实现，项目引用LogicHardware/Drive DLL；记录本地哈希，未宣称运行版本或超时契约验证。
- 后续继续统计/数据主链，并保留其他运动、算法、驱动源码/契约、完整图形与设备验证缺口。

## 2026-09-28：统计与数据主链

- 新增SupportFeature统计局部复核，补Infrastructure/DBService；确认本机SQL Server及容量500的内存队列。
- 当前12组部分复核、17组待逐组复核；117条代表关系、197段模块源码证据。
- 已记录同步入队可能阻塞、写库失败不重试、查询错误空列表和指标提前返回；未连接数据库或执行清理。
- 下一步补其余数据生产者/生命周期，再推进外部依赖与剩余分组；整套图形/运行验证仍待完成。

## 2026-09-28：日志生产与退出保存

- 已补报警直接写库、参数/UI日志过滤、状态先改后入队及窗口/其他退出入口。
- 配置DataSave不是统计/存图队列排空；异常捕获后仍可退出。所有结论附源码行号。
- 当前12组部分复核、17组待逐组复核；122条关系、205段模块证据。
- 下一步推进外部依赖清单和剩余模块，保留AOP织入、完整数据源及退出测试缺口。


## 2026-09-28：统一外部依赖声明审计

- 统一16项目口径，自动记录806条声明、条件、精确XML行号和项目哈希；8条字面路径缺失。
- 修正旧依赖入口的17项目统计及历史构建文档的过度完成表述。
- 模块复核状态未增加：12组部分复核、17组待逐组复核；122条代表关系、205段模块证据。
- 后续继续剩余模块和分支证据补齐，再同步专题图；依赖解析、完整编译、SDK契约与设备运行仍待验证。


## 2026-09-28：配置驱动的自动对焦链路

- 已追踪P1–P4定位开关经System1/2传入视觉控制器，再进入AutoFocusing粗扫、六轮细调与VisionDesigner评分。
- 对焦位于所读控制器的DryCycle提前返回之前；末轮下降直接退出而没有注释所说的回峰动作；范围、取消/超时和资源契约列为缺口。
- 当前13组部分复核、16组待逐组复核；130条代表关系、219段模块源码证据。计数不等同全源码覆盖率。
- 下一步优先展开标定调用中的参数方向、相机选择和完整任务链，再继续其他待复核分组；对焦专题图与主图整合仍待完成。


## 2026-09-28：自动标定主调度与偏移子链

- 已梳理主界面按System1/2分流、人工确认、串行子任务和最终保存/结果窗口；单项入口与总流程分别记录。
- 确认启动事件忽略回零bool、标定对焦上下界反向、偏移重复上限和单轮检查不保证精度；源码保持不变。
- 当前14组部分复核、15组待复核；137条代表关系、229段模块证据。
- 继续其余标定子算法及参数/坐标保存，再同步相关图；不可用本记录宣称全标定或实机完成。


## 2026-09-28：点胶与邦定相机采样和保存

- 已复核点胶9点、邦定30点、模板选择、VM文件导出及Halcon图像到相对计划坐标的变换。
- 分阶段保存不具事务回滚；点胶测高失败跳过本方法后续清理。Singleton保存实现未找到，保持外部依赖缺口。
- 当前14组部分复核、15组待复核；142条关系、239段模块证据。
- 下一步继续上视/同标记/晶圆标定与居中/测高下层，再整合图形；无生产源码变更或设备执行。


## 2026-09-28：上视、同标记、晶圆与公共居中

- 已追30点上视/圆拟合、同标记覆写、左右标记间距与25点晶圆/G0坐标建立。
- 区分居中false仍继续与PR异常直接传播；记录2轮尝试、固定像素中心、分阶段保存和不同右标记属性。
- 当前14组部分复核、15组待复核；150条代表关系、251段模块源码证据。
- 下一步将已核实标定主链及子链整合为可溯源Archify图；独立/全局标定其他入口、测高/运动底层及运行验收仍未完成。

## 2026-09-28：标定图与逐节点源码映射整合

- 交付10节点、10连线的Archify标定执行专题图，加入统一入口；十个节点均绑定源码证据。
- 交付9/9检查通过，浏览器检查pass；只表达已复核主链，代表失败边不等于全部异常已覆盖。
- 当前仍14组部分复核、15组待复核；150条代表关系、251段源码证据。
- 下一步优先补测高/运动下层、其余标定入口与恢复边界，再推进待复核分组。全量框架、业务及实机验收尚未完成。

## 2026-09-28：测高分发、人工重试与安全移动边界

- 已追标定到邦头WithTDSensor、人工Retry/Cancel、点胶激光/探针/IO分发，以及调用者保存和失败收尾。
- 已追点胶Z/XY入口、邦头安全移动分支与单步闸门；闸门false后调用者继续测高是条件性源码结论，尚未设备复现。
- 新增8条关系与10段证据；当前14组部分复核、15组待复核，158条关系、261段模块证据。
- MeasureHeightEntity及IOJudgeCondition未在trunk C#中找到类实现；记录项目引用及本地DLL哈希，不以传入10秒推断完整超时/清理语义。
- 下一步补邦头安全高度计算、XY/Z运动包装和单步false来源，再继续其余标定入口及15个待复核分组。全量覆盖与实机验收仍未完成。

## 2026-09-28：邦头安全高度与单步退出来源

- 已核对三维安全高度的TU/点胶/吸嘴/非工作/华夫盒顺序，以及XY/Z包装和返回值。
- 已找到单步false路径：等待期间标志清除；Stop会清标志，UI关闭先Set再清标志，因此返回结果存在时序差异。
- Z动作的Abort未由安全移动上层消费；XY离线/轴缺失可直接返回；均是源码边界而非已复现故障。
- 新增7条代表关系、11段源码证据；当前14组部分复核、15组待复核，165关系、272证据。
- 下一步继续独立/全局标定入口及其他待复核模块，保留外部运动/测高库、线程竞争和实机验收缺口。

## 2026-09-28：全局标定多模式调度与扫描输出

- 已分清Only相机按钮、全局窗口与Ex窗口入口；全局窗口不是StartAutoCalib子步骤。
- 已复核八种索引调度及Record/二维补偿/Z-XY主要扫描、两轮预补偿、驱动与Excel分阶段输出。
- 区分预补偿PR失败抛异常和主扫描失败占位继续；Stop置标志并非立即停轴，部分后续前置动作仍可执行。
- 新增10条代表关系、14段源码证据；当前14组部分复核、15组待复核，175关系、286证据。
- 下一步展开Only/Ex、Scale/Test/Record其余算法以及补偿配置和生产消费，再推进待复核分组；外部SDK、异常恢复及设备精度验收未完成。

## 2026-09-28：补偿数据来源与生产消费分离

- 发现BondCompensate.GetBondCompensate无条件提前返回，后续插值不可达；已修正全局标定配套说明。
- 生产CalculateBondPos调用TransportUnitCompensate：统计列表按产品网格导入、缩放和平滑、保存，计算后从G0位置减补偿并转机械目标。
- 记录列表未显式排序、索引夹边不重算余数、清除仅改内存、辅助全局插值未找到其他直接调用等边界。
- 新增8条代表关系、16段证据；当前14组部分复核、15组待复核，183关系、302证据。
- 下一步继续Only/Ex及全局剩余算法，再推进尚未复核的项目分组；保留配置/SDK/数据库契约及运行质量缺口。


## 2026-09-28：独立相机标定与自动主链差异

- 已复核四个Only相机方法，区分上视取片、BMC双标放片、放后复测、重取、采样、旋转和提前保存。
- BMC放片失败Ignore后返回；其他PR点Ignore构造结果继续。结果窗口不代表所有步骤成功。
- 新增9条代表关系、10段源码证据；当前14组部分复核、15组待复核，192关系、312证据。
- 下一步继续Ex入口及全局剩余算法，再推进待复核分组；没有生产源码变更或设备运行验收。


## 2026-09-28：Ex扫描准备、补偿验证与循环调度

- 已复核独立窗口到四种扫描模式、温漂、区域插值、点位生成/导入导出与异步包装；补偿扫描把插值加到名义位置。
- 停止以取消break结束时仍可能派发循环；完成标志是零值数量检查，网格行列间距读取同一个控件，预测器初始化被注释。均未设备复现。
- 新增14条代表关系、30段源码证据；当前14组部分复核、15组待复核，206关系、342证据。
- 下一步补旧全局窗口Scale/Test/Record，再推进待复核分组；后续统一图需纳入独立Ex链，禁止混入生产必经步骤。


## 2026-09-28：旧全局单轴补偿、测试记录与驱动输出

- 已补ScaleX/Y逐轮残差累积、测试偏移与记录占位、无界居中、OpenStage/CloseStage、ETEL下载及固高AutoScale、Excel目录/保存。
- 明确停止/PR失败可能跳过恢复；部分ETEL下载异常被吞后仍激活，固高开启bool未由窗口消费；固定表步长及先取整步长需设备配置核对。
- 新增10条代表关系、19段证据；当前14组部分复核、15组待复核，216关系、361证据。
- 下一步按模块清单扩展待复核分组，并整合独立标定专题图；其他工具窗口、SDK/配置/运行验收保留缺口，不将局部复核称作模块完成。


## 2026-09-28：应用进程启动与主窗口就绪边界

- Program分组从待复核推进到部分复核，记录磁盘/迁移/条件授权、本地版本公告、硬件初始化、PR后台任务与MainForm.Load。
- PR Task在Main未等待；硬件初始化catch提示后无退出；主窗口Load未回零且非离线则禁用入口并提前返回，窗口显示不等同就绪。
- 新增9条代表关系、12段源码证据；当前15组部分复核、14组待复核，225关系、373证据。已修正本计划顶部旧模块计数。
- 下一步沿启动前提追授权模块和后台生命周期，同时继续其他待复核分组及图形整合。未修改生产源码，未运行设备。

## 2026-09-28 授权与后台生命周期补充
本轮新增授权检查、辅助进程读取重试、设备后台调用顺序、图片/数据库消费线程与关闭路径的限定范围复核。当前16组部分复核、13组待复核，241条代表关系、391段快照；均不代表完整验收。专题见[授权与后台生命周期](authorization-background-source-review.md)。外部授权库、队列排空、线程异常及设备退出仍待验证。

## 2026-09-28 配置与数据保留补充
复用已有配方、日志及存图证据，新增5段清理源码快照和4条下层关系；当前241条代表关系、396段快照，仍为16组部分复核、13组待复核。未把重复阅读计为新增模块覆盖。新增[配置与数据保留复核](configuration-persistence-source-review.md)：八表保留字段、生产启动前同步清理、视觉图片目录不受同一清理入口覆盖，及失败不代表完成的边界。未执行删除、数据库连接或设备动作。

### 2026-09-28：配方删除与备份边界补充

补齐配方删除选择、PR文件/内存/JSON保存顺序、备份与缓存恢复差异、配置归属解除和界面提交边界。详见[源码复核](recipe-deletion-backup-source-review.md)。当前277条代表关系、444段源码快照；16组部分复核、13组待复核。外部库、失败场景及现场验收仍待完成。

### 2026-09-28：轴补偿与实验调用边界

[轴补偿复核](axis-compensate-module-review.md)新增计算、拟合及测试按钮调用证据。分段补偿目前原样返回输入，启用属性未被GetOffset读取；未发现拟合函数的显式调用，不将实验窗口当作生产接入。当前18组部分复核、11组待复核，277条代表关系、444段源码快照。尚未完成全工程业务、构建、设备及交接验收。

### 2026-09-28：胶路编辑与模板持久化

[本轮复核](dispense-pattern-editor-source-review.md)串起人工编辑、单位转换、内存回写、校验重开和独立Confirm保存，补齐模板BMP/XML读写失败边界。当前19组部分复核、10组待复核；277条代表关系、444段源码快照。编辑到生产运行实体的完整消费链仍待贯通，未声明全模块验收。

### 2026-09-28：S1胶型配置消费闭环

已将参数变更/测试按钮保存、名称列表解析、当前步骤按名查仓库及S1点胶控制器消费接到[胶路专题](dispense-pattern-editor-source-review.md)。当前277条代表关系、444段源码快照；19组部分复核、10组待复核。S2和运行中编辑隔离仍未闭环；本次未执行设备控制。

### 2026-09-28：S2胶型缓存与生产消费

[胶路专题](dispense-pattern-editor-source-review.md)补齐S2动作选择时初始化胶型引用、缓存getter、吸嘴分支和生产预处理调用；明确与S1直接查名的差别。当前277条代表关系、444段源码快照，19组部分复核、10组待复核。运行中编辑隔离、缺失步骤/胶型的可达性以及硬件行为仍待验收。

### 2026-09-28：配置消费交互图候选稿

已形成11节点、11关系的Archify配置消费候选图，并绑定已有源码证据。9项SVG/连线检查通过，但桌面可读性仍有1项错误（配置文件节点文字投影5.24px，要求至少6px）；未交付HTML、未做浏览器验收，不并入正式图统计。候选与状态分别为dispense-config-consumption-workflow.archify.json和dispense-config-consumption-workflow.review.json。正式入口保留原有已交付内容。


### 2026-09-28：配置消费图正式交付（更新候选状态）

已交付[胶型配置与S1/S2生产消费图](dispense-config-consumption-workflow.html)，接入总入口。11节点、11关系绑定既有证据。Archify 9项检查通过，组合检查0错误0警告；Edge自动检查通过，1440×900浅色截图已目视复核。本记录取代上方候选稿的当前状态，历史记录保留。仍为19组部分复核、10组待复核，277条代表关系、444段源码快照；不代表全模块或设备验收。


### 2026-09-28：标定工具模块接入边界

新增[标定工具源码复核](calibration-tool-module-review.md)：区分类库声明、窗口工具链和生产调用；核实方案加载/保存、结果回调、单次Run与DripCalib。新增14段证据、9条关系，当前20组部分复核、9组待复核，286条代表关系、458段快照。其余标定API、算法和外部SDK待展开。


### 2026-09-28：标定API结果与转换失败传播

[标定工具专题](calibration-tool-module-review.md)补齐三个窗口标定API、四类PRC转换、偏移计算及主工程实际调用对照。发现窗口三个API输出赋值被注释，GetOffsetWorld未消费转换bool；均为静态边界，未运行复现。新增9段证据与9条代表关系，复用2段已有主工程证据。当前20组部分复核、9组待复核，295条代表关系、467段快照；仍未完成全工程或设备验收。


### 2026-09-28：标定控件与事件生命周期

[标定工具专题](calibration-tool-module-review.md)补齐两个控件包装/设计器、页面切换、连续运行事件和日志。配置字段实例化被注释，停止回调未恢复保存按钮，日志失败重新抛出；均明确限定为源码边界，未运行验证。新增8段证据、6条代表关系。当前20组部分复核、9组待复核，301条代表关系、475段快照；剩余纠偏算法、SDK与现场验收继续保留。


### 2026-09-28：单点双点批量仿射纠偏

[标定工具专题](calibration-tool-module-review.md)新增公开单点/双点入口、矩阵构造和逐点映射；公开三点批量实现整段为注释，未登记为运行关系。底层转换bool未消费，未发现公开入口显式调用方，不接到自动生产主图。新增6段源码证据、7条有效代表关系；当前20组部分复核、9组待复核，308条代表关系、481段快照。其余偏移角度算法、外部SDK与设备验收尚待完成。


### 2026-09-28：组合偏移与几何辅助方法

[标定专题](calibration-tool-module-review.md)补齐组合偏移、角度、单/双点偏移和私有定位重载。确认CalcOffset向上视旋转传0；双点中点第二实参为P1.X；私有三点映射缺少矩阵构建。均记录调用可达性与SDK验证限制，不宣称已复现生产故障。新增9段证据和9条关系；当前20组部分复核、9组待复核，317条代表关系、490段快照。


### 2026-09-28：标定接口与方案依赖核验

[标定专题](calibration-tool-module-review.md)已补Correction四个同名标定API；[依赖记录](calibration-tool-dependency-audit.json)确认trunk内未找到固定要求的1个SOL及4个PRC，11个指定SDK引用DLL存在，但未加载/执行或核实版本许可。新增6段证据、4条关系；当前20组部分复核、9组待复核，321条代表关系、496段快照。主要行为方法已分段阅读，不宣称模块完整验收。下一步回到未复核分组和生产内部缺口，外部方案/运行环境验证继续保留。

## 2026-09-28：配置迁移工具增量复核

Akrs.ChangeJson 已从待复核转为部分复核。手动迁移及原地写入边界见 change-json-module-review.md；此工具不计入生产自动循环。下一步继续剩余待复核组及主生产链内部缺口。

## 2026-09-28：日志测试入口与外部库边界

日志测试组改为部分复核。两个按钮分别提交异常与普通日志，不是生产自动循环。配置加载、实际落盘及运行验证仍列缺口，详见 log-test-module-review.md。

## 2026-09-28：PR测试与共享编辑器链路

新增测试入口到仓库、编辑器刷新和关闭保存的源码复核。false参数未阻止构造函数启动后台刷新；采图受连续开关和相机条件约束。未运行硬件初始化，剩余内部功能仍列缺口。详见 pr-test-module-review.md。

## 2026-09-28：示教测试导航和注释动作边界

TeachTest 改为部分复核：当前项目声明类库，TU调整测试有效步骤为导航和关闭，采点/配置写入为注释。其余五类窗体仍待复核，不能算作生产示教完成。详见 teach-test-module-review.md。

## 2026-09-28：插补测试实际运动分支

新增两轴按钮实际四轴五段Uml路径、两轴PT两点和DsaException清理复核，区分UI名称、参数保存与有效运动。未执行设备。详见 interpolation-test-module-review.md。

## 2026-09-28：曲线演示与设备采集边界

组件演示组改为部分复核：类库内定时曲线使用随机数，Bond force仅为标题。未将模拟曲线纳入生产采集链，详见 component-demo-module-review.md。

## 2026-09-28：公共声明与生产语言维护链

Common.cs 和 Localization 改为部分复核。公共类型不虚构执行关系；语言切换已连到生产界面事件、设置保存及文件/控件应用，但覆盖率与动态验收仍待补齐。

## 首轮分组覆盖后的推进门槛（2026-09-28）

29组均有限定范围复核记录，仅表示每组已开始；尚无分组完整验收。接下来优先收敛生产自动工作的内部步骤，不继续以增加图数或读过文件数充当完成率。顺序：生产任务/等待与退出 → 视觉和运动下层边界 → 配方与数据一致性 → 工程师导航和运行验收。每项必须保留源码调用点、被调用实现或外部边界、异常路径及未确认项。

## 生产主链进展：料仓上下料（2026-09-28）

已补料仓模式启动、当前/下一层定位、上下料双向信号握手、层号修改责任、NoStart/None/Abort/Exception处理和暂停时序边界。新增10条代表关系、15段精确源码快照。详见[上下料握手复核](loader-unloader-handshake-source-review.md)。

下一项：继续输送料仓控制器的传感器等待和推杆/皮带路径，再联查停止与暂停恢复；下层硬件与故障复现仍未验收。

## 生产主链进展：料仓输送内部（2026-09-28）

已展开上下料输送控制器、传感器循环、推杆和皮带包装及Ignore/重试/异常分支，新增10条代表关系、17段源码快照。详见[控制器复核](bin-transfer-controller-source-review.md)。下一步联查全局停止与这些循环、后台缩回Task的实际关系。静态风险未作实机复现。

## 生产主链进展：停止与料仓任务（2026-09-28）

已联查Pause/Continue/Stop/EmergencyStop、退出任务清单、报警清窗和料仓内部循环，新增8条代表关系、7段源码快照。详见[执行位置影响矩阵](bin-stop-resume-source-review.md)。明确继续不重建已退出任务、局部后台缩回Task不在退出检查清单中；并发路径仍需隔离测试，不能据静态代码宣布实机故障或安全停止。下一项核实轴动作实际实现边界、层位移动和保存恢复。

## 生产主链进展：层位移动与保存（2026-09-28）

已核实层位公式、推杆安全判据、A/B切仓、Y/Z返回传播差异及程序文件路径。新增9条代表关系、16段源码快照。详见[层位复核](bin-layer-motion-persistence-review.md)。轴SDK和Singleton保存的实际契约仍缺源码级证明；接续仓库名称选择/加载与图内语义同步。

## 2026-09-28：料仓配置选择与加载
新增8条代表关系、12段源码快照，当前424条关系、640段快照。核实下拉过滤、名称保存、生产按名称查找、仓库关闭保存和设备/配方文件边界。见[源码复核](bin-configuration-selection-review.md)及[配置调用时序](bin-configuration-sequence.html)。29组仍为部分复核；外部存储库、上层编辑门控及异常运行验证尚未闭环。

## 2026-09-28：编程编辑门控与启动入口
新增10条关系、15段源码快照，当前434条代表关系、655段源码快照。已确认Working/Pause按钮禁用、编辑点击拦截、后台BeginInvoke状态刷新及普通/Production启动关窗范围不同。见[门控源码复核与待验收场景](production-edit-gating-review.md)。下一步沿其他入口与外部持久化依赖闭环；UI/设备验证尚未完成。

## 2026-09-28：自动化入口分类与快捷操作
新增10条代表关系、13段源码快照，累计444条关系、668段快照。已区分Machine.Start、独立视觉扫描Task、四段并行输送、全局/窗口单步信号及Continue状态恢复。见[入口对照与待验收清单](automation-entrypoint-matrix.md)。不将所有进入Working的路径合并为正常生产启动；事件路由、任务异常/重入与运行验收仍待验证。

## 2026-09-28：配置故障与依赖证据边界
细化已有MachineConfig/路径关系，不重复增加调用计数；仍为444条代表关系、668段快照。新增[配置失败边界](persistence-failure-boundary-review.md)与[可重建依赖基准](persistence-dependency-boundary.md)。验证脚本检查5个依赖/声明文件和5个既有源码绑定，扫描1436个C#文件中的3个外部类定义候选；check模式已纳入verify-all。该检查不执行DLL，不证明实际加载版本、保存原子性或外部库行为。

## 2026-09-28：模块级源码交接阅读器
新增[交互式模块源码查看页](module-source-explorer.html)，接入统一入口主导航。沿用29模块、444关系和668证据，不以阅读器新增虚报业务覆盖。浏览器测试与快照原文显示已验证；生成页面的新鲜度检查纳入verify-all。见[工程师使用和更新说明](source-explorer-handoff.md)。

## 最新推进：生产启动就绪与失败传播

[源码专题](production-start-readiness-review.md)。新增5条代表关系、7段源码证据；累计449条关系、675段快照，29组仍全部部分复核。明确载具Abort在输送内部Stop/return后外层仍继续调用后续Start；不推断任务必然运动。下一步逐任务核对状态门控、失效料仓名首次解引用和其他域检查。未进行硬件运行。

## 最新推进：任务Start门控已核对

[五类任务启动门控](production-task-start-gates-review.md)：新增5条关系和16段证据，累计454条代表关系、691段快照。供晶及翻转的Working重写、助焊/翻转循环前归位已逐段对应源码；不代表设备动作或全链路已验收。下一步：失效料仓名称解引用及异常传播。

## 最新推进：失效料仓名称异常路径

[料仓缺失配置复核](bin-missing-configuration-review.md)：新增3条关系、11段证据，累计457条关系、702段快照。有料盒条件下LayerNum空引用被工作任务catch提示，区别于Abort显式Stop；异常时本次首次允许推料Set未执行。29组仍部分复核；信号全局与运行影响未验收。下一步：其他域就绪检查与异常后的全局握手。

## 最新推进：各域启动就绪检查

[域级就绪检查](production-domain-readiness-review.md)：新增6条关系、8段证据，累计463条关系、710段快照。核实检查中的运动/输出/保存调用、自检放行、BP空列表、异形TU注释分支和FC按步骤计数。仍需展开委托检查、失败后的全局握手及运行影响；29组均部分复核。

## 最新推进：S1/S2下层就绪校验

[委托检查专题](production-readiness-delegates-review.md)：新增6条代表关系、10段快照，累计469条关系、720段证据。点胶对象缺失、固晶力控/视觉/延时、吸嘴架七槽位和预点胶放行条件均对应源码；扩展方法绑定、实际配置边界和运行测试待完成。下一步恢复异常后全局握手追踪，随后补这些明确缺口。

## 最新推进：料仓异常后的四信号闭环

[握手等待与恢复边界](bin-failure-handshake-recovery-review.md)：新增5条关系、9段快照，累计474条代表关系、729段证据。完成本四信号具名引用清单与生产者/消费者/复位矩阵；确认无参Wait无整体超时、Continue不重建、Start先复位再检查任务。其他域失败传播、并发运行仍待复核。

四信号专题已补[Archify时序图](bin-failure-handshake-sequence.html)并接入统一门户；9/9检查、Edge布局及明暗截图审阅通过。图只呈现条件场景，不新增全项目完成声明。

## 最新推进：输送—固晶失败传播

[交接与重试专题](bond-transport-failure-handshake-review.md)：新增5条关系、11段源码快照，累计479条代表关系、740段证据。区分枚举Retry与报警Retry、真实S2ActionNodeController绑定、停止后收尾可达路径以及异常枚举/抛异常差异。29组仍部分复核；下一步供晶—取片—顶针失败握手及补偿返回副作用。未执行设备运行。

## 最新推进：供晶—取片—顶针握手

[源码专题](wafer-pick-ejection-handshake-review.md)及[Archify时序](wafer-pick-handshake-sequence.html)已接入。新增6条关系、18段快照，累计485条代表关系、758段证据。明确异步通知不随节点Success保证完成、提示后才Stop、实际顶针Task.Wait路径；29组仍部分复核。下一步非晶圆相机等待和视觉切换请求，再追后台通知竞争与全局异常观察。

## 最新推进：相机等待与视觉重取路由

[源码专题](vision-request-routing-review.md)补齐Bond相机延后等待、Block到位检查、静态华夫跳过、上视重取与正常换类型请求。新增6条关系、16段快照，累计491条代表关系、774段证据。确认正常上视异步请求可在后续补偿Abort之前已启动；未承诺任务完成或实机恢复。下一步后台通知共享字段、全局异常观察与剩余视觉工艺。29组仍部分复核。

## 最新推进：后台通知上下文与异常观察

[源码专题](async-notification-exception-review.md)补充三个通知路径的动态芯片查询、实例字段、动作仓库复用和调度切换，并核对Program的两个异常处理器只提示、不执行Stop/Join。新增4条代表关系、10段快照，累计495条关系、784段证据；29组仍全部部分复核。共享字段交错是源码支持的风险推断，不是实测故障。

本轮进一步对 `BondSystem/Models/ActionNodes` 的 37 个 C# 文件做全量通知写入面盘点，登记 54 个匹配点：晶圆 41、翻转台 2、刮胶盘 11；同时记录每个匹配点附近的 `Task.Run`/`Task.Factory.StartNew` 词法证据。该盘点补齐了源码写入点清单，但不证明委托闭包、Task 等待、并发顺序或设备行为；结果见 [机器审计](async-notification-write-surface-audit.json) 与 [复核说明](async-notification-write-surface-review.md)。

随后对其中 8 个实际通知 `Task.Run` 块做了源码生命周期核对：8 个启动处都未保存返回 Task，块结束后 20 行内也未发现可归属于该块的 `await`/`Wait` 观察。该结果只说明当前源码的任务可观察性缺口，不推断运行时一定丢异常或一定发生交错；见 [Task 生命周期审计](async-notification-task-lifecycle-audit.json) 与 [复核说明](async-notification-task-lifecycle-review.md)。

又对绑定的原始 ZX2200 程序集做了 Mono.Cecil IL 复核：三个动作节点类型共 24 个 `Task.Run` 调用点，其中 12 个立即 `pop`、12 个存入局部变量；承载通知的 Pick/Substrate/UpLook `DoWork` 调用点均属于立即 `pop` 的 6 个点。该证据锁定了程序集层的返回值处理，但仍不等于任务已执行、异常已发生或设备已停止；见 [IL 审计](async-notification-il-audit.json) 与 [复核说明](async-notification-il-review.md)。

[可重建异常引用审计](task-exception-audit.json)覆盖1436个C#文件，纳入verify-all；零命中仅限具名文本查询，不排除DLL、反射和其他监督机制。下一步补其余视觉/读码通知写入点、停止与关闭回收链路，并独立标注外部服务缺失实现及运行验收。未改生产源码，未运行设备。


## 最新推进：停止、急停与软件退出边界

[源码专题](stop-shutdown-lifecycle-review.md)区分普通Stop、EmergencyStop、窗口关闭和关机/重启弹窗；补充空Abort方法、点胶Dispose、退出空catch与任务状态谓词的实际边界。新增5条代表关系、8段快照，累计500条关系、792段证据；29组仍全部部分复核。没有把Stop状态或退出码0当作任务回收、保存和硬件清理成功证明。下一步继续其他视觉/读码通知分支，再展开激光检测调度和外部关闭契约。未执行设备操作。


## 最新推进：上视双点、读码与空跑

[源码专题](uplook-code-two-point-review.md)补充一/二/四次定位分支、读码条件与码值、自动和人工重取、报警UI返回以及空跑后台换型请求。新增5条代表关系、12段快照，累计505条代表关系、804段证据；29组仍部分复核。读码方法未使用传入位置执行移动，空跑仍调用运动，报警switch的未处理结果保留条件性风险说明。下一步继续报警按钮门控、硬件设置/关灯和码值数据链，并按计划追激光检测调度与外部关闭契约。未运行设备。


## 最新推进：视觉报警门控与硬件设置

[源码专题](vision-alarm-hardware-review.md)明确上视相机分支隐藏Skip并显示下一颗，收窄上轮未处理Ignore的UI可达性判断；SetHardware本地链仅绑定名称，关灯依单点P1/双点P2的IsFlash条件执行。报警后台异常可能遗留isWork=true与关闭仅轮询Running列为条件性风险。新增5条代表关系、12段快照，累计510条关系、816段证据。29组仍部分复核。下一步码值导入导出链，之后激光检测调度和外部关闭契约。未运行设备。


## 最新推进：芯片码值Mapping导出与恢复

[源码专题](component-code-mapping-review.md)串联上视码值、无流道自动保存、格式开关、文件覆盖及手选/扫码导入。确认导出模块首焊点码值、导入复制到模块全部焊点；保存异常只提示后调用方仍可能记录成功。新增5条代表关系、8段快照，累计515条关系、824段证据，29组仍部分复核。下一步按计划追激光检测调度和外部关闭契约；码值样本往返和窗口绑定缺口已登记。未读写现场文件、未运行设备。


## 最新推进：激光监控调度与关闭依赖边界

[源码专题](laser-monitor-shutdown-review.md)确认后台串行检查、未等待的Task.Delay、环境/算法/光强/通讯异常的不同返回，以及未接入的具名预热方法。核对共享ThreadFlag和BaseMachine.ExitApp，未将其误接到ZX2200退出链；登记LogicHardware引用和本地DLL身份但保留内部契约缺口。新增4条代表关系、9段快照，累计519条关系、833段证据，29组仍部分复核。下一步回到Mapping恢复构造/制程注入和独立样本往返验证；外部关闭实现留作明确依赖缺口。未运行设备。


## 最新推进：Mapping构造与制程恢复原方法测试

[源码专题](mapping-restore-step-review.md)追到构造Init已注入S2/S1、读取后再次注入，以及完成/禁用的不同写入。新增3条关系、6段快照，累计522条关系、839段证据。提取原方法的8项纯内存C#测试通过，覆盖重复注入、状态完成和Split空字段；不是完整Mapping编解码或设备验证。29组仍部分复核。下一步恢复专题可视化及真实编解码隔离样本，保留坐标构造与下游调度缺口。

## 2026-09-28：恢复流程图与调度消费者

- 已交付 mapping-restore-workflow.html / .archify.json，9/9 showcase、零错误警告；四桌面尺寸浏览器检查及浅色/深色人工视觉复核通过。
- 新增 mapping-restore-dispatch-review.md：区分焊点完成属性、身份识别门控、受LagerNumber控制的S2禁用过滤与动作队列Finished。
- 当前登记526条关系、845份源码快照；29分组仍为partial，数字不是整体覆盖率。
- 待完成：完整编解码隔离样本、启动时对象和Init顺序、各具体生产动作恢复门控。

## 2026-09-28：导入对象到生产门控

- 已核实S1/S2 Mapping窗口绑定，文件导入固定写S2与扫码写绑定对象的差异。
- 已核实S1/S2 IsProduct重建条件、Machine.Start顺序和七类动作恢复字典门控。
- 30项原始C#门控方法隔离测试通过；不含生产DoWork、启动、输送或硬件执行。
- 当前532条关系、865份源码快照，29个模块组仍partial。
- 下一步：MapBelt/Refresh副作用及交接对象身份，再完成Mapping编解码样本验证；实机续跑仍未验收。

## 2026-09-28：输送对象保留及编解码受控样本

- 核实S1/S2 MapBelt早退、搜索/真空分支、人工确认保留/清空及有限范围的逐层Refresh作用。
- 核实S1→S2→等待下料→下料皮带三处引用交接，区分Refresh与重新构造。
- 已完成提取码值Mapping完整读写方法的25项临时文件检查，包含三种阵列及保留码、空格、空值和异常路径；生产对象构造/完整配置/设备并未参与，不能等同整机验收。
- 当前537条关系、879份源码快照；29组仍partial。
- 后续优先确认文件格式业务契约、生产构造和配置一致性，补可复现的恢复全链路验收场景，再推进其他模块缺口。


## 2026-09-28：恢复链路交接验收清单

新增[12项验收场景页面](mapping-recovery-acceptance.html)，关联36处已有源码证据及3份隔离测试报告。覆盖配方配置、导入目标、对象重建、搜索交接、码值格式、动作门控、保存异常与停止重启。所有场景的端到端运行均保持未验收；不新增代表调用数量。顶部计数已同步537/879，29组仍部分复核。源码链接与报告来源自动检查已纳入回归。下一步先核对实际配置与历史文件，再补生产构造和完整执行记录。


## 2026-09-28：构造副作用实验与材料盘点

补充基岛/焊点构造、配置访问和数量字段5段证据、1条关系，当前538条代表关系/884段快照，29组仍部分复核。ModifyMatter/ClearInformation的13项原方法隔离测试确认清配置、部分实体状态保留及二次异常传播；未执行真实保存或完整构造。trunk文件名盘点未找到七类核心配方同名文件，不能以调试参数代替认证配方。恢复验收页增至13场景/44处证据；Archify恢复图已补构造异常说明并重新严格交付。下一步追配置编辑路径的数量/坐标/名称一致性及其保存调用。

## 配置编辑一致性与测试更正（2026-09-28）

新增16段证据、3条代表关系，当前541条关系/900段快照。已确认示教Save的数量/坐标同步及焊点改名中的状态列表遗漏，见[专题](config-edit-consistency-review.md)。更正原状态测试的类/结构体替身错误：缺名返回Enable，不触发清理；原13项报告被14项更正测试替代。另有6项改名方法断言通过。29组仍部分复核；恢复验收14场景均未端到端验收。下一步是认证配置材料及剩余加载/编辑入口，不以局部测试冒充整机完成。

## 设置提交与示教分派（2026-09-28）

新增17段快照和4条代表关系，当前545条关系/917段快照。已核对常规设置页即时内存修改、Confirm提交顺序、两个按钮的异常边界及位置示教继续分派；8项原方法隔离断言通过。见[专题](config-submit-reload-review.md)。没有完成实际UI生命周期、外部Singleton反序列化或设备运行；29组仍部分复核。下一步逐页核实未实现IProgrammingControl的保存路径及配置加载的外部边界材料。

## 编程页面保存入口盘点（2026-09-28）

已盘点33处页面创建、32种主类型（20种主类直接声明提交接口，12种未直接声明），并区分7种说明页、配置展示及4种独立事件保存页。新增23段源码证据、7条代表关系，累计552条/940段。点胶列表9项原方法隔离断言确认取消增删不阻止刷新Save调用；不推断现场文件损坏。见[页面盘点](programming-page-inventory.md)与[方法复核](programming-page-save-review.md)。下一步继续20种接口页面的Confirm方法体、委托保存与对话框提交，未完成UI/设备验收。

## 到位等待二进制契约审查（2026-09-28）

已定位BondModule八处源码调用，并用Mono.Cecil读取随仓库LogicHardware、Drive与Infrastructure的程序集，保存哈希、IL偏移与精度/返回码枚举的[可复现证据](motion-arrival-binary-evidence.json)。[分层审查](motion-arrival-contract-review.md)确认逐轴等待、非Success结果聚合、HighAccuracy的实测等待路径、可选位置差检查以及四类厂商驱动分叉；指出提示文本0.5mm与实际比较常量2不一致。本轮没有增加代表源码关系或源码快照计数；29组仍为partial，未验收现场轴配置、依赖源代码、SDK内部实现、设备运行。下一步应先核实现场采用的驱动与配置，再制定设备到位/取消/异常传播的受控验收记录。

[Archify到位等待时序图](motion-arrival-sequence.html)已按相同证据生成，10消息/20锚点全部回链，showcase 9/9、零错误警告；浏览器四桌面视口和两主题通过，明/暗最终截图人工复核。交互图仅解释已提取的软件路径，未补齐现场验收。

## 编程页面方法体与间接保存（2026-09-28）

在原33处创建/32种页面的盘点上，[完整提取20种直接接口页面的Confirm方法体](programming-confirm-bodies.md)，固化文件哈希、起止行及正文。17种方法体包含直接Save调用，4种含提前return，2种显式throw；`UcConfiguration1.Confirm`为空，`UcMagazineGeometry`与`UcComponentEdit`各委托到本地保存方法。复核确认组件检查方法内部的警示return不直接阻断调用者的`CarrierConfigRepository.Save()`。这些是源码静态证据，不表示20种都已完成保存路径/事务/实际UI验收，也不覆盖另外12种未直接声明接口的页面；29组仍partial。下一步逐页核对Save实现及非接口事件保存路径，记录配置样本与外部依赖。

## 非接口页面事件保存复核（2026-09-28）

已将[四种非接口编程页的17个事件/辅助方法](noninterface-save-events-review.md)及22处直接Save调用定位到源码，固化[方法体、哈希、Designer或构造绑定与条件](noninterface-save-events.json)；另外八种主文件及其Designer均未命中Save，七种说明页无本地事件绑定，配置展示页仅有树焦点绑定，这仍不等于子控件无持久化。运输单元清空事件直接清两个列表并Save；焊点CellValueChanged在YesNo弹窗后以OK条件Save，包装器未见Yes转OK，记为需现场验证的高风险不一致；点胶刷新含分支Save，焊后仓库删除回调与程序保存分离。29组模块仍partial，不能声称全链路或设备验收。下一步核对间接子控件/委托、实际配置与现场依赖。

## 编程页 Save 实现分叉与二进制证据（2026-09-28）

沿页面事件向下复核[配方对象与设备仓库的保存边界](persistence-save-contract-review.md)，用 Mono.Cecil 固化随仓库 Infrastructure DLL 九个方法的[IL、令牌、异常处理表、程序集哈希与十二个源码哈希](persistence-save-binary-evidence.json)：新增 Singleton.GetInstance/Load、ReadGenericObject/List 的读取及默认实例分支。`Singleton.Save` 在锁内调用对象 JSON 保存；随附 helper 的对象路径采用临时文件/Replace 或 Move，但首次保存先创建目标；列表保存直接以 FileMode.Create 写目标，无本地 catch；两种序列化错误回调标记 Handled。视觉仓库 Save 在源码中 catch 并记录日志。当前只有仓库二进制的静态证据，现场 DLL 版本、磁盘异常和多文件事务未验收。Archify 专题图候选因路线走廊校验未通过而未交付，不计入已完成图；Confirm 二十页的保存目标矩阵已另行完成限定追踪。29组模块仍 partial。

## 编程页 Confirm 保存目标逐层溯源（2026-09-28）

已把[20种直接实现接口的Confirm入口](programming-confirm-save-targets.md)映射到24处直接Save调用：9处对象目标、10处列表目标、5处本地或子控件委托。进一步展开五种页面的委托方法，定位料仓配置两次保存与几何仓库保存、组件仓库、吸嘴仓库、邦点产品配置，以及运输单元三个仅修改配置的子控件方法；16个目标类声明和路径表达式均固化文件哈希与源码行，[机器可读矩阵](programming-confirm-save-targets.json)由生成器回归核对。宿主Save与Start按钮的可选Confirm调用也已链接源码，其中非接口页面可显示“保存成功”但无该接口提交调用。这里的“目标”表示源码调用意图，不表示现场文件成功落盘。另12种未直接声明接口页面的子控件路径、运行期实际版本/配方路径、条件异常分支和设备UI验收仍未完成；29组模块依然partial。下一步继续非接口子控件，并取得现场样本和依赖版本。

本轮继续展开 5 个间接保存/模态源文件：`FrmAddObject`/`FrmObjectCopy` 只构造返回对象，由父页面在 OK 后保存；两个新建配方对话框在确认事件内加入仓库并保存；通用 `FrmRepository<T>` 的显式保存按钮和 FormClosed 都保存仓库，新增/删除通过仓库调用，提取/双击通过委托刷新父页面。共登记 5 个直接 Save、9 个 DialogResult 赋值和 5 个通用仓库调用；结果见 [对话框保存闭环审计](programming-dialog-save-closure.json) 与 [复核说明](programming-dialog-save-closure-review.md)。真实 UI、外部 Singleton、异常回滚和设备仍待验收。

随后补齐 `FrmRepository<T>` 所依赖但仓库缺少源文件的 `FrmCreateName` 外部模态边界：从随附 `AKRS.Galaxy2.Infrastructure.dll` 的 `FrmCreateName` 类型记录 10 个方法及 8 个关键方法 IL，确认 `ValidatePredicate` 校验、`CreateName` 输出、OK/Cancel `DialogResult` 和编辑事件的按钮启用逻辑。该证据锚定当前 DLL 哈希，不能替代 UI 执行、部署版本一致性或异常恢复验收；见 [外部对话框 IL 审计](programming-external-dialog-il.json) 与 [复核说明](programming-external-dialog-il-review.md)。

## 非接口说明页与配置展示页组成核查（2026-09-28）

在四种非接口事件保存页面之外，[另外八种页面的主类与Designer逐一核查](programming-display-pages.md)：七种说明页只添加一个Label且无本地事件绑定；`UcConfiguration2`含14处内置控件嵌套、一条树焦点订阅、构造时数据绑定及树列表刷新，两个文件均未见直接Save。每个主类与Designer的SHA256、创建行、控件与事件位置写入[机器证据](programming-display-pages.json)，生成器纳入全套回归。宿主按钮的可选Confirm在非接口页可为空调用并仍显示成功消息。只证明有界源码组成，第三方GridControl编辑副作用、实际UI、现场文件与设备版本未验收；29组模块依然partial。下一步核对四个事件保存页的委托目标及真实配方路径。

## 非接口事件页保存目标回链（2026-09-28）

已将[四种页面、17种事件或辅助方法中的22处直接Save](noninterface-save-targets.md)逐处回链到目标类和路径表达式：19处普通对象Save、2处列表Save、1处视觉仓库自定义对象Save（附当前文件的复制备份及仅日志catch）。静态调用点数量不是实际执行次数；分支条件及原方法体仍见[事件证据](noninterface-save-events-review.md)。[机器可读目标矩阵](noninterface-save-targets.json)绑定页面与目标源码哈希，并纳入回归。至此已覆盖当前树节点选择法中32种页面的主类提交或事件保存入口；这不表示穷尽应用其他入口、运行期路径、跨文件回滚或现场成功落盘。接下来聚焦配方切换时FilePath初始化及现场依赖材料。


后续原S1启用Working/Pause任务核验：[8独立宿主进程](native-s1-working-pause-progress.json)及[报告与限定流程](native-s1-working-pause-review.md)已通过，两轮各70次执行/29不同断言标签、29原方法IL；162编译引用含10个源引用，运行16原保真资源程序集。完整原Start/DoWork实际Working：Pause阻塞、再次Start保持原Running任务；Continue执行四层原离线身份并发送放行，观察者Stop前可进入第二轮，不宣称恰好一循环/实际点胶制程完成。Pause→Stop在原WaitStart睡眠释放窗口仍返回true，下一载具身份在Stop下执行1次，随后退出不放行。两个公开回调故障使原Task Faulted、故障观察时设备仍Working/消息未Finish；fixture随后Stop收尾。公开配置/预置视觉及其他测高完成/禁用载具测高/同步及故障回调是限定fixture，未替换原动作/线程/信号、无私有写；在线硬件/预点胶来料/S2/SQL/UI未执行。准备引用数量与两次宿主using编译失败保留；87新增+5113父=5200。下一步S1真实来料/预点胶/Retry/返回故障/分段等待及S2Working链，完整生产生命周期/设备/构建部署仍待验收；正式1328和旧阅读器未改写，整体目标未完成。


后续原任务来料等待/预点胶门与S2入口：[两轮各54不同检查](native-task-input-gates-progress.json)和[报告/限定流程](native-task-input-gates-review.md)已通过。原私有S1/S2输入门绑定真实任务receiver直接执行，5个fixture等待线程均Join；S1只消费State，原Wait可再消费底层事件，不代表重复实物生产。S1 Pause期间不预点胶，Stop释放仍执行1次原Off/Off预点胶再false；无信号轮询3次回调Pause，Stop后第4次才false。S2原Wait同时消费AutoReset事件与状态，Pause→Stop保留事件/false；Compensate或未配置但有TU的私有门在Stop仍true，不代表整任务绕过外层Stop。真实原S2 Working Start两轮各Enable=true/false共4任务在原吸嘴架缺失AxisY处Faulted，来料未消费、设备仍Working、原运行字段已Reset，非成功完整S2工作循环。Compensate模式Stop状态先提交后缺失顶针输出异常亦原生验证。31原IL/19源码哈希，16保真资源物理绑定；2编译失败、无效输出EFTYPE未创建CLR、38断言后实际Stop缺硬件exit1全部保留。72新增+5200父=5272，不增正式1328/旧40专题3817。无私有替身/生产源码修改/物理预点胶/在线S1/UI/SQL/设备成功；继续分段Wait/Retry/返回故障、预点胶真实下层及S2安全/清零/补偿/UI前提和实际生产循环退出，整体目标未完成。


后续原启用S1分段交互：[12宿主/两轮各121次断言、42标签](native-s1-segment-interaction-progress.json)与[限定报告](native-s1-segment-interaction-review.md)通过。原两基板7实体、22消息在Working/OffLineWork实际Start：每轮5任务4正常完成/1公开WorkStop注入故障；交互Wait因Stop返回false被原IL丢弃，动作仍Success且firstDispense提交；进入pending Wait后Pause，再Set完成仍消费，下一层Pause门才阻塞。原Continue完成首轮7个身份并BondRelease，第二轮公开Stop回调限定运行。原输送控制器Stop守卫则Abort，真实输送任务/转移未执行；完成信号由测试Set，视觉/高度公开预置完成，真实点胶step仍false。24原IL/14原源码哈希、16保真程序集，新111+父5272=5383，正式1328/旧40专题3817/主阅读器89节点101边保持冻结。无生产源码修改/私有写/物理点胶/输送/UI/S2/SQL/在线设备成功；继续真实Retry/返回失败、预点胶下层和S2前提/实际生产退出，整体目标未完成。


后续原S1真实返回失败/单步与finally刷新：[12宿主/两轮各120断言、34标签](native-s1-return-gates-progress.json)及[限定报告](native-s1-return-gates-review.md)通过。真实原点胶直接返回Abort/Fail，原启用离线任务每轮5个中3正常早退/2预期Faulted，未提供虚假返回值。原离线步骤先true再单步等待，原Stop关闭单步标志释放等待为false/Abort；仅公开关闭模式亦使原任务自行Stop。原Off/Off预点胶公开回调Stop使后续WaitStart false/Fail。nonSuccess早退保留前12条完成/当前消息未完成/已提交step、无最终Finish/无BondRelease。原finally刷新槽自然null抛真实NullReference，或公开测试委托throw同实例，原Task Faulted/设备已Stop。公开observer不是真实UI；视觉/测高预置，未物理点胶/胶型取得/插补/SQL/在线设备。26原IL/12源码哈希、16保真程序集；117新增+父5383=5500，正式1328/旧40专题3817/主阅读器保持冻结。Retry实际返回尚未执行；继续原结果处理/重做、预点胶下层、S2前提与实际生产退出，整体目标未完成。


后续原胶检结果映射/重做上下文：[两轮各47不同检查](native-s1-rework-context-progress.json)及[限定报告](native-s1-rework-context-review.md)通过。原PostBondEpoxyCheck以明确null/数量测试输入、真实PR/胶检仓库、公开测试DialogResult映射为Success/Fail/Abort/Retry；非真实UI/相机。原排序三种focus配置各13消息，同一步只有点胶或胶检之一。直接绑定原ReDispense在Framework Dictionary Keys枚举中写回，首步false后InvalidOperation，其余两步true，消息尚未重置；不是先全部重置再SortError。单独原公开SetActionNodeReWork则同一步缺配对SortError、可能先部分提交点胶消息。真实EpoxyApplicationDefect直接调用在原GetHardware实际缺硬件处NullReference，未到映射；原整动作/任务Retry未执行。编译漏命名空间、18检查后错误预期exit1、38检查诊断全部留存，最终2accepted宿主47固定检查/18原IL/9源码哈希/16保真程序集通过。71新增+父5500=5571，正式1328/旧40专题3817/主阅读器保持冻结，无私有消息/源码/硬件替身或UI/SQL/物理点胶；继续真实Retry传播和下层前提，整体目标未完成。


后续原预点胶谓词/板分配/下层失败：[两轮各30不同检查](native-predispense-prerequisites-progress.json)及[限定报告](native-predispense-prerequisites-review.md)通过。BeforeEvery时机单独配置Mode Off不触发，原DoWork Success；原板列优先/耗尽循环/无效Index先提交后越界已验证。真实启用原预点胶先消费位置，再依次因缺坐标系、缺标定点、公开真实SDK坐标及零点fixture下缺Z轴返回Alarm；原输入helper收到真实Alarm后false，来料State保留、设备Working观察，非整任务/物理生产。5原DoWork中1Success/4Alarm，LastDispenseTime保持；4UI Action只收集未执行，DB Lazy未创建，IsAlarm=true直写SQL支路未运行。61原IL中45为静态Xtra重载，18源码哈希/16保真程序集，3次21/21/25检查后exit1及输入保留，最终2accepted各30成功。90新增+父5571=5661，正式1328/旧40专题3817/主阅读器冻结；无私有写/替身/轴/挤胶/UI/SQL/完整构建部署。继续S2原前提、整Retry和生产握手退出、实际标定设备验收，整体目标未完成。


后续原S2吸嘴架/单步/送走信号：[两轮各58不同检查](native-s2-shelf-gates-progress.json)及[限定报告](native-s2-shelf-gates-review.md)通过。原OffLine/Stop未开启单步时仍访问缺AxisY，3原单步等待线程分别Stop/关闭模式得原Abort、Set消费后缺轴异常。12真实槽模型配置检查固定前7槽，非空名字跳过Sensor，短6槽数组越界，实际12个缺Sensor原故障已验证。原SendAway直接绑定Stop不发，Working/Pause均发真实信号；无参Wait重置State，Wait(int)仅消费事件保留State，首次51检查后错误预期exit1完整保留。整任务回零/清零返回pop仅静态IL，ResetBondhead/Modbus/SQL报警未执行，非完整S2或物理输送。31原IL/13源码哈希/16保真程序集，56新增+父5661=5717；正式1328/旧40专题3817/主阅读器冻结，无生产源码/私有写/替身/设备/UI/SQL。继续S2清零/补偿前提、整Retry与完整生产退出、构建设备验收，整体目标未完成。


后续原S2补偿/Modbus前提：[两轮各51不同检查](native-s2-compensation-prerequisites-progress.json)及[限定报告](native-s2-compensation-prerequisites-review.md)通过。原Offline Connect true而真实客户端null，下层两Reset内部重试后自然null异常，读/断开亦故障，无串口/外层SQL报警。原周期用Minutes分量，60分钟fixture不触发/11分钟触发，first绕过；6次原视觉工厂缺硬件故障，DryCycle亦先硬件。真实SDK公开数组下原四点差值只返回X，单点精确0.5允许/超限抛、组合超限返回零；原catch丢异常类型/inner。取片超0.2提示后返回原值，温漂超限抛，NaN继续；两个UI Action只收集，DB Lazy未创建。Scan非first跳过，first缺数组/硬件故障，未Save/Excel；空首扫D盘导出仅静态。诊断50检查通过但错误摘要工厂计数5保留，实际计数6accepted51两轮通过。31原IL/14源码哈希/16保真程序集，53新增+父5717=5770；正式1328/旧40专题3817/主阅读器冻结，无生产源码/私有写/替身/真实设备/UI/SQL。继续S2清零整任务传播及补偿成功前提、整Retry/完整退出与构建设备验收，整体目标未完成。


后续原完整S2单步退出/清零故障：[两轮各70不同检查](native-s2-reset-propagation-progress.json)及[限定报告](native-s2-reset-propagation-review.md)通过。每轮8个真实原任务4预期Faulted/4Stop守卫正常退出；实际待首个单步时Stop或关闭模式让原吸嘴架Abort，任务丢弃后仍执行外层清零，两个Stop模式确实在Stop下清零失败。Modbus/Enable=true及IO/Enable=false自然缺客户端/输出，外层捕获后原Alarm，公开UI callback收集后抛同一fixture异常，SQL之前中断/DB Lazy未创建；不是下层NullReference未捕获，也非正常DialogResult或实际清零/UI/SQL。原Start保持Running任务、空AbortThread无效、Faulted之后Stop下重建正常退出，来料State Set/未放行。18原IL/14源码哈希/16保真程序集，44新增+父5770=5814，正式1328/旧40专题3817/主阅读器冻结。无生产源码/私有写/SDK动作替身或物理清零/串口/轴/贴片/UI/SQL；原任务入口运行但生产循环未完成。继续S2正常清零结果及依赖、输入/补偿/动作/退出、整Retry/完整握手与构建设备验收，整体目标未完成。


后续原S2动作提交/回调边界：[两轮各31不同检查](native-s2-action-boundaries-progress.json)及[限定报告](native-s2-action-boundaries-review.md)通过。每轮9个原排序/公开新TU上下文各19消息，组件/检测/点胶互斥优先；Pick离线Success不提交步骤/回调，Bond离线前缺轴准备失败，AfterBond离线/频率跳过提交步骤但不提交调度消息，实际null刷新及公开Start/Stop故障分别影响提交/末尾刷新。已配置Dip在Stop真实Abort；S2点胶离线IsDoWork=false，明确直接绕过条件调用才验证单步Stop Abort及两个WaitStart Fail，epoxy仍pending，禁用预点胶清manual/时间不变。29原IL/20源码哈希/16保真程序集，72新增+父5814=5886冻结绑定。公开UI收集后抛同实例在SQL之前，未执行UI/SQL/硬件/整生产Task或成功循环，无生产源码/私有写/SDK动作替身。正式1328/旧40专题3817/主阅读器冻结，继续S2成功动作/清零正常结果/真实依赖/整任务与Retry、完整握手、构建设备验收，整体目标未完成。


后续原力控计算/配置/数据：[两轮各46不同检查](native-force-calibration-progress.json)及[限定报告](native-force-calibration-review.md)通过。原forward/inverse与角度/初值、PID排序替换/间隙null、分段阈值实际执行，公开数值样本非物理标定；空forward在意图守卫前异常/inverse999，重复横坐标NaN/非有限未完整拒绝，线性角度不环绕。原SDK两个JSON Save/标定Load真实替换单例，锁定Save普通Exception包装/旧字节保留；原EPPlus两表各6行导出读回，空不建文件/再次同名表异常。两个公开UI Action收集后抛fixture异常/不执行。64原IL含45静态Xtra重载/3物理调用方仅静态，11源码哈希/16保真程序集，75新增+父5886=5961冻结绑定；两次探针预期/Span比较失败保留、明确Linq后重放成功。无生产源码/私有写/硬件/物理标定/UI/SQL/完整Task，正式1328/旧40专题3817/主阅读器冻结。继续实际力控/标定/设备成功链、S2整任务/Retry/握手和构建依赖，整体目标未完成。


后续原生证据源码交接：[独立阅读器](module-source-explorer-native-runtime.html)、[限定报告](native-runtime-reader-review.md)及[进度](native-runtime-reader-progress.json)通过。接入7个已冻结原生报告与240原声明快照，29模块552代表关系不改；保留保真阅读器40专题4757快照JSON值，新视图47专题4997快照，正式主阅读器40专题3817不变。同类型/成员名原IL匹配仅声明候选/同名重载不证明执行，明确显示绑定报告与边界，SDK无源码成员未伪造。63源编码哈希/Roslyn1456声明0语法错，Edge实际导航/检索/深链接/4997精确显示/240边界/四宽度/0浏览器错误；本轮无新生产运行。82新增+父5961=6043冻结，未改生产源码/原生报告/旧阅读器/原模块关系；全部业务/动态调用/设备/Build/部署与交接验收仍待完成，整体目标未完成。


后续原点胶编辑器曲线/模板：[两轮各50不同检查](native-dispense-geometry-progress.json)及[限定报告](native-dispense-geometry-review.md)通过。原内部Utility绑定原delegate、Curve真实GDI几何/屏幕缓存清零及public factory更新/部分异常，原数据数组复制/Bitmap共享/live矩阵短setter部分提交；正常控件随后UpdateAllCurves已静态核对，不等同实际UI坏。实际原PatternFile/厂商SXml两XML一BMP读回，HeightMeasurement丢失、锁XML时BMP已写蓝、缺BMP Read返回null、读入图像锁临时文件吞删除异常/调用方Dispose后清理均实测；两轮文件SHA一致。61原IL含7UI方法仅静态/15源码哈希/16保真程序集，68新增+父6043=6111冻结。初编译失败/零emit跳过及探针typed静态delegate初始化启动fatal保留；迁入Run后两轮成功，不声明唯一缺程序集。无生产源码/私有写/SDK算法替身/实际编辑UI鼠标/生产运动设备/SQL，原82文件模块/整体目标未完成；旧主及47专题4997独立阅读器不改。


后续原点胶控件：[两轮各35检查](native-dispense-control-progress.json)及[事件边界报告](native-dispense-control-review.md)通过。真实STA构造原DevExpress控件，无Handle/显示窗口或真实/模拟鼠标；原变换入口实际重建全部屏幕端点，SetFigure无事件/导出过滤，尺寸与scale转换、删除非当前早期项索引越界、公开回调抛错时已提交状态及原PaintCurveHandler.SetMode/ActionChanged前后两次均验证。43原IL/11源码/16保真程序集，52新增+6111父=6163冻结。首轮设计器尺寸506误作运行尺寸590的探针断言失败已保留，更正为公开明确Size后两轮成功；无生产修改/私有写/设备/SQL/原完整Task。本轮没有进行可视绘制和鼠标验收，模块及整体目标未完成，旧主与47专题4997阅读器保持。


后续原点胶绘制：[两轮各42检查](native-dispense-rendering-progress.json)及[背景/预览/释放报告](native-dispense-rendering-review.md)通过。原STA控件OnPaint真实绘制背景居中/scale/Append平移/RotateAt、Curve当前红/其他蓝/隐藏，原SaveSnapshoot14PNG每轮完整SHA匹配。清背景null后缓存仍旧图/Resize更新、公开Paint先于背景及回调部分像素、stale索引先画其他后fault、小尺寸null背景/preview故障、die文件尺寸不乘scale/截断/锁写/0维失败均复现。原替换Bitmap已Dispose，旧Matrix和选定内部Bitmap/Matrix/Pen/Brush在Control.Dispose后仍可用；仅只读持有观察，探针明确清理，未测持久泄漏或全资源所有权。45原IL/6类型/12源码/16保真程序集，163新增+6163父=6326冻结，1编译零emit和4探针预期失败全部保留。无Handle/显示窗口/真实或模拟输入/设备/SQL/生产修改；模块及整体目标未完成，旧主和47专题4997阅读器保持。


后续原点胶输入语义：[两轮各44检查](native-dispense-input-progress.json)及[七类原处理器报告](native-dispense-input-review.md)通过。通过11封闭原方法传入构造Mouse/Key事件对象，合成事件确实执行、无OS输入/Handle/窗口/实际用户交互；Paint/Insert吸附后端点与事件raw坐标不一致，Append报告提交点，Move回调失败保已移点/省后通知，Erase回调候选未复位允许二次up，空curve使Append动作已提交后fault、比例下逻辑hover扩宽、Right down启动Translate、0滚轮放大/Zoom越16、ESC字符与keydown区别均复现。84原IL含3Form Set/Get仅静态旧尺寸/未SetDefaultValues线索，22源码/16保真程序集；54新增+6326父=6380冻结，无失败候选/生产修改/私有写/设备/SQL，原Form参数桥及整体目标未完成。旧主及47专题4997阅读器保持。


后续原窗体/ZX2200数据桥：[两轮各40检查](native-dispense-form-progress.json)及[限定往返报告](native-dispense-form-review.md)通过。真实原Form×2/Uc构造，Set/Get默认参数丢失但逐点测高保持、隐藏列不清标志，旧尺寸SetContent及原Load修正分别实测，显式刷新与旧表行/部分输入故障区分。原ZX转换float×1000/int截断/glue反转，反向EndSpeed-Z-Name-Index-Type丢失/Acc覆盖Dec，清列表后fault/首曲线部分提交，原仓库BinaryFormatter clone预处理及Uc忽略返回均实测。34IL/2程序集含3modal入口仅静态，19源码/1resx/16保真程序集；64新增+6380父=6444冻结。首次默认SingleDot策略探针预期失败/初SDK clone匹配错误输出保留纠正；无ShowDialog/Handle/窗口/OS输入/设备/SQL/生产修改/私有写。全编辑Retry/模板管理及整体目标未完成，旧主及47专题4997阅读器保持。


点胶原生报告源码交接：[派生阅读器](module-source-explorer-native-dispense.html)、[限定报告](native-dispense-reader-review.md)及[进度](native-dispense-reader-progress.json)通过。接入几何/控件/绘制/输入/窗体5份原报告260段声明，派生视图52专题5257快照、12原生专题500边界提示；29模块552代表关系及旧47专题4997视图全部保留。同类型/成员名/泛型/重载候选不证明执行，输入报告窗体静态与新窗体报告实际Set/Get分别标注；弹窗3入口仍静态IL。41源编码哈希/Roslyn567声明含6运算符0语法错，267所选IL均有声明候选但不是精确语义/运行覆盖。Edge8次检索选择/深链恢复/5257精确源码/500边界/四宽度/0错误；验证脚本两处错误断言候选保留并按原声明/IL修正，无生产修改/新生产执行。91新增+父6444=6535冻结；全部业务/动态调用/设备/Build/部署与交接验收仍待完成，整体目标未完成。


原点胶策略/数值/模型提交补证：[两轮51不同检查](native-dispense-policy-progress.json)和[限定报告](native-dispense-policy-review.md)通过。原SingleDotOnly/Drawing/Printting三种纯预处理实际执行，BinaryFormatter深克隆/三角旋转/全曲线边界、空首曲线包含零/退化NaN清理及旋转再污染、非正默认100/1000与百分比无守卫已观察；未执行物理策略。原模型先提交所有零值100/100/10再范围检查，helper速度10000对模型1000，末点/单点范围跳过与NaN接受、null后段部分修复已验。5原UI Actions公开收集/不执行，分发异常保持修复；原旧静态Interpolation及安全门有效IL无call/直接Success或return，不是真正控制器运动。60原IL含45静态提示重载和3静态调用方；控制器闭包保存clone/Uc pop仅静态。本轮12源/16保真程序集，59新增+6535父=6594冻结；失败计数/重放引用/预检候选保留修正，无生产修改/私有写/设备/UI/SQL/完整Task或Build。52专题5257阅读器未改，完整语义/交接/现场验收待完成，整体目标未完成。


原真正点胶控制器入口补证：[两轮40不同检查](native-dispense-controller-progress.json)及[限定报告](native-dispense-controller-review.md)通过。真实System1Domain控制器/模块、公共原SDK坐标/标定/原仓库点胶头下，每轮10次InterpolationApplication：9Fail/1原提示公开分发异常，10真实UI Actions只收集不执行。缺坐标→标定→选定点胶头→空列表末尾缺Z、null克隆/列表/点、空曲线索引与配置蘸胶T先行失败均实测，尚未创建压力Task。坐标parented90度/往返、未接父级忽略自身、重复名第一项及针/传感器偏移已核；直接坐标不检查示教就绪。Offline随机/安全移动跳过与DryCycle真实缺轴、激光跳气缸后缺Z、链接压力包装丢inner/阀IO/群组/蘸胶盘缺依赖实测；4声明12/15/16/19名称重复相机且漏T轴。99原IL含45提示重载及压力闭包静态；24源/16保真程序集，无源码/私有写/硬件替身/运动/SQL/完整Task/Build或成功制程。59新增+父6594=6653冻结，旧52专题5257视图不变；完整语义/交接/设备验收待完成，整体目标未完成。


全原工程符号/静态关系增量：[16工程两轮32次提取](original-semantic-graph-progress.json)及[报告/查询入口](original-semantic-graph-review.md)通过。1410原Compile保真语义绑定、26原排除文件只语法；29764声明、384201操作边（含3252属性元数据）、4581类型/成员关联，5187跨源工程精确目标。17518虚调用声明目标/546委托运行目标未解析。6图原字节一致、10图仅编译警告排列不同，完整诊断排序后16图均一致。查询已核真正控制器完整正文、原泛型Clone/Point2D运算符，旧552业务关系/52专题5257视图不改。1982新增+父6653=8635冻结；完整业务解释、动态连接、派生交接接图与构建/设备仍待验收，整体目标未完成。


语义图降级边界：本图收录遍历可见IOperation中的上述目标，没有做完整IL降级补全。foreach的GetEnumerator/MoveNext/Dispose、using隐式Dispose、await/async状态机及其他编译器生成调用不能据此图断言已完整列出；属性引用也没有自动扩展成全部访问器调用路径。静态图定位和已执行原生报告是不同证据范围。


完整源码/静态符号/报告交接增量：[新离线阅读器](module-source-explorer-semantic.html)、[进度](semantic-source-reader-progress.json)及[限定报告](semantic-source-reader-review.md)通过。1436完整文件/1410Compile语义/26排除只语法，29764声明/384201操作/4581声明关联接入；旧29模块552业务关系与5257快照原值保持，新增策略/控制器2报告154精确程序集/签名快照，共54专题5411快照654提示。159选定IL中4无原构造声明/1压力闭包单列，5377源码范围/2排除/32非C#证据分类；静态与运行覆盖不混淆。Edge实际所有源码/快照/提示/1436文本SHA、直接链/重载/泛型深链/报告双向导航/四宽度通过，无网络或错误。62新增+父8635=8697，1464既有冻结副本复用不增数。完整业务/动态关系、完整构建和真实设备验收仍待完成，整体目标未完成。


委托注册/传递/调用增量：[报告](delegate-provenance-review.md)与[进度](delegate-provenance-progress.json)通过。16工程1410Compile两轮32静态提取10967记录，546原调用位置逐条一致，75接收符号中27有直接源码注册候选/161调用；不等于运行目标解析。启动异常/线程入口、PR静态存图注册/3调用、MainForm静态UI字段实例PostAction/两个Show捕获lambda/Control.Invoke源码连接已核。发现2441匿名函数中2194落在351组非唯一Roslyn文档签名，新委托证据以文件/span隔离；冻结旧完整图/阅读器匿名owner仍待另建派生修复，不能按共享旧签名认定唯一链。25合成守卫、来源/CLI/父绑定通过；249新增+8697=8946，1818复用不增数。生产源码未改/未运行，业务/运行时动态/完整构建/设备验收仍待完成，整体目标未完成。


完整图/阅读器匿名身份派生修复：[新离线页](module-source-explorer-lexical.html)、[报告](lexical-source-reader-review.md)与[进度](lexical-source-reader-progress.json)通过。16工程32分析、384201原操作/29764声明/4581关联逐值保持；351旧身份组2194匿名方法按源span隔离，完整2458匿名方法/14903操作/138嵌套父及546委托主身份核对。比委托专项2441多17表达式树lambda，逐个源码/包含签名已解释，未执行SQL。源符号33955/总38760；1436文件/5411旧快照原值/654提示/2458匿名视图/全部文本SHA、匿名深链/四宽度浏览器通过。166新增+8946=9112，1869复用不增数。旧图/页保持历史归并限制，新派生图/页已修复；完整业务、动态、构建和真实设备验收仍待完成，整体目标未完成。


原虚/接口源码候选连接：[报告与CLI](virtual-dispatch-provenance-review.md)、[进度](virtual-dispatch-provenance-progress.json)通过。16工程32分析完整匹配17518旧虚调用及独立匿名owner，1179实际源码类型约束675集合/3257候选行；710处有仓库类型候选，455处有索引源码方法，均非运行目标解析。FindModel4调用/30方法、ActionNode.DoWork2/39、Confirm2/20和PREntity.DoWork97/1的原位置/候选完整声明已核。普通转换前界限/new槽/接口/泛型/变体24守卫、五步来源/重放/父绑定通过，16完整诊断排序后相同/4原字节相同。362新增+9112=9474，1847复用不增数；反向依赖/SDK/插件/实例/泛型替换仍有限，阅读器候选接入待办。生产未改/未运行，全部业务、动态、构建和真实设备验收待完成，整体目标未完成。


虚/接口候选源码浏览交接：[新离线页](module-source-explorer-dispatch.html)、[报告](dispatch-source-reader-review.md)与[进度](dispatch-source-reader-progress.json)通过。全部17518原位置、675集合/3257候选行和35036入向/出向候选按钮接入；518行有原声明、2739元数据方法明确无源码。295目标/360方法/1053类型反向登记与原直接入向边分开，8个所需引用符号追加，总38768；全部既有payload/384201操作/29764声明/4581关系和5411快照原值保持。Edge实际全调用/候选/1436全文与文本SHA/2458匿名/654提示、导航/分页/候选深链及四宽度通过。39新增+9474=9513，1855复用不增数；阅读器候选接入已完成，实例配置/泛型/运行派发仍未解析，业务/构建/真实设备与整体目标未完成。


原算法实例选择补证：[两轮163项](native-algorithm-selection-progress.json)与[报告](native-algorithm-selection-review.md)通过。30原枚举各创建普通/null名字对象、3未知枚举fallback及实体/公开替换，每轮65个真实算法对象；工厂类型与AlgFlowType默认Fast不同，命名PREntity实际Xld但查询Fast，SetFast原同标签守卫true且保留Xld，公开CircleFind替换/只改标签亦实测。30FindModel覆盖仅反射/源码对应，未调用算法/VM；两轮16保真原程序集、69声明37文件/44IL与三个验证步骤通过。准确任务选择目标为Main.Machine.Process.S1/S2ActionNodeController，非同名旧服务，节点选择仍静态。96新增+9513=9609，212复用不增数；整体业务、不同标签/流程初始化、实际任务、构建/UI/SQL/设备与整体目标未完成。


原S1/S2消息选择增量：[两轮5655项](native-action-selection-progress.json)与[报告](native-action-selection-review.md)通过。准确主程序控制器公开Init各八排序、16计划/848条消息及848次重复请求/轮，实际34注册节点中选择26种原接收者，真实2×2树上下文；没有私有消息写入，Finish由宿主公开方法推进，未执行节点DoWork/生产Task。缺失名返回null留未完成消息、重名取首实例、S2未匹配层级留旧指针及名字转换读原current已实测。95原声明59文件、161静态IL、16保真程序集各轮及四步父绑定通过。50新增+9609=9659，260复用不增数；其余组件/浸胶/校正/分段选择、实际任务及PR/SQL/构建/UI/设备与整体目标未完成。


原组件配方与完整注册选择：[两轮31655项](native-recipe-action-selection-progress.json)及[报告](native-recipe-action-selection-review.md)通过。8真实组件SDK保存重载、64个S2/24个S1计划，5888消息/轮实际选择全部34种注册接收者；5376重复请求，512校正重复提示未执行。真实浸胶前后/禁用组件/未知枚举/Null哨兵和分段差异核验，原Interactive仅五次无传料短DoWork及开始/停止事件异常；其他节点DoWork/生产Task仍待验收。102声明65文件/544静态IL、两轮各16保真程序集及五步父绑定通过。75新增+9659=9734，275复用不增数；下一步节点条件/非设备执行与任务等待/Retry/Pause/异常链，PR/SQL/构建/UI/设备及整体目标未完成。


原注册节点前置条件：[两轮584项](native-node-preconditions-progress.json)及[报告](native-node-preconditions-review.md)通过，每轮544次IsDoWork调用覆盖34种注册类型、15种公开状态与34次公开载具移除。S2仅贴片测高守卫差异、17次载具移除异常/16种下级缓存接受，以及原Pick离线返回跳过事件和状态已实测。146声明71文件/35静态IL及六步父绑定通过，102新增+9734=9836，283复用不增数。其他节点DoWork/原Task/设备与整体目标未完成。


原S1实际Working循环：[两轮126项](native-s1-task-loop-progress.json)及[报告](native-s1-task-loop-review.md)通过，每轮13真实Task（11完成/2故障）、317次动作尝试覆盖9种类型；8排序各45消息/31动作/14跳过。正常周期发信号、Pause→Stop多执行一个节点、活跃Abort失败和公开事件故障后仍Working/当前未完成已实测。151声明74源/52静态IL与七步父绑定通过，170新增+9836=10006，288复用。限定离线/关闭定位/空测高配置；真实点胶/检测、S2成功Working/运行重试及整体目标未完成。


原S1真实点胶步骤提前提交：[两轮85项](native-s1-step-commit-progress.json)及[报告](native-s1-step-commit-review.md)通过。每轮12次原点胶/6次Off预点胶、4个真实Task（2完成/2故障）及12次原关闭查询；Abort/Fail前已置步骤完成，单步等待忽略Stop/公开关闭单步才退出、finally委托故障覆盖返回、关闭查询排除活跃未配置S1或接受Faulted均实测。162声明82源/47静态IL、八步父绑定通过，90新增+10006=10096，301复用。真实业务/原Machine.Stop释放等待/重启返工、设备与整体目标未完成。


原S1停止与返工恢复：[两轮51项](native-s1-stop-recovery-progress.json)及[报告](native-s1-stop-recovery-review.md)通过。每轮6个真实Task（5完成/1故障），原Stop实际释放单步等待；消息返工/注入/结束保留提前提交步骤，两个重启跳过业务DoWork便发传料信号；原SetProcessUnable恢复条件后Fail再次提交。原ReDispense辅助方法0/1/3键直接调用，非空字典首键重置后枚举异常、后续消息返工未执行，不算检测DoWork或返回Retry。165声明82源/54静态IL，九步父绑定通过，68新增+10096=10164，306复用。真实业务/设备及整体目标未完成。


原S1完整胶检节点：[两轮109项](native-s1-defect-outcomes-progress.json)及[报告](native-s1-defect-outcomes-review.md)通过。每轮十五次真实原DoWork、三个实际Task（1完成/2故障）；声明WithReferenceSearch与999绕过检测仍返回成功并提前提交。缺失配置原catch/Show/Alarm经公开调度夹具抛异常，finally可覆盖，Task故障仍Machine Working而关闭查询接受。原结果处理器16次/2次Retry为公开回调夹具结果，完整返工调用者实际空硬件先失败；不算生产Task Retry。179声明92源/61静态IL三程序集，十步父核验；86新增+10164=10250，321复用，旧1328保持。真实业务/设备及整体目标未完成。


原检测配置持久化与就绪：[两轮108项](native-inspection-readiness-progress.json)及[报告](native-inspection-readiness-review.md)通过。每轮原Add12/Save2/Load3/Remove2及原PR JSON，12行就绪矩阵、3次重载完整胶检DoWork，无生产Task。S1门不查检测，流程门仅S2；示教与编辑门分离，禁用外配方仍全局查找并执行模式缺口；缺失名称清理使就绪false/true/false。191声明98源/94静态IL三程序集、十一项父核验；94新增+10250=10344，332复用。整Machine.Start/回零SelfCheck/匹配PR复制与真实业务仍待验收，整体目标未完成。


原S2就绪：[两轮56项](native-s2-readiness-progress.json)及[报告](native-s2-readiness-review.md)通过。完整离线S2 CheckIsReady、13双门矩阵、12拒绝/恢复门；未示教未知检测模式与外配方配置仍通过。多工具SelfCheck误绑定LanguageExt.Option.Count，只计0/1，而GetToolOnBondhead实际拒绝相同状态。213声明112源/69IL含真实SDK，十二项新旧核验；111新增+10344=10455，348复用。生产Task/DoWork零次，完整真实业务与设备仍待验收，整体目标未完成。


原载具就绪：[两轮100项](native-carrier-readiness-progress.json)及[报告](native-carrier-readiness-review.md)通过。真实料架/静态盘解析与载具typed JSON重绑定、40力值/18IPT标定矩阵；NaN、未知力模式、零标定项、零拍照点位与未示教配置仍可就绪，IPT force-use漏检/误拒绝已证；缺失/空槽/错误子类型路径差异保留。228声明124源/85IL、十三项新旧核验；89新增+10455=10544，362复用。生产Task/DoWork零次，整启动/真实业务与设备待验收，整体目标未完成。


原整机环境：[两轮123项](native-machine-environment-progress.json)及[报告](native-machine-environment-review.md)通过。64组合确认六层首失败顺序、16晶圆选项/8初始化标志及实际信号复位；18信号复位、5保留。原私有启动先D盘清理，再无条件轴复位检查；门传感器先于配置判断，完整启动仍待验收。243声明135源/116IL、十四项新旧核验；141新增+10544=10685，375复用。生产Task/DoWork零次，整体目标未完成。


原任务关闭：[两轮310项](native-machine-task-closure-progress.json)及[报告](native-machine-task-closure-review.md)通过。原16任务持有者256行公开CLR状态夹具矩阵仅Running拒绝，等待/失败/取消均接受；8实际原S1 Task/轮，7完成1故障，配置关闭隐藏真实Running任务、Faulted时Machine仍Working，Start替换非Running任务及活任务Dispose失败已实测。249声明141源/126IL、十五项新旧核验；76新增+10685=10761，383复用。完整启动/业务/设备待验收，整体目标未完成。


原S2任务入口：[两轮497项](native-s2-task-entry-progress.json)及[报告](native-s2-task-entry-review.md)通过。122原任务/轮20Stop完成102首步故障；5模式6状态×Enable/ToolBank共120行及2真实暂停任务，离线亦查真实缺失吸嘴架轴，Enable/ToolBank不拦首步。空AbortThread不取消暂停；10运行标量重置、11保留，计时器StartNew返回丢弃，排程保持。257声明147源/137IL、十六项绑定；96新增+10761=10857，391复用。节点DoWork零次，完整任务业务/设备待验收，整体目标未完成。


原Flip/Slide入口：[两轮487项](native-aux-task-entry-progress.json)及[报告](native-aux-task-entry-review.md)通过。106原任务/轮7完成99故障；Flip先回零无离线/配置/Stop门，Start先提交Working；Slide在线先缩回故障，离线无蘸胶6真实等待Stop释放，配置异常早于Running门且关闭查询仍拒绝运行任务。原日志队列500满时Working已提交但任务未建，封闭队列异常同样留Working。263声明153源/154IL、17项绑定；117新增+10857=10974，399复用。完整业务/设备待验收，整体目标未完成。


原晶圆/传输入口：[两轮660项](native-wafer-transport-entry-progress.json)及[报告](native-wafer-transport-entry-review.md)通过。每轮434原启动捕获任务完成，40显式宿主原晶圆方法任务35完成5故障，175个Init子任务仅IL推算。在线28启动故障早于状态/任务，离线7任务真实创建并Stop释放；LoaderBin活性查询错查皮带，出料传感器早于NoMaterial保护门，Dry重启TU先于Running门重建。289声明177源/200IL，18项绑定；191新增+10974=11165，425复用。完整业务/设备待验收，整体目标未完成。


原Loader/Unloader入口与重置：[两轮773项](native-loader-unloader-entry-progress.json)及[报告](native-loader-unloader-entry-review.md)通过。90原Task/轮82完成8故障，2通用Running夹具另计；Pause启动直接终结，Working先读料盒传感器、catch后留Working。原重置内存先提交、锁定实际Save失败保留磁盘旧值，4次解锁保存重载通过。300声明188源/260IL，19项阶段绑定；216新增+11165=11381，438复用。完整业务/设备待验收，整体目标未完成。


原料仓握手与编辑聚合：[两轮834项](native-bin-handshake-readiness-progress.json)及[报告](native-bin-handshake-readiness-review.md)通过。53原Task/轮51完成2故障；仓首步失败后25输送任务有限等待并Stop释放，4许可异常路径跳过复位/移动确认。128真实三仓库依赖组合及8实际程式重载复现编辑聚合反向返回，不是整机SelfCheck。310声明198源/292IL，20项阶段绑定；93新增+11381=11474，450复用。完整业务/设备待验收，整体目标未完成.


原进出料握手：[两轮550项](native-inout-handshake-progress.json)及[报告](native-inout-handshake-review.md)通过。490直接helper和40原接口/轮，6原拓扑加999，28原Task/轮22完成6故障。SMEMA缺失与记忆门先后、Exception原父任务重复调用、公开分派故障及原共享UiLock阻挡已补证。310声明198源/306IL，21项阶段绑定；148新增+11474=11622，452复用。整机六门没有直接输送检查；完整生产就绪/业务/设备待验收，整体目标未完成.


原输送配置与整机环境组合：[两轮3141项](native-transport-environment-progress.json)及[报告](native-transport-environment-review.md)通过。1792配置行原六门通过，512首失败行与父证据相同；336状态/拓扑/启用行及8重载后原域入口返回无异常但未建业务Task。每轮2649环境/344域/7直接前置调用，176模组Init子任务880由原IL推算且未捕获句柄。310声明198源/306IL，22项阶段绑定；177新增+11622=11799，457复用。完整生产就绪/业务/设备待验收，整体目标未完成.


运行中原任务程式重载：[两轮93项](native-recipe-live-reload-progress.json)及[报告](native-recipe-live-reload-review.md)通过。四行实际重载保留五个Running输送Task；每轮12帮助调用、28原Task（26正常/2调度夹具Faulted），前四单例可在晶圆Save失败后部分提交。域基础缓存保留首次A；S1停止入口重建表，S2保留旧表/实体。320声明207源69IL，23阶段绑定；166新增+11799=11965，436复用。真实UI/完整生产链待验收，整体目标未完成.


原界面离线配方重载：[两轮48项](native-recipe-ui-reload-progress.json)及[报告](native-recipe-ui-reload-review.md)通过。真实控件每轮6次重载（4成功/2晶圆保存失败）；保存失败先提交4单例并保持界面禁用，解锁程序化重试恢复。真实Load1、原刷新登记1已删除；SDK基础线程句柄/正常停止未捕获。346声明230源111IL，24阶段绑定；414新增+11965=12379，461复用。精确SDK23/补充16/缺1；完整UI/在线VM/设备SQL生产链待验收，整体目标未完成。


原界面取消/任务关闭恢复：[两轮572项](native-ui-stop-recovery-progress.json)及[报告](native-ui-stop-recovery-review.md)通过。每轮261取消/离线Stop、570刷新，256持有者行225恢复31等待；实际S1配置关隐藏仍Running任务，再开不重新禁用，公开回调故意Faulted后恢复。4配方Save失败行中，Stop+遗留停止提示可恢复UI但仍部分提交/Pr=false。6状态12转换，Operate/Teaching/Preparing保留原按钮状态；次加载按钮为空，主模态加载未运行。346声明230源125IL，25阶段绑定；155新增+12379=12534，481复用。完整交互/生产链待验收，整体目标未完成。


原配方模态对话框：[两轮89项](native-recipe-dialog-events-progress.json)及[报告](native-recipe-dialog-events-review.md)通过。每轮12原SDK选择器+1名称提示，11加载尝试/9尾订阅/2原Save异常，1新建取消；5原重载中2明确私有重试。配置内存/磁盘/程序部分提交及同ID跳过复现；5调用者Dispose缺口公开清理。私有STA桌面原输入Default不变/线程结束/CloseDesktop成功。原SDK刷新每轮因独立MainForm.MF=null抛1次原NullReference，公开Framework观察仅控制错误弹窗呈现，完整主窗体未验收。27JSON24字节一致、6截图已查看，346声明230源142IL，26阶段绑定；382新增+12534=12916，482复用。新建/拷贝确认和完整生产链待验收，整体目标未完成。


原新建/拷贝确认：[两轮163项](native-recipe-create-copy-progress.json)及[报告](native-recipe-create-copy-review.md)通过。每轮14原SDK选择器+5提示+9真实Yes/No确认，9原随机Guid/日期新记录，2公开源夹具，最终14条；4完整目录拷贝、1残余目录、2无目录配方。PR回调在SDK copy catch外，2原按钮异常用公开Cancel退出；3原调用者Save异常中列表为IOException且Dispose已执行。74JSON语义比较44字节一致，备份bound4/replay3及原SDK刷新故障bound3/replay4均保留原差异；10原生截图已查看。348声明231源201IL/8程序集，27阶段绑定；735新增+12916=13651，484复用。完整MainForm/PRVM/设备SQLBuild部署待验收，整体目标未完成。


原主窗体上下文：[两轮40项](native-mainform-context-progress.json)及[报告](native-mainform-context-review.md)通过。原正常MainForm构造/Load、在线未复位门、离线DataLoad/ChangeData和两个Modbus离线入口、真实MF赋值与原PostAction、SDK激活主模块及实际标题刷新已运行，SDK界面异常0/轮。公开共享ThreadFlag先false等机器线程Join再true运行SDK刷新，清理后false；机器监控循环0，SQL/存图消费者未启动。每轮28文件=10可解析JSON+17原空仓库文件+1时间备份，8可解析JSON字节一致；8截图已查看，1920×999控件图可见资源，1552×832整窗体文档区域未捕获，布局未验收。354声明236源码225IL/8程序集，28阶段绑定；554新增+13651=14205，490复用。6失败候选及两轮39项初稿保留，生产关闭链通过公开Dispose跳过；整Program/PRVM、监控消费者、设备SQLBuild部署待验收，整体目标未完成。


原PR初始化失败边界：[两轮31项](native-pr-init-boundary-progress.json)及[报告](native-pr-init-boundary-review.md)通过。29项阶段绑定；每轮3原Task全部Faulted，真实缺失C:ModulePathGenerate.txt，原通用加密狗提示3次；false/false/true前值失败后保留，原Program.Main IL丢弃返回Task。托管SDK初始化已尝试，本机API和算法未到达。357声明239源码230IL/8程序集，补捕获lambda1独立标注；6原生截图已查看，8实际SDK身份/路径/字节另绑。241新增+14205=14446，496复用。1准备失败候选无CLR、1只读路径断言草稿保留；成功VM、关闭保存链、监控消费者、设备Build部署待验收，整体目标未完成。


原关闭保存及真实退出：[两轮60项](native-mainform-close-save-progress.json)及[报告](native-mainform-close-save-review.md)通过，每轮正常29＋晶圆占用31，共4独立进程。Working的Yes／No均先退出确认再停止提示并取消，StopNo不保存，StopYes原DataSave→Environment.Exit(0)。正常28→44文件，16新增19改变，17空仓库变真实JSON；首晶圆Save失败仍退出0，28文件SHA无变，后续保存跳过。RecipeList与ProcessDomain修改未保存。26截图3字节等价代表已查看；公开FormClosed后置订阅0由原处理器先退出所致，Host返回／wrapper Join／CloseDesktop／Dispose未到达。357声明239源236IL/9程序集，4声明7IL日期来源运行后独立补证；30阶段绑定，372新增+14446=14818，498复用。离线无硬件消费者，整UI、VM设备Build部署仍待验收，整体目标未完成。


原退出与存图／统计消费者：[两轮25项](native-exit-consumer-pending-progress.json)及[报告](native-exit-consumer-pending-review.md)通过，31阶段绑定。每轮4096原生产者位图入队，原消费者写盘并释放首图；原StopYes关闭时存图和统计线程仍活、队列尚有2699／2803采样项，最终仅1457／1341完整BMP，2639／2755未形成文件，原退出未等图片排空。统计线程仅消费500未知对象／轮，SQL Lazy与SDK初始化false；公开ThreadFlag=false不停止两个消费者，监控仍0。所有2798BMP独立核对头和像素字节，采样／磁盘时点差异与数量变化原样保留，不作现场丢图率。358声明240源243IL/9程序集，42JSON语义／38字节一致；3028新增+14818=17846，503复用。旧1328独立，1只读语法初稿保留；正常监控、已识别SQL日志、整UI／设备Build部署待验收，整体目标未完成。


原正常监控与消费者：[两轮40项](native-monitor-consumer-startup-progress.json)及[报告](native-monitor-consumer-startup-review.md)通过，32阶段绑定。原MainForm离线Load自动启动监控及两消费者；每轮16真实Bitmap保存／Dispose、500普通对象取走而SQL初始化false。两个监控时代各观察起点后至少两次耗材List重建，合计至少4循环；125顺序Start守卫保留活线程，false／Join后重启新监控仍保留消费者。两监控均Join后两个消费者仍活，真实StopYes退出0。360声明242源263IL／9程序集，运行后监控lambda另捕1方法1程序集；32BMP逐文件检查，42JSON语义38字节一致。449新增+17846=18295，506复用；两轮40项观察起点初稿独立保留，原代码未改，旧1328独立。在线告警／SQL／整UI／VM设备Build部署待验收，整体目标未完成。


原主窗口合成截图与布局：[四轮47项](native-mainform-layout-progress.json)及[报告](native-mainform-layout-review.md)通过，33阶段绑定。原HWND的12张PrintWindow合成图包含真实SDK文档，28PNG／12独立SHA代表全部已查看；原DrawToBitmap仍遗漏SDK表面。默认和公开原Program.Main样式夹具均复现96DPI文档最小1920×999超出客户区1536×793，TU／Wafer底部及右侧裁切，客户区布局未验收。原Designer2194×1284经8×18→7×14字体缩放解释实测尺寸；源码／IL一致、原Bounds及MinimumSize未改、原Program.Main未运行。360声明242源263IL／9程序集，410新增+18295=18705，507复用。一个46项初步进程与四只读校验初稿保留，旧1328独立。正常监控／退出证据保持；布局修复、在线／SQL／VM设备Build部署待验收，整体目标未完成。


原Program.Main真实离线入口：[两轮41项](native-program-main-entry-progress.json)及[报告](native-program-main-entry-review.md)通过，34阶段绑定。原private入口在STA主线程1真实执行首次版本0→1.5保存／模态、设备身份保存、原字体皮肤／日志／Harmony／PR图像委托及实验日志、Application.Run／正常MainForm.Load监控／两空消费者、SDK文档和标题刷新、原StopYes保存并Exit0。三个后台线程仍活、ThreadFlagtrue，原Mutex.ReleaseMutex与宿主返回未到达；原生父启动器指定私有桌面后等待退出并CloseDesktop成功，输入Default不变。互斥ProductName／EntryAssembly／配置属宿主，不作原EXE部署验收。365声明246源278IL／9程序集，42JSON语义37字节一致，9精确时间字段；原UI处理器覆盖宿主观察器，回调未插桩。六PNG三代表实际查看，原入口96DPI裁切仍存在。401新增+18705=19106，512复用；五失败候选与三失败只读校验器保留，旧1328独立，整体目标未完成。


原工程MSBuild实际构建：[两份隔离副本40次Build](native-msbuild-build-progress.json)及[报告](native-msbuild-build-review.md)完成结果核验，每轮16工程仅SoftKey成功、4种解决方案配置均失败；旧csc不接受latest、LC.exe缺失、DevExpress资源类型解析失败可复跑。原3,023输入含1,436源保持字节，614证据绑定；框架属性文件及TEMP/TMP已隔离。旧共享临时目录40次候选保留；ToolsVersion15的预处理失败与实际Build自动按4.0执行分开记录，.NET4.8引用程序集缺失在本工具中是MSB3644警告。SoftKey两个EXE元数据一致但MVID/SHA不同，32位标记与架构/版本警告保留，未执行或部署；Fody/PostSharp/缺失Parameters工程及未选中Build的安装工程仍待完成。来源台账19106和正式1328不变，本诊断不增加业务计数，整体目标未完成。


后续原主窗体客户区矩阵：[两轮每轮71项、6种尺寸](native-mainform-viewport-progress.json)及[报告](native-mainform-viewport-review.md)通过。原文档固定1920×999、AutoScroll=false；96 DPI观察客户区1536×793稳定右溢出384、下溢出206，1024×600时右896、下399；两轮几何与PrintWindow PNG哈希一致。1920以上请求受当前桌面工作区限制为1540×846，不能替代目标设备屏幕验收。测试只改公开Form客户区尺寸，没有修改生产源码、DPI、最小尺寸、滚动、Program.Main、设备、SQL、图像消费者或业务任务；因此证明当前配置裁切，未修复界面。来源台账19106、正式1328和前轮18705独立，整体目标未完成。


后续原SetupZX2200.vdproj部署清单：[465个File项只读核验](native-setup-vdproj-progress.json)及[报告](native-setup-vdproj-review.md)完成。原安装项目含393个当前工作区存在项、72个缺失项、195个依赖项，LaunchCondition为.NET Framework 4.7.2且禁止更高版本；缺失项主要为VisionMaster/VM/Apps/MVD外部程序集。原解决方案四种配置均未给Setup项目Build.0，ProjectOutput为空；未生成MSI、未写注册表、未安装。构建、外部依赖和现场部署仍待完成，整体目标未完成。

重复启动入口已补充：[native-program-main-entry-duplicate-progress.json](native-program-main-entry-duplicate-progress.json) 通过隔离私有桌面实际持有 Application.ProductName 互斥体，观察原 #32770 消息框、WM_CLOSE 和 Environment.Exit(1)；生产源码/工程/SDK未改，完整部署与29组验收仍待完成。

当前安全门暂停链复跑：[safety-door-pause-current-progress.json](safety-door-pause-current-progress.json) 在当前源码树重新执行 S1/S2/单步三条真实 Signal 链，共 98 项通过；设备、生产 Framework 宿主、完整并发和现场传感器仍未验收。

16项源码产物依赖/API闭包核验已完成：[进度](original-source-artifact-reference-closure-progress.json)及[报告](original-source-artifact-reference-closure-review.md)。对16个独立发射物核对254个AssemblyRef和15条产物间引用边，缺失依赖为0；发现WindowsFormsApp1仍引用AKRS.ZX2200 v1.2.0.0，而主程序新发射物为v1.5.0.0，因此闭包可解析但程序集身份/API一致性尚未通过。未执行联合MSBuild、生产源码修改、设备、SQL、VM或部署；下一步先收敛该版本身份差异，再继续16工程联合依赖验证。

依赖身份修复候选已通过：[进度](original-source-artifact-reference-closure-repair-progress.json)及[报告](original-source-artifact-reference-closure-repair-review.md)。隔离重编WindowsFormsApp1时只将旧AKRS.ZX2200 v1.2.0.0元数据替换为当前v1.5.0.0发射物，编译通过，候选12个AssemblyRef的缺失和身份冲突均为0。该结果只证明可行的隔离修复路径，不修改原工程、不代表联合MSBuild/部署/运行验收；下一步仍需在原始工程依赖声明层核对并确认版本策略。


原始工程依赖声明审计已完成：[声明审计](original-source-artifact-reference-declaration-audit.json)及[审计说明](original-source-artifact-reference-declaration-review.md)确认 InterpolationMovementTest 的 ProjectReference 在原隔离准备中解析到仓库既有 AKRS.ZX2200 v1.2.0.0 二进制，当前主程序源码发射物为 v1.5.0.0；隔离修复候选已用当前元数据通过。原始 csproj、生产源码和原 Compile 输入均未修改，版本策略、联合 MSBuild、部署、在线设备及 SQL 仍待完成，整体目标未完成。


原动作目录依赖闭包候选已登记：[审计](original-action-catalog-closure-audit.json)与[说明](original-action-catalog-closure-review.md)在隔离目录接入原始 DispenseActionNodes、BondActionNodeRepository 及 51 个动作节点/分部源文件；37 个构造引用全部解析到仓库源文件。Roslyn 候选编译记录 1,585 个错误，主要是 LogicHardware、VM、DevExpress、Wafer/Bond/Dispense 服务和配置成员缺口，未生成可运行 DLL。候选输入、失败日志和源哈希已保留，两个目录仅作只读输入且生产源未改；正式1328回归保持独立。下一步只扩展实际仓库依赖闭包，先通过目录构造与 Init 顺序核验，再推进完整 System2Domain/SelfCheck、相对贴片/重做、PR/相机/校准/测量与硬件边界，整体目标未完成。

动作目录源码候选已进一步闭合：[审计](action-catalog-binary-reference-audit.json)与[说明](action-catalog-binary-reference-review.md)用未修改的原 ZX2200 发射物及 162 个真实引用完成 54 个源文件的 Roslyn 编译，错误降为 0；候选 `Init` 两轮一致注册 S1 15 个、S2 19 个动作，并与原二进制独立探针逐项核对了两组完整注册顺序；另一个只调用基类逻辑的 `InteractiveAction.IsDoWork()` 候选与原二进制均返回 `True`。118 个警告中 109 个为候选源与原程序集同名类型的 `CS0436`，因此该输出只用于源码闭包、注册顺序和受限分支验证，不是可部署产物；动作 `DoWork`、完整 System2Domain/SelfCheck、PR/视觉/设备和联合构建仍待完成。

身份、测高、视觉与预点胶非设备分支已补充：[审计](native-node-do-work-branches-progress.json)与[说明](native-node-do-work-branches-review.md)复用公开完整树/步骤夹具和 16 个保真程序集，两轮各 604 项检查；两个原始公开控制器各选出 34 个注册接收者，每轮执行 544 次原始 `IsDoWork()` 调用和 510 个条件场景观察。S1/S2 八个身份离线 `DoWork` 均返回 `Success` 并设置身份标志，S1 载具/基板/模块三个测高分支在禁用测高门后返回 `Success`，S1 载具及 S2 载具/基板/基岛/焊点五个视觉分支在离线或分割短路后返回 `Success` 并设置视觉标志，S1 相对固晶焊点定位通过离线标志和相对位置门在视觉硬件前返回 `Success`，S2 上视纠偏在运动和视觉前返回 `Success`，S2 预点胶在关闭系统2点胶硬件门后返回 `Success` 且不触发设备工作；十九条分支均各调用一次开始/停止回调并以 `Stop` 收尾，实际硬件仓库保持空。其它具体动作、在线分支、生产 Task、Retry/Pause/异常链、PR/测量/VM/SQL/设备和联合构建仍待完成。

主程序入口与产品编辑门控已继续复核：[审计](main-entry-gating-audit.json)及[说明](main-entry-gating-review.md)确认 STA/互斥体/createNew/Application.Run 顺序、在线 `InitPR` 未等待的异步边界、MainForm 回零/离线 Load 门、编辑程式三项运行前置条件、运行/暂停/停止按钮状态，以及普通启动与生产启动的 DockPanel 差异。证据绑定当前源码哈希；未启动真实主程序、VM、硬件或设备，权限实现、事件竞态和 PR 完成契约仍待继续核对。

权限与编辑事件门控已继续展开：[审计](permission-gating-audit.json)及[说明](permission-gating-review.md)确认角色编码、MethodAop 对 BarButtonItem 与 SimpleButton 的分支差异、编辑程式入口缺少角色检查、参数控件的独立 RoleLevel 门、管理员专用入口及自动登出条件。当前结论仍为源码部分复核；Fody 织入、登录数据源、权限配置持久化和操作员真实路径待验证。

`Machine.Start` 启动就绪链已继续展开：[审计](machine-start-readiness-audit.json)及[说明](machine-start-readiness-review.md)登记启动前清理/信号/总复位/任务关闭/PR/磁盘/安全门/域自检顺序、System1/System2/Wafer/Process 的配置门、任务启动返回值未消费，以及 Transport 失败后停止而后续 Wafer 启动重新写入 Working 的源级风险。仅为源码顺序证据，未调用真实运动、真空、信号、VM、硬件或设备；并发回收和任务健康状态仍待核验。

启动后的任务生命周期已继续展开：[审计](machine-task-lifecycle-audit.json)及[说明](machine-task-lifecycle-review.md)确认 `ActionNodesService.Init` 无本地失败结果、四类 Worker 的 Task 创建与异常观察边界、`IsAllowTaskClosed` 只阻挡 Running 句柄，以及 EmergencyStop 下点胶 Dispose、Bond 空 Abort、Wafer 注释式 Abort 的差异。该证据仍是源码部分复核，未执行后台任务、Stop、急停或设备动作。

任务生命周期语义已补充隔离运行证据：[审计](task-lifecycle-probe-audit.json)及[说明](task-lifecycle-probe-review.md)用官方 .NET 4.8 目标夹具复现 Running-only 状态谓词，并确认 Running Task 上直接 Dispose 会抛出 `InvalidOperationException`，完成后才可 Dispose；该夹具不引用生产程序集，生产任务的集成回收仍待安全运行环境验证。

权限织入链路已登记：[审计](permission-weaving-audit.json)及[说明](permission-weaving-review.md)确认 ZX2200/PR 声明的 Fody 与 MethodBoundaryAspect、生成 NuGet 导入意图和现有织入器文件；ZX2200 声明 Fody 6.6.4，但仓库/本机缓存缺少对应 Fody.targets，仅有6.0.5目标。官方隔离构建日志只出现包与引用评估，没有 FodyTarget、Fody.WeavingTask、FodyExecutedWeavers 或织入执行诊断，并继续受 Dispense/PR 的 LC.exe 缺失阻塞，因此运行时权限织入仍未验证。未安装包、未修改生产源、未执行生产程序、登录、数据库、VM、设备或部署，整体目标未完成。

登录会话与权限配置边界已补充：[审计](permission-session-audit.json)及[说明](permission-session-review.md)确认宿主在登录对话框返回 OK 后才写入进程级 CurrentLoginUser；仓库 UserManager DLL 的只读元数据显示 UserVerify→UserDal.QueryByAccount→Role 加载、Disabled 检查、UserManagerContext 缓存、lastUserAccount 配置保存，以及内置 localhost/UserManager SQL 连接和建库/CodeFirst 初始化路径。ZX2200 的 IsPermissionOpen 默认 true，FilePath 指向 DeviceDirPath 下的 MachineSoftwareConfiguration.json，宿主有 Save 调用；通用 Singleton 的合法/缺失/损坏 JSON 行为已有独立隔离探针，但 MachineSoftwareConfiguration 真实设备路径仍未执行。未连接 SQL、未执行登录/用户管理、未修改生产源码，真实账号、密码、配置持久化和操作员路径仍未验收，整体目标未完成。

原 S2 自检边界已补充：[审计](s2-self-check-audit.json)及[说明](s2-self-check-review.md)固定 `CheckIsReady` 的14段顺序、`ActionNodesService.SelfCheck` 的7类失败门、`BondProgram.SelfCheck` 的载具/力控/视觉/延时门、吸嘴架程序检查和7槽传感器读取。确认自检开启与吸嘴检测默认值为 true，并登记 Yes/No、OK/Cancel 对话框和 `ThrowAction`/硬件读取边界。自检完整入口仍未执行，因为依赖 DevExpress UI、吸嘴架传感器、焊头/真空动作和设备配置；未修改生产源、未执行 SQL/VM/设备/部署，整体目标未完成。

本轮进一步对原始 ZX2200 程序集做 IL 锚定，固定 `System2Domain.CheckIsReady`、`S2ActionNodeController.SelfCheck`、`BondProgram.SelfCheck`、`NozzleShelfProgram.SelfCheck` 与 `NozzleShelfController.CheckToolBankConfiguration` 五个方法的调用顺序和 UI/设备边界：336/109/439/81/304 条指令，检查确认先开焊头真空、再进入两层自检，吸嘴架检查读取 1–7 号槽传感器并可进入报警对话框。该证据增强了原始程序层可追溯性，仍不等于真实 UI/硬件自检成功；见 [原始 S2 自检 IL 审计](original-s2-selfcheck-il.json) 与 [复核说明](original-s2-selfcheck-il-review.md)。

在非设备动作分支清单上继续增量复跑：复用原 604 项节点夹具，只增加 `AfterBondCheckActionNode` 的离线 `DoWork`。605 项检查通过，新增分支返回 `Success`、提交当前 S2 步骤并完成 `WorkStart/WorkStop`；16 个源码程序集绑定一致，硬件仓库为 0。夹具仅把 UI 刷新委托设为空操作，不把真实 UI/生产任务算作完成；见 [AfterBond 增量进度](after-bond-offline-extension-progress.json) 与 [复核说明](after-bond-offline-extension-review.md)。

原 S2 清零正常路径已补充：[审计](s2-reset-normal-audit.json)及[说明](s2-reset-normal-review.md)确认 `BondTask.DoWork` 在清零后忽略 `ResetBondhead()` 的 bool 返回；清零助手按 Modbus/IO 分支执行，Retry 为无界递归，Ignore 返回 true，Abort/默认返回 false；Modbus 清零对寄存器94最多写两次，第二次异常逸出。既有故障回归继续保留，真实 Modbus/IO 成功、正常生产循环与返回值修复仍未验收，未修改生产源、未执行 SQL/VM/设备/部署，整体目标未完成。

原 S2 翻转台/刮胶盘任务启动边界已补充：[审计](s2-flip-slide-start-audit.json)及[说明](s2-flip-slide-start-review.md)确认 SlideFluxerTask 的配置门、Running 防重复、刮胶信号/超时/回零顺序，以及 FlipTask 的直接入口缺少配置门、启动即写 Working、未保存句柄的通知 Task.Run、翻转动作结果映射和 Bond/晶圆信号等待。Machine.Start 仍提供外层 Flip 配置条件；未执行任务、UI、轴/传感器、SQL、VM、设备或部署，整体目标未完成。

S1/S2 步骤注入链已补充：[审计](process-step-injection-audit.json)及[说明](process-step-injection-review.md)固定两个动作控制器只注入启用步骤，按焊点名称匹配，并只为缺失的 S1/S2 RemainingSteps 键加入 `false`；已有键和值不清除。已核对 TransportUnit 构造、两个 Mapping 读取入口、DispenseWorkTask 和 BondTask 的注入位置及顺序，共 14 项源码检查通过。该项仍是哈希锚定的源码证据，未执行真实载具/Mapping、完整任务、UI、SQL、VM 或设备；重复载具/配方切换时保留旧键的业务影响仍待匹配环境验收，整体目标未完成。

相对贴片排序已补充：[审计](relative-bond-order-audit.json)及[说明](relative-bond-order-review.md)固定 `Init()` 在禁用动作移除后调用 `SortRelativeBond()`，删除相对步骤原视觉消息并在对应 Pick 前重新插入；同时登记无匹配启用步骤时的空引用边界，以及无 Pick 消息时删除后无备用插入路径。共 7 项源码检查，其中 6 项确认预期结构、1 项确认缺少空值保护；未执行动作控制器、配方、载具、UI、VM、SQL 或设备，整体目标未完成。

动作节点条件清单已补充：[审计](node-isdo-work-audit.json)及[说明](node-isdo-work-review.md)解析 35 个原始 `IsDoWork()`，覆盖身份、视觉、测高、点胶、取片、固晶、纠偏和焊后检查节点，登记离线/空跑/状态/步骤/完成标志等条件；并对照 `DoWork()` 记录 30 个离线门存在性差异。8 项结构检查通过；该项只建立源码条件地图，未调用全部节点或执行完整 Task/Retry/Pause/异常链，整体目标未完成。

S2 任务集成夹具已按当前源码复跑：[当前进度](s2-task-integration-current-progress.json)及[复跑说明](s2-task-integration-current-review.md)记录 `node scripts/test-s2-task-integration.cjs` 的 59 项检查、13 个原始方法提取，以及 `build-s2-task-integration-audit.cjs --check` 的一致通过。该复跑保持真实 Signal 句柄和原任务同步调用的限定范围；动作服务、Task.Factory 调度、完整 UI/插补/补偿/硬件/存储及设备验收仍未完成。

原组件配方与动作选择已按当前源码复验：[当前进度](native-recipe-action-selection-current-progress.json)及[复验说明](native-recipe-action-selection-current-review.md)记录两轮各 31,655 项检查、每轮 5,888 条消息和 34 个注册接收者全部选中；绑定复验通过，冻结绑定 9,734。仅原 Interactive 短 DoWork 分支执行，其他具体节点、生产 Task、PR/VM/SQL/UI、设备及完整构建部署仍待验收。

其余节点早退边界已登记：[审计](remaining-node-early-boundary-audit.json)及[说明](remaining-node-early-boundary-review.md)确认 S1 缺陷胶检离线标记后仍会进入检测/视觉路径，S2 焊后检查离线门前会读取完整上下文且 `finally` 刷新 UI；焊后隔离探针编译通过但运行退出码为 `3762504530`，未形成成功结果，因此未加入非设备成功夹具。6 项源码顺序检查通过，生产源未改，整体目标未完成。

原动作目录、域与控制器已按当前源码复验：[当前进度](native-action-controller-current-progress.json)及[复验说明](native-action-controller-current-review.md)记录 251 项检查（目录子检查 119 项）、37 个具体节点、2 个完整域、16 份控制器排程和 3,292 个冻结绑定；硬件仓库为 0 项，两轮重放一致。该复验仍限定在原隔离控制器构造/Init 证据，具体节点 DoWork 全覆盖、生产 Task、PR/VM/SQL/UI、设备和完整构建部署仍待验收。

原配方任务生命周期已按当前源码复验：[当前进度](native-recipe-task-lifecycle-current-progress.json)及[复验说明](native-recipe-task-lifecycle-current-review.md)记录 100 项检查；原任务启动 6 次、5 次完成、1 次原初始化异常，2 个直接 Signal 门控线程、6 个配方单例、16 个源程序集和 3,376 个冻结绑定通过。晶圆 JSON 仅语义重放一致，DateTime.Now 字段使字节重放不一致；在线生产任务、真实硬件、完整 UI、PR/VM/SQL、联合构建和部署仍待验收。

原任务输入门与 S2 入口已按当前源码复验：[当前进度](native-task-input-gates-current-progress.json)及[复验说明](native-task-input-gates-current-review.md)记录两次接受进程、每轮 54 项检查、54 个标签和 31 个选定方法通过；原 S2 任务每轮仍在真实缺失 AxisY 前置处 Faulted，冻结绑定 5,272。该结果保留 Faulted 边界，不代表生产循环成功，UI、SQL、VM、设备和部署仍待验收。

四条原任务链的当前源码指纹已登记：[S1 当前复验](native-s1-task-loop-current-review.md)通过 126 项、74 个源码文件和 10,006 个冻结绑定；[S2 当前复验](native-s2-task-entry-current-review.md)通过 497 项、147 个源码文件和 10,857 个冻结绑定；[Machine 闭环当前复验](native-machine-task-closure-current-review.md)通过 310 项、141 个源码文件和 10,761 个冻结绑定；[辅助任务当前复验](native-aux-task-entry-current-review.md)通过 487 项、153 个源码文件和 10,974 个冻结绑定。四项均只重验原隔离绑定并记录当前源码指纹，未扩大运行范围；在线生产、UI、PR/VM/SQL、设备、联合构建和部署仍待验收。

S1/S2 就绪与收尾子链也已按当前源码登记：[S1 缺陷](native-s1-defect-outcomes-current-review.md) 109 项/10,250 绑定、[S1 步骤提交](native-s1-step-commit-current-review.md) 85 项/10,096 绑定、[S1 停止恢复](native-s1-stop-recovery-current-review.md) 51 项/10,164 绑定、[S2 就绪](native-s2-readiness-current-review.md) 56 项/10,455 绑定、[载具就绪](native-carrier-readiness-current-review.md) 100 项/10,544 绑定、[检测就绪](native-inspection-readiness-current-review.md) 108 项/10,344 绑定均通过当前绑定验证，并保存当前源码文件指纹。真实在线动作、视觉、设备安全和完整部署仍待验收。

返回/交互与 S2 动作子链当前复验已登记：[S1 返回门](native-s1-return-gates-current-review.md) 120 项/5,500 绑定、[S1 重工上下文](native-s1-rework-context-current-review.md) 47 项/5,571 绑定、[S1 分段交互](native-s1-segment-interaction-current-review.md) 121 项/5,383 绑定、[S1 Working/Pause](native-s1-working-pause-current-review.md) 70 项/5,200 绑定、[S2 动作边界](native-s2-action-boundaries-current-review.md) 31 项/5,886 绑定、[S2 补偿前置](native-s2-compensation-prerequisites-current-review.md) 51 项/5,770 绑定、[S2 清零传播](native-s2-reset-propagation-current-review.md) 70 项/5,814 绑定和[料架门](native-s2-shelf-gates-current-review.md) 58 项/5,717 绑定均通过，当前源码指纹与历史冻结源文件一致。真实在线动作、Retry 全链、设备和部署仍待验收。

算法与点胶支线当前复验已登记：[算法选择](native-algorithm-selection-current-review.md) 163 项/9,609 绑定、[点胶控制](native-dispense-control-current-review.md) 35 项/6,163 绑定、[点胶控制器](native-dispense-controller-current-review.md) 40 项/6,653 绑定、[点胶输入](native-dispense-input-current-review.md) 44 项/6,380 绑定、[点胶策略](native-dispense-policy-current-review.md) 51 项/6,594 绑定、[点胶几何](native-dispense-geometry-current-review.md) 50 项/6,111 绑定、[点胶源码读取](native-dispense-reader-current-review.md) 260 个新增快照/6,535 绑定和[点胶渲染](native-dispense-rendering-current-review.md) 42 项/6,326 绑定均通过，并重新核对当前源文件指纹。算法 VM、真实点胶、在线 UI、SQL、设备和部署仍待验收。

点胶窗体、数据库、校准、输送、统计和图像队列支线也已复验：[点胶窗体](native-dispense-form-current-review.md) 40 项/6,444 绑定、[数据库保存](native-db-saver-current-review.md) 30 项加 12 项完成子检查/3,461 绑定、[力控校准](native-force-calibration-current-review.md) 46 项/5,961 绑定、[输送上下文](native-transport-context-current-review.md) 180 项/3,322 绑定、[统计生产者](native-statistics-producer-current-review.md) 60 项/3,491 绑定和[视觉图像队列](native-vision-image-queue-current-review.md) 41 项加 12 项关闭生产者检查/3,579 绑定均通过。SQL、VM、真实输送/校准、在线 UI、设备和部署仍待验收。

输送和料仓边界支线当前复验已登记：[进出料握手](native-inout-handshake-current-review.md) 550 项/11,622 绑定、[料仓握手与设置](native-bin-handshake-readiness-current-review.md) 834 项/11,474 绑定、[上/下料入口](native-loader-unloader-entry-current-review.md) 773 项/11,381 绑定、[输送环境组合](native-transport-environment-current-review.md) 3,141 项/11,799 绑定和[晶圆输送入口](native-wafer-transport-entry-current-review.md) 660 项/11,165 绑定通过当前完整验证器并保存当前源码指纹。完整 Machine、生产业务循环、设备和部署仍待验收。

主程序、PR 和 UI 生命周期当前复验已登记：[PR 初始化边界](native-pr-init-boundary-current-review.md) 31 项/14,446 绑定、[预点胶前置](native-predispense-prerequisites-current-review.md) 30 项/5,661 绑定、[动作节点前置](native-node-preconditions-current-review.md) 584 项/9,836 绑定、[程序就绪](native-program-readiness-current-review.md) 58 项/3,259 绑定、[Program.Main](native-program-main-entry-current-review.md) 41 项/19,106 绑定、[MainForm 上下文](native-mainform-context-current-review.md) 40 项/14,205 绑定、[关闭保存](native-mainform-close-save-current-review.md) 60 项/14,818 绑定和[布局裁切](native-mainform-layout-current-review.md) 47 项/18,705 绑定通过。VM、在线 PR、完整 UI 布局、设备和部署仍待验收。

监控、退出和配方 UI 支线当前复验已登记：[监控消费者启动](native-monitor-consumer-startup-current-review.md) 40 项/18,295 绑定、[退出积压](native-exit-consumer-pending-current-review.md) 25 项/17,846 绑定、[客户区矩阵](native-mainform-viewport-current-review.md) 71 项、[UI 停止恢复](native-ui-stop-recovery-current-review.md) 572 项/12,534 绑定、[配方实时重载](native-recipe-live-reload-current-review.md) 93 项/11,965 绑定、[配方 UI 重载](native-recipe-ui-reload-current-review.md) 48 项/12,379 绑定、[配方对话框](native-recipe-dialog-events-current-review.md) 89 项/12,916 绑定和[配方新建拷贝](native-recipe-create-copy-current-review.md) 163 项/13,651 绑定通过。退出不等待消费者、图像积压、UI 裁切和 SDK/VM 缺失边界均保留，完整部署仍待验收。

部署前置当前复验已登记：[隔离 MSBuild](native-msbuild-build-current-review.md) 完成 40 次构建调用核验（每轮仅 1 个工程通过，解决方案/LC/Fody/DevExpress/外部依赖阻塞保持）；[Setup 清单](native-setup-vdproj-current-review.md) 完成 465 项只读核验（393 存在、72 缺失、195 依赖）。未生成 MSI、未安装，完整联合构建和部署仍待验收。

整机环境与停止边界当前复验已登记：[Machine 环境](native-machine-environment-current-review.md) 123 项/10,685 绑定、[Machine Stop](native-machine-stop-current-review.md) 70 项/3,418 绑定通过；完整 Machine.Start、Prepare、硬件自检和设备动作仍未执行。运行时源码读取的当前浏览器结果 JSON 哈希变为 `6ac2442a...`，与历史冻结 `ee448dc5...` 不一致，未登记为成功当前复验，源读取边界保持待重建。

源码浏览器 artifact 当前复验已登记：[点胶浏览器](native-dispense-source-explorer-browser-current-review.md)通过 52 个主题/5,257 个证据（500 个原生边界），[运行时浏览器](native-runtime-source-explorer-browser-current-review.md)通过 47 个主题/4,997 个证据（240 个原生边界）；四种视口均无浏览器错误。浏览器证据与运行时冻结 JSON 分离，仍不代表生产运行或部署验收。

运行时源码读取已补充当前语义复验：[native-runtime-reader-current-review.md](native-runtime-reader-current-review.md)重新核对 47 个主题、4,997 个快照、63 个源文件和 1,456 个声明，解析错误为 0，当前源指纹和浏览器结构均通过。历史 browser-results.json 字节哈希漂移仍单独保留，不覆盖旧冻结记录，也不扩展为生产运行验收。

就绪辅助链当前复验已登记：[readiness-helpers](readiness-helpers-current-review.md) 303 项/100 个源码片段、[焊后检测就绪](bond-inspection-readiness-current-review.md) 45 项/22 个片段、[输送检测启动准备](transport-inspection-readiness-startup-current-review.md) 20 项/469 个片段、[输送检测集成](transport-inspection-readiness-integration-current-review.md) 1,209 项/469 个片段和[配方就绪门](recipe-readiness-gate-current-review.md) 16 项均通过；焊后启动集成和完整生产组合仍待验收。

任务集成夹具当前复验已登记：[S1 任务集成](s1-task-integration-current-review.md) 30 项、[外输送任务](outer-transport-task-current-review.md) 52 项、[任务启动并发](task-start-concurrency-current-review.md) 47 项、[任务闭环](task-closure-current-review.md) 155 项、[门控暂停](door-task-pause-current-review.md) 28 项、[空跑任务](dry-run-task-current-review.md) 115 项和[标定入口](calibration-task-entry-current-review.md) 8 项均通过。它们仍是隔离夹具，不代表完整在线生产或设备验收。

正常启动集成当前复验已登记：[当前进度](normal-start-integration-current-progress.json)及[复验说明](normal-start-integration-current-review.md)重新运行 `node scripts/test-normal-start-integration.cjs`，175 项检查、67 个方法、19 个属性、2 个枚举和 12 个主题快照通过，并由来源审计复核。该记录仍限于隔离启动夹具，不代表完整在线生产、UI、VM、SQL、硬件或部署验收。

急停与模式生命周期当前复验已登记：[急停入口](emergency-entry-current-progress.json)通过 27 项、45 个成员和 8 组观察；[急停收尾](emergency-abort-current-progress.json)通过 87 项、44 个成员和 42 组观察；[模式生命周期](mode-lifecycle-current-progress.json)通过 34 项、23 个方法。三项均由当前来源审计复核，仍限于隔离夹具，不代表物理急停、在线生产、设备或部署验收。

生产启动入口当前复验已登记：[当前进度](production-start-launch-current-progress.json)及[复验说明](production-start-launch-current-review.md)重新执行 30 项隔离检查并通过，覆盖 16 种配置/补偿组合、准备失败、同步调用异常传播、任务返回值和输送停止后继续调用；源码证据快照 7 个锚点同步通过。该结果仍不代表后台任务完成、设备安全、在线 UI 或部署验收。

ProcessDomain 就绪门当前复验已登记：[当前进度](process-start-gate-current-progress.json)及[复验说明](process-start-gate-current-review.md)通过 14 项隔离检查：空 S2 列表、有效/无效索引、焊点名称、异形配置绕过、禁用步骤、Null 字段和翻转多步骤计数边界均按当前源码重跑。该项只验证就绪方法，不代表完整 Machine.Start、配置文件、UI、VM、SQL 或设备验收。

输送配置门当前复验已登记：[当前进度](transport-config-guard-current-progress.json)及[复验说明](transport-config-guard-current-review.md)通过 32 项组合检查，覆盖五个子配置的整体缺失、部分存在、`IsSettingNull` 聚合结果、`UcInput.Confirm` 保存次数和缺失引用异常。Settings、UI、仓库保存仍是隔离替身，不代表真实持久化或设备行为。

启动门控支线当前复验已登记：[晶圆启动初始化](wafer-start-init-current-progress.json)通过 9 项失败/重试/正常顺序检查；[状态队列与 Stop 异常](state-queue-failure-current-progress.json)通过 18 项队列、清理截断、空跑和异常提示检查。两项均使用当前源码片段和隔离替身，未扩大为生产任务、设备或现场调度器验收。

失效料仓配置当前复验已登记：[当前进度](bin-missing-configuration-current-progress.json)及[复验说明](bin-missing-configuration-current-review.md)通过 19 项隔离检查：上下料有效/超限/零层、空料仓引用异常、LoaderTask Success/Abort/异常捕获、信号和 Stop 副作用、禁用与 DryCycle 门均按当前源码重跑。仓库查找、完整上下料循环、真实信号消费者和设备仍未验收。

料仓仓库查找当前复验已登记：[当前进度](bin-repository-lookup-current-progress.json)及[复验说明](bin-repository-lookup-current-review.md)通过 7 项 `BaseSettingRepository.Find` 隔离检查，覆盖匹配、缺失名称、重复名称取首项、null 名称、大小写敏感和 null 列表异常。该项只验证内存查找方法，不代表 JSON/数据库加载或设备配置验收。

料仓当前复验范围已扩展：同一记录现为 28 项，增加 `UnloaderTask.Start` 的当前源码绑定，并覆盖上下料两侧 Success/Abort/异常捕获、推料信号发送与等待门；此前 19 项结果作为子集保留，不覆盖真实信号消费者或现场设备。

输送配置门当前复验已扩展为 35 项：在原 32 个子配置组合之外，新增根 `TransportProgram=null`、子配置对象为 null 的聚合检查和 `UcInput.Confirm` 检查；三项均复现源码的 NullReference 边界，未把异常误判为配置校验成功。

等待区输送集成当前复验已登记：[当前进度](transport-waiting-integration-current-progress.json)及[复验说明](transport-waiting-integration-current-review.md)重新执行 1,076 项检查并通过，覆盖下料推料信号消费者、等待/停止包装和等待区传输组合；来源片段 166 个。该隔离集成不代表完整在线生产或设备验收。

检测仓库集成当前复验已登记：[当前进度](transport-inspection-repository-integration-current-progress.json)及[复验说明](transport-inspection-repository-integration-current-review.md)重新运行 1,303 项隔离集成检查并通过，包含 498 个源码片段、398 个主题快照和 241 个唯一来源文件。该记录仍不代表真实仓库、VM、SQL、在线生产或设备验收。

产品配置原生准备当前复验已登记：[当前进度](product-config-native-source-current-progress.json)及[复验说明](product-config-native-source-current-review.md)重新执行 36 项独立断言（两份实际 SDK 各 36 次，共 72 次）并由既有验证器通过。该结果覆盖原配置/JSON/Singleton/就绪边界的隔离准备，不等同完整启动、焊点实体、Fody、UI、设备或部署验收。

焊点配置原生准备当前复验已登记：[当前进度](bond-config-native-source-current-progress.json)及[复验说明](bond-config-native-source-current-review.md)重新执行 56 项独立断言（两份实际 SDK 各 56 次，共 112 次），并由既有验证器通过。该结果覆盖完整焊点对象、状态/保存/加载和汇总边界，不等同完整启动、Fody、UI、设备或部署验收。

完整 Framework/SDK 组合当前复核已登记：[当前进度](transport-full-framework-sdk-current-progress.json)及[复核说明](transport-full-framework-sdk-current-review.md)。当前验证器确认 1,328 项受控 Framework 组合、两份 SDK 各 58 项准备检查、512 个源码片段和 269 个冻结输入的证据一致；本轮明确是既有证据复核，没有把长测试重新执行次数冒充为本轮运行。Fody、原工程 MSBuild、原生 UI、设备和部署仍未验收。

完整原配置 SDK 当前复验已登记：[当前进度](transport-whole-config-sdk-current-progress.json)及[复验说明](transport-whole-config-sdk-current-review.md)。在保留历史焊点配置输入的临时隔离复跑中，两份实际 SDK 各通过 142 项、共 284 次断言且每份执行 28 次原启动调用，产物一致；当前焊点配置文件已由 finally 恢复，未覆盖当前 56 项证据。该结果仍独立于正式 1328 回归和完整 29 组验收。

完整实体与检测 SDK 当前复验已登记：[当前进度](transport-whole-entity-sdk-current-progress.json)及[复验说明](transport-whole-entity-sdk-current-review.md)。在保留历史焊点配置输入的临时隔离复跑中，两份实际 SDK 各通过 187 项、共 374 次断言且产物一致；当前焊点配置文件已恢复，未覆盖当前 56 项证据。实体、检测、PR/校准/设备和部署边界仍保持独立。

完整动作 SDK 当前复验已登记：[当前进度](transport-whole-action-sdk-current-progress.json)及[复验说明](transport-whole-action-sdk-current-review.md)。在保留历史焊点配置输入的临时隔离复跑中，两份实际 SDK 各通过 278 项、共 556 次断言且产物一致；当前焊点配置文件已恢复。该结果仍独立于正式 1328 回归、当前 56 项焊点准备和 187 项实体/检测复验；Fody、原工程构建、原生 UI、设备和部署仍未验收。

视觉缺陷 Retry 当前复验已登记：[当前进度](vision-defect-retry-current-progress.json)及[复验说明](vision-defect-retry-current-review.md)通过 7 项隔离检查，覆盖首个非空结果停止、null 重试与延迟、零/负次数、空列表和异常不重试。该项只验证当前源码循环，未执行相机、光源、运动、算法、生产 Task 或设备 I/O。

晶圆变更 Retry 当前复验已登记：[当前进度](wafer-change-retry-current-progress.json)及[复验说明](wafer-change-retry-current-review.md)通过 16 项隔离检查，覆盖三类换片路径的重试、Stop 入口、异常逸出、对话框 Abort 及缺片/传感器分支。该项只验证 ChangeTabletAuto 控制流和受控替身，未执行真实运动、窗口、设备 SDK、完整 worker 或生产安全验收。

输送暂停当前复验已登记：[当前进度](transport-pause-current-progress.json)及[复验说明](transport-pause-current-review.md)通过 32 项隔离检查，覆盖等待、Pause/Stop 状态变化、物料门、Task.WaitAll、保存失败、异常传播和 jam Abort。该项仍使用受控替身，不代表原 Machine.Stop、外层输送任务、完整 Framework 或现场设备验收。

晶圆消费者暂停当前复验已登记：[当前进度](wafer-consumer-pause-current-progress.json)及[复验说明](wafer-consumer-pause-current-review.md)通过 212 项隔离检查，覆盖入口/等待内 Pause 与 Stop、信号消费、四类载具、换片/视觉 Retry、异常传播和取料信号发布边界。该项使用动作、视觉、运动、对话框、数据库和 Excel 替身，不代表原 Stop 集成、驱动、UI、持久化或设备验收。

动作排序与相对贴片当前复验已登记：[当前进度](action-sort-current-progress.json)及[复验说明](action-sort-current-review.md)通过 80 项隔离检查，覆盖 S1/S2 八种排序、动作生成、组件/缺陷/环氧选择、禁用过滤、分批和相对贴片重排边界。该项使用配置、仓库和动作实例替身，不代表完整域 SelfCheck、生产 Task、PR/校准、IO、设备或部署验收。

点胶动作节点当前复验已登记：[当前进度](dispense-node-current-progress.json)及[复验说明](dispense-node-current-review.md)通过 68 项隔离检查，覆盖 S1/S2 点胶 DoWork、两种安全位移动作、WaitSingleStep、结果映射、步骤提交、离线门、finally 与异常边界。该项仍使用控制器、信号、配置、坐标、统计和 UI 替身，不代表完整调度器、物理阀、硬件、构建或部署验收。

晶圆动作门当前复验已登记：[当前进度](wafer-action-gates-current-progress.json)及[复验说明](wafer-action-gates-current-review.md)通过 210 项隔离检查，覆盖 Working/Pause/Stop、四类搜索、单步等待、偏移、换片判断、移动顺序、异常截断、保存失败和取料许可发布。该项使用视觉、标定、轴到位、碰撞、顶针、Machine.Stop、存储和 UI 替身，不代表真实动作或设备安全验收。

晶圆顶针就绪与停止当前复验已登记：[当前进度](wafer-eject-ready-current-progress.json)及[复验说明](wafer-eject-ready-current-review.md)通过 110 项隔离检查，覆盖就绪阈值、对话框、离线门、移动顺序、依赖故障、消费者完成、Stop/单步取消和保存边界。该项使用轴 SDK、标定、碰撞、视觉、UI 和 I/O 替身，不代表现场设备安全或部署验收。

S2 动作节点选择当前复验已登记：[当前进度](s2-node-selection-current-progress.json)及[复验说明](s2-node-selection-current-review.md)通过 9 项隔离检查，覆盖未完成节点选择、Finish 推进、特殊节点重复拒绝、缺失注册、空列表和空工作消息边界。该项只验证节点选择控制流，不代表完整域上下文、BondTask、SelfCheck、生产任务或设备验收。

Mapping 动作门当前复验已登记：[当前进度](mapping-action-gates-current-progress.json)及[复验说明](mapping-action-gates-current-review.md)通过 30 项隔离检查，覆盖 IsDoWork 的完成/禁用/缺失键、实体类型拒绝及 Pick 的 EntityState 边界。该项不代表生产构造、完整任务、硬件、厂商 DLL、启动或设备验收。

晶圆停止链当前复验已登记：[当前进度](wafer-stop-chain-current-progress.json)及[复验说明](wafer-stop-chain-current-review.md)通过 172 项隔离检查，覆盖 Stop 注入、单步取消、搜索/视觉停止传播、移动顺序和结果发布边界。该项使用搜索、运动、对话框、存储和机器状态替身，不代表原 Machine.Stop 集成、驱动、UI、持久化或设备验收。

晶圆安全门当前复验已登记：[当前进度](wafer-safety-guards-current-progress.json)及[复验说明](wafer-safety-guards-current-review.md)通过 135 项隔离检查，覆盖安全门、单步/Stop、依赖异常、移动抑制和状态发布。该项使用机器状态、运动、搜索、碰撞、存储和 UI 替身，不代表真实驱动、Machine.Stop、现场安全或设备验收。

晶圆视觉控制当前复验已登记：[当前进度](wafer-vision-control-current-progress.json)及[复验说明](wafer-vision-control-current-review.md)通过 118 项隔离检查，覆盖视觉请求路由、成功/失败/Stop、单步门、移动抑制和状态发布。该项使用视觉、运动、对话框、存储和机器状态替身，不代表相机 SDK、标定、Machine.Stop、UI 或设备验收。

晶圆视觉采集当前复验已登记：[当前进度](wafer-vision-acquisition-current-progress.json)及[复验说明](wafer-vision-acquisition-current-review.md)通过 112 项隔离检查，覆盖采集路由、成功/失败/Stop 传播、单步门、移动抑制和状态发布。该项使用相机、视觉、运动、对话框、存储和机器状态替身，不代表真实相机 SDK、标定、Machine.Stop、UI 或设备验收。

晶圆搜索门当前复验已登记：[当前进度](wafer-search-gates-current-progress.json)及[复验说明](wafer-search-gates-current-review.md)通过 172 项隔离检查，覆盖搜索模式路由、偏移、Stop/Pause/单步门、故障传播、换片判断和结果发布。该项使用搜索、运动、视觉、存储和机器状态替身，不代表相机 SDK、标定、Machine.Stop、UI 或设备验收。

晶圆选择当前复验已登记：[当前进度](wafer-selection-current-progress.json)及[复验说明](wafer-selection-current-review.md)通过 23 项隔离检查，覆盖空值/缺失/重复选择、适配器失败、加载回退、显式名称事件以及晶圆/适配器槽位状态。该项使用控件、初始化和存储替身，不代表真实 UI 事件、文件持久化或设备验收。

晶圆几何当前复验已登记：[当前进度](wafer-geometry-current-progress.json)及[复验说明](wafer-geometry-current-review.md)通过 180 项隔离检查，覆盖坐标/偏移计算、几何模式、边界值、Stop/Pause/单步门和异常传播。该项使用坐标、运动、视觉、存储和机器状态替身，不代表标定 SDK、相机、轴到位、Machine.Stop、UI 或设备验收。

晶圆位置精度当前复验已登记：[当前进度](wafer-position-accuracy-current-progress.json)及[复验说明](wafer-position-accuracy-current-review.md)通过 99 项隔离检查，覆盖精度门、偏移、阈值、Stop/Pause/单步行为和异常传播。该项使用坐标、运动、视觉、存储和机器状态替身，不代表标定 SDK、相机、轴到位、Machine.Stop、UI 或设备验收。

晶圆标记中心当前复验已登记：[当前进度](wafer-mark-center-current-progress.json)及[复验说明](wafer-mark-center-current-review.md)通过 76 项隔离检查，覆盖标记中心计算、模式/偏移处理、Stop/Pause/单步门和异常传播。该项使用坐标、视觉、运动、存储和机器状态替身，不代表相机 SDK、标定、轴到位、Machine.Stop、UI 或设备验收。

晶圆下一位置当前复验已登记：[当前进度](wafer-next-position-current-progress.json)及[复验说明](wafer-next-position-current-review.md)通过 229 项隔离检查，覆盖下一位置计算、移动/偏移路由、边界值、Stop/Pause/单步门、重试和异常传播。该项使用坐标、运动、视觉、存储和机器状态替身，不代表相机 SDK、标定、轴到位、Machine.Stop、UI 或设备验收。

晶圆范围初始化当前复验已登记：[当前进度](wafer-range-init-current-progress.json)及[复验说明](wafer-range-init-current-review.md)通过 105 项隔离检查，覆盖范围设置、边界值、偏移路由、Stop/Pause/单步门、重试和异常传播。该项使用坐标、运动、视觉、存储和机器状态替身，不代表相机 SDK、标定、轴到位、Machine.Stop、UI 或设备验收。

晶圆相机间隙当前复验已登记：[当前进度](wafer-camera-clearance-current-progress.json)及[复验说明](wafer-camera-clearance-current-review.md)通过 174 项隔离检查，覆盖相机配置、精确间隙边界、Bond 严格容差、消费者模式、Stop/Pause 门及异常传播。该项使用运动、视觉、坐标、存储和机器状态替身，不代表相机 SDK、标定、轴到位、Machine.Stop、UI 或设备验收。

晶圆 Blob 位置当前复验已登记：[当前进度](wafer-blob-position-current-progress.json)及[复验说明](wafer-blob-position-current-review.md)通过 131 项隔离检查，覆盖 Blob 计数/释放、匹配坐标修正、离线/干运行门、畸形结果、依赖失败、坐标快照、消费者模式及 Stop 传播。该项使用图像、视觉、坐标、运动、存储和机器状态替身，不代表真实图像算法、标定、轴/IO、Machine.Stop、UI 或设备验收。

S2 预点胶前置门当前复验已登记：[当前进度](assistant-predispense-gates-current-progress.json)及[复验说明](assistant-predispense-gates-current-review.md)通过 19 项隔离检查，覆盖点胶器/吸嘴状态、几何与教学门、禁用/启用分支、胶名与胶板就绪以及缺失参数异常。该项使用程序、硬件配置、仓储和 UI 替身，不代表真实仓储查找、UI 教学、持久化、硬件或完整生产任务验收。

S1/S2 动作控制器当前复验已登记：[当前进度](action-controller-current-progress.json)及[复验说明](action-controller-current-review.md)通过 51 项隔离检查，提取并复核 17 个原方法，覆盖 InjectSteps、当前节点选择、完成/重置、重复与缺失键、特殊节点拒绝、消息遍历、缓存保留、构造注入顺序及部分失败传播。该项使用流程、消息、产品、几何、仓储和对话框替身，不代表完整排序初始化、完整任务、UI、硬件或生产部署验收。

S2 预点胶分配当前复验已登记：[当前进度](s2-predispense-allocation-current-progress.json)及[复验说明](s2-predispense-allocation-current-review.md)通过 13 项隔离检查，覆盖网格端点、列主序分配、初始化/保存、耗尽、重建规则、索引异常及保存失败状态。该项使用坐标、UI 答案、参数和 System1 保存替身，不代表设备运动、真实持久化、配置有效性或生产执行验收。

流程门组合当前复验已登记：[当前进度](process-gate-composition-current-progress.json)及[复验说明](process-gate-composition-current-review.md)通过 9 项隔离检查，覆盖空/有效/禁用流程、缺失与空 BondPosition、组件/列表空值以及控制器门和流程门差异。该项使用显式流程、单例和 UI 替身，不代表完整 Machine.Start、完整任务、硬件、UI 或部署验收。

S2 当前消息与层级状态更新复验已登记：[当前进度](s2-context-update-current-progress.json)及[复验说明](s2-context-update-current-review.md)通过 14 项隔离检查，覆盖消息绑定、禁用/缺失层级保留、重复项选择顺序、遍历异常、仓储异常边界及空输入行为。该项使用最小容器、仓储、启用步骤过滤和消息框替身，不代表真实配方、仓储实现、任务集成、Fody、硬件、UI 或部署验收。

S2 门暂停与恢复当前复验已登记：[当前进度](s2-door-pause-current-progress.json)及[复验说明](s2-door-pause-current-review.md)通过 37 项隔离检查并复核 17 个原方法，覆盖门暂停进入/恢复、外层/内层门、单步、来料事件等待、释放信号、完整 Stop 抑制、节点失败推进及 Stop 后插值提交。该项使用受控线程、事件句柄和动作/UI/插值/补偿/硬件/存储替身，不代表完整 DoWork、硬件、UI 或生产部署验收。

S1 任务集成当前复验已登记：[当前进度](s1-task-integration-current-progress.json)及[复验说明](s1-task-integration-current-review.md)通过 30 项隔离检查并复核 6 个原方法，同时通过独立来源/片段审计。覆盖正常完成、节点结果、重试、插值/统计失败、安全顺序、禁用/已完成节点、输入门、产品重建、Stop/离线行为及异常传播。该项使用服务、Stop、信号、插值、坐标和硬件替身，不代表任务启动、并发、完整控制器或设备验收。

通用安全门暂停当前复验已登记：[当前进度](safe-door-pause-current-progress.json)及[复验说明](safe-door-pause-current-review.md)通过 16 项隔离检查并复核 8 个原方法，覆盖门开关、传感器异常、状态/日志顺序、暂停阻塞与恢复、Stop 顺序、预点胶结果保留及信号异常传播。该项使用线程、传感器、状态、日志、预点胶和信号替身，不代表完整产品任务、真实传感器 IO、原生 UI 或机械停止验收。

Machine Stop 与信号当前复验已登记：[当前进度](machine-stop-signal-current-progress.json)及[复验说明](machine-stop-signal-current-review.md)通过 60 项隔离检查并复核 11 个原方法，覆盖 Stop 顺序/提交边界、重复 Stop、稳定状态等待、手动/自动信号复位、单步门、S1 失败集成、依赖异常传播及部分清理。该项使用真实 EventWaitHandle、受控依赖失败和交错序列替身，不代表并发生产行为、真实服务或设备验收。

安全运动当前复验已登记：[当前进度](safe-motion-current-progress.json)及[复验说明](safe-motion-current-review.md)通过 34 项隔离检查，覆盖 4D/2D 软限位、Z 路由、外层/安全 Z 拒绝、异常顺序、驱动返回值及速度缩放。该项使用安全、轴、信号和运动操作替身，不代表物理运动、并发执行、真实轴/信号或设备验收。

轴补偿数值当前复验已登记：[当前进度](axis-numeric-current-progress.json)及[复验说明](axis-numeric-current-review.md)通过 37 项隔离检查，覆盖补偿门、区间边界、NaN/Infinity 传播、多项式、分段行为、最小二乘拟合、重复替换及圆拟合退化。该项使用惰性 Singleton/PathConfig 和数值输入替身，不代表磁盘保存、UI、生产启动、.NET Framework 构建、物理运动或设备验收。

轴补偿拟合比例当前复验已登记：[当前进度](axis-fit-scale-current-progress.json)及[复验说明](axis-fit-scale-current-review.md)通过 108 个组合、6 组校验，覆盖单/多列表、样本数、原点、阶数、训练/中点/守卫误差及系数安装。该项使用原始类、MathNet net48 二进制和持久化替身，不代表真实拟合容差、生产构建或硬件验收。

轴返回值与传输当前复验已登记：[当前进度](axis-return-transfer-current-progress.json)及[复验说明](axis-return-transfer-current-review.md)通过 84 项隔离检查并复核 9 个原方法，覆盖 Bond/Waiting 全部轴返回值、物料提交/保存顺序、Stop、下游命令边界及异常传播。该项使用轴返回值、异常、信号/状态和传输替身，不代表真实轴 DLL、驱动行为或设备验收。

传输解夹与 Stop 当前复验已登记：[当前进度](transport-unclamp-stop-current-progress.json)及[复验说明](transport-unclamp-stop-current-review.md)通过 46 项隔离检查并复核 9 个原方法，覆盖升降/真空报警组合、Retry/Ignore、Stop 失败、提交边界、配置缺失和正常传感器路径。该项使用线程、任务、事件、I/O、轴、状态、日志、配置和持久化替身，不代表完整外层任务、产品宿主、物理设备或原生 I/O 验收。

传输自动上料集成当前复验已登记：[当前进度](transport-auto-loader-integration-current-progress.json)及[复验说明](transport-auto-loader-integration-current-review.md)通过 238 项隔离检查，绑定 279 个源码片段和 23 个信号声明，覆盖加载时序、状态/路由、构造与刷新、Stop 及下游集成。该项使用受控任务、UI、配置、仓储、SDK、对话框、保存、程序和域替身，不代表完整装载任务、原生 UI、构建/DLL、剩余料仓转移或设备验收。

传输自动下料集成当前复验已登记：[当前进度](transport-auto-unloader-integration-current-progress.json)及[复验说明](transport-auto-unloader-integration-current-review.md)通过 287 项隔离检查，绑定 186 个源码片段和 23 个信号声明，覆盖下料路由、状态/配置传播、初始化及 Stop 行为。该项使用受控任务、UI、仓储、SDK、配置、存储和设备替身，不代表完整产品任务调度、原生 UI、构建/DLL、剩余运输分支或设备验收。

传输料仓集成当前复验已登记：[当前进度](transport-bin-integration-current-progress.json)及[复验说明](transport-bin-integration-current-review.md)通过 578 项隔离检查，绑定 180 个源码片段和 23 个信号声明，覆盖料仓路由、配置/状态传播、上下料集成、信号、重试、Stop 及异常边界。该项使用配置、仓储、UI、持久化、设备和信号替身，不代表真实料仓文件、硬件、原生 UI、构建/DLL 或完整生产调度验收。

传输 Bond 集成当前复验已登记：[当前进度](transport-bond-integration-current-progress.json)及[复验说明](transport-bond-integration-current-review.md)通过 310 项隔离检查，绑定 145 个源码片段和 23 个信号声明，覆盖 Bond 路由、配置/状态传播、初始化、信号、Stop、重试及异常边界。该项使用配置、仓储、持久化、UI、设备和信号替身，不代表真实 Bond 硬件、原生 UI、构建/DLL 或完整生产调度验收。

传输载具映射集成当前复验已登记：[当前进度](transport-carrier-map-integration-current-progress.json)及[复验说明](transport-carrier-map-integration-current-review.md)通过 1,355 项隔离检查，绑定 341 个源码片段和 23 个信号声明，覆盖配置判定、报警选择、Retry 路由、映射状态、信号、启动/刷新及 Stop。该项使用受控任务、UI、配置、仓储、SDK、日志、对话框、持久化和设备替身，不代表完整动作注入、原生 UI、构建/DLL、真实日志或设备验收。

传输坐标与产品集成当前复验已登记：[当前进度](transport-coordinate-product-integration-current-progress.json)及[复验说明](transport-coordinate-product-integration-current-review.md)通过 1,031 项隔离检查，绑定 420 个源码片段和 23 个信号声明，覆盖坐标与产品路由、配置传播、载具/映射集成、信号、Stop 及异常边界。该项使用坐标、产品、仓储、UI、SDK、存储和设备替身，不代表真实标定、原生 UI、构建/DLL、持久化或设备验收。

传输点胶 Bond 集成当前复验已登记：[当前进度](transport-dispense-bond-integration-current-progress.json)及[复验说明](transport-dispense-bond-integration-current-review.md)通过 184 项隔离检查，绑定 210 个源码片段和 23 个信号声明，覆盖点胶/Bond 路由、配置/状态传播、初始化、信号、Stop、重试及异常边界。该项使用配置、仓储、UI、持久化、设备和信号替身，不代表真实点胶/Bond 硬件、原生 UI、构建/DLL 或完整生产调度验收。

传输点胶12 集成当前复验已登记：[当前进度](transport-dispense12-integration-current-progress.json)及[复验说明](transport-dispense12-integration-current-review.md)通过 276 项隔离检查，绑定 223 个源码片段和 23 个信号声明，覆盖点胶12路由、配置/状态传播、初始化、信号、Stop、重试及异常边界。该项使用配置、仓储、UI、持久化、设备和信号替身，不代表真实点胶硬件、原生 UI、构建/DLL 或完整生产调度验收。

传输 Unit 服务集成当前复验已登记：[当前进度](transport-unit-services-integration-current-progress.json)及[复验说明](transport-unit-services-integration-current-review.md)通过 1,011 项隔离检查，绑定 391 个源码片段和 23 个信号声明，覆盖 Unit 实体、TuService 坐标/行列/索引/状态处理、TransportProgram.RefreshTransportUnit、TransportModule.Init、信号、Stop 及异常边界。该项使用配置、仓储、UI、持久化、设备和信号替身，不代表真实 SDK/设备、原生 UI、构建/DLL 或完整生产调度验收。

传输产品声明集成当前复验已登记：[当前进度](transport-product-declarations-integration-current-progress.json)及[复验说明](transport-product-declarations-integration-current-review.md)通过 1,328 项隔离检查，绑定 512 个源码片段和 23 个信号声明，覆盖产品/程序/配置声明、传播、默认值、身份/替换、生命周期及异常边界。该项使用配置、仓储、UI、持久化、设备和信号替身，不代表真实 SDK/设备、原生 UI、构建/DLL 或完整生产调度验收。

传输教学集成当前复验已登记：[当前进度](transport-teaching-integration-current-progress.json)及[复验说明](transport-teaching-integration-current-review.md)通过 1,144 项隔离检查，绑定 449 个源码片段和 23 个信号声明，覆盖教学状态、默认值、聚合传播、坐标/配置身份、初始化、信号、Stop 及异常边界。该项使用配置、仓储、UI、持久化、设备和信号替身，不代表真实 SDK/设备、原生 UI、构建/DLL 或完整生产调度验收。

传输检查仓储集成当前复验已登记：[当前进度](transport-inspection-repository-integration-current-progress.json)及[复验说明](transport-inspection-repository-integration-current-review.md)通过 1,303 项隔离检查，绑定 498 个源码片段和 23 个信号声明，覆盖仓储构造、Load/Find/Filter、配方/存在性、Save、PR 增删/名称枚举、初始化、信号及异常边界。该项使用配置、仓储、UI、持久化、设备和信号替身，不代表真实 SDK/设备、原生 UI、构建/DLL 或完整生产调度验收。

传输检查就绪集成当前复验已登记：[当前进度](transport-inspection-readiness-integration-current-progress.json)及[复验说明](transport-inspection-readiness-integration-current-review.md)通过 1,209 项隔离检查，绑定 469 个源码片段和 23 个信号声明，覆盖默认值、空值/未知状态、警告与短路路径、初始化、信号、Stop 及异常边界。该项使用配置、仓储、UI、持久化、设备和信号替身，不代表真实 SDK/设备、原生 UI、构建/DLL 或完整生产调度验收。

传输入料皮带集成当前复验已登记：[当前进度](transport-loading-belt-integration-current-progress.json)及[复验说明](transport-loading-belt-integration-current-review.md)通过 252 项隔离检查，绑定 275 个源码片段和 23 个信号声明，覆盖入料皮带路由、任务协调、Refresh 顺序、状态/配置传播、信号、Save、Stop 及异常边界。修正了夹具中两个硬件名称因编码折叠造成的重复序列标签后，252 个断言标签均唯一。该项使用配置、仓储、UI、持久化、设备和信号替身，不代表真实硬件、原生 UI、构建/DLL 或完整生产调度验收。

传输料仓集成当前复验已登记：[当前进度](transport-loader-bin-integration-current-progress.json)及[复验说明](transport-loader-bin-integration-current-review.md)通过 288 项隔离检查，绑定 302 个源码片段和 23 个信号声明，覆盖料仓路由、超时与重试、推杆顺序、状态/配置传播、信号、Save、Stop 及异常边界。该项使用配置、仓储、UI、持久化、设备和信号替身，不代表真实硬件、原生 UI、构建/DLL 或完整生产调度验收。

传输自动上料集成当前复验已登记：[当前进度](transport-auto-loader-integration-current-progress.json)及[复验说明](transport-auto-loader-integration-current-review.md)通过 238 项隔离检查，绑定 279 个源码片段和 23 个信号声明，覆盖自动上料路由、超时、状态/配置传播、信号、Save、Stop 及异常边界。该项使用配置、仓储、UI、持久化、设备和信号替身，不代表真实硬件、原生 UI、构建/DLL 或完整生产调度验收。

传输自动下料集成当前复验已登记：[当前进度](transport-auto-unloader-integration-current-progress.json)及[复验说明](transport-auto-unloader-integration-current-review.md)通过 287 项隔离检查，绑定 186 个源码片段和 23 个信号声明，覆盖自动下料与 Bond 到等待下料路由、任务协调、状态/配置传播、信号、Save、Stop 及异常边界。该项使用配置、仓储、UI、持久化、设备和信号替身，不代表真实硬件、原生 UI、构建/DLL 或完整生产调度验收。

传输普通料仓集成当前复验已登记：[当前进度](transport-bin-integration-current-progress.json)及[复验说明](transport-bin-integration-current-review.md)通过 578 项隔离检查，绑定 180 个源码片段和 23 个信号声明，覆盖普通料仓与 Bond/等待下料连接路由、任务协调、状态/配置传播、信号、Save、Stop、重试及异常边界。该项使用配置、仓储、UI、持久化、设备和信号替身，不代表真实硬件、原生 UI、构建/DLL 或完整生产调度验收。

传输 Bond 集成当前复验已登记：[当前进度](transport-bond-integration-current-progress.json)及[复验说明](transport-bond-integration-current-review.md)通过 310 项隔离检查，绑定 145 个源码片段和 23 个信号声明，覆盖 Bond 路由、子任务 Task.Run/WaitAll、配置/状态传播、信号、Save、Stop、重试及异常边界。该项使用配置、仓储、UI、持久化、设备和信号替身，不代表真实硬件、原生 UI、构建/DLL 或完整生产调度验收。

传输生产器当前复验已登记：[当前进度](transport-producer-current-progress.json)及[复验说明](transport-producer-current-review.md)通过 870 项隔离检查，绑定 129 个源码片段和 23 个信号声明，覆盖 TransportTask.Start、九个 Task.Run 生产任务、加载枚举、信号发布、Stop/就绪协调及异常路径。该项使用配置、仓储、持久化、设备和信号替身，不代表控制器内部完整动作、真实硬件、原生 UI、构建/DLL 或完整生产调度验收。

传输等待下料集成当前复验已登记：[当前进度](transport-waiting-integration-current-progress.json)及[复验说明](transport-waiting-integration-current-review.md)通过 1,076 项隔离检查，绑定 166 个源码片段和 23 个信号声明，覆盖等待下料皮带/料仓、共享等待包装、任务协调、状态/配置传播、信号、Save、Stop、重试及异常边界。该项使用配置、仓储、UI、持久化、设备和信号替身，不代表真实硬件、原生 UI、构建/DLL 或完整生产调度验收。

UI 启动模式当前复验已登记：[当前进度](ui-start-mode-current-progress.json)及[复验说明](ui-start-mode-current-review.md)通过 262 项隔离检查，绑定 114 个源码片段和 23 个信号声明，覆盖启动模式、就绪判定、状态复位、任务关闭、信号绑定及异常边界。该项使用配置、仓储、持久化、设备和信号替身，不代表原生 UI 事件分发、真实硬件、构建/DLL 或完整生产调度验收。

检查仓储 JSON SDK 运行时当前复验已登记：[当前进度](inspection-repository-json-sdk-runtime-current-progress.json)及[复验说明](inspection-repository-json-sdk-runtime-current-review.md)通过两个隔离 .NET Framework 进程中的 52 个断言位置（26 个独立行为），覆盖 JSON 列表/对象保存读取、缺失文件、序列化错误、目录错误及 Singleton 缓存/加载/并发。该项使用两份 DLL、合成记录和隔离临时目录，不代表产品配置、PR、原生应用、部署 UI 或设备验收。

坐标生命周期当前复验已登记：[当前进度](coordinate-lifecycle-current-progress.json)及[复验说明](coordinate-lifecycle-current-review.md)通过 113 项隔离检查，绑定 3 个未修改坐标源文件，覆盖构造、父子变换、ElementCoordinate 初始化、偏移、边界、VM 标定顺序及失败语义。该项仍是独立坐标探针，不代表 Unit 服务/实体全量组合、原生 SDK、设备或部署验收。

产品 Opposite 生命周期当前复验已登记：[当前进度](product-opposite-lifecycle-current-progress.json)及[复验说明](product-opposite-lifecycle-current-review.md)通过 29 项隔离检查，绑定 7 个源码片段，覆盖产品就绪/类型查找/重置、TransportProgram 重置及 Opposite 配置查找/创建/添加/Save。该项仍是独立生命周期准备探针，不代表原生持久化、递归实体组合、产品配置部署或设备验收。

Singleton Load 当前复验已登记：[当前进度](singleton-load-current-progress.json)及[复验说明](singleton-load-current-review.md)通过 27 项隔离检查，绑定 3 个源码成员并完成 3 个二进制方法元数据检查，覆盖 ProcessDomain 初始化/重置路径。该项不代表产品持久化、原生应用、部署配置、原生 UI 或设备验收。

检查仓储启动准备当前复验已登记：[当前进度](inspection-repository-preparation-current-progress.json)及[复验说明](inspection-repository-preparation-current-review.md)通过 50 项隔离检查，绑定 29 个源码片段并编译 3 个未修改原始源文件，覆盖 19 个方法、7 个属性、2 个字段和 1 个枚举。该项属于启动准备探针，尚未替代检查就绪全量回归、原生持久化、UI/实体集成或设备验收。

载具映射日志 SDK 当前复验已登记：[当前进度](transport-carrier-map-log-sdk-current-progress.json)及[复验说明](transport-carrier-map-log-sdk-current-review.md)通过 2 个方法和 2 组枚举元数据核验，确认 Transport=7、InFileAndUI=3 及 RecordTime 显式调用签名。该项仅证明 Mono.Cecil 元数据与 IL 静态契约，不代表日志 SDK 执行、部署 DLL、原生 UI 或设备验收。

原生动作选择当前复验已登记：[当前进度](native-action-selection-current-progress.json)及[复验说明](native-action-selection-current-review.md)通过两轮、每轮 5,655 项的原始 S1/S2 选择验证，共 11,310 个断言位置，覆盖 34 个注册接收器、26 个选中接收类型、95 个源码声明和 161 个 IL 方法。生产 Task/DoWork、真实 UI、SQL、VM、设备、完整 MSBuild/Fody 和部署仍未执行。

原生动作选择严格进度绑定已修复并复验通过：同步当前计划/交接文档哈希、验证/进度登记及隔离快照九文件；verify-native-action-selection-progress.cjs --check 返回 5,655 项/轮、两轮、11,310 个断言位置。

四个 SDK 准备记录（full-framework、whole-config、whole-entity、whole-action）的当前源码浏览器哈希与产品声明下游指针已同步；完整底层回放仍受历史 transport-loading-belt 夹具哈希阻塞，当前夹具已因稳定标签修复产生新哈希，故仍保持准备项而不宣称完整回放通过。

三项进度校验器已对齐当前 action-catalog 文档闭合日志尾标（保留旧 source-artifact 尾标兼容）：native-mainform-viewport、native-msbuild-build、native-setup-vdproj 均通过严格绑定校验；对应验收仍分别保持布局溢出、完整构建和部署未完成边界。

产品配置原生启动准备的 test/audit 与编译日志快照已同步，verify-product-config-native-progress.cjs --check 通过 36 项断言、72 个位置、22 个原始源文件；产品配置完整启动组合、原生持久化、部署与全量验收仍未完成。

债券配置原生准备、native-dispense-reader、native-runtime-reader 与 native-pr-init-boundary 的结果/审计/快照哈希已同步并通过严格进度校验；这些项仍属于准备或源码阅读边界，未扩展为生产全量验收。

更正：loading-belt 当前夹具哈希已登记到四个 SDK 准备测试与基线，full-framework、whole-action、whole-config、whole-entity 四项完整准备回放现均通过严格校验；历史 carrier-map branch1292 快照仍单独保留旧哈希边界。

Catalog Init SDK 准备项的父 whole-action 进度哈希已同步，verify-catalog-init-sdk-progress.cjs --check 通过 119 项断言、238 个位置；整节点原始编译仍保留 642 个错误和未执行运行时边界。

原始 S2 清零/Retry 调用边界已增量补齐：[IL 进度](original-s2-reset-il.json)及[复核说明](original-s2-reset-il-review.md)锚定当前原始程序集的 `BondTask.DoWork`、`BondHeadController.ResetBondhead` 和 `ModbusService.ResetBondhead`；435 条任务 IL 明确 DoWork 无本地异常处理器，来料成功后按 PickUpCompensationVision→System2TemperatureCompensation→ScanReferencePoints 顺序通过三项补偿门，任一失败早退且均先于 InjectSteps；随后按 InjectSteps→IsFirstDispense→Enable→载具产品/输送配置判断→必要时重建 System2 TransportUnit 并设置 IsProduct→IsNewProduct 顺序初始化上下文；循环按 WaitStart→GetNextActionNode（空值退出）→IsDoWork→CloseDispenseCylinder→节点 DoWork→FinishCurrentActionNode→再次 WaitStart 执行，清零返回值被 `pop` 丢弃后继续首组件查询，Abort/Exception/报警终止的 Stop 与安全位移、Retry 回跳、动作/产品完成、补偿归一化、可选顶针耗时保存、`SendAway` 与 UI 刷新也已固定；两个清零方法各含 Catch 处理器，控制器按 ForceZeroMode 选择 Modbus/IO，IO 30ms 延迟和 Retry/Ignore/Abort 映射、到 Modbus/`Machine.Stop` 的调用关系及 34 条 Modbus IL（寄存器 94、50ms 等待、二次写入）已通过绑定校验。该项仍未执行真实 Retry、UI、Modbus、轴、数据库、VM、硬件或部署验收，整体目标未完成。

原始 S2 来料信号门已增量补齐：[IL 进度](original-s2-incoming-signal-il.json)及[复核说明](original-s2-incoming-signal-il-review.md)固定 `BondTask.GetIncomingSignal` 的 103 条 IL、11 个分支和 14 个调用：补偿模式直通、已配置输送等待完成信号、未配置输送时提示/映射/停止路径均已通过绑定校验。该项仍未执行真实信号、对话框、输送、任务、UI、数据库、VM 或设备验收，整体目标未完成。

原始 S2 完成后送走载具边界已增量补齐：[IL 进度](original-s2-send-away-il.json)及[复核说明](original-s2-send-away-il-review.md)固定 `BondTask.SendAway` 的 120 条 IL、7 个分支和 19 个调用：输送配置下的允许传送信号、Stop 抑制，以及无输送配置下的 AutoSaveMapping、载具清理和人工取料提示均已通过绑定校验。该项仍未执行真实传送、Mapping 持久化、UI、任务、数据库、VM 或设备验收，整体目标未完成。

原始 S2 任务入口已增量补齐：[IL 进度](original-s2-start-il.json)及[复核说明](original-s2-start-il-review.md)固定 `BondTask.Start` 的 33 条 IL、4 个分支和 6 个调用：Running 状态门、`Task.Factory.StartNew`、`CancellationToken.None`、`TaskCreationOptions.LongRunning`、默认调度器和返回 `true` 均已通过绑定校验。该项仍未执行真实线程、异常监督、停止回收、并发或生产设备验收，整体目标未完成。

原始 S2 任务工作线程目标已增量补齐：[IL 进度](original-s2-start-worker-il.json)及[复核说明](original-s2-start-worker-il-review.md)固定 `BondTask.<Start>b__20_0` 的 8 条 IL：先设置“固晶工作线程”线程名，再调用 `DoWork()`，两处调用和无分支结构均通过绑定校验。该项仍未执行真实调度、异常监督、停止回收、并发或生产设备验收，整体目标未完成。

原始 S2 任务关闭入口已增量补齐：[IL 进度](original-s2-abort-thread-il.json)及[复核说明](original-s2-abort-thread-il-review.md)固定 `BondTask.AbortThread` 只有 `nop`/`ret` 两条 IL、无调用和无分支，确认该入口不会取消或 Dispose `BondWorkTask`。该项仍未执行真实停止回收、并发或生产设备验收，整体目标未完成。

S2 Task integration 夹具按当前源码快速复跑：`test-s2-task-integration.cjs` 与 `build-s2-task-integration-audit.cjs --check` 均通过 59 项检查、13 个原始方法提取；该结果保留受控服务、信号、动作、Stop、Retry/异常和存储替身边界，不扩大为真实设备、完整调度或部署验收。

S2 door pause 夹具按当前源码快速复跑：`test-s2-door-pause.cjs` 与 `build-s2-door-pause-audit.cjs --check` 均通过 37 项检查、17 个原始方法提取；该结果保留门暂停/恢复、单步、来料等待、Stop 抑制和动作失败推进的受控线程与信号替身边界，不扩大为真实传感器、UI、设备或生产部署验收。

S2 消息/层级状态夹具按当前源码快速复跑：`test-s2-context-update.cjs` 的 14 项检查全部通过，覆盖消息绑定、禁用步骤保留、重复项选择顺序、层级缺失、仓储异常和空输入边界；结果仍限定于受控容器与仓储替身，不扩大为真实配方、任务、UI、硬件或部署验收。

S2 节点选择与预点胶分配夹具按当前源码快速复跑：`test-s2-node-selection.cjs` 通过 9 项检查，覆盖未完成节点、Finish 推进、特殊节点重复拒绝、缺失注册和空输入；`test-s2-predispense-allocation.cjs` 通过 13 项检查，覆盖网格端点、列主序索引、初始化/保存、耗尽重建、维度变化、越界和保存失败状态。两项仍限定于受控节点、坐标、参数、UI 答案和保存替身，不扩大为完整任务、设备或部署验收。

原始 S2 动作前点胶气缸门已增量补齐：[IL 进度](original-s2-close-cylinder-il.json)及[复核说明](original-s2-close-cylinder-il-review.md)固定 `BondTask.CloseDispenseCylinder` 的 16 条 IL、1 个分支和 4 个调用：按动作 `IsCloseCylinder` 决定是否调用 `S2DispenseController.CloseDispenseHeightMeasurementCylinder()`。该项仍未执行真实气缸、点胶、任务或生产设备验收，整体目标未完成。

S2 补偿前置快速复核（2026-10-07）：直接复核既有 primary/replay 隔离产物，严格绑定校验两轮各 51 项、31 个方法、5770 项冻结绑定通过；未扩大为真实 UI、Modbus、轴、SQL、VM、硬件或部署验收，整体目标未完成。

S2 既有冻结产物并行快速复核（2026-10-07）：native-s2-action-boundaries 两轮各31项、native-s2-reset-propagation 两轮各70项、native-s2-shelf-gates 两轮各58项、native-s2-task-entry 两轮各497项均通过严格校验；任务入口实际 S2 122 tasks/轮、20 完成与 102 在料架轴前故障，未扩大为节点动作、私有写、VM、UI、SQL、设备或完整构建验收。

S2 自检运行时边界已补齐（2026-10-07）：在保留真实设备/UI/SQL/VM 未执行边界的前提下，接入 native-s2-readiness 原始 16 程序集 bound/replay 两轮实际运行；每轮 56 项、13 行就绪矩阵、12 个拒绝/恢复门、26 次公开 UI 分派，System2Domain.CheckIsReady() 离线受控路径通过，verify-s2-self-check-runtime-current.cjs 与原始 S2 自检 IL 校验均通过。硬件自检、视觉、生产 Task、节点 DoWork 和 UI 继续链仍未执行，整体目标未完成。

整机环境源码阅读器指针已复核（2026-10-07）：新增 verify-native-machine-environment-reader-pointer.cjs，绑定整机环境 123 项/135 文件与当前 native-runtime-reader 47 主题、4997 快照、63 源文件、1456 声明及 0 浏览器错误；当前 artifact SHA 一致，旧 browser-results.json 哈希仅保留历史边界。Machine.Start、Prepare、硬件自检、设备、SQL、VM、部署仍未验收。

传输教学聚合 pending 已完成当前证据对照（2026-10-07）：29 个 next-evidence 源片段逐项匹配当前 1,144 项教学集成测试的源码/片段 SHA-256，均已实际编译并执行；结果独立记录于 transport-teaching-aggregation-current.json，历史 next-evidence 快照保持原哈希。真实 SDK、原生 UI、生产调度、SQL、VM、设备、构建与部署仍未验收。

当前 transport 教学隔离重绑定已完成（2026-10-07）：run-transport-teaching-current-rebind.cjs 在不改写历史 integration-test 快照的前提下，使用当前 loading-belt harness 重新执行 1,144 项、449 个源码片段和 23 个信号绑定；verify-transport-teaching-current-rebind.cjs 通过，历史快照恢复哈希一致。旧正式整合审计仍保留 branch1292 loading-belt 旧哈希边界，故不将该隔离结果升级为完整生产验收。

检查就绪与检查仓储当前源码复核已并行完成（2026-10-07）：transport-inspection-readiness 1,209 项/469 个源码片段/23 个信号绑定，transport-inspection-repository 1,303 项/498 个源码片段/23 个信号绑定均通过当前注册器；真实 SDK、原生 UI、生产调度、SQL、VM、设备、构建和部署仍未验收。

当前源码集成复核继续完成（2026-10-07）：传输产品声明 1,328 项/512 个源码片段、Transport Unit 服务 1,011 项/391 个源码片段、坐标与产品路由 1,031 项/420 个源码片段均通过当前注册器；真实标定、SDK、原生 UI、SQL、VM、设备、构建和部署仍未验收。

三项输送集成审计产物已按当前正式测试快照串行重建并复核：Unit 服务 1,011 项/391 片段、坐标产品 1,031 项/420 片段、产品声明 1,328 项/512 片段的 build-*integration-audit.cjs --check 均通过；后续共享输出操作采用串行运行以保持哈希稳定。

产品 Opposite 生命周期当前复核继续完成（2026-10-07）：当前源码隔离探针 29 项/7 个源码片段通过，产品配置原生数据准备 36 项/72 个位置/22 个源码文件也通过；完整启动组合、真实持久化、VM、设备、构建和部署仍未验收。

独立坐标生命周期当前复核已刷新（2026-10-07）：3 个未修改坐标源文件的 113 项检查通过，覆盖构造、父子变换、ElementCoordinate 初始化、偏移、边界、VM 标定顺序及失败语义；与 1,031 项坐标/产品组合审计分别计数，原生 SDK、设备、产品配置和部署仍未验收。

仓储/单例数据证据继续完成（2026-10-07）：Singleton Load 当前复核通过 27 项、3 个源码成员和 3 个二进制方法；检查仓储启动准备通过 50 项、29 个源码片段、3 个未修改源文件；双 DLL JSON SDK 运行时通过 52 个断言位置（26 个独立断言、2 个隔离进程）。产品持久化、原生应用、部署 UI、SQL、VM、设备和完整启动组合仍未验收。

原生 Program.Main 启动入口当前复核已完成（2026-10-07）：native-program-main-entry 绑定校验通过 41 项/轮、19,106 个冻结绑定，当前源码清单 246 个文件重新指纹；保留线程未 Join、布局裁切和无硬件边界，未扩大为完整主程序、设备或部署验收。

原生 MainForm 当前绑定复核继续完成（2026-10-07）：上下文 40 项/14,205 绑定、关闭保存 60 项/14,818 绑定、布局合成 47 项/18,705 绑定均通过；当前源码清单分别重新指纹，保留布局裁切、保存失败、后台线程和无设备边界，未宣称完整 UI 或部署验收。

当前检查链已收敛（2026-10-07）：新增 verify-transport-inspection-current-chain.cjs，严格绑定教学重绑定→检查就绪→检查仓储当前源码链 1,144→1,209→1,303 项；教学 171 个源输入、就绪 180 个源输入和两组 next-evidence 接续均被下游当前测试纳入。仓储启动准备仍单独报告 1 个历史 loading-belt 哈希漂移，未改写历史输入。

原生源码浏览器证据当前复核已完成（2026-10-07）：runtime source explorer 47 个主题/4,997 个证据（240 个运行时边界）、dispense source explorer 52 个主题/5,257 个证据（500 个运行时边界）均无浏览器错误；仅证明浏览器证据选择与渲染，不扩大为生产运行、VM、SQL、设备或部署验收。

焊后检测就绪与原动作控制器当前复核已完成（2026-10-07）：bond-inspection-readiness 通过 45 项/22 个源码片段；native-action-controller 通过 251 项（目录子检查 119）、37 个具体节点、16 个排程、3,292 个冻结绑定，两轮回放一致。完整生产 Task、PR/VM/SQL、UI、设备、构建和部署仍未验收。

启动准备历史漂移已隔离（2026-10-07）：新增 verify-transport-inspection-startup-preparation-current-rebind.cjs，按当前 loading-belt 哈希重绑定教学 20 项、检查就绪 20 项、检查仓储 44 项三份静态快照，所有源码片段校验通过，历史快照保持原字节；该收据不宣称新增原生 UI/设备运行。

整机源码闭包候选已复核（2026-10-07）：在正式 123 输入外追加 33 个真实 Dispense/BondForce/Wafer 依赖源文件进行隔离编译，候选错误 1,176，高于正式基线 642，故按 register-whole-node-source-closure-candidate.cjs 保留为未提升候选；正式基线未改写，后续需拆分缺失依赖闭包而非直接并入。

整机源码闭包已完成分组诊断（2026-10-07）：以正式 123 输入为基线分别追加 Dispense 9 个源文件（132 输入/686 错误）、BondForce/Nozzle 7 个源文件（130 输入/654 错误）、Wafer 16 个源文件（139 输入/1,120 错误）；三组均高于正式 642，均登记为诊断候选，未提升或改写正式编译基线。

完整原动作控制器 SDK 当前重绑定已完成（2026-10-07）：历史回执中的产品声明 test/audit 两个输入哈希相对当前正式文件发生漂移；新增当前重绑定验证器按当前哈希重新核验两份 SDK 各 278 项、556 个放置、54 个原始源文件、55 个编译单元和两份运行日志，均通过。历史 whole-action 回执未改写，仍不加入正式 1328 回归；完整域、具体节点 DoWork、PR/校准/测量、Fody、构建、部署、原生 UI 和设备仍待验收。

动作下层快速复核已完成（2026-10-07）：轴相对移动 IL 契约 12 项/6 方法、到位等待 8 个调用点/8 个驱动方法、安全移动序列 10 条消息/20 个锚点及 1440/850/390 三种浏览器视图均通过；范围仍是元数据、源码/IL 和浏览器证据，不扩大为真实轴、IO、相机、设备或生产任务验收。

原生节点前置与检测就绪当前重绑定已完成（2026-10-07）：两套旧进度验证器共同受 transport-product-declarations 历史 post-documentation 计划哈希影响；在保留历史回执的前提下，当前重绑定重新通过节点前置 584 项/9,836 绑定与检测就绪 108 项/10,344 绑定，历史快照和下游指针均保持一致。该结果仍不扩大为在线动作、完整生产 Task、PR/校准/测量、SQL、VM、设备、联合构建或部署验收。

后台任务与持久化边界快速复核已完成（2026-10-07）：通知 IL 24 个 Task.Run 调用点/6 个 DoWork 通知点、后台任务契约 14 方法/3 源文件、持久化 Save 契约 9 方法/12 个源码哈希、持久化写入入口 5 个直接写入/11 个来源、信号等待与任务状态锚点、后台任务和邦头校准图均通过；生产配置门浏览器 134 条证据及响应式视图无错误。TemperatureCompensationEntity 仍保留为未匹配源码缺口，未扩大为真实任务、磁盘、UI、轴、设备或部署验收。

温补数据库消费者隔离回放已复跑（2026-10-07）：`test-async-db-consumer.cjs` 的 11 项受控检查通过，确认温补对象被取出后无 Insert/告警分支但后续对象仍可继续消费；该结果使用真实 `BlockingCollection` 与受控数据库替身，不连接现场数据库，也不替代并发、线程重启或生产设备验收。

生产启动与任务入口当前复跑已完成（2026-10-07）：生产启动 30 项、普通启动 175 项/91 个源码片段、启动配置 63 项/29 个成员、启动入口 43 项/39 个成员、任务并发 47 条、UI 启动模式 262 项/114 个源码片段及对应 6 份审计均通过。该链仍使用受控调度器、工作线程、UI/状态替身，不代表在线生产、真实 Stop/设备、SQL/VM 或部署验收。

生产任务生命周期当前重绑定已扩展（2026-10-07）：配方任务生命周期 100 项/3,376 绑定、Machine Stop 70 项/3,418 绑定直接通过；在共享历史计划哈希漂移下，Machine task closure 310 项/10,761 绑定、退出消费者 25 项/17,846 绑定、监控消费者启动 40 项/18,295 绑定经当前重绑定重新通过，历史快照保持不变。仍保留真实在线任务、设备动作、SQL、VM、UI 和部署边界。

输送任务与上下料当前重绑定已扩展（2026-10-07）：Transport context 180 项/3,322 绑定直接通过；Transport environment 3,141 项/11,799 绑定、晶圆输送入口 660 项/11,165、Loader/Unloader 773 项/11,381、进出料握手 550 项/11,622、料仓握手就绪 834 项/11,474 在共享历史计划哈希漂移下经当前重绑定通过，历史快照未改写。真实输送设备、在线动作、SQL/VM、联合构建和部署仍待验收。

原生 S1/S2 动作链当前重绑定已扩展完成（2026-10-07）：在同一历史计划哈希漂移下，当前重绑定重新通过 S1 工作循环 126 项/10,006 绑定、步骤提交 85 项/10,096、停止恢复 51 项/10,164、缺陷结果 109 项/10,250、S2 任务入口 497 项/10,857、S2 就绪 56 项/10,455；连同节点前置与检测就绪共 8 套验证器，历史快照均保持不变。仍未宣称在线生产、完整 Retry、设备、SQL/VM、联合构建或部署完成。

当前原生重绑定复核已提速（2026-10-07）：统一验证器现按每批 4 个独立进程并行执行 29 套检查；本轮完整回放耗时约 1.87 秒，29 套结果与历史快照均通过，正式整机编译基线仍保持 123 输入/642 错误/退出码 1。

原生任务与配方/UI 生命周期当前重绑定已扩展（2026-10-07）：辅助任务 487 项/10,974 绑定、载具就绪 100 项/10,544、整机环境 123 项/10,685、配方实时重载 93 项/11,965、配方 UI 重载 48 项/12,379、UI 停止恢复 572 项/12,534 均按当前源码重新通过；历史快照未改写，真实在线任务、完整 UI、设备、SQL/VM、联合构建和部署边界保持不变。

主程序与配方交互当前重绑定已扩展（2026-10-07）：MainForm 上下文 40 项/14,205 绑定、关闭保存 60 项/14,818、布局 47 项/18,705、PR 初始化边界 31 项/14,446、Program.Main 41 项/19,106、配方新建拷贝 163 项/13,651、配方对话框 89 项/12,916 均按当前源码通过；客户区矩阵 71 项继续保留独立当前校验边界，未改写正式历史回执。

算法与动作选择当前重绑定已补齐（2026-10-07）：配方动作选择 31,655 项/9,734 绑定、算法选择 163 项/9,609 绑定按当前源码重新通过；历史快照保持不变，实际生产 Task、算法 VM、PR/SQL、在线 UI、设备和部署边界继续单独登记。

点胶与消费者支线当前校验已复跑（2026-10-07）：点胶控制 35/6,163、控制器 40/6,653、窗体 40/6,444、输入 44/6,380、策略 51/6,594、几何 50/6,111、源码读取 260/6,535、渲染 42/6,326、数据库保存 42/3,461、力控校准 46/5,961、统计生产者 60/3,491、视觉图像队列 53/3,579 项/绑定均通过当前校验；SQL 写入、算法 VM、真实设备和在线生产边界保持未验收。

构建与部署前置当前重绑定已完成（2026-10-07）：MSBuild 当前校验保留 40 次构建调用、源清单 19,106 和正式运行时检查 1,328；Setup/Vdproj 当前校验保留 465 条记录（393 存在、72 缺失、195 依赖）。两项均隔离旧计划哈希漂移并通过非计划历史快照校验，未生成 MSI、未安装，完整联合构建和部署仍待验收。

三项输送 SDK 准备当前重绑定已完成（2026-10-07）：full-framework 通过受控 1,328 项、SDK 116 项/两份副本；whole-config 通过 142 项、284 个放置；whole-entity 通过 187 项、374 个放置。三项均重新验证编译/运行退出码 0、产物一致和 3,817 个浏览器主题快照，保留两个产品声明输入哈希漂移，未并入正式 1,328 回归。

源码读取与配置准备当前重绑定已扩展（2026-10-07）：dispatch source reader 9,513 绑定、virtual dispatch provenance 9,474 绑定、Bond 配置准备 56 项/112 个放置、产品配置准备 36 项/72 个放置均按当前输入或计划哈希重新通过；历史快照保持不变，完整启动组合和生产运行边界继续保留。

MainForm 客户区矩阵当前重绑定已完成（2026-10-07）：两轮各 71 项视口检查按当前计划重新通过，保留 6 组视口矩阵、右侧 384 与底部 206 的已知溢出，以及完整源码/下游快照校验；布局修复、在线设备、VM、SQL、联合构建和部署仍未验收。

整机源码闭包细分诊断已完成（2026-10-07）：以正式 123 输入分别追加 Dispense 参数/程序 18 个文件（141 输入、700 错误）、BondForce/Nozzle 扩展 73 个文件（196 输入、1,499 错误）、Wafer/搜索芯片扩展 26 个文件（149 输入、1,072 错误）。三组均高于正式 642，均保留为依赖诊断候选，未提升或改写正式编译基线。

整机源码闭包最小候选出现错误下降（2026-10-07）：仅追加 `DispenseRunTimeProvider.cs` 与 `EpoxyApplicationLocation.cs` 后，候选 125 输入、574 个错误，较正式 642 减少 68 个；候选仍退出码 1，已登记为未提升诊断，正式基线保持 123/642/1。
整机源码闭包下一层探针已完成（2026-10-07）：以两个 Dispense 参数文件的 574 错误种子并行比较六组依赖组合；BondDevicePara 组合为 126 输入/553 错误（较正式基线减少 89、较种子减少 21），统计/力控 127/585、点胶枚举程序 129/579、补偿服务 129/583、吸嘴核心 129/581，控制器组合 128/1085。最佳结果仍退出码 1，已登记为未提升候选；正式基线保持 123/642/1，后续继续沿 BondDevicePara 传递依赖补齐。
源码闭包探针执行已提速（2026-10-07）：六组独立编译改为最多 4 个并行槽，本轮约 10.16 秒完成；六组错误计数与输入哈希保持一致，最佳 BondDevicePara 仍为 126 输入/553 错误，未改变正式 123/642/1 基线。
整机源码闭包 BondDevicePara 种子继续补齐（2026-10-07）：以 126 输入/553 错误候选为种子，最多 4 槽并行比较六组传递依赖；同目录 BondSystem/Models/DeviceParams 全量组合为 134 输入/544 错误，较正式基线减少 98、较种子减少 9。统计/力控 129/567、点胶服务 132/616、校准/温补 130/610、控制器组合 142/1,158、吸嘴/补偿 154/657。最佳候选仍退出码 1，已登记为未提升诊断，正式基线保持 123/642/1。
整机源码闭包设备参数候选继续下降（2026-10-07）：以 134 输入/544 错误候选为种子，并行比较六组直接依赖；吸嘴核心为最佳 138 输入/539 错误，较正式基线减少 103、较种子减少 5。校准参数 135/540、点胶枚举程序 136/543、力控服务 135/548、统计 135/551、BondModule 135/622。539 候选仍退出码 1，已登记为未提升诊断，正式基线保持 123/642/1。
整机源码闭包吸嘴种子继续下降（2026-10-07）：以 138 输入/539 错误候选为种子，最多 4 槽并行比较七组直接依赖；System1Domain 与 System2Domain 组合最佳为 140 输入/509 错误，较正式基线减少 133、较种子减少 30。FrequencyConsumables 为 139/537、点胶枚举为 140/538、统计/力控/校准为 141/546、晶圆域任务为 140/766、大组合为 146/769。509 候选仍退出码 1，已登记为未提升诊断，正式基线保持 123/642/1。
整机源码闭包 System Domain 候选继续下降（2026-10-07）：以 140 输入/509 错误候选为种子，最多 4 槽并行比较六组小依赖；FrequencyConsumables 与点胶枚举/程序组合最佳为 143 输入/502 错误，较正式基线减少 140、较种子减少 7。单独耗材 141/507、点胶枚举 142/505、统计 141/512、力控/校准 142/509，全部小依赖组合 146/505。502 候选仍退出码 1，已登记为未提升诊断，正式基线保持 123/642/1。
整机源码闭包 502 候选下层探针已完成（2026-10-07）：以 143 输入/502 错误候选并行比较六组依赖；TimeConsumable 保持 144/502，BondProgram 146/517、点胶 Services/Modules 150/612、统计/力控/校准 146/505、Bond 控制器 158/926、晶圆控制器 144/620。未发现低于 502 的候选，正式基线保持 123/642/1，结果仅用于依赖排序。
整机源码闭包晶圆单文件探针已完成（2026-10-07）：以 143 输入/502 错误候选为种子分别追加 WaferSystemDomain（144/594）、WaferSubSystemTask（144/640）、两者组合（145/726）和 Eject/Flip 控制器（144/620）；没有低于 502 的结果，正式基线保持 123/642/1。
整机源码闭包 502 聚焦探针已完成（2026-10-07）：以 143 输入/502 错误候选分别追加 BondProgram（144/511）、S2DispenserProgram（144/505）、System2Controller（144/595）、BondModuleController（144/573）、DispenseModule（144/551）、System2ActionNodesService（144/517）、ForceCalibrationService（144/506）和 StatisticsDomain（144/505）。没有低于 502 的结果，正式基线保持 123/642/1。
整机源码闭包命名空间探针已完成（2026-10-07）：以 143 输入/502 错误候选并行比较四个缺失命名空间单文件；加入 ActionNodesSortService 后得到 144 输入/496 错误的当前最佳诊断候选，较正式基线减少 146、较前候选减少 6；TimeConsumable 为 145/528、DispenserMoveHelper 为 145/531、ModbusService 为 145/505。496 候选仍退出码 1，未提升正式基线，后续继续补齐跨子系统符号。
整机源码闭包服务依赖探针已推进（2026-10-07）：JudgeHelper、CoordinateSystemHelper、ForceConfig、DefectCompensate、FlipTool 五个低依赖文件逐轮将候选从 144/496 降到 149/473；随后 14 个服务/参数文件复探均未低于 473。473 候选仍退出码 1，仅保留为未提升诊断，正式 123/642/1 基线不变。
整机源码闭包根类型与程序探针已推进（2026-10-07）：CalibrateRunPara、IPTController、SlideFluxerController、UpLookController 组合将候选推进到 153/465；程序组合未改善，EpoxyApplication、GeometryService、DispenserMoveHelper 逐轮将候选推进到 156/456。后续根类型复探仍以并行探针排序依赖，456 候选仍退出码 1，正式 123/642/1 基线不变。
整机源码闭包统计与力控依赖已推进（2026-10-07）：StatisticsDomain、六个统计实体和 DBService 将候选推进到 164/444；ForceCalibrationService 与 ForceCalibrationData、ForceRelateAngleItem 再推进到 167/427。Modbus 扩展及 Bond/Wafer 高耦合组合未改善，427 候选仍退出码 1，正式 123/642/1 基线保持不变。
整机源码闭包力控配置探针已推进（2026-10-07）：单独加入 RtuConnectConfig.cs 将候选推进到 168/423；在已有配置上复测 ModbusService、统计服务、耗材、程序和视觉服务，均未低于 423。423 候选仍退出码 1，仅保留为未提升诊断，正式 123/642/1 基线不变。
整机源码闭包模块探针已推进（2026-10-07）：SlideFluxer.cs 将候选推进到 169/422；UpLookModule、EjectModule、MagazineBoxModule、FlipModule 和 WaferTableModule 均未降低错误，422 候选仍退出码 1，正式 123/642/1 基线保持不变。
整机源码闭包耗材探针已推进（2026-10-07）：以 169 输入/422 错误候选为种子，最多 4 槽并行比较 BaseConsumable、TimeConsumable、FrequencyConsumables 及 UI 组合；BaseConsumable+TimeConsumable 得到 171 输入/413 错误，较正式基线减少 229、较前候选减少 9。候选仍退出码 1，已登记为未提升诊断，正式 123/642/1 基线保持不变。
整机源码闭包 413 下一层探针已完成（2026-10-07）：以 171 输入/413 错误候选并行比较晶圆控制器/参数、SearchChip、Bond 控制器、点胶程序和任务闭包；点胶程序组为 176/417，晶圆参数 177/438，任务 174/445，程序细分的 FlipModuleProgram 保持 172/413，均未低于 413。候选仍退出码 1，正式 123/642/1 基线保持不变。
整机源码闭包 413 单符号与交叉探针已完成（2026-10-07）：FlipTableController 单文件为 172/414、NozzleShelfController 为 172/416；两者交叉及 BondProgram 组合最低为 173/417，未产生低于 413 的候选。候选仍退出码 1，正式 123/642/1 基线保持不变。
整机源码闭包程序实现闭包已推进（2026-10-07）：以 171 输入/413 错误候选并行比较 FlipTask、模块实现和程序实现；加入 `SlideFluxerProgram.cs` 后得到 172 输入/411 错误，`DispenserProgram.cs` 为 172/412，其余均未更低。411 候选仍退出码 1，已登记为未提升诊断，正式 123/642/1 基线保持不变。
整机源码闭包程序实现复跑已推进（2026-10-07）：以新的 172 输入/411 错误候选重跑单文件探针，加入 `DispenserProgram.cs` 后得到 173 输入/410 错误，较前候选再减少 1；SlideFluxerProgram、FlipModule 和 NozzleShelfModule 未继续下降。410 候选仍退出码 1，已登记为未提升诊断，正式 123/642/1 基线保持不变。
整机源码闭包 S2 程序组合探针已完成（2026-10-07）：以 173 输入/410 错误候选比较 BondProgram、S2DispenserProgram 及其最小组合，最低为 175/412；加入更多 S2 程序或 NozzleShelfController 后更高，未低于 410。候选仍退出码 1，正式 123/642/1 基线保持不变。
整机源码闭包 SearchChip 实体已推进（2026-10-07）：以 173 输入/410 错误候选拆分 SearchChip 单文件，PickRefEnd.cs 与 ReferencePoint.cs 各自得到 174/408；近邻组合未继续下降。为保持最小输入，登记 PickRefEnd.cs 的 174/408 候选，仍退出码 1，正式 123/642/1 基线保持不变。
整机源码闭包 SearchChip 408 复跑已完成（2026-10-07）：以 174 输入/408 错误候选重跑 SearchChip 单文件，MarkedDie、ReferencePoint、WaferMapDataConfig 以及晶圆域/弹出模块组合均未低于 408，当前候选保持不变，正式 123/642/1 基线保持不变。
整机源码闭包支持类型探针已完成（2026-10-07）：以 174 输入/408 错误候选并行验证 MachineStateModel、PREntity、UcMainSystem、力控曲线窗体和 Machine.SelfCheck；最低为 UcmainSystem.Action 的 175/461，均高于 408，正式 123/642/1 基线保持不变。
整机源码闭包点胶程序尾部已推进（2026-10-07）：以 174 输入/408 错误候选验证剩余点胶程序，System1OtherProgram.cs 单独为 175/406、EpoxyApplicationProgram.cs 为 175/407；两者组合得到 176/405，较正式基线减少 237、较前候选减少 3。405 候选仍退出码 1，已登记为未提升诊断，正式 123/642/1 基线保持不变。
整机源码闭包 405 程序后续复核已完成（2026-10-07）：在已有 System1OtherProgram 与 EpoxyApplicationProgram 闭包上加入 PreDispense、EpoxyMaterial、S2EpoxyMaterial、S2PreDispense 或 NozzleShelfModule 均未低于 405，最低保持 177/405，正式 123/642/1 基线保持不变。
整机源码闭包 Bond 程序增量已推进（2026-10-07）：以新的 176 输入/405 错误候选重跑程序/模块近邻探针，单独加入 `BondProgram.cs` 后得到 177 输入/404 错误，其余程序和模块未低于 405。404 候选仍退出码 1，已登记为未提升诊断，正式 123/642/1 基线保持不变。
整机源码闭包 404 协同复跑已完成（2026-10-07）：以 177 输入/404 错误候选重跑点胶、S2、Flip 和模块尾部文件，S2EpoxyMaterialProgram 最低为 178/406，其余均保持或高于 404，正式 123/642/1 基线保持不变。
整机源码闭包 CleanNozzle 程序已推进（2026-10-07）：以 177 输入/404 错误候选验证缺失程序类型，单独加入 `CleanNozzleProgram.cs` 得到 178 输入/402 错误，较正式基线减少 240、较前候选减少 2；与 Nozzle/S2 邻接组合未继续下降。402 候选仍退出码 1，已登记为未提升诊断，正式 123/642/1 基线保持不变。
整机源码闭包点胶/补偿支持组合已推进（2026-10-07）：以 178 输入/402 错误候选验证点胶参数与 MotionAreaCompensate，加入 `PreDispensePlatePara.cs` 与 `CompensateCalculator.cs` 后得到 180 输入/398 错误，较正式基线减少 244、较前候选减少 4；加入 DataService 为同错但多输入。398 候选仍退出码 1，已登记为未提升诊断，正式 123/642/1 基线保持不变。
整机源码闭包 398 支持复跑已完成（2026-10-07）：以 180 输入/398 错误候选重跑点胶仓储、任务和补偿文件，Dispenser/仓储保持 398，BondCompensate 为 399，DispenseWorkTask 为 401，未发现低于 398 的候选，正式 123/642/1 基线保持不变。
整机源码闭包缺失任务探针已完成（2026-10-07）：以 180 输入/398 错误候选拆分 SlideFluxerTask、BondTask、CalibController、S2DispenseController、System2Controller 和 NozzleShelfProgram；最低为 SlideFluxerTask 的 181/404，未发现低于 398 的候选，正式 123/642/1 基线保持不变。
整机源码闭包配置路径探针已完成（2026-10-07）：以 180 输入/398 错误候选验证 ZX2200PathConfig、PathConfig 与 MachineConfigContext；ZX2200PathConfig 为 181/449、MachineConfigContext 为 181/442，路径组合未形成可用下降，未发现低于 398 的候选，正式 123/642/1 基线保持不变。
整机源码闭包设备参数增量已推进（2026-10-07）：以 180 输入/398 错误候选验证补偿、产品、工具和设备参数来源，加入 `FlipTableDevicePara.cs` 后得到 181 输入/393 错误，较正式基线减少 249、较前候选减少 5；其余来源未低于 398。393 候选仍退出码 1，已登记为未提升诊断，正式 123/642/1 基线保持不变。
整机源码闭包 393 符号来源复跑已完成（2026-10-07）：以 181 输入/393 错误候选重跑补偿、产品、工具和 BondHead 来源，TransportUnitCompensate 与 ProductDomain 保持 393，其余更高，未发现低于 393 的候选，正式 123/642/1 基线保持不变。
整机源码闭包瓦片台控制器增量已推进（2026-10-07）：以 181 输入/393 错误候选并行验证 EjectController、FlipTableController、WaferSubController 和 FlipTask；加入 FlipTableController.cs 得到 182 输入/392 错误，较正式基线减少 250、较前候选减少 1。其余候选均更高，候选仍退出码 1，正式 123/642/1 基线保持不变。
整机源码闭包 Flip 模块依赖已推进（2026-10-07）：以 182 输入/392 错误候选加入 FlipModule.cs 后降至 183/389，再加入 FlipModuleProgram.cs 降至 184/387，较正式基线减少 255、较前候选减少 2。其余晶圆模块依赖均更高，候选仍退出码 1，正式 123/642/1 基线保持不变。
整机源码闭包 Flip 程序依赖复核已完成（2026-10-07）：以 184 输入/387 错误候选验证 FlipToolRepository、EjectionBank 仓储、Static/DataOffsetHelper 及 Wafer 组合；最低保持 387，未产生更低候选，正式 123/642/1 基线保持不变。
整机源码闭包 Bond partial 闭包复核已完成（2026-10-07）：以 184 输入/387 错误候选比较 BondHead、BondModule、System2 和 NozzleShelf 组合，最低仍为 387，未发现可登记的新候选，正式 123/642/1 基线保持不变。
晶圆视觉/几何清单当前复验已完成（2026-10-07）：按当前源码并行重跑几何 180 项、视觉控制 118 项、视觉采集 112 项，三项测试与审计均通过；实际 SDK、标定、设备、UI、SQL/VM 和完整联合构建边界仍按原清单保留。
搜晶停止/动作门控复验已完成（2026-10-07）：当前源码 172 项检查、9 个源码片段和 2 个信号绑定重新通过，搜晶图同步校验 12 节点/15 关系通过；真实并发、设备轴、完整 TransportDomain.StartTask 和联合构建边界仍保留。
完整 Machine 启动与 TransportDomain.StartTask 当前复验已完成（2026-10-07）：按当前源码重跑 175 项启动组合检查与审计均通过，覆盖 Machine.Start、PrepareMachineReadyToStart、TransportDomain.StartTask、晶圆启动、模式分派及 Stop；TransportTask.Start 原始生产者、外层 delegate、真实 UI 启动调用、配置/DLL、SDK/设备和完整联合构建边界仍按清单保留。
启动准备辅助当前复验已完成（2026-10-07）：按当前源码重跑 303 项检查与审计均通过，覆盖 ResetMachineSignal、任务状态、MachineInitSuccess、CheckOperatingEnvironment 和就绪失败顺序；CleanFile、完整生产配置、原生 UI、SDK/设备与联合构建边界仍按清单保留。
TransportTask.Start 完整生产者当前复验已完成（2026-10-07）：按当前源码重跑 870 项、129 个源码片段及审计均通过，覆盖九个 Task.Run 生产任务、ConfigureAwait、信号发布、Stop/就绪协调和异常路径；控制器内部真实动作、硬件、原生 UI、构建/DLL 与完整生产调度边界仍保留。
UI 启动/模式调用边界当前复验已完成（2026-10-07）：按当前源码重跑 262 项、114 个源码片段及审计均通过；真实原生 UI 消息循环、SDK/设备和联合构建边界仍未宣称完成。
TransportUnit/TuService 生命周期当前复验已完成（2026-10-07）：按当前源码重跑 1011 项检查、391 个源码片段及审计均通过，覆盖实体、坐标/行列/索引、状态掩码和服务生命周期；真实设备 SDK、原生 UI、SQL/VM、部署与完整联合构建边界仍按清单保留。
传输载具/地图整链当前复验已完成（2026-10-07）：按当前源码重跑 1355 项、341 个源码片段、23 个信号绑定及审计均通过，覆盖载具配置、地图状态、报警/Retry、启动刷新、装载段和 Stop；完整动作注入、真实日志、原生 UI、构建/DLL 与设备行为仍按清单保留。
S1 点胶任务当前复验已完成（2026-10-07）：当前源码 30 项检查、6 个方法及审计通过；任务调度、完整控制器、硬件和设备验收仍保留。
S2 任务当前复验已完成（2026-10-07）：当前源码 59 项检查、13 个方法及审计通过；动作服务、UI、插补、补偿、硬件和存储仍按清单保留。
Bond 传送当前复验已完成（2026-10-07）：当前源码 310 项检查、145 个源码片段及审计通过；真实控制器动作、硬件、原生 UI、构建/DLL 和完整调度仍未验收。
输送自动上料当前复验已完成（2026-10-07）：当前源码 238 项检查、279 个源码片段、23 个信号绑定及审计通过；真实 SDK、配置仓储、原生 UI、构建/DLL 和设备验收仍保留。
输送自动下料当前复验已完成（2026-10-07）：当前源码 287 项检查、186 个源码片段、23 个信号绑定及审计通过；真实轴/硬件、日志对话框、原生 UI、构建/DLL 和设备验收仍保留。
输送仓式上料当前复验已完成（2026-10-07）：当前源码 288 项检查、302 个源码片段、23 个信号绑定及审计通过；真实配置、SDK、原生 UI、构建/DLL 和设备验收仍保留。
输送等待段当前复验已完成（2026-10-07）：当前源码 1076 项检查、166 个源码片段及审计通过；真实设备、SDK、原生 UI、构建/DLL 和完整调度仍保留。
输送坐标/产品当前复验已完成（2026-10-07）：按当前源码重跑 1031 项、420 个源码片段及审计通过，覆盖坐标/产品构造、刷新、视觉/高度清理、偏移和声明；真实实体服务、SDK、原生 UI、构建/DLL 与设备仍保留。
点胶 1/2 输送当前复验已完成（2026-10-07）：当前源码 276 项检查、223 个源码片段及审计通过；真实设备、控制器内部动作、SDK、原生 UI 和完整调度仍保留。
点胶至 Bond 输送当前复验已完成（2026-10-07）：当前源码 184 项检查、210 个源码片段及审计通过；真实硬件、控制器、SDK、原生 UI、构建/DLL 和完整调度仍保留。
加载皮带输送当前复验已完成（2026-10-07）：当前源码 252 项检查、275 个源码片段、23 个信号绑定及审计通过；真实控制器动作、SDK、原生 UI、构建/DLL 与设备仍保留。
仓式传送当前复验已完成（2026-10-07）：按当前源码重跑 578 项、180 个源码片段、23 个信号绑定及审计通过，覆盖等待段至仓、收回/推料/层级辅助、模块移动与就绪；真实 SDK、轴硬件、仓储、原生 UI、构建/DLL 和设备仍保留。
输送产品声明当前复验已完成（2026-10-07）：按当前源码重跑 1328 项、512 个源码片段及审计通过；配置/仓储/SDK、原生 UI、构建/DLL 与设备边界仍保留。
输送检查就绪当前复验已完成（2026-10-07）：按当前源码重跑 1209 项、469 个源码片段及审计通过；实体/仓储、单例加载保存、VM、动作注入、SDK、原生 UI 和完整构建仍保留。
输送检查仓储当前复验已完成（2026-10-07）：按当前源码重跑 1303 项、498 个源码片段及审计通过，含仓储分支与检查快照；正式回归、原生构建、部署配置/DLL、UI、设备和整组验收仍保留。
外层 TransportTask 当前复验已完成（2026-10-07）：当前源码 52 项检查、9 个方法及任务委托审计通过；完整在线生产循环、真实设备和原生 UI 仍保留。
Transport Pause 当前复验已完成（2026-10-07）：当前源码 32 项检查通过，覆盖等待、Pause/Stop 转换、材料门控、兄弟任务等待、保存失败和 Jam Abort；外层任务、设备和完整产品框架仍保留。
Transport UnClamp/Stop 当前复验已完成（2026-10-07）：当前源码 46 项检查、9 个方法及审计通过，覆盖气缸/皮带、Stop 状态、重试/忽略和提交边界；物理设备、原生 I/O 和完整外层任务仍保留。
S2 上下文更新当前复验已完成（2026-10-07）：当前源码 14 项检查通过，覆盖消息绑定、层级保留、重复选择、遍历/仓储异常和空输入边界；真实配方、仓储、Fody、硬件、UI 和部署仍保留。
S2 门控暂停当前复验已完成（2026-10-07）：当前源码 37 项检查、17 个方法及审计通过；完整 BondTask、设备和部署仍保留。
S2 节点选择当前复验已完成（2026-10-07）：当前源码 9 项检查通过，覆盖未完成节点选择、Finish 推进、重复节点拒绝、注册表缺失和空列表边界；完整上下文、BondTask、域就绪和设备仍保留。
S2 预点胶分配当前复验已完成（2026-10-07）：当前源码 13 项检查通过，覆盖网格端点、列优先分配、耗尽/重建、维度变化、越界和保存失败状态；设备运动、实际持久化和生产执行仍保留。
S1 原生任务循环/暂停/停止/分段当前验证已完成（2026-10-07）：四个绑定验证器通过，覆盖任务循环 252 次执行、工作/暂停 8 进程、停止恢复 102 次、分段交互 12 进程；真实 UI、VM、SQL、设备和整机业务仍保留。
S1 原生缺陷/返回门/返工上下文/步骤提交当前验证已完成（2026-10-07）：四个绑定验证器通过，缺陷模式 218 次、返回门 12 进程、返工上下文 2 个进程、步骤提交 170 次执行；重试完整循环、真实 UI/视觉/VM/SQL/设备与 MSBuild 仍保留。
S2 原生动作/补偿/就绪/重置/货架/入口当前验证已完成（2026-10-07）：六项绑定验证通过，动作 2 进程、补偿 2 进程、就绪 112 次、重置 2 进程、货架 2 进程、入口 994 次执行；真实生产循环、UI/VM/SQL、硬件和整机启动仍保留。
Transport/wafer 原生入口当前验证已完成（2026-10-07）：context 180 项绑定、environment 6282 次执行、wafer 1320 次执行均通过，覆盖环境门控、域预检、程序保存/加载、TransportDomain 和 Wafer Start 拓扑；完整生产业务、UI/SQL、设备和 MSBuild 仍保留。
Bond 配置原生源码当前验证已完成（2026-10-07）：56 个断言、112 次布置、23 个整源码文件及 8 个编译延续捕获通过，含前置 36 项回归和 20 项新增；完整启动组合和设备验收仍保留。
产品配置原生源码当前验证已完成（2026-10-07）：36 个断言、72 次布置、22 个整源码文件及 8 个编译延续捕获通过；完整启动组合、SDK/设备和部署仍保留。
检查仓储原生源码当前验证已完成（2026-10-07）：27 个断言、54 次布置、6 个整源码文件通过；完整产品集成、启动、UI/设备和部署仍保留。
Transport Whole Action SDK 当前重绑定已完成（2026-10-07）：针对产品声明、产品声明审计和 Bond 配置测试三项历史输入漂移，当前重绑定核验两份 SDK 各 278 项、共 556 次放置，54 个原始文件和 55 个编译单元均通过；未纳入正式 1328 回归。
Transport Full Framework/SDK 当前重绑定已完成（2026-10-07）：当前重绑定验证受控 1328 项、两份 SDK 各 58 项（116 次）、6 个编译单元及 269 个冻结输入通过；Fody、原工程 MSBuild、原生 UI、设备和整组验收仍保留。
Mapping 恢复隔离链当前复验已完成（2026-10-07）：codec 25 项、constructor/state 14 项、step semantics 8 项、action gates 30 项均通过；恢复链路页面 14 场景/51 处源码绑定通过，端到端运行验收仍保持 0。
Plate teaching 当前复验已完成（2026-10-07）：当前源码 16 项隔离检查通过；真实 WinForms、硬件、持久化和完整向导仍保留。
Tool teaching 当前复验已完成（2026-10-07）：当前源码 6 个路径检查通过，覆盖成功、拟合失败、Retry、Offline、内层保存失败和外层保存异常；真实工具/硬件/UI 仍保留。
Vision teaching 当前复验已完成（2026-10-07）：当前源码 17 个路径检查通过，覆盖模板、位移边界、Retry、DryCycle、单步、NaN/Inf 和异常传播；真实相机、光源、算法、运动和设备仍保留。
Autofocus alternatives 当前复验已完成（2026-10-07）：当前源码 8 项检查通过；相机、评分、轴、仓储、UI、硬件和生产可达性仍保留。
动作控制/模式生命周期/视觉缺陷重试当前复验已完成（2026-10-07）：动作控制 51 项、模式生命周期 34 项、视觉重试 7 项均通过；自动对焦范围 3 项通过；完整生产任务、真实设备和 UI 仍保留。
动作排序当前复验已完成（2026-10-07）：当前源码 80 项检查、33 个方法及审计通过；完整动作服务、UI、硬件和生产调度仍保留。
启动配置/入口当前复验已完成（2026-10-07）：启动配置 63 项、启动入口 43 项及对应审计通过；原生 UI、SDK、设备、完整构建和部署仍保留。
Emergency abort 当前复验已完成（2026-10-07）：当前源码 87 项检查、44 个源码成员及审计通过；真实急停链、硬件、UI 和设备仍保留。
Emergency entry 当前复验已完成（2026-10-07）：当前源码 27 项检查、45 个成员及审计通过；真实急停入口、UI、硬件和设备仍保留。
Door task/Safe door pause 当前复验已完成（2026-10-07）：门任务暂停 28 项、Safe door pause 16 项及审计通过；真实安全门、任务调度、UI 和硬件仍保留。
Safe motion 当前复验已完成（2026-10-07）：当前源码 34 项安全运动路径通过，覆盖 2D/4D 轴顺序、门控、异常和 NaN 边界；真实轴、驱动器和设备仍保留。
Single-step door 当前复验已完成（2026-10-07）：当前源码 33 项检查、17 个方法及审计通过；真实门控、UI、硬件和任务调度仍保留。
Wafer action/safety/stop/eject 当前复验已完成（2026-10-07）：action gates 210、safety guards 135、stop chain 172、eject ready 110 项及审计均通过；真实轴、设备、SDK、UI 和完整任务仍保留。
Wafer range/next-position 当前复验已完成（2026-10-07）：range init 105、next position 229 项及审计均通过；真实标定、视觉、设备和生产循环仍保留。
Wafer camera-clearance 当前复验已完成（2026-10-07）：当前源码 174 项检查、46 个源码片段及审计通过；真实相机、标定、轴硬件和设备仍保留。
Wafer blob-position 当前复验已完成（2026-10-07）：当前源码 131 项检查、58 个源码片段及审计通过；真实视觉算法、相机、标定和设备仍保留。
Wafer mark-center 当前复验已完成（2026-10-07）：当前源码 76 项检查、64 个源码片段及审计通过；真实标定、视觉、硬件和生产循环仍保留。
Wafer position-accuracy 当前复验已完成（2026-10-07）：当前源码 99 项检查、52 个源码片段及审计通过；真实相机、标定、坐标和设备仍保留。
Action controller/sort、background edit/monitor、curve geometry、cycle config、driver consumption/lifecycle 当前复验已完成（2026-10-07）：对应静态检查与审计均通过；真实 UI、设备和完整 Framework 仍保留。
Dispense node、dry-run、editor bridge、heating host、machine stop、mode lifecycle、mouse edit、parameter roundtrip 当前复验已完成（2026-10-07）：对应静态检查与审计均通过；真实 UI、设备和完整任务仍保留。
Pattern roundtrip、pretreatment、repository delete、transform select、startup config/entry、task closure、normal start 当前复验已完成（2026-10-07）：对应检查与审计均通过；真实数据库、UI、设备和完整构建仍保留。
Assistant predispense、async DB consumer、autofocus、axis fit/numeric、axis return、calibration、coordinate lifecycle 当前复验已完成（2026-10-07）：对应入口检查通过；异步通知任务生命周期仍以记录状态保留，真实数据库、硬件和完整 Framework 未验收。
Bin/config/callsite/changejson/completeness/emergency/epoxy/gugao/ledger/manual wafer 当前复验已完成（2026-10-07）：对应入口检查通过；真实 UI、数据库、设备和部署运行仍保留。
Nozzle/postbond/process gates/production launch/recipe/resource/semantic/singleton/state/substrate/task concurrency/teaching/vision 当前复验已完成（2026-10-07）：对应入口检查通过；真实 UI、设备、数据库和完整运行链路仍保留。
Wafer change-retry/consumer-pause/selection/start-init 当前复验已完成（2026-10-07）：入口检查通过，consumer-pause/search/vision acquisition/vision control 审计通过；真实设备和生产循环仍保留。
Whole config/entity SDK 当前重绑定已完成（2026-10-07）：config 142 checks/284 placements、37 个源码文件；entity 187 checks/374 placements、45 个源码文件；均编译产物一致，formal 1328 回归仍未纳入。
整机源码闭包 387 缺失依赖单文件探针已完成（2026-10-08）：以 184 输入/387 错误候选逐个加入 WaferTable/Eject/WaferSub/StaticWaffle/MagazineBox 参数和 WaferTable/Eject/WaferSub 模块，最低 StaticWaffle 单文件仍为 185/387，未低于当前候选；正式 123/642/1 基线保持不变。
整机源码闭包 387 外部引用探针已完成（2026-10-08）：以 184 输入/387 错误候选为种子，仅补充现有 AutoFocusing、DispensingPattern、Component、UserManager、Halcon、Dataflow、AccessControl、DevExpress 和 PresentationCore 引用，降至 184 输入/370 错误，减少 17；退出码仍为 1，正式 123/642/1 基线不变。源码模块组合升至 596，未采用。
整机源码闭包 370 程序/仓储单文件探针已完成（2026-10-08）：对 8 个直接缺失程序/仓储文件逐个编译，最低 DispenserRepository 为 185/370，未低于外部引用候选；正式 123/642/1 基线不变。
整机源码闭包 370 控制器单文件探针已完成（2026-10-08）：BondHead/BondModule/System2/NozzleShelf/S2Dispense/Dispense/DispenseVision/Calib 八个控制器逐个加入均未低于 370，最低 NozzleShelfController 为 185/373；正式 123/642/1 基线不变。
整机源码闭包 367 组合候选已完成（2026-10-08）：在 184 输入/370 错误外部引用候选上加入 MeasureHeightModule、VisionModule 与 EpoxyMaterial.cs，得到 187 输入/367 错误，较 370 再减少 3；退出码仍为 1，正式 123/642/1 基线不变。
整机源码闭包 367 Epoxy 仓储配对复核已完成（2026-10-08）：在 187/367 候选上加入 EpoxyMaterialRepository 后为 188/368，未优于 367，故保留 367 为当前最佳诊断候选。
整机源码闭包 367 模块/任务与低耦合复核已完成（2026-10-08）：BondModule/IPT/UpLook/NozzleShelf/System2 模块、Bond/Slide 任务及 Dispense 模块单文件均未低于 367；MeasureHeightModule+VisionModule+EpoxyMaterial.cs 三文件组合稳定为 187/367，仓储配对升至 368。
整机源码闭包 367 Product/Statistics 与域组合复核已完成（2026-10-08）：FrmStatistics、Designer、ProductDomain、UcMainSystem.DataAdministrator 单文件最低 385/367 候选，Controllers/Modules/Tasks/Services 组合 979，Repositories 369，UcMainSystem 828，BondSystem.Controls 2046；均未优于 187/367，正式 123/642/1 基线不变。
整机源码闭包复核收尾审计已完成（2026-10-08）：source-coverage-audit check 通过（16 项目、29 组、1436 C#、89 步骤、101 关系、89 语义登记、552 模块关系、940 快照、13 requirements）；git diff --check 通过；正式日志 SHA 与登记值一致，仍为 123 输入/642 错误/退出 1。
