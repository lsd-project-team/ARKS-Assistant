# 原新建配方、拷贝及切换确认验证

两轮各163项检查通过，共326项；27项阶段绑定通过。每轮实际执行14个原SDK新建选择器、5个原名称/拷贝提示和9个原AKRSXtra Yes/No切换确认。735新增+12916=13651，484复用。整体目标未完成。

|真实原流程|实际结果|边界|
|---|---|---|
|空白、非法字符、重复名称|3条真实SDK提示，选择器保持可用，实际取消|没有添加配方或修改当前配置|
|空白新建、不切换|生成原随机Guid、添加配方、创建空目录|原6程序不重载，当前A及Designer标题Name保留|
|复制B、不切换|7文件（6原JSON+嵌套夹具文件）逐字节复制，保存新配方|原PR回调仍刷新一次当前ProductConfiguration，另外5程序保持|
|空白新建并切换|RecipeID保存新Guid，原6程序默认对象初始化，步骤0|目录仍空；内存默认对象不是6份已落盘JSON|
|复制B并切换|原6程序重载，流程1步，标题及当前Guid更新|实际4条完整拷贝目录中之一，不包含VM过程成功|
|嵌套拷贝遇源文件锁|先复制4JSON及嵌套文件，SDK提示后非递归DeleteDirectory又抛IOException|未添加配方，残余目录5文件保留；公开DialogResult.Cancel才退出原选择器|
|MachineConfig保存锁|新配方只在列表内存；内存RecipeID新值，磁盘仍旧值，原PR回调已换1程序|原调用者未Dispose/未Save列表，由公开夹具清理窗体|
|晶圆保存锁|新RecipeID已落盘，前4程序换新、后2保留，UI禁用/Pr=false；列表磁盘仍旧7条|一次明确程序化私有重载才修复程序；不把禁用UI当作可鼠标操作|
|RecipeList保存锁|原调用者已经Dispose对话框，再直接抛IOException|内存10条，磁盘7条；不泛化成配置保存的通用Exception|
|原PR算法缺失|原PREntity.CopyPREntity抛NullReference，无SDK拷贝提示、无后续确认/添加|缺算法来自显式公开原PREntity夹具；回调在SDK catch及finally之前，公开Cancel退出|
|已知配方但源目录缺失|原CopyDirectory静默返回，SDK仍OK并添加/保存新配方|列表有记录、目标目录不存在，原回调保存空视觉库|
|仅一个源文件且该文件锁定|创建空目标目录后File.Copy失败，SDK提示并成功删除空目录，仍OK添加/保存|第二条列表有记录但目标目录不存在，复制失败没有阻止后续添加|

每轮9条新配方由原SDK Recipe构造器产生，Guid及ModifyDateTime保持原随机/时间值，未写成固定夹具。初始原未命名默认记录和A/B使用公开固定ID/日期种子；后两条MissingSource/BareSource是显式公开拷贝源夹具。最终列表14条=原默认/A/B3+原SDK新建9+公开源夹具2。CopyPartial和CopyPrInvalid没有成为配方，前者仍有未登记的随机Guid残余目录。全部实际列表快照、随机值与文件字节保留。

14次真实Designer BtNewProduct事件中11次到达追加尾部观察订阅，3次原调用者Save异常中断后续订阅。原RecipeRepository末尾Save尝试12次，其中11成功、1列表锁失败；公开种子Save1次和两个源夹具Save2次独立。原切换确认Yes4次/No5次；MachineConfig事件Save4次尝试3成功1失败，另一次公开初始Save不混入。实际ReLoadRecipe4次（3成功/1晶圆失败），其中1次明确程序化私有重试。前置初始化辅助3次。原调用者跳过Dispose2次，均先记录IsDisposed，再公开Dispose清理。

原SDK BtOk_Click的PR复制委托Invoke位于IL offset417，文件拷贝try从423开始；故PR回调异常不进入文件拷贝catch，也不进入其重新启用窗体finally。SDK File.Copy失败在catch中显示真实提示，然后DeleteDirectory(target,false)；有内容的目标目录会再抛异常，而空目录会删除成功，随后代码仍Add/Recipe/OK。原CopyDirectory先递归子目录、再遍历文件，源目录不存在时直接返回，没有成功标志。原TuService.CopyOldRecipePR有6个foreach Finally处理器，没有Catch；这不等于完全没有处理器。

