# 原工程委托注册、传递和调用证据

本轮对16原工程的1410个Compile文件进行两轮独立Roslyn分析，保留原编码、编译宏和357份真实元数据。得到10967条静态委托证据；546处调用的文件、位置、声明目标、implicit和旧owner身份与冻结静态图逐条对应，43199次源码范围检查通过。32个分析进程均exit0，没有原编译语义错误。完整记录见[证据JSON](../../.archify-work/delegate-provenance/evidence.json)与[进度](delegate-provenance-progress.json)。本轮只运行分析器，没有执行生产程序集或原入口。

这补充了跨模块连接的源码解释；运行时派发、全部29组业务解释及16工程/29组/1436文件/13项整体目标未完成。

## 调用和注册的范围

|证据|数量|含义|
|---|---:|---|
|委托创建|5160|方法组/lambda到委托的静态转换，不等于调用|
|委托参数传递|2507|保留实际调用位置、构造签名、参数序号/构造类型与接收符号|
|事件追加/移除|2569 / 73|两种操作均保留，不推断当前订阅列表|
|委托+= / -=|31 / 4|追加与删除分别记录|
|赋值|50|保留null、别名、条件/合并和未解析返回值|
|返回、局部/默认参数/属性/字段初始化|2 / 20 / 3 / 1 / 1|按原IOperation可见范围记录|
|委托调用|546|仍没有运行时目标证明|

546调用的接收符号类型为属性454、字段59、参数17、局部13和事件3，共75个独立接收符号。61个符号具有源码写入，8个具有参数传入证据；仅27个具有直接方法组/lambda注册候选，涉及161个调用位置。161是静态候选可关联的调用数量，不是运行成功或目标已解析数量。

每个符号的写入、追加、移除、参数输入与调用位置都可查阅。相同字段/属性符号不能证明接收实例相同；条件分支、空值重置和-=也不能在无执行顺序时直接确定最终列表。属性getter/setter、委托返回方法、数组元素、反射、SDK内部代码和动态配置仍有边界。参数按所属原始方法身份和序号区分；泛型参数的原定义身份可能相同，因此另存实际调用签名与构造参数类型，不能跨所有泛型调用合并成一条实际流。

## 三组业务连接

1. **启动异常处理与线程入口。** Program.Main在102/105行分别给Application.ThreadException和当前AppDomain.UnhandledException追加AppUIThreadException/AppThreadException；127行将FindFormThread传给真实Thread(ThreadStart)构造器。这里有注册和构造参数证据，不能据此声称框架异常派发或线程执行已经验收。Main有磁盘、迁移、加密和硬件初始化等前提，本轮没有运行Main。
2. **PR存图回调。** Program.Main第248行向静态PREntity.SaveLocateImageAction追加VisionService.SaveVisionImage；PR在532/546/595行从同一个字段调用。回调原正文构造路径并把Bitmap/文件名放入BitmapBlockingCollection，异常经原catch记录。三处调用与主工程注册按完整程序集身份连接；启动到达注册、当前多播列表及真实消费/文件结果仍须另外验证。此前有界存图队列运行证据保持独立，未以这次静态连接扩大其覆盖。
3. **UI派发。** MainForm构造器第61行向静态SendUiAction追加实例this.PostAction。Show(XtraMessageBoxArgs)在38/48行两分支传入两个不同的捕获lambda；各lambda正文调用XtraMessageBox.Show(args)。PostAction第70行把自己的Action参数交给Control.Invoke。注册字段全源码有24个调用位置。本轮把调用现场、参数、接收字段和两个lambda源码范围分别绑定；并未证明窗口句柄、实际UI线程、回调生命周期或当前订阅列表。构造器使用+=，该源码操作是追加；不推断生产一定创建多个窗体。Show(string)仍只转发重载，不把上述两处委托调用读成它的直接操作。

可用[查询脚本](../../scripts/explore-delegate-provenance.cjs)检索确切字段/方法文档ID或名称。例如在仓库根运行：

`node scripts/explore-delegate-provenance.cjs SaveLocateImageAction`

`node scripts/explore-delegate-provenance.cjs SendUiAction`

结果给出原文、行号、UTF16位置、方法/参数/实例范围及所在工程；删除和null保留。两条精确字段查询分别核对3和24个调用及各1处追加。

## 匿名函数身份修正与历史边界

本轮发现Roslyn会为不同匿名函数返回相同的非空GetDocumentationCommentId。2441个匿名源方法中，2194个落入351组非唯一文档签名；UI两lambda就是同签名的具体例子。首候选沿用旧图算法，虽然位置/调用数量检查通过，却不能证明匿名方法唯一身份；完整候选结果、日志和脚本已归档。

最终委托提取改用完整程序集身份加匿名方法原源码文件/span，2441个身份逐个核对。原Roslyn签名只留作诊断；旧owner ID只用于与旧546调用位置集合对照。UI的旧静态调用边按对应lambda原文范围归属，禁止按共享旧owner ID混合两个正文。25项合成守卫包含同签名lambda隔离、重载、条件invoke、捕获状态、事件增删、ref参数、空值重置和泛型调用上下文。

**冻结旧语义图和离线阅读器尚未修复匿名函数身份。** 它们保持既有原文/边位置；涉及匿名owner的符号归并和入向/出向列表不能当作唯一匿名调用链。本轮JSON/查询的匿名身份已经隔离，但没有把全部384201操作改为新身份，也没有改旧页面。下一步需要另建完整图和阅读器派生版本，补全匿名方法/相关参数归属后重验。普通具名成员签名和完整原源码文本检查的证据边界保持。

## 重放、冻结与后续

16工程重放全部来源值/记录/数组顺序一致；5工程原JSON字节相同，其余11工程仅完整编译诊断排序不同。仅排序完整诊断记录用于比较，没有删除诊断或正规化源码/位置。来源哈希、每个callSite/值范围和2441匿名身份均核对，原546调用集合逐条一致。

证据汇总首脚本对每条记录重复读取图文件计算SHA，已确认只读Node进程PID16828后停止；真实exit1和慢候选代码保留。改为每工程一次哈希后通过。不是源码/编译器失败，没有运行或修改生产代码。

最终25项夹具、完整来源/重放、业务JSON重建、两条CLI查询以及父图/父阅读器绑定通过。新增249冻结输入，复用1818个既有冻结输入，父8697+249=8946；这些是证据绑定数量，不是业务覆盖率或运行断言。历史1328正式回归、旧阅读器/旧图和原C#/工程文件保持冻结。

剩余：完整图/阅读器的匿名身份派生修复，虚/接口实现和实例/委托流解释、29组业务复核、foreach/using/async降级与反射/织入关系、完整MSBuild/LC/Fody/VM/target pack、原启动/真实UI/SQL/设备及成功制程验收。整体目标未完成。

只读复验：`node --max-old-space-size=4096 scripts/verify-delegate-provenance.cjs`、`node scripts/verify-delegate-provenance-fixture.cjs --check`、`node --max-old-space-size=4096 scripts/prepare-delegate-provenance-evidence.cjs --check`、`node scripts/verify-delegate-provenance-bindings.cjs`。冻结抽取/准备脚本禁止覆盖重跑；新实验另建目录。

见[测试](delegate-provenance-test.json)、[审计](delegate-provenance-audit.json)、[进度](delegate-provenance-progress.json)。
