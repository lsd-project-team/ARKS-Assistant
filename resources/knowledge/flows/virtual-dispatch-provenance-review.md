# 原虚方法与接口的源码候选连接

已为16原工程1410个Compile文件中的17518处虚方法/接口调用增加源码候选记录，原位置、声明目标及匿名owner与完整派生图逐条一致。可用[四组业务连接](../../.archify-work/virtual-dispatch-provenance/business-connections.json)或下述CLI查询。候选关系已验证；实际接收者、配置、执行顺序和运行派发仍未解析，16工程/29组/1436文件/13项整体目标未完成。

## 结果与范围

|静态数据|数量|含义|
|---|---:|---|
|原虚方法/接口调用位置|17518|完整匹配原可见IOperation图的调用集合|
|声明目标|295|完整程序集身份与原定义文档签名|
|候选集合|675|按声明目标、构造签名和接收者静态类型分别记录|
|候选行|3257|类型、方法、构造方法和接口投影组合；不是唯一方法数或执行次数|
|有仓库类型候选的调用|710|其中可能只继承SDK方法；不等同有源码方法|
|有已索引源码方法候选的调用|455|有静态源码定位；不证明该方法执行|
|类型声明目录|1179|仅原源码实际类型/委托声明；排除编译器生成闭包等元数据类型|

每次原编译只枚举当前工程及可见引用中的仓库程序集类型。反向依赖工程中的实现不保证可见，SDK、外部插件和未知运行类型不在源码声明目录中。因此completeRepositoryImplementationSet、completeRuntimeTypeSet和runtimeDispatchResolved均为false。空候选仅表示本次静态源码范围没有候选，不能解释为调用不可达；即使只有一个候选，也不能解释为运行目标已确定。

候选行中2044项选取原虚槽或继承正文、1155项选取最近override链、58项由Roslyn接口映射选取。3194项有隐式引用/装箱/身份转换关系；63项只匹配泛型原定义，类型替换仍未解析。402集合属于虚类槽，273集合属于接口。继承的SDK方法明确标为无已索引源码方法，不伪造源码正文。

## 选择规则

普通类型转换前的接收者静态类型用于约束候选，转换后的声明类型另存；每处调用都有独立原表达式，不能将同一集合中首处表达式当作其他调用的接收者。用户自定义转换不当作类型继承/接口实现关系。

类虚方法沿最近类型的OverriddenMethod链寻找原声明槽，new虚槽不替换原槽。接口使用FindImplementationForInterfaceMember，保留显式实现、结构体装箱及构造接口投影。存在精确构造接口时优先它；没有精确接口时保留协变/逆变可匹配的所有投影，不任取一个。泛型未闭合和类型参数约束仅标未解析，没有声称完成全变量流/别名/对象生命周期分析。

## 四组业务连接

完整记录保存调用的原范围、调用owner、每处静态接收者和完整候选方法声明文本/原字节及文本SHA。以下四组调用合计105处；4+2+2+97=105，不能与17518之外另加为新调用覆盖。

1. **PR算法入口：4处、30个方法候选。** UcAlgEditor.cs第135/952行与PREntity.cs第210/510行调用BaseAlg.FindModel。PREntity在SetImage之后调用、随后读取MatchResults和布尔结果；候选包括圆/边/模板/二维码等30个FindModel实现。实际Alg的配置、图像和算法执行没有在本轮验证。
2. **S1/S2动作任务：2处、39个方法候选。** BondTask.cs第232行与DispenseWorkTask.cs第149行从ActionNode静态类型调用DoWork。原任务以IsDoWork等前提和返回值控制流程；S1 Retry执行continue，非Success走安全位置/Stop/return。S2也按返回值分支。39个候选含原基类正文和各具体override，不等同任务实际注册列表。基类DoWork在try之前通知WorkStart并设Running，finally中恢复Stop/通知WorkStop；派生override是否调用它必须按各自正文检查。
3. **编辑设置确认：2处、20个方法候选。** UcEditProductProgramming.cs第872/1070行通过selectedControl as IProgrammingControl的条件调用Confirm。Start按钮在确认后调用Start(true)；Save按钮在try内确认后显示保存成功，catch显示异常。null条件调用可能跳过确认；20种控件实现不证明当前选中哪种，也不证明每个实现完成保存。
4. **PR实体入口：97处、1个方法候选。** 原PREntity.DoWork(PRHardware,bool,bool)覆盖多种省略可选参数写法，查询按绑定目标完整签名聚合，而不是按源码参数数量分开。范围内均映射到同一源码方法；硬件、采图、Alg成员、结果和存图分支仍依赖实例/配置，没有因为候选唯一就认定真实PR运行成功。