成功拷贝运行使用原视觉仓库正常构造出的空列表，执行真实PR回调、产品配置缓存清空/读取及VisionEntityRepository.Save和备份。没有替换回调、SDK窗体、动作节点或写私有字段。明确缺Alg的公开原PREntity夹具只用于故障路径。真实视觉流程CopyPREntity的正常路径会初始化VM过程，本轮未执行该正常路径，不把空视觉仓库拷贝视为PR/在线VM验收。

公开CreateControl为隐藏原UcMainSystem创建句柄，执行一次原Load，原Designer和SDK ShowDialog消息泵实际运行。主窗体未构造，MainForm.MF=null：原SDK BeginInvoke刷新回调在bound抛3次、replay抛4次同一位置NullReference。公开Application.ThreadException只捕获原异常、控制Framework错误弹窗呈现，不替换SDK回调；保留实际调度次数差异，未重跑至次数相同。原热键注销、公开RemoveTask及全部模态窗体清理完成；SDK基础线程Task句柄及正常终止未捕获。

两轮私有STA桌面在原控件之前分配，实际输入桌面前后Default、主线程仍Default，工作线程结束、CloseDesktop成功；没有SwitchDesktop或物理点击。主窗体SendUiAction保持null，让原AKRSXtraMessageBox真实直接Show，选择真实Yes/No/OK窗体的公开DialogResult；SDK消息使用公开MessageBoxArgs.Text读取。原SDK按钮的2次异常通过公开Cancel退出，这是夹具显式收尾，不是原代码自动取消。

实际JSON文件bound78份/replay77份，其中74份按名称映射的同范围JSON逐项语义一致，44份原字节一致。9个原新Guid、9个原创建时间与1个残余目录Guid只在确切ID/日期字段和目录槽按已观察身份比较，原字节不改。程序Bond与晶圆设备仅对既有5个精确构造时间路径模式比较；14配置/14列表快照逐行核实际内存/磁盘状态。原晶圆备份按秒命名，秒内覆盖导致bound4份/replay3份；7份各自核SHA及相同晶圆语义，数量差异保留，不伪称一一重放字节一致。

![原SDK拷贝选择器](C:/Users/akrs/Documents/ChatGPT/archify/.archify-work/native-recipe-create-copy/bound/selector-row-4.png)

![原切换确认](C:/Users/akrs/Documents/ChatGPT/archify/.archify-work/native-recipe-create-copy/bound/confirmation-row-4.png)

每轮5张原DrawToBitmap PNG（空名提示、拷贝选择器、Yes/No确认、两个文件锁提示），10张已视觉查看并分别冻结。源码348声明/231文件、201原IL方法/8程序集，严格编码与UTF16符号位置绑定；实际16原源资源程序集及5SDK依然逐身份/路径核SHA，172原runtime-map与23精确SDK/16补充/缺log4net1.2.15保持。

保留5个失败候选：首次括号编译错误无CLR；初始新模态等刷新但原Load未创建句柄；SDK自绘消息不在子Control.Text造成确认分类错误；原列表IOException类型预期错误；原PR回调在catch外而预期提示的错误。另2个只读验证草稿（未充分处理原随机值/调度差异，foreach Finally误判为零）和一次生成脚本语法错误均保留回执。成功宿主未为文档或只读校验重跑，无生产C#/csproj修改。

证据：[台账](native-recipe-create-copy-test.json)、[审计](native-recipe-create-copy-audit.json)、[进度](native-recipe-create-copy-progress.json)。16项目、29组、1436文件、13项任务范围保持，29组仍partial，旧正式1328独立。下一步继续原完整MainForm上下文和PR/VM初始化依赖；整机Start/Prepare/CleanFile、实际设备/视觉、SQL消费者、完整MSBuild/LC/Fody及部署仍待验收。整体目标未完成。
