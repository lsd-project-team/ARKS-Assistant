# 原主窗体退出与存图、统计消费者衔接验证

两轮各25项通过，共50项；31项阶段绑定通过。两个独立进程在真实原存图和统计线程仍运行时，通过原MainForm.Close→FormClosed→ExitSoftware→Environment.Exit(0)退出。原源码和SDK未修改，整体目标未完成。3028新增＋14818＝17846，503复用；原输入条数不等于不同业务场景数。

|观测|bound|replay|
|---|---|---|
|原SaveVisionImage实际入队|4096个真实Bitmap|4096个真实Bitmap|
|关闭前图片队列计数采样|4077|4060|
|ProcessExit事件时队列计数采样|2699|2803|
|进程完全结束后的图像文件|1457|1341|
|入队后最终未形成文件的图片|2639|2755|
|退出事件时原存图／统计线程|均仍存活、IsBackground=true|均仍存活、IsBackground=true|
|原统计消费者处理的普通对象|500，队列归零|500，队列归零|
|主数据库Lazy／SDK数据库初始化|均false|均false|
|真实进程退出码|0|0|

数据保存和存图队列处理是不同流程。两轮都完成原DataSave，Settings从28文件变44文件（16新增、19字节改变、0删除），但图片没有全部写完。原ExitSoftware的IL没有队列CompleteAdding、排空、Join或等待保存线程，也没有写ThreadFlag；本轮实际ProcessExit时两个原消费者存活且图像队列未空，最终文件少于4096，证明这些运行的退出流程未等待图片排空。

队列采样与进程退出后的磁盘清点时间不同，ProcessExit回调执行期间原存图线程仍可继续写文件。2699／2803不能与1457／1341做瞬时守恒配对，也不能作为现场固定丢图数或失败率。原计数和两轮不同输出数量全部保留，没有等待到人为相同的数字再接受结果。最终各文件严格为0000.jpg起连续编号，最后分别1456.jpg和1340.jpg；最终目录共2798个文件，全部为完整78字节BMP，没有在本轮观察到半写文件。

每个输入是明确的3×2／24bpp测试位图，六个像素为黑、绿、蓝／白、黑、黄。原生产者逐段创建独立宿主内consumer-images目录，直接入队原对象。原消费者实际保存并Dispose第一幅图后才开始Close，确认不是仅入队而没有工作；剩余对象由原队列持有。所有2798个输出逐文件独立检查BM头、DIB40、像素偏移54、3×2尺寸、24位无压缩、BGR倒序扫描行与填充，SHA完全一致。原SaveBitmap使用ImageFormat.Bmp，因此.jpg文件名实际仍为BMP；没有把测试图当作相机或视觉算法输出。

统计队列采用原容量500集合，先入队500个普通System.Object，再调用原StatisticsService.StartSaveThread。原消费者全部取走，真实原数据库存储线程继续在空Take等待；普通对象不匹配四类数据库模型，DBService.Lazy.IsValueCreated和SDK数据库初始化标志在启动前、关闭前及退出时均为false。本轮验证真实统计消费者与退出的衔接，不证明操作日志、缺陷或参数记录已入库，也没有连接SQL、建表或清理数据库。

两个原StartSaveThread均直接通过原公开入口调用；没有替换原队列或线程，没有私有写入、CompleteAdding、Thread.Abort或退出调用替身。原MainForm正常Load仍使用公开ThreadFlag=false让机器监控线程在循环前退出并Join，所以本轮并非正常监控循环自动启动消费者。两个消费者在该false标志下实际运行，退出事件中标志仍false；这与此前单独消费者测试保持一致，新增的是实际主窗体退出衔接。

![真实退出确认](C:/Users/akrs/Documents/ChatGPT/archify/.archify-work/native-exit-consumer-pending/bound-normal/close-dialog-3-0.png)

每轮只有一次Stop／Yes关闭和一张真实1536×793原Flyout图，不重复上一轮三种取消关闭矩阵。两图与上一轮已查看原Flyout逐字节同SHA；原Description、Yes／No Commands、Visible、Modal及句柄单独核对。公开Timer设置DialogResult.Yes为明确程序化确认，不是物理点击。原MF和PostAction保持原窗体，界面未处理异常0，输入桌面Default；原FormClosed先退出，因此后置FormClosed订阅0、Host返回、窗体Dispose及wrapper Join／CloseDesktop均未到达，不能据此认定消费者优雅停机。

接受宿主前绑定358原声明／240源码文件、243原IL方法／9程序集，并核对每轮16原源码资源程序集身份、路径、SHA。复用前轮4声明／7IL的构造日期来源，42份共同JSON按8个精确日期路径比较语义，38份字节一致；每轮2份原晶圆时间备份按字节独立绑定。原RecipeList与ProcessDomain内存修改仍未由退出DataSave保存，沿用上一轮已经验证的边界。

原编译元数据scope继承父轮“没有消费者”的文字，原输出保留；实际两个线程身份、队列及文件证据明确证明本轮消费者执行，SQL仍未执行。该文字不是运行证明。一个只读验证器生成初稿重复声明canonical函数而失败，原稿完整保留，修复后通过；两次已接受宿主没有重跑。

证据：[台账](native-exit-consumer-pending-test.json)、[审计](native-exit-consumer-pending-audit.json)、[进度](native-exit-consumer-pending-progress.json)。16项目、29组、1436个C#文件、13项任务范围保持，29组仍partial，旧正式1328独立。下一步继续正常监控入口、真实已识别统计记录与SQL、整主窗体呈现和成功VM／设备；完整MSBuild／LC／Fody及部署仍待验收，整体目标未完成。
