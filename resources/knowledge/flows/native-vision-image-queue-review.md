# 原始图片队列、所有权与异步异常核验

原生CLR4.0.30319.42000正常41项和关闭队列生产者12项通过；3个独立故障进程在终止前分别通过10/8/9项，共56个不同断言。它们不是“80项成功运行”，三个消费者故障子进程实际退出3762504530（有符号-532462766）。外层记录器exit0表示成功核对预期故障。完整Main1137编译项/资源与16个源码/资源程序集位置、SHA保持父绑定；本轮测试的VisionService文件是有效UTF8。宿主EXE、完整正常JSON、原异常事件JSON、进程结果、23选定原IL、实际BMP字节及编码审计独立重放一致。88新增冻结+3491父=3579。整体16工程/29组/1436文件/13项仍未完成。

## 原生产者入队同一个Bitmap，原消费者保存后释放它

完整执行[SaveVisionImage](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L213)、[StartSaveThread/SaveBitmap](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L326)，没有截取方法或替换原类。原BitmapBlockingCollection是容量-1的无界集合；公开队列身份保持，原thread在静态初始化后为null。测试Bitmap来自实际Framework System.Drawing，普通3×2/24bpp像素作为输入；所有写入路径经测试端校验位于实际宿主启动目录，启动路径没有替换。

生产者逐段Path.Combine，跳过空字符串、建目录，最后加入(bitmap,allPath+"//"+bitmapName)，不是Clone。入队后同一个输入仍可读取和修改；在消费者启动前把左上像素改为黑，原SaveBitmap实际文件像素随之改变。原消费者指定ImageFormat.Bmp，即使文件名为native-bmp.jpg也输出BM头BMP。独立检查78字节大小、54像素偏移、40字节DIB、3×2/24bit/无压缩，以及24字节BGR倒序扫描行和填充，不只调用同一编码器作“预期”；实际文件再次加载也得到黑色左上像素。

成功保存后原消费者Dispose同一个输入Bitmap，读取Width得到ArgumentException；两个输入均在实际保存后释放。原PR成功/失败源图及结果图调用路径各自Clone新Bitmap，因此“同一对象重复入队”的故障输入不等同正常PR总是重复同一个对象；本轮也未运行相机和PR算法。

## 目录与同步生产者失败边界

后面的绝对路径段会使Path.Combine重置此前累计路径，已经创建的前一目录仍存在；测试各段仍约束在宿主内。bitmapName含冒号的非法文件名能入队，生产者没有验证文件名；仅做入队观察后测试端取出并释放它，没有向这个非法名称写入。空路径列表也能入队，目标字符串是//no-parent.bmp；它未实际写入，不能由此宣称根目录文件已产生。

null路径列表、含NUL的路径段在原try中失败，原catch发布SDK Error并正常返回，没有入队，输入Bitmap仍可读。创建目录先于GetInvalidPathChars/Replace，后置过滤无法挽回前面的Path.Combine/CreateDirectory异常。完整原主IL传LogCategory.PR=2、ViewType.InFileAndUI=3；SDK原数据库只接受2或4，3返回，不等于构造UI控件。实际SDK数据库初始化标志false、主DBService Lazy未创建，宿主没有实际日志UI订阅者。

另一个正常退出进程先关闭空原队列且不启动消费者，再调用完整生产者：目标目录已创建，Add失败被原catch记录，调用正常返回且无文件/无入队，Bitmap仍可读。调用方不能从void正常返回判断图已经持久化；测试端最后释放自己的未入队输入。原生产者的catch也不包含错误日志调用自身的第二层保护，本轮未制造SDK记录器抛错。

## 保存失败发生在另一个原始线程，原生产者catch覆盖不到

- missing-parent进程用完整原SaveVisionImage创建基目录并加入not-created/image.bmp。生产者已经正常返回，但没有创建文件名携带的子目录。原消费者取出后Image.Save抛ExternalException/GDI+一般性错误；事件记录当前线程就是原私有thread，IsBackground=true、isTerminating=true，栈含Image.Save和VisionService.SaveBitmap。该Bitmap在异常事件时仍可读，证明这条失败路径没有到达后面的Dispose；不声明永久内存泄漏。一个后续队列项仍在，原线程没有继续消费。没有创建失败目标文件。
- reused进程对同一个真实Bitmap两次完整SaveVisionImage，第一项实际保存first.bmp并Dispose，第二项再Save已释放对象抛ArgumentException。事件中输入已不可读，后续标记项仍在；first.bmp保持，second.bmp未创建。它是明确的对象所有权故障输入，不是现场发生率。
- complete进程原消费者在空Take等待，真实集合CompleteAdding后Take抛InvalidOperationException，原循环无catch，原后台线程异常终止CLR。原源码检索没有该集合的生产CompleteAdding调用，所以保留为隔离故障；不说应用常规退出必然走此路径。

