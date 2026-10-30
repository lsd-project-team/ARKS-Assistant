# 原算法实例选择与类型属性差异

两轮隔离原生宿主各163项检查通过，覆盖原AlgsFactory全部30个枚举选项与PREntity命名构造/同属性短路。本轮实际执行原源码的工厂和实体方法，并未调用FindModel或初始化VM流程。16工程/29组/1436文件/13项整体目标未完成。

## 已复现的差异

原命名构造`new PREntity("entity-selection")`通过AlgsFactory创建XldModelAlg，但该对象的AlgFlowType仍为枚举默认值FastModelAlg。GetAlgFlowType直接读取该属性，实际返回Fast。因此属性标签和具体对象类型不同。

随后调用`SetAlgFlowType(FastModelAlg)`，原守卫判断当前Alg非null且Alg.AlgFlowType与参数相同，返回true；对象引用保持同一Xld实例，并未换成FastModelAlg，也未初始化流程。这是原方法的真实执行结果，不是仅由静态候选推断。

|执行入口|具体接收者|类型属性|本轮观察|
|---|---|---|---|
|命名PREntity构造|XldModelAlg|FastModelAlg|工厂选择与标签不同|
|随后设置Fast|同一个XldModelAlg|FastModelAlg|返回true，守卫直接保留原实例|
|公开Alg赋值为CircleFind实例|CircleFindAlg|FastModelAlg|更换对象后，查询仍读默认标签|
|只将该实例的AlgFlowType改为CircleFind|同一个CircleFindAlg|CircleFindAlg|标签改变，对象引用不变|
|随后设置CircleFind|同一个CircleFindAlg|CircleFindAlg|同标签守卫返回true，流程仍未初始化|

对象类型、可变类型属性和已初始化VM流程是三个不同状态，不能仅用GetAlgFlowType的返回值确定实际FindModel接收者或认定算法准备完成。公开Alg和AlgFlowType赋值是普通原对象数据操作，没有使用未初始化对象、私有字段写入、替身类或SDK方法替换。

原SetAlgFlowType的不同标签分支会创建对象、写类型属性、替换Alg，然后调用InitVmProcedure；该分支本轮未执行。其完整源码与静态IL保留。原InitVmProcedure内部捕获异常并记日志，不能由SetAlgFlowType源码末尾return true推断VM已成功初始化。实际加载、授权、流程文件、相机和图像验收仍待完成。

## 完整工厂选择

30个原枚举名称与工厂30个显式case一一对应。每个枚举以普通名字和null名字分别创建真实算法对象，验证具体类型、原名字传递、不同对象引用、独立空MatchResults及没有已初始化的图像/流程名字，共60个对象。所有工厂构造出的AlgFlowType属性均为FastModelAlg，工厂本身不写所选枚举标签。

两个未知整数端点及999999均实际进入default，返回FastModelAlg并保留传入名字。每轮额外加上PREntity默认Xld与公开替换CircleFind，共65个算法对象；不是65次FindModel调用。

对30个具体对象用原CLR反射读取FindModel的DeclaringType和GetBaseDefinition，确认各自覆盖BaseAlg声明槽，并以完整程序集/文档签名对应原源码和上一轮30个静态方法候选。没有调用这些方法，不能把30个已创建类型当成30个算法已运行。

30组完整映射、原构造签名、运行类型、枚举数值/标签和FindModel符号见[源码/实例证据](../../.archify-work/native-algorithm-selection/selection-source-evidence.json)。69个原声明来自37文件，包含原工厂、枚举、构造、反射对应的方法正文、实体守卫、编辑器GetBaseAlg和两条任务选择入口。声明正文的原字节哈希、严格解码和UTF16位置均核对；对应FindModel正文仍属静态来源。

## 动作选择链的准确入口

按任务的精确IOperation目标核对：DispenseWorkTask.cs第119行调用Main.Machine.Process.S1ActionNodeController.GetNextActionNode，BondTask.cs第216行调用同命名空间的S2ActionNodeController.GetNextActionNode。仓库另外存在名称相似的System1ActionNodesService/System2ActionNodesService文件，不能用其正文替代这两处实际绑定目标。

原S1控制器GetNextActionNode清当前消息，再选WorkMessages中第一个未完成消息，以ActionNodeName到原目录ActionNodes.Find匹配Name；没有匹配会返回null。原S2控制器先记住当前名字、清当前消息、遍历首个未完成消息，特定两个重复名字触发提示/异常，再转ChangeNameToActionNode。准确控制器正文和IL已保存；本轮没有执行它们的节点选择或DoWork，完整注册/排序/实例上下文接任务仍待继续。

这一区分缩小了下一步复核对象，没有将同名服务或目录中全部39个虚候选认定为实际任务节点。原目录37类型的其他限定原生报告仍保持各自范围，本轮163检查不与其相加认定全任务覆盖。

## 验证与限制

宿主两份源码以原162引用编译，真实emit exit0之后才运行。两轮分别使用已冻结bound/replay的16份保真原文件资源程序集，每轮原CLR加载位置一致，32个对应文件SHA均保存；没有重编译、替换原生产源码或项目。原文件保真程序集未经过完整原工程LC/Fody/MSBuild流程，不能等同部署产物验收。

两轮163项名称/顺序和完整结果相同，合计326次断言放置。30个枚举数值与实际原PE元数据匹配；44个静态IL方法含30构造、BaseAlg/实体/工厂及准确任务选择方法。IL读取只加载Cecil与PE，不执行生产程序集；原生宿主则确实执行了明示的原工厂/实体方法。

首次163项检查已通过，但摘要漏算公开替换对象，64改为实际65；原可执行文件/输入/完整输出/脚本保留，断言范围不变，重新编译后两轮通过。第一次IL采集因Framework PowerShell无Get-FileHash命令真实exit1，改用SHA256.Create/ComputeHash并保留失败脚本和日志。早期源码证据草稿的symbol对象被声明ID覆盖，已保留草稿并增加独立symbolRecord，最终完整符号/文本/位置核对通过。

三步流水线完成原生选择/完整源码绑定及阅读器、虚候选父冻结核验。96新增冻结输入，212既有副本复用不增数，父9513+96=9609；这是来源绑定，不是业务断言。正式1328受控回归、旧阅读器/图/报告、全部生产C#/csproj均保持原值。

下一步继续实际S1/S2控制器目录/消息与GetNextActionNode的选择及任务使用，PR不同标签替换/流程初始化的真实依赖、保存重载和编辑控件桥，再推进完整业务解释、原构建/UI/SQL/设备成功路径。整体目标未完成。

只读复验：`node --max-old-space-size=4096 scripts/verify-native-algorithm-selection.cjs`、`node scripts/verify-native-algorithm-selection-bindings.cjs`。冻结生成/编译/运行输出禁止覆盖，新实验另建目录。

见[测试](native-algorithm-selection-test.json)、[审计](native-algorithm-selection-audit.json)、[进度](native-algorithm-selection-progress.json)。
