# 原 Program.Main 离线首次启动与真实退出

原 private Program.Main 已在两个独立进程实际调用，两轮各41项，共82项通过；34项阶段绑定通过。实际原入口完成首次版本更新、设备身份保存、字体皮肤、日志设置、Harmony补丁、PR图像委托、实验日志、Application.Run、原MainForm.Load、正常监控及两消费者启动、原SDK文档和标题刷新，随后原Stop／Yes关闭→DataSave→Environment.Exit(0)。401新增＋18705＝19106，512复用。生产源码、工程和SDK未改，整体目标未完成。

|每个独立进程的实际结果|bound|replay|
|---|---|---|
|原 Program.Main／Application.Run|实际执行|实际执行|
|入口主线程|STA／ManagedThreadId=1|STA／ManagedThreadId=1|
|原版本信息窗体|一次真实模态|一次真实模态|
|CurrentVersion／LastVersion|1.5.0.0／0.0.0.0|1.5.0.0／0.0.0.0|
|原正常Load自动监控|一个实际活线程|一个实际活线程|
|观察起点后耗材List重建|至少两次|至少两次|
|原自动存图／统计消费者|均活，队列为空|均活，队列为空|
|原SDK文档创建／标题刷新|1次／实际发生|1次／实际发生|
|原正常关闭真实退出码|0|0|
|ProcessExit时三个后台线程／ThreadFlag|均活／true|均活／true|
|SQL Lazy／SDK数据库尝试|false／false|false／false|
|外部等待／私有桌面CloseDesktop|完成／成功|完成／成功|
|客户区布局|裁切仍复现，未验收|裁切仍复现，未验收|

原入口通过只读反射调用，宿主没有复制Program.Main逻辑或直接构造主窗体。独立目录提供明确公开夹具：OffLineWork、Stop、空硬件、安全门／激光／加热／S1／S2点胶／助焊剂／自动登出关闭、加密检测和启动轴复位false、首次版本0.0.0.0、两步骤配方OriginalProgramEntry。实际C／D剩余空间符合原10／200GiB门限，原磁盘检查未替换。

机器身份文件起初不存在，原JudgeDataMigrated写入本机信息并保存后返回false；本轮没有迁移不匹配提示。原版本检查实际将当前版本更新到1.5.0.0，保留旧0.0.0.0、记录真实LastVersionUpdataTime并保存，实际FrmVersionInfo显示新旧版本；公开Timer仅设置原对话框DialogResult.OK，不作物理点击。

实际主线程1保留原HookMarshalingControl的条件语义。Harmony.GetPatchInfo只读核对原owner和原Prefix方法；两个PR图像委托各一个原接收者。实际创建原“重复标定实验”日志器，但ConfigureFileOutput只设置路径，未生成精度实验文件。原字体和Office2010Blue确由Program.Main执行，未再使用前轮公开样式复制夹具；三个SDK字体getter最终均为Tahoma9Bold。

原Application.Run消息循环为true，Program.MainForm、原MainForm.MF和原PostAction目标为同一实际窗体。正常原Load启动监控，原循环启动两个空队列消费者；每轮在观察开始后等到两次新的耗材列表，证明至少两循环，不提供精确计数。原SDK公开激活创建一个MainDocument，标题刷新写入OriginalProgramEntry。离线分支跳过PR／VM／硬件初始化；本轮不向存图队列或统计队列提交输入，不验证已识别数据库记录。

原Stop／Yes关闭实际保存Settings后调用Environment.Exit。ProcessExit仍观察到监控、存图和数据库存储三个原后台线程存活、ThreadFlag=true；宿主没有false／Join、CompleteAdding、替换Exit或强杀。后置FormClosed观察0、宿主返回标记不存在。ProcessExit堆栈仅保留回调本身，没有完整原调用栈，不把它当成完整栈取证。原Application.Run之后的Mutex.ReleaseMutex代码未到达；原关闭链、实际退出0和原IL单独绑定。

