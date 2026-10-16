# 原 PR 初始化任务及 VM SDK 失败边界验证

两轮各31项通过，共62项；29项阶段绑定通过。每轮实际调用原Machine.InitPR三次，得到三个不同的Task，全部Faulted；异常、AggregateException及六张原生提示截图完整保留。整体目标未完成。

|原流程／状态|两轮实际结果|验证边界|
|---|---|---|
|离线，初始化标志false|返回Task，最终Faulted，标志false|原InitPR没有离线保护，仍进入VM SDK初始化|
|正常工作模式，标志false|返回Task，最终Faulted，标志false|未执行完整Program.Main或硬件初始化|
|离线，公开预置标志true|返回Task，最终Faulted，标志仍true|原失败处理不清除成功标志；预置true明确为公开夹具|
|VM.Core.VmSolution类型初始化|TypeInitializationException内层FileNotFoundException：C:\ModulePathGenerate.txt|失败在原StreamReader构造；尚未进入CloseSolution方法体、CreatSolInstance、PR名称收集或算法初始化|
|原失败提示|设备初始化视觉模板失败，请检查加密狗或联系设备人员!|三次真正SDK模态提示／轮，使用原MainForm.PostAction与Control.Invoke；不能据此判定加密狗故障|
|Settings文件|每次PR调用前后无新增、删除或字节改变|每轮28文件：10可解析JSON、17原零字节仓库、1晶圆时间备份；两轮8份可解析JSON字节一致|

原Program.Main的IL在调用InitPR后直接pop丢弃返回Task，然后继续硬件初始化相关调用。本轮只读核对了该入口，没有执行完整Program.Main，也不声称已经复现进程级未观察Task异常或硬件继续运行。原InitPR后台lambda捕获Exception后显示原提示、记录错误并rethrow；唯一PrInitSuccess=true赋值在全部后续步骤之后，入口和catch均无清零。

原MainForm正常构造、Show及Load建立MF和原PostAction派发器，未反射设置MF或替换回调。公开ThreadFlag=false使原机器监控线程创建后在循环前退出并Join，主系统文档保持懒加载，因此没有SDK界面刷新任务；每轮界面未处理异常0、硬件0，SQL和存图消费者未执行。每轮公开固定配方ID ffffffff-1111-2222-3333-444444444444、名称PrInitBoundary和日期2020-01-01；一次明确私有InitProgramNodes辅助和原Save生成种子。任务全部终止后公开清理标志并Dispose窗体，生产FormClosed→ExitSoftware→Environment.Exit关闭链未执行。

![原PR初始化失败提示](C:/Users/akrs/Documents/ChatGPT/archify/.archify-work/native-pr-init-boundary/bound/pr-warning-row-0.png)

六张370×129的原DrawToBitmap截图已查看并按字节冻结，提示的Visible、Modal与IsHandleCreated均为true。公开WinForms Timer只读取原MessageBoxArgs.Text并通过DialogResult.OK关闭，使用真实消息泵，没有物理点击或截图修改。两轮不同TaskID与耗时原样保留，比较只排除这两个具体字段。

接受宿主前已绑定357原声明／239源码文件、230原IL方法／8程序集及额外SDK5方法／3程序集／221个PInvoke声明。嵌套Machine/<>c的InitPR lambda在运行后只读补捕获1方法，并独立标注时序；没有把补捕获伪称为运行前证据。原SDK声明依赖相对路径.\iMVS-6000PlatformSDK.dll；仓库检索未找到该本机DLL，当前C:\ModulePathGenerate.txt不存在。本轮未伪造安装配置或替换VM SDK，不声称本机视觉初始化、加密狗或算法成功。

每轮16原资源程序集及8实际已加载SDK程序集分别核对身份、路径、SHA。VM.Util／VM.Utility等依赖由原LoadFrom目录解析到HikVision库，部分路径与旧补充映射的Debug回退路径不同，因此新增了实际已加载文件的只读元数据及字节绑定。保留第一次只读验证器路径断言失败，按实际元数据修正；接受宿主没有重跑。

原宿主字段actualNativeVmInitializationAttempted=true措辞过宽，原输出完整保留。台账明确解释为“已尝试托管VM SDK类型初始化”，actualNativeVmApiReached=false、successfulVmInitialization=false；失败发生于首次配置文件读取，不能把三次Faulted Task计为三次本机API调用。

一个准备候选的源码绑定因错误命名空间失败，虽编译通过，守卫未执行CLR；归档完整保留。原源码、项目文件和SDK未修改。证据：[台账](native-pr-init-boundary-test.json)、[审计](native-pr-init-boundary-audit.json)、[进度](native-pr-init-boundary-progress.json)。新增来源数和总来源数见台账，父来源14205保持。16项目、29组、1436个C#文件、13项任务范围不变，29组仍partial，旧正式1328独立。下一步继续整窗体呈现和关闭保存链；成功VM／算法、真实设备、监控／SQL／存图消费者、完整MSBuild／LC／Fody及部署仍待验收，整体目标未完成。

文档验证初稿误把更早的新建配方父台账13651写成14205，原断言及失败日志完整冻结；另建最终进度验证器修正旧指针断言，原运行结果未重跑、原冻结输入未改。扩展7项，最终241新增+14205=14446。
