# 原主窗体关闭、数据保存及真实进程退出验证

两轮各60项（正常保存29＋晶圆文件占用31），共120项；30项阶段绑定通过。共4个独立进程实际执行原MainForm.Close→原FormClosed→ExitSoftware→DataSave→Environment.Exit(0)，保留真实进程退出事件、原文件和26张截图。372新增＋14446＝14818，498复用。整体目标未完成。

|关闭条件|每个进程的实际结果|磁盘及边界|
|---|---|---|
|Working，确认No|原退出Flyout后仍出现“请先停止设备”，取消关闭|原FormClosing公开后置观察Cancel=true；Settings无变化|
|Working，确认Yes|原提示要求先停止设备，取消关闭|窗体保持可见，原退出保存链未进入|
|Stop，确认No|取消关闭，没有停止提示|窗体保持可见，Settings无变化|
|Stop，确认Yes，正常保存|原DataSave及原Environment.Exit执行，进程退出码0|Settings从28变44：16新增、19字节改变、0删除；17原空仓库全部保存为真实JSON|
|Stop，确认Yes，首个晶圆文件被占用|原“加载数据失败／文件保存失败”弹窗，公开OK后仍退出，退出码0|28文件全部保留原SHA，17仍为零字节；后续数据保存被跳过|

正常保存前公开修改产品IsOppositeSex=true和晶圆CurrentTablet.CreateTime=2021-02-03T04:05:06Z，退出后文件均含新值，证明实际持久化。同时公开修改内存RecipeName=UnsavedExitRecipe及ProcessStepName=unsaved-exit-step，退出后的RecipeList.json与ProcessProgram.json仍为原种子名称和原SHA。原DataSave的39个Save调用位置不含RecipeRepository.Save或ProcessDomain.Save；本轮证明退出不会顺带保存这两个内存修改，没有将39静态位置计作39个逐方法运行追踪。

失败场景在独立Settings目录的现有晶圆文件上持有公开FileShare.None锁，锁持续到进程退出事件。原WaferSubDevicePara.Save位于DataSave第一项，失败后被DataSave捕获，错误文本仍使用“加载数据失败”，原ExitSoftware随后继续运行并以0退出。没有替换保存函数、异常、SDK、退出调用或关闭事件。该结果说明退出码0不能证明数据已保存；本轮没有修改生产C#以改变这一原行为。

![原退出确认](C:/Users/akrs/Documents/ChatGPT/archify/.archify-work/native-mainform-close-save/bound-normal/close-dialog-0-0.png)

![原保存失败提示](C:/Users/akrs/Documents/ChatGPT/archify/.archify-work/native-mainform-close-save/bound-wafer-lock/close-dialog-3-6.png)

四个进程共16次真实退出Flyout、8次运行中停止提示、2次保存失败提示，均Visible、Modal及IsHandleCreated=true。26原DrawToBitmap图对应3组完全相同SHA的图片：1536×793原Flyout、138×129停止提示、378×157保存失败提示。3份代表图逐一查看，其他23份按完全一致的字节校验覆盖；不是删除重复截图。公开WinForms Timer读取原Flyout.Action.Description／Commands和MessageBoxArgs.Text，再设置原窗体公开DialogResult，确认Yes／No和提示OK为明确程序化夹具，没有物理按钮点击。

原FormClosing后置公开观察4行Cancel=true、true、true、false。原FormClosed处理器先调用ExitSoftware，直接结束进程，因此后置公开FormClosed订阅次数0；这个0不能解释为原FormClosed未运行。原Host的正常返回与stdout、私有STA wrapper的Join／CloseDesktop及Dispose均未到达，真实ProcessExit回执和父进程退出码单独验证；不声称窗体已Dispose或桌面显式清理成功。ProcessExit回调只写观察，不拦截退出或释放文件锁；回执时原MF／PostAction仍指向原窗体，输入桌面保持Default。

每个进程采用原MainForm正常构造／Show／Load，原MF赋值及原PostAction派发，私有STA桌面在控件构造前分配。原主系统文档保持懒加载，没有SDK界面刷新任务。公开ThreadFlag=false让原机器监控线程在循环前退出并Join，硬件库为空，公开IsTransportHeatConfigured=false，工作模式为OffLineWork；在线CloseAllHardware和配置加热器关闭分支未执行，SQL／存图消费者未启动。未执行整Program.Main、整机Start、设备或本机VM。

接受宿主前绑定357原声明／239源码文件、236原IL方法／9程序集，以及只读原SDK退出Flyout元数据与ShowDialog调用。正常场景42份共同可解析JSON语义一致，38份字节一致，另有两份原晶圆时间备份／进程；文件占用场景10份共同可解析JSON语义一致、8份字节一致，17空仓库和1原时间备份／进程独立绑定。比较仅排除8个明确构造日期路径。ForceCalibrationData.ForceCaliFinishTime和默认TouchDown／BMC两条吸嘴CreateTime在首次只读比较中发现，运行后额外绑定4原声明／7原IL方法说明DateTime.Now来源，明确标注补证时序；原文件和已接受宿主未重跑。

首编译候选使用错误枚举名Running而失败，运行守卫阻止CLR，修正为原Working后接受；一个只读日期比较初稿失败完整保留。证据：[台账](native-mainform-close-save-test.json)、[审计](native-mainform-close-save-audit.json)、[进度](native-mainform-close-save-progress.json)。16项目、29组、1436个C#文件、13项任务范围保持，29组仍partial，旧正式1328独立。下一步继续整主窗体布局、后台监控与消费者、成功VM／算法和真实设备；完整MSBuild／LC／Fody及部署仍待验收，整体目标未完成。
