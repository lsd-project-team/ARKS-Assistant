# 统计与数据保存：生产事件到SQL Server

2026-09-28。SupportFeature首次限定复核，覆盖统计队列与直接数据库实现；其他支持功能、报表和所有数据源尚未覆盖。

## 自动链路

1. BondActionNode在SkipBond标签之后清物料标记、标记步骤完成，然后同步调用StatisticsBondPositionInfo。注释写异步，但此调用本身没有Task包装；不能声称生产不受统计阻塞。[338–357](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs#L338)。
2. StatisticsBondPositionInfo先递增bondUphCount和AllBondedNumber，再判焊点/组件null；null时已计数但不建日志。有效时构造BondPositionLogEntity并入队，之后更新周期；周期条件使用TimeSpan.Seconds分量，而赋值使用TotalMilliseconds，不能把它当作总时长小于10秒的检查。[165–213](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsDomain.cs#L165)。
3. 焊后检测LogDefect把偏差X/Y乘1000、角度及补偿等信息组成DefectStatisticsEntity；调用AddDefectResult先入队，再同步调用RePostBondInspection。后者默认更新按检测名称分组的内存列表，最新插到头部，超过2000删除索引2000；这不是数据库落盘回执。[551–587](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/AfterBondCheckActionNode.cs#L551)；[407–422](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsDomain.cs#L407)；[默认回调24–51](../../trunk/AKRS.ZX2200/SupportFeature/Compensate/DefectCompensate/DefectCompensate.cs#L24)。
4. SaveEntity操作日志按最后message字符串去重，未把操作员纳入去重键；入队成功后才更新lastMessage和LastOperaDateTime。队列为BlockingCollection<object>(500)，Add没有超时或取消参数，满队列可能阻塞生产者。这也影响前述同步生产调用。[53–92](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L53)。
5. 后台监控循环启动数据库存储线程；线程不存活时创建，消费者无限Take。只处理OperateLog、DefectStatistics、ParameterChangeLog、BondPositionLog，参数变更还检查SugarTable属性；其他对象被取出后未见保存或告警。消费者无本地catch、重试或退出排空协议。[97–139](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L97)；[后台693](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L693)。
6. DBService.Insert通过CopyNew客户端Insertable.ExecuteCommand；异常捕获后仅记日志，返回void。消费项已经Take，没有重入队，故写入失败不等于阻塞等待恢复，也没有成功回执。队列和内存计数不能作为完整落库证明。[84–97](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L84)。

## 存储与生命周期

DBService使用Lazy单例，连接本机SQL Server的ZX2200数据库、Windows信任连接、自动关闭连接。首次构造创建八类表后执行CleanInfo；这里只看到CodeFirst建表，不是数据库实例/数据库创建。表初始化异常也仅记日志。[27–78](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L27)；[144–171](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L144)。

清理由构造触发，CleanInfo调用八种记录清理，示例按Now.AddDays(-SqlSaveDue)删除旧焊点日志；不是注释所说固定180天，也未在该调用链发现独立周期清理调度。真实保留值、权限、建表/删除效果需验证。[161–193](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L161)。

条件查询失败记录日志并返回空List，不能从空结果区分无数据与查询故障。GetScalar先CopyNew再直接return null，后面的SQL执行不可达；因此客户端取得成功时GetMaxMTBA会返回0而非计算查询，若CopyNew先失败则可能抛异常。GetTotalAlarmSeconds自身直接return 0，后面查询不可达，不能把零值当真实设备指标。[104–139](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L104)；[369–375](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L369)；[142–185](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L142)。

## 缺口与验收边界

- 继续操作AOP、参数变更、报警直接写入、产能/运行时长数据和查询界面的完整调用链；不是所有记录都经过此队列。
- 检查队列满时生产/界面行为、数据库断连、消费者异常、软件退出未排空、重复事件和保存失败的运行影响。
- 继续缺陷回调订阅者、补偿/UI线程和共享列表并发；未把回调名字直接解释为完成物理补偿。
- SQL Server安装/数据库/权限、SqlSugar实际版本、数据表约束和真实运行尚未验证；本轮未连接数据库、未执行清理或修改生产代码。

## 日志生产与退出补充

已补报警直接写库、属性/UI日志过滤、状态先改后入队、退出配置保存与队列边界，详见[数据生命周期证据](data-lifecycle-source-review.md)。未确认所有AOP织入或全部退出入口。
