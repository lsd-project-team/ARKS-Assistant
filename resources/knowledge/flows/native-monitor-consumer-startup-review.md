# 原主窗体正常监控启动、消费者及受控重启验证

两轮各40项通过，共80项；32项阶段绑定通过。原MainForm正常离线Load实际自动启动“后台监控线程”，该线程启动原存图和统计消费者；宿主没有直接调用两个StartSaveThread。449新增＋17846＝18295，506复用。生产源码、工程文件和SDK未修改，整体目标未完成。

|每个独立进程的实际观察|bound|replay|
|---|---|---|
|正常Load自动创建的监控线程|1|1|
|公开停止／Join后再启动的新监控线程|1|1|
|每个监控线程观察到的新耗材列表|至少2次|至少2次|
|两线程合计实际循环下界|至少4次|至少4次|
|活监控线程期间顺序重复Start调用|100＋25|100＋25|
|自动启动的原存图／统计线程|各1，重启期间身份保留|各1，重启期间身份保留|
|初始原生产者队列|16真实Bitmap＋500普通Object|16真实Bitmap＋500普通Object|
|Close前已保存图像／已Dispose输入位图|16／16|16／16|
|Close前和ProcessExit时两队列|均空且未CompleteAdding|均空且未CompleteAdding|
|false标志并Join两监控后，两个消费者|仍存活|仍存活|
|主数据库Lazy／SDK数据库初始化|均false|均false|
|真实原Close→Environment.Exit退出码|0|0|

原MainForm构造和Load保持真实MF赋值、原PostAction与SDK窗体；主要业务文档保持lazy，不激活SDK刷新。公开ThreadFlag在Load前置true，消费者此前均未创建，原队列已明确有16图和500普通对象。正常原Load经过DataLoad、ChangeData及离线Modbus入口后调用StartBackGroundThread；随后实际两个原消费者取队列、写BMP、Dispose全部输入位图。不是独立直接StartSaveThread的前轮范围。

原监控循环先安全门、激光尺、自动登出、温度、耗材、传感器，再存图／统计，最后Sleep(100)。正常离线、空硬件配置明确关闭安全门、激光尺、加热、S1、S2点胶、助焊剂和自动登出，登录用户为null。耗材列表实际为空，每次原GetConsumablesList创建新List；传感器原离线分支保持池为空。两个时代分别在观察起点之后等到新List，再观察下一新List，因而每个至少两轮；没有修改原循环或安装计数器，不报告精确总循环次数。此范围不验证在线门控、加热、耗材告警或传感器IO。

监控存活时100次／25次顺序公开StartBackGroundThread保留同一线程，证明原IsAlive守卫在这些顺序调用中有效。公开false标志＋Join结束第一监控；再true并调用原公开Start创建不同的第二监控，两个消费者身份保持；再次false＋Join后消费者仍活、IsBackground=true并在空Take等待。没有并发Start竞态、线程替换、私有写入、CompleteAdding、Abort或强杀。原激光检查中的Task.Delay(100)由IL可见且返回未等待，未捕获其句柄；原生产业务Task为0不代表没有计时任务。

两轮32个图像均为完整78字节3×2／24bpp BMP，尽管原文件名为.jpg；逐文件独立核对BM、DIB40、偏移54、BGR像素和填充，SHA相同。所有16输入位图均实测Dispose，关闭前队列已空。本轮不再测积压丢图数量；前轮4096输入的退出遗漏证据完整保留。

原统计消费者处理500普通System.Object，没有匹配实际数据库实体，不创建原DBService.Lazy，不连接SQL、不建表／清库、不证明已识别日志持久化。两消费者在ProcessExit时仍存活、集合仍开放，监控已Join并不意味着所有后台线程优雅退出。

每轮原Stop／Yes关闭完成DataSave：Settings28→44，16新增、19改变、0删除；42共同JSON按8个原构造日期路径比较，38字节一致，每轮2时间备份独立绑定。RecipeList和ProcessDomain内存修改仍未由该退出保存。原处理器先Environment.Exit，后置FormClosed订阅0、Host返回、窗体Dispose及wrapper Join／CloseDesktop未到达。

两张实际原Flyout图与此前已查看代表逐字节等价，SHA和1536×793尺寸单独核对。公开Timer设置DialogResult.Yes，未作物理点击；输入桌面Default、UI未处理异常0。整主窗体文档布局仍待验收。

执行前绑定360声明／242源码、263原IL／9程序集，每轮16源码资源程序集路径和SHA匹配。执行后独立只读捕获遗漏的生成监控lambda，1方法／1程序集，证明循环调用顺序、volatile ThreadFlag读取、Sleep100及无catch；不把补捕获算成执行前证据。复用前轮4声明／7IL的日期构造来源。

保留两轮40项初稿：重启观察可能读取前一线程留下的耗材列表，原报告至少两轮的观察起点不严谨。保留完整原输出／宿主／编译／来源证据；调整测试观察起点后重新编译并运行当前两轮。该修正只针对探针，没有改生产代码；初稿不加入当前80项执行数。

证据：[台账](native-monitor-consumer-startup-test.json)、[审计](native-monitor-consumer-startup-audit.json)、[进度](native-monitor-consumer-startup-progress.json)。16项目、29组、1436个C#文件、13项任务保持，29组仍partial，旧正式1328独立。下一步继续在线监控／告警、真实已识别统计记录及SQL、整窗体布局、成功VM与设备、完整MSBuild／LC／Fody及部署；整体目标未完成。
