# 原S1/S2工作消息到节点实例的选择

两轮隔离Framework原生宿主各5,655项检查通过。每轮通过公开Init生成16份排序计划、选择848条消息，并再次请求相同848条消息；节点选择和上下文初始化确实执行原主程序控制器。宿主随后显式调用公开FinishCurrentActionNode推进消息，未运行节点IsDoWork/DoWork或生产Task。16工程/29组/1436文件/13项整体目标未完成。

## 本轮观察

|入口或状态|原对象实际行为|影响与范围|
|---|---|---|
|S1/S2 GetNextActionNode|按首个未完成消息选择目录中Name相同的第一个原节点实例|验证引用相同，未执行节点动作|
|再次请求同一未完成消息|当前配方仍返回同一消息和同一节点|完成标记必须由调用方推进；本配方未生成两种校正节点|
|公开目录移除当前名称|返回null，当前消息仍被选中且未完成|两条原Task源码将null作为break条件；此项是任务影响的源码推断，未执行Task|
|公开目录出现重名|返回列表中的第一个实例，即使具体类型不同|测试修改公开Name/列表后恢复，不代表生产目录已发生重名|
|公开ActionNodes设null|抛NullReferenceException，当前消息已选中|S2 ChangeNameToActionNode在显式null判断前调用Find，因此预期的Sort Error守卫不先触发|
|S2上下文没有匹配当前树层级|ProcessStep按当前消息更新，基板/基岛/焊点字段保留先前指针|低层级未匹配时不能把这些缓存getter当成当前消息的完整上下文|
|S2直接ChangeNameToActionNode传另一个消息|按参数名称返回节点，但InitCurrentMessage读取原CurrentBondActionNode|参数的基板/基岛/步骤不替换当前消息；返回节点和上下文可能来自不同输入|
|空步骤公开Init|工作列表先清空，提前return保留旧当前消息|下一次GetNextActionNode才清当前消息；S2空Finish索引0抛异常，S1正常清当前|

完整两轮输出及断言名称保留在[bound原生记录](../../.archify-work/native-action-selection/bound/stdout.json)和[replay原生记录](../../.archify-work/native-action-selection/replay/stdout.json)。缺失节点、重名和null是隔离宿主中的公开数据边界夹具，所有目录恢复；没有私有字段写入或未初始化对象。

## 真实对象与配方范围

实际System1Domain/System2Domain给出准确Main.Machine.Process.S1ActionNodeController和S2ActionNodeController，正是DispenseWorkTask第119行与BondTask第216行的IOperation目标；没有使用同名旧服务代替。真实SDK单例构造原目录，分别15/19个注册实例，共34个。全部实例来自原Main程序集。

原公开TransportUnit构造生成2基板×2基岛、每基岛2焊点的实际树；公开配置和TransportProgram的两个区段TransportUnit赋值使两个控制器访问同一真实树。启用两步骤、禁用一个无效步骤，S1采用点胶消息，S2采用焊后检测消息；每种排序各53条。四种WorkProcess与两种WorkProcessModule共八组合，两个系统合计16份计划。

每份计划真实选择53条并核对目录引用、首个未完成消息、完成标记、过程步骤及树上下文；公开FinishCurrentActionNode每次只标记当前消息。再请求同一消息的848次选择不会自行完成消息。完整遍历后返回null并清当前；无当前Finish抛原异常。Finish重置全部标记，S1清当前，S2设为列表首项；重新请求可从首个注册对象继续。

34个注册实例中，本配方实际选中26种具体接收者。全部34个DoWork符号均与静态39候选集合对应，但DoWork正文只作为来源保留，未调用。Pick/Bond/DipFlux、两种校正和S1分段Interactive等剩余注册实例、不同组件/浸胶/分段/重复校正提示组合待下一阶段；不得用本轮数量认定34或39种动作均已执行。

S2两种校正节点重复GetNextActionNode会先提示再抛异常，准确源码/IL已保留；本轮配方没有生成它们，specialRepeatWarningBranchExecuted=false。没有绕过提示、替换消息框或执行真实UI。

## 来源与验证

95个完整原声明来自59个原文件，含准确控制器、目录、上下文实体、注册类型、静态DoWork方法和两条原Task正文。原字节SHA、严格UTF8/CP936解码、UTF16偏移、完整符号记录逐项验证。源码候选与已选择实例为不同证据，完整静态候选阅读器保持。

静态Cecil读取原Main PE中两个完整控制器及嵌套闭包，共161个IL方法；并不声明161个方法都执行。GetNextActionNode/FinishCurrentActionNode的调用、S2名字转换和异常处理均核对；控制器选择方法不调用节点DoWork。IL采集只读PE，不执行生产程序集。

宿主2份源码、162实际引用编译真实exit0后才运行。bound/replay各16个冻结保真资源源码程序集按原物理路径实际加载，32个程序集文件哈希核对；两个过程真实exit0/nullsession，两轮5,655个唯一标签/顺序和完整业务结果相同，合计11,310次断言放置。原硬件路径自然位于隔离启动目录、文件缺失，实际SDK硬件仓库始终为空。

四步检查完成本轮原生/严格源码/IL验证及算法实例、阅读器、虚候选父冻结复验。50新增冻结输入，260既有绑定复用不增数，9609+50=9659。来源台账与业务断言不同，5655不加入正式冻结1328，也不与历史原生套件相加认定全业务覆盖。

原生产C#/csproj、既有阅读器/完整语义图及全部冻结历史报告保持原值。所用资源保真原源码程序集未经过完整原工程LC/Fody/MSBuild/部署流程。没有生产Task、节点IsDoWork/DoWork、PR FindModel/VM、SQL、相机/轴/设备、原Program.Main或真实UI验收。

下一步从公开组件仓库和实际配方生成Pick/Bond/浸胶/校正及分段消息，继续准确控制器选择/上下文及安全原节点分支，再接真实任务的等待/Retry/Pause/异常路径。PR不同标签替换/流程初始化、SQL配方持久化、完整构建与UI/设备及29组完整业务解释仍待完成。整体目标未完成。

只读复验：`node --max-old-space-size=4096 scripts/verify-native-action-selection.cjs`、`node scripts/verify-native-action-selection-bindings.cjs`。已冻结生成、编译、运行与IL输出禁止覆盖；新实验另建目录。

见[测试](native-action-selection-test.json)、[审计](native-action-selection-audit.json)、[进度](native-action-selection-progress.json)。