三个原UnhandledException处理器只保存证据，不抑制异常、不主动Environment.Exit。错误码和原异常事件都保存，没有把非零子进程写成数据库成功或设备运行成功。原SaveBitmap的全方法无catch/finally，Dispose在Save之后；原框架System.Drawing加载位置与只读IL捕获路径匹配，原System.Drawing方法没有替身。

正常41项进程在ThreadFlag=false时实际启动存图线程，消费null图时只丢弃而不创建文件；20次顺序StartSaveThread保持同一存活原线程，空队列等待，Join100ms没有结束。原循环不读取ThreadFlag。正常Main返回时队列仍开、保存线程仍活且为后台线程；exit0不是优雅停止/排空协议。未测试并发Start，不能用20次顺序调用证明没有启动竞争。

## 委托连接确实存在，不能只检索带括号的直接调用

16个完整源码/资源程序集共18286个方法体的只读call/callvirt/ldftn/ldvirtftn/newobj扫描找到6个相关调用或委托位置。主工程几处直接SaveVisionImage(...)被注释，但[Program.Main](../../trunk/AKRS.ZX2200/Program.cs#L247)实际IL有ldftn VisionService.SaveVisionImage，并Delegate.Combine写入PREntity.SaveLocateImageAction，同时注册IsSaveLocateImage到[SaveLoacteImage](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/MachineSoftwareConfiguration.cs#L191)。因此不能宣称生产链没有接通。这里只证明注册代码存在；完整启动中的许可证、硬件、Harmony补丁及是否实际到达注册点未运行。

[PREntity.Excute](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L458)的原IL有3次SaveLocateImageAction.Invoke。相机/算法成功且IsSaveImage时Clone原图；IsSaveLocateImage()且postImage时Clone匹配结果图；失败且IsSaveImage时Clone原图。调用处在PR本地try/catch中，同步回调异常可以被它记录，而SaveBitmap稍后的异步异常不回到这个catch。源图和结果图对象所有权由克隆后交给生产者，再由保存消费者释放；相机/FindModel/算法输出、本地result实际取值和完整调用时序未执行验收。

还有[实验界面simpleButton22_Click](../../trunk/AKRS.ZX2200/Experiment/TestFunction/FrmTest.cs#L1001)直接同步调用无穷SaveBitmap，IL确认没有在此处新建Task；按钮控件和事件没运行，不能说已实际挂起UI。后台Machine监控正常代码调用StartSaveThread，本轮只直接执行完整服务Start。8个PR委托字段读写位置单独登记，支持跨程序集调用关系，不把简单grep结果当成动态分派全覆盖。

## 新发现：冻结PR源码编译的字符串保真存在缺口

追踪回调的原文件PREntity.cs没有BOM且严格UTF8解码失败。CP936解码没有替代字符，能读到D:\视觉定位成功图像\和D:\视觉定位失败图像\。当前冻结脚本compile-original-project-source.ps1使用默认ReadAllText，实际冻结PR程序集里的这两个路径常量匹配带U+FFFD的UTF8损坏字符串，不匹配CP936文本。用同一个bundled pwsh编译宿主实测ReadAllText产生923个替代字符；Framework只读审计产生918，解码器计数差异保留，目录常量损坏本身是直接IL证据。

这不是原源文件被改写，也不能把它当作生产部署的目录已经损坏：目前未验证原csc/MSBuild的编码选择或部署程序集。本轮服务测试的VisionService是有效UTF8，41/12/10/8/9行为及实际BMP证据仍成立，但已有“源码编译成功/哈希一致”不足以证明全仓库字符串保真。旧源码/编译器/程序集/父验证均保持冻结，不把父验收涂改成新的成功；最新清单明确增加这个实质缺口。

**下一优先项是全仓库源文件编码审计和另名保真编译/重放，并核对原工具链的解码规则。** 当前工作不是把原PR路径强行改成测试目录，也没有启动相机/VM或写入D盘原路径。阅读器/源码展示的解码也需要纳入后续审计，不能仅修正本轮两条目录描述就声称整体完成。

## 冻结与验收范围

首次宿主编译成功，但17项之后测试误期望Error默认InFile0，实际Main传InFileAndUI3，原生exit1；原失败Cases/JSON/进程记录保持。修正测试预期，41/12/10/8/9全部达到预期。早期19方法IL与41项运行保存；后续补到23方法/委托连接及编码风险，冻结前只澄清宿主scope，不改原程序集/方法和41项表达式。62项先冻结，独立重放后追加26项为88；85590绑定核验实际exit0。三个故障子进程仍实际非零。

见[测试](native-vision-image-queue-test.json)、[审计](native-vision-image-queue-audit.json)、[进度](native-vision-image-queue-progress.json)。各本轮分进程断言、父生产者60、消费者30/12、机器70、任务100、输送180、动作251、程序58、正式1328、受控278/目录119、98/124和40专题3817保持独立。LC5/Fody2/VM5失败、388资源1498条不改写。编码审计/保真重编译优先，其后继续其他等待/异常退出链、真实数据库持久化/SQL故障、生产配方重建、在线节点下层/就绪/PR/校准/测量/IO、匹配完整构建/部署及真实UI/设备。
