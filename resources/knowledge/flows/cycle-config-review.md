# 批次数输入、保存事件与JSON配置边界

32项隔离检查通过。执行四个原界面方法、两份原枚举声明、完整SystemProcess原类，并在本机.NET Framework使用项目HintPath所指trunk/AKRS.ZX2200/libs/Newtonsoft.Json.dll进行真实内存JSON往返。生产源码未改动。

## 输入边界

UcProcessStep.Designer.cs为SpCycleNumber设置初值、MinValue、MaxValue均为1。因此不能宣称普通用户一定能通过原生数字控件输入0或负数；本轮未加载DevExpress控件。

原IsEnableToEditCycleNumber依据作业模式、多基板/基岛标志和开关启用编辑器；载具优先使用基板Count作为最大值，基板优先使用基岛Count。其他模式只禁用，不清旧最大值。原方法不验证Count与下限是否相容，夹具Count=0时记录MaxValue=0、MinValue=1；真实控件如何钳制、拒绝或触发事件未验收。

## 原事件与内存状态

- SpCycleNumber_EditValueChanged直接把decimal Value转int写入CurrentSystemProcess.WorkCycleNumber，再Save。未检查isLoad、Enabled、最小值。夹具调用0、-1、3及3.9分别保存为0、-1、3及3；此为原事件入口测试，不是原生控件输入可达性证明。
- decimal溢出在赋值前失败，未调用Save；Save替身抛异常时，已写入的数值留在内存中。真实文件写入未运行。
- ChkWorkByNumber_CheckedChanged先改开关、再Save、最后刷新编辑器。保存失败时开关已变而编辑器未刷新；isLoad=true不阻止该事件。
- 真实系统选择方法仅把System1分到S1，其他枚举值落到S2；null选择会在拆箱时失败。

## 完整原配置类与真实JSON

SystemProcess默认批次数1、开关false、主模式BondPositionFirst，均为无验证的自动属性。使用项目Newtonsoft DLL实际验证：

- 开启开关时，0、-1、Int32.MinValue和Int32.MaxValue均可反序列化，并在序列化/回读后保持。
- 空JSON保留默认值；字符串形式的0也可成为整数0。
- 未定义模式整数99及ProcessSteps=null均可进入对象。
- 批次数null和超出Int32上界的数值反序列化失败。

这证明对象和默认JSON反序列化边界不强制正数；不是读取实际客户配方的结果，也不证明Singleton所有加载选项或上游迁移行为。测试未读写生产ProcessProgram.json。

## 源码调用路径与风险条件

ProcessDomain继承外部Singleton<ProcessDomain>，配置路径指向当前配方ProcessProgram.json；InitProcessProgram设置路径并清instance，真实单例加载实现尚未在本专项执行。

所检查的ProcessDomain.IsEnableToWork、CheckIsReady及S2ActionNodeController.SelfCheck原文没有引用WorkCycleNumber或IsWorkCycleNumber，不能用这些方法证明批次数已验证；此为指定方法范围的静态检查，不是全程序负面证明。

Machine.Start在PrepareMachineReadyToStart通过后设Working，并在相应条件下启动输送、供晶及S1任务，之后才调用S2 ActionNodesService.Init，再启动BondTask。顺序已绑定原文，未实际启动线程或设备。

结合[排序专项](action-sort-review.md)：S2载具优先/基板优先且开启按个数执行时会使用WorkCycleNumber。若对应总数为正且批次数非正，原GetCycleList循环不推进并持续添加空列表。此次证明非法值可由默认JSON进入原对象，仍缺真实Singleton加载→所有生产门控→Init的端到端验证；不能将条件风险升级为已复现现场故障。没有执行无限循环。

## 执行与边界

node scripts/test-cycle-config.cjs
node scripts/build-cycle-config-audit.cjs --check

审计绑定原类、四个事件/选择方法、两份枚举、项目JSON DLL、界面下限、配置路径、门控方法及Start顺序。使用Roslyn编译原源码，再由Windows PowerShell/.NET Framework执行；UI对象、域单例及Save为夹具。尚需原生控件约束/事件顺序、真实单例文件加载及异常、实际配方校验、并发任务和设备验收。29组仍部分复核。

后续已补[真实单例文件专项](singleton-load-review.md)：实际项目Singleton与JSON帮助器读取临时文件可接受开启开关的0，真实保存重读可保留负数，并已验证缓存、重置、旧接收对象保存和文件锁失败。该包装器不含完整生产门控；本报告所列整条生产链验证仍未完成。