互斥名使用实际宿主Application.ProductName=NativeProgramMainEntryHost，运行中OpenExisting确认存在；宿主EntryAssembly及其配置环境与原执行文件不同。本轮证明原入口函数和上述离线分支真实执行，不等价于原EXE部署验收，也未测试重复启动分支。原在线硬件、加密狗、回零和完整Machine.Start待验收。

外部原生启动器先创建私有桌面，用CreateProcess的STARTUPINFO.lpDesktop指定winsta0子桌面，并隐藏启动窗口，使CLR STA初始化从一开始就在私有桌面；输入桌面Default保持。实际Environment.Exit使子进程自己的桌面清理不可达，外部启动器等待原退出后CloseDesktop成功；没有SwitchDesktop或强制终止。此前主线程SetThreadDesktop失败符合[Microsoft对已有窗口／钩子的限制](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setthreaddesktop)；原生CreateDesktop保留参数必须为NULL，参见[官方API文档](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-createdesktopw)。修正仅用于宿主隔离。

保留五个准备／运行失败候选：原SDK加载后切桌面失败0检查；提前托管STA入口仍切桌面失败且真实CLR异常退出3762504530；启动器保留设备参数由PowerShell空字符串传入导致87参数错误、未创建CLR；Timer提前创建窗口导致原SetUnhandledExceptionMode拒绝更改；新独立准备过程中原BondProgram保存的File.Replace失败，7检查、未调用原入口。最后一项具体外部原因未证实，未修改原保存器或忽略异常，原空BondProgram文件及失败输出保留。将对话框Timer延至原版本窗体创建后通过公开BeginInvoke启用，再重新编译、绑定、运行当前两轮。

UI异常范围有明确限制：宿主先注册观察器，原Program.Main随后注册原异常处理器；运行后只读捕获实际Framework4 IL证实该事件add直接覆盖原线程处理器，而非Delegate.Combine。宿主回调0不能证明原处理器从未触发，没有更改原处理器或再安装替代观察器。当前完整运行、标题刷新、正常关闭及三张预期窗体图已实测；原异常处理器回调次数未插桩。SDK ViewType.InFileAndUI=3，而数据库分支只接受2／4，SQL状态实测false。

执行前365声明／246源、278IL／9程序集，每轮16源码资源程序集路径和SHA一致。预检查另捕4程序集：166个SDK方法和359个宽范围选取的原主工程方法；不把该宽选集合当成全代码覆盖。运行后实际Framework事件／OpenForms的3个方法和SDK日志枚举单独标注。复用已冻结的原构造日期来源，新增版本日期由本轮原源码和IL直接绑定。

Settings在入口前10、关闭前30、最终44；关闭新增14、改变17、无删除。42共同JSON语义一致、37字节相同，只比较8个原构造日期路径与1个原版本更新时间；每轮2个Wafer时间备份独立核对。两个身份／版本文件在Program.Main中已写入，因此不套用前轮28→44与19改变的计数。

六张PNG具有三个独立SHA，版本提示、原HWND主窗口、原退出确认三个代表均通过view_image实际查看，bound／replay各图字节相同。96DPI下原文档1920×999仍大于客户区1536×793，TU／Wafer底部和右侧裁切；真实原入口补证后问题依然存在，布局未修复、未验收。

![实际原Program.Main启动的主窗口](C:/Users/akrs/Documents/ChatGPT/archify/.archify-work/native-program-main-entry/bound-normal/original-entry-document.png)

三份失败只读校验器初稿保留：Windows路径分隔符比较、误套19个改变文件、误用.NET10字段名而实际Framework4字段无下划线；另保留成功但把宿主UI回调0范围写宽的旧摘要／校验器。仅修正证据比较和说明，没有因此重跑已接受CLR。

证据：[台账](native-program-main-entry-test.json)、[审计](native-program-main-entry-audit.json)、[进度](native-program-main-entry-progress.json)。16项目、29组、1436个C#文件、13项任务保持，29组仍partial，旧正式1328独立。后续继续目标布局、迁移与重复启动及异常入口、在线监控、已识别统计SQL、成功VM／设备、完整MSBuild／LC／Fody和部署；整体目标未完成。
