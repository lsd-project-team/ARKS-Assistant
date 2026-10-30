# ZX2200视觉服务：执行与异步存图

2026-09-28。Infrastructure首次限定复核，仅覆盖VisionService及直接调用链。

## 实际自动工作步骤

1. 点胶检测控制器调用VisionService.VisionDefect。服务按名称查PR，锁定实体并调用PREntity.DoWork(hardware,setLight,true)。普通定位Vision找不到PR时弹窗返回null；VisionDefect却在判空前写IsDefectPR=true，因此缺失PR会先抛异常。该标记在这两个服务入口未见复位。[服务78–204](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L78)；[点胶调用195–246](../../trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseVisionController.cs#L195)。
2. PREntity还使用静态lockObj，设置相机、轴名及光源名；isSetLight时设置灯光、等待15ms并设置曝光/增益/Gamma。这些设置API返回false仅记录日志后继续。[静态锁42](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L42)；[硬件165–180](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L165)；[执行339–432](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L339)。
3. Excute先置结果None，取8位图；图为null记录错误并返回。克隆图像后，闪光且非硬触发时另起任务关灯，此处不等待；再执行Alg.SetImage、FindModel、读取MatchResults。算法调用在存图try之前，异常不由该catch捕获。[458–515](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L458)。
4. 成功/失败分支按选项提交存图，然后才赋Success/Fail；try内异常被日志捕获时可能保留None，不能把FindModel=true当作上层一定成功。DoWork成功时构造结果展示并向检测/通用视觉窗口Post。[516–638](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L516)；[400–432](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L400)。
5. Vision成功时对MatchResult复制中心和角度，其他类型返回AlgResult；VisionDefect成功直接返回AlgResults，非成功返回null。两个服务入口无本地重试循环，重试/停止须继续追各调用方。[78–204](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L78)。

## 委托、队列与文件

Program把SaveLoacteImage绑定到IsSaveLocateImage、SaveVisionImage绑定到SaveLocateImageAction。服务内部旧直接存图语句虽已注释，PREntity仍有实际委托调用。[启动246–248](../../trunk/AKRS.ZX2200/Program.cs#L246)；[提交520–595](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L520)。

SaveVisionImage先逐级建目录，再清理路径非法字符，然后把同一个Bitmap及路径入队；catch只记日志。队列无容量上限，没有磁盘容量检查或落盘回执。入队不等于保存成功。[213–250](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L213)；[320–321](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L320)。

Machine后台ThreadFlag循环调用StartSaveThread，末尾Sleep(100)，不是严格100ms调度器。存图线程不存在或不存活时创建后台线程；消费无限Take→Save(Bmp)→Dispose，无本地catch/finally、重试、取消或排空协议。写盘异常时未保证Dispose/重入队；运行时全局异常策略未验证，不能承诺自动恢复。[监控662–701](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L662)；[线程326–355](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L326)。

## 输入输出与缺口

输入为PR名称、硬件参数、灯光开关、相机图像和存图配置；输出为算法结果/null/异常、展示消息、日志及异步BMP文件。此队列是内存队列，不是持久消息服务。

- 待展开各派生算法、VM SDK、相机/灯光驱动、坐标标定及所有失败调用方。
- 待验证静态/实例锁组合、图像所有权、队列退出、磁盘错误和窗口断连。
- Infrastructure其他服务、DistanceCheck调用方和BaseMatters消费者未完成。
- 部分PR文件UTF-8解码出现替换字符；证据保留原始字节哈希和行号，中文字符串须核对实际编码。
- 未修改生产源码，未运行SDK或设备；以上不是全模块验收。

## 数据服务补充

已补DBService的SQL Server连接、建表清理、写入/查询与异常返回；见[统计与数据保存](statistics-data-module-review.md)。尚未运行数据库或验证完整数据源。