四份查询JSON保留每处全部候选及投影，连接JSON另外保存候选方法完整声明正文、精确原文件/span/行号和92个相关文件的哈希核对结果。四组样例是业务交接增量，不是全部29组职责/异常/数据流解释。

## 验证与历史候选

两轮32次原输入语义分析真实exit0；16份完整值仅排序完整编译诊断记录后相同，4份原JSON字节一致。357份引用哈希、810个有调用的原文件严格编码/文本SHA、全部17518位置/调用目标/匿名owner均核对。未执行原CLR生产程序集；分析器仅读取源文件与PE元数据。

24项合成语义守卫覆盖最近override、继承正文、隐藏new槽、显式接口、装箱、抽象类型排除、用户转换排除、重载、开泛型、不兼容闭合泛型、双接口正确选择、类型参数边界、SDK正文、运行未解析标记、普通强转前界限、协变/逆变、精确投影优先、多投影和独立每处表达式。

第一候选虽通过旧位置/两轮检查，但把引用中的生成闭包当成源码类型，并只用转换后类型限制候选。第二候选排除此问题，仍缺变体接口投影且表达式只留集合首例。两者全部32分析日志、图、夹具和当时脚本已分别归档，未接受为最终证据。第三版扩充24守卫并再次完成32分析；最终五步流水线验证全图、夹具、业务查询及两个冻结父绑定。

本轮362个新增冻结输入，1847个已有来源副本复用不增数，父9112+362=9474；这是来源绑定台账，不是业务断言覆盖。正式1328回归、原C#/csproj、冻结旧图/阅读器/报告保持原值。

## 查询与下一步

在仓库目录执行：

`node scripts/explore-virtual-dispatch-provenance.cjs M:AKRS.Galaxy2.PR.Models.Algs.BaseAlg.FindModel`

`node scripts/explore-virtual-dispatch-provenance.cjs M:AKRS.ZX2200.Infrastructure.Models.CommonModels.ActionNode.DoWork`

`node scripts/explore-virtual-dispatch-provenance.cjs M:AKRS.ZX2200.Infrastructure.Interface.IProgrammingControl.Confirm`

优先精确文档签名或完整程序集身份。原泛型/可选参数的构造签名、原接收者表达式和源候选正文都随结果保留。完整[源码阅读器](module-source-explorer-lexical.html)仍展示原声明调用目标；本轮候选仅进入CLI/JSON/报告，阅读器候选浏览尚待接入和浏览器验收。

只读复验：`node scripts/verify-virtual-dispatch-provenance.cjs`、`node scripts/verify-virtual-dispatch-fixture.cjs --check`、`node scripts/prepare-virtual-dispatch-evidence.cjs --check`、`node scripts/verify-virtual-dispatch-provenance-bindings.cjs`。冻结抽取/生成禁止覆盖重跑，新实验另建目录。

接下来接入候选浏览，继续真实配置/实例注册与委托流、全部业务解释、反射/Fody/foreach/using/async降级关系，以及原工程构建、完整启动/UI/SQL/设备成功路径。整体目标未完成。

见[测试](virtual-dispatch-provenance-test.json)、[审计](virtual-dispatch-provenance-audit.json)、[进度](virtual-dispatch-provenance-progress.json)。
