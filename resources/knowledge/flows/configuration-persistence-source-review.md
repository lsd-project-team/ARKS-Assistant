# 配置加载、运行记录与持久化：源码复核

更新：2026-09-28。限定范围静态复核，未运行设备、连接数据库或修改生产源码。复用既有 recipe-*、stats-*、data-*、vision-* 证据，新增 persist-* 用于保留与清理下层。本文整合工作步骤，不把重复阅读计为新增覆盖。

## 工作步骤摘要

1. MainForm_Load 调用 Machine.DataLoad，依次取得供晶、邦定、输送、System1 点胶相关配置单例，最后设置 PropertyChangeAop.InitSuccess=true。这不是一个统一文件加载器：每个GetInstance是否读文件取决于其实现和缓存状态。任意调用抛异常会跳过余下调用，catch记录日志并弹窗，方法无成功返回值；重复加载前也未在此方法重置InitSuccess。见 [DataLoad](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs#L294)。
2. 主窗体继续启动后台服务。运行时操作日志、部分参数变更、设备状态变更、检测结果进入数据库队列；图片保存请求进入另一条图片队列。两条消费者线程独立运行，不是同一个事务。图片真实调用通过Program绑定的PREntity.SaveLocateImageAction委托进入，不能仅用直接调用名搜索认定没有生产者；成功原图受IsSaveImage控制，成功结果图受IsSaveLocateImage()与postImage控制，失败原图受IsSaveImage控制。PREntity这些分支先Clone再传递，SaveVisionImage本身不再次Clone。见 [委托绑定](../../trunk/AKRS.ZX2200/Program.cs#L246)、[视觉结果](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L516)。
3. 数据库消费者阻塞Take，按实体类型调用DBService.Insert；Insert复制SqlSugar客户端并ExecuteCommand，异常捕获后只记Info日志，不向消费者返回失败或重入队。已出队不代表已持久化。见 [数据库消费者](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L110)、[数据库写入](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L84)。
4. 图片消费者Take后Save(Bmp)、Dispose；保存抛异常时没有局部catch/finally保证释放或重试。见 [图片消费者](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L343)。
5. 退出链调用Machine.DataSave，顺序调用各模块Save及SaveMachineConfig。任意抛出的异常会跳过余项；catch中的文字仍为“加载数据失败”，不能用该提示区分读/写故障。之后外层退出链还会继续，不存在本方法的汇总成功标志。见 [DataSave](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs#L352)。

## 输入输出与关键分支

|入口|实际输入与输出|源码限定与失败语义|
|---|---|---|
|StatisticsService.SaveEntity|message、operate → OperateLogEntity入队|只以message与静态lastMessage比较；同文字不同操作员也可能被抑制。无时间窗口或持久化确认。见 [SaveEntity](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L77)|
|PropertyChangeAop.OnPropertyChangedEvent|对象、属性名、变更前后值 → ParameterChangeLogEntity|InitSuccess必须为true；空值、空字符串、相等值、Point3D相等、缺少显示名称均返回；不是所有参数变化都有审计记录。见 [属性过滤](../../trunk/AKRS.ZX2200/Infrastructure/AOP/Module/PropertyChangeAop.cs#L47)|
|Machine.SetState|旧新状态不同 → 先改变状态，再日志入队|数据库队列满时Add没有显式超时/取消参数，调用可能停在状态已改变之后。不能当成状态与审计原子提交。见 [状态日志](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.StateRelated.cs#L52)|
|StatisticsDomain.AddDefectResult|检测实体 → SaveDataToDb → 入队，然后调用补偿结果处理|顺序是入队而非等待数据库成功；若入队等待，后续处理也未执行。见 [检测结果](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsDomain.cs#L407)|
|VisionService.SaveVisionImage|Bitmap、目录片段列表、名称 → 图片队列|逐段创建目录在非法路径字符清理之前；直接入队原Bitmap引用，没有Clone；“考虑磁盘是否够用”仅注释，本方法没有容量判断。见 [图片入队](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L213)|

数据库队列初始有界容量500；图片队列默认无界。两者为公开可设置属性，以上为初始构造配置，不代表不能被替换。各Add入口没有指定取消或超时；图片生产快于消费时，不能声称有内存背压保护。见 [数据库队列](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L53)、[图片队列](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L320)。

## 数据库与配置边界

- DBService为Lazy单例，配置指向本机SQL Server的ZX2200库，使用Windows集成身份认证及自动关闭连接。首次构造逐一尝试初始化8类表，再调用CleanInfo。这里不是远程云服务，也没有证据证明数据库本身被自动创建。见 [构造](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L44)。
- Query两个重载异常时返回空List，调用者仅根据空集合不能区分“没有记录”与“查询失败”。CreateTableIfNotExists也捕获异常后记录日志，不能把构造函数完成等同于所有表可用。见 [查询与建表](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L104)。
- CleanInfo在构造时调用各表清理，阈值采用Now.AddDays(-SqlSaveDue)，不是按“180天”注释固定执行。未发现本段中的周期调度，不能把构造时清理画成定时任务。见 [清理入口](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L161)。逐表条件已列在下节。
- MachineConfigContext.GetInstance：文件不存在则新建默认实例；文件存在但读取失败只弹窗，未创建默认替代实例，因此该调用可能返回null。SaveMachineConfig将this传给JsonFormatHelper保存，没有本地catch。RecipeID决定CurrentRecipe/RecipeName的仓库查询，不代表配方一定存在。见 [机器配置](../../trunk/AKRS.Galaxy2.MachineSupport/Config/MachineConfigContext.cs#L25)。

## 配方切换与文件存储

- 根目录为Application.StartupPath/Settings；MachineConfig.json保存RecipeID；配方目录为RecipeParams/{RecipeID}，设备参数目录为DeviceParams。产品配置写ProductConfiguration.json，点胶程式写DispenseProgram.json，供晶设备参数写DeviceParams/WaferSub/WaferSubDevicePara.json。见 [根路径](../../trunk/AKRS.Galaxy2.MachineSupport/Config/PathConfig.cs#L40)、[模块路径](../../trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs#L90)。
- BarBtLoad先将新RecipeID保存，再按旧配方是否存在/ID是否不同决定ReLoadRecipe；同ID不会重载。失败后此路径没有恢复旧ID。ReLoadRecipe禁用界面、清dock并初始化六个程式节点，这些调用在try/finally之前，若此处异常，不能保证恢复Enabled。进入try后离线置PrInitSuccess=true返回；在线重建视觉方案，逐一查PR，未找到只记日志继续，最后仍可能置true。见 [选择配方](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L804)、[重载](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L124)。
- ProductConfiguration/System1Program的初始化方法重新设置路径并清instance，不能等同于文件加载已经成功。外部Singleton实现停在DLL边界。供晶的本地SingletonJson.GetInstance有lock；Load先new T再读文件，无catch。如果读文件抛异常，当前GetInstance会传播异常，不能认为后面的null兜底必然执行。Save在lock内先写文件，再CopyFile，备份目录为Path.GetDirectoryName(FilePath)+"Baks"（字符串拼接，不是Path.Combine子目录），传入true及50；其外部函数契约仍待确认。见 [本地单例](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/DeviceParams/WaferSubDevicePara.cs#L59)。

## 数据保留与清理：本轮新增复核

两条清理链触发不同，不是一个统一定时器：

|链路|触发及实际范围|失败/完成语义|
|---|---|---|
|文件清理|PrepareMachineReadyToStart先同步CleanFile(FileSaveDue)，之后才重置信号和检查总复位|若清理抛异常，不会执行该方法剩余步骤；启动按钮外层catch调用Stop并提示。不是后台Task，亦不能保证生产已启动。见 [准备入口](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L185)、[按钮catch](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L68)|
|文件选择|遍历D:\ZX2200存储数据\的一级目录，再取其直接子项；以子项ToString解析yyyy-MM-dd，日期严格小于Now.AddDays(-day)才Directory.Delete(path,true)|不使用文件修改时间，也不递归搜索任意层次日期名；选中后删除是递归的。不解析的条目跳过。未先判断子项是目录；日期名普通文件可能使Directory.Delete抛错。见 [CleanFile](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Sustain.cs#L215)|
|清理异常|catch抛新的“定期删除图片失败”异常；等待窗仅在成功路径Close|未用finally关闭等待窗；已删目录不会回滚。日期阈值有时分秒，不能直接理解为保留完整day个自然日。见同一方法|
|数据库清理|首次访问Lazy DBService时建表，然后CleanInfo逐项调用八个删除方法|每个方法独立catch记录Info；单表失败通常不阻止后续方法。没有统一事务、删除结果汇总或本地重试。源码默认SqlSaveDue=180，运行值可来自配置。见 [配置默认值](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/MachineSoftwareConfiguration.cs#L51)|

所有表均按严格小于各方法当时计算的Now.AddDays(-SqlSaveDue)删除，影响行数保存在局部变量后不使用：

|表实体|保留比较字段|证据|
|---|---|---|
|AlarmLogEntity|StartTime|[323–341](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L323)|
|CapacityLogEntity|StartTime|[302–318](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L302)|
|DefectStatisticsEntity|DateTime|[281–297](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L281)|
|ProductTimeStatisticsEntity|StartTime|[260–276](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L260)|
|TemperatureCompensationEntity|DateTime|[239–255](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L239)|
|OperateLogEntity|DateTime|[218–234](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L218)|
|ParameterChangeLogEntity|DateTime|[197–213](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L197)|
|BondPositionLogEntity|DateTime|[176–192](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L176)|

**目录覆盖缺口：**PREntity自动存图使用D:\视觉定位成功图像\和D:\视觉定位失败图像\，不在上述CleanFile根目录下。不能宣称FileSaveDue控制了这两类图像的保留。GetMachineDatePath仅返回D:\ZX2200存储数据\{类别}\{日期}路径，本方法不创建目录；受力数据生产者调用此方法。其他清理机制是否存在仍需单独核实，不能由此断言现场必然无限增长。

## 本轮待补与验收边界

- 已补配置路径、配方重载外层、本地SingletonJson及八类表的清理条件；其他仓库Save与配方操作仍待逐项复核。
- JsonFormatHelper、SqlSugar及配方仓库的外部实现不能从调用名推断原子写入、锁、回滚或事务。
- 所有队列生产者的业务调用覆盖、外部调用及线程安全仍待验收；文字检索只用于定位，不能证明动态调用不存在。
- 需在受控测试环境验证断数据库、目录/磁盘失败、队列满及关闭期间未写完数据；本轮没有执行这些故障测试。
