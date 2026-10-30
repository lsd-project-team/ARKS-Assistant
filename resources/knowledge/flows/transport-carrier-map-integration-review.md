# 启动载具检查、物料记忆、真空与计时日志：完整生产器组合验证

1355项专项检查通过，含191个完整原方法、122个属性、11个枚举、17个字段和23条信号初始化契约，共341段原代码。140个文件有显式依赖绑定，另29个源码文件按片段绑定，共169个唯一文件。来源审计绑定全部来源与本专题242段原代码快照；统一回归和四宽度阅读器验证通过，见[集成验证回执](transport-carrier-map-integration-verification.json)。

原生产C#源码未修改。原Task.Run、Task.Wait、Stopwatch、忙循环和Thread.Sleep保持原实现；SDK、硬件与参数仓库、服务、坐标/子实体、对话框、日志接收端、Save与域/程式生命周期保留明确替身。以下结论仅限受控组合，原项目构建、部署配置/DLL、原生UI和设备待验收。

## 启动检查与物料记忆

载具检查先读下料入口，再读点胶入口；六种配置验证报警条件、SecondLevel、输入采样参数、Retry回到下料读入、Abort以及其他返回值的fallthrough。方法没有Stop/Pause守卫或本地catch。

两系统验证反向搜索、自动工作、缓存载具、搜索结果和Yes/No选择的组合。关闭反搜且自动工作且缓存不为空，MapBelt提前返回，不修正先前状态或点胶1标志。搜索找到已缓存载具，先HasMaterial后原Refresh；Refresh异常留下已有载具和HasMaterial。新载具在构造完成后才赋值；构造异常保留先前状态。两种映射均不Save。

点胶搜索未发现已缓存载具而选择Yes时，原点胶1标志为false且配置Divide才减DistanceToRight；没有Refresh。正常完成后标志变true，早返或异常可保留原标志。警告返回未列明选择时，原switch可保留先前记忆与状态。用例以显式先前状态和对象引用验证写入顺序。

MapMaterial按Bond、可选System1、可选入料前端的顺序执行；仅Online和OnlineWithAutoLoader更新入料状态。五个区段的IsExistTu覆盖32种缓存组合。原搜索的13种受控SDK返回码均被void运动包装忽略；同步前进速度按80×0.375=30记录，停止参数为false/true。卡料Retry重新搜索，Ignore返回false，其他选择fallthrough。

## 真空与实际时间

Middle打开中、检查中；MiddleAndFront打开中/前、检查中/右；MaxRight打开中/右、检查中/前；All打开并检查三通道。未知尺寸不打开输出但检查三通道。五种尺寸、八种输入值和八种缺失输入组合验证短路和空输入视为成功。关闭真空受IsManuallyReleaseVacuum控制，缺失输出可忽略。

OpenVacuumAndCheck采用原Stopwatch和无延时循环，-1/0/25/1000ms分别验证；到时返回false，不关闭真空。仅观察层将真空读入/仓库追踪限制为前16条，另计每次调用，fault和hook仍逐次执行。Stop/Pause及第20次读入恢复true证明业务循环未被观察限制截断。

无输送配置时，Bond.SearchBelt忽略OpenVacuumAndCheck的false并返回true，输出异常则catch为false；Bond.MapBelt使用实际bool结果且不捕获异常。缓存成功时不Refresh。无缓存且真空失败，No清记忆并关闭真空，Retry重新打开与检测；其他返回值可保留先前状态。

## 日志与实际入口/连续输送

原RecordTime输出当前本地时间、原始item/sub字符串和真实elapsed毫秒，再Restart当前属性返回的Stopwatch。初始未启动计时器输出0并启动；日志接收端异常时不Restart；null计时器在日志调用前抛错。接收端更换计时器时，原后续getter启动新实例。仓库日志DLL元数据核对四参数void Post、Transport=7、InFileAndUI=3；Level仍是适配器，日志DLL未执行。

两条原UI路径验证载具Abort以及载具、Bond、点胶、入料前端读入异常。TransportDomain内部早返或catch阻止输送生产器创建，外层Machine.Start仍启动真实供晶Task并使机器Working。直接搜索Task在轴状态SDK观察门处改变Stop/Pause，释放响应后原映射仍构造载具并提交HasMaterial；没有Save。

两条UI路径的启动搜索实际创建System1载具，初始坐标X=11、偏移标志true，无Save。该同一对象随后经过点胶1→2、点胶→Bond、Bond→等待、等待→出料皮带、出料皮带→收板机五个原父Task。构造一次、坐标创建四次、Refresh三次、Save四次；最终移出，X=10、预点胶标志保留、偏移标志清除。坐标、Save、动作服务和SDK效果仍限于替身。

## 搜索配置与嵌套异常

System1与Transport两个配置开关、找到/未找到分别验证点胶搜索。关闭配置可跳过解夹与挡料下降；仍发异步反向指令，找到后两挡料升起也无配置守卫。夹紧只受System1控制，因此无Transport而有System1仍可夹紧。直接Search不提交Unit或Save。另以正常NoMaterial状态和缓存不为空验证三种早返模式保留不一致记忆；先前的哨兵状态只用于辨别是否发生写入。

两系统的13个受控SDK返回码逐一记录先异步距离-7/速度20、后同步距离19/速度30；Bond还停止点胶轴，停止参数false/true。空皮带设置先经过UnClamp提示，再在搜索读参数时NullReferenceException，没有轴指令或记忆提交。

两条UI中，原输送域catch日志或错误弹窗再次抛错，异常进入原UI catch，调用完整Machine.Stop，显示启动失败，并在finally恢复UI Enabled。供晶与输送Task未创建，机器Stop。该结果与域正常catch之后外层仍启动供晶、机器Working分开记录。实际启动搜索警告或构造边界抛错而域catch正常时，仍可启动真实供晶，但无输送Task、载具或Save。

## 当前范围与后续

专项命令：`node scripts/test-transport-carrier-map-integration.cjs`；来源审计：`node scripts/build-transport-carrier-map-integration-audit.cjs --check`；日志契约：`node scripts/build-transport-carrier-map-log-sdk.cjs --check`。本增量的专项、审计和专题登记独立于此前料仓288项回归；当前统一回归与阅读器收尾由新的验证回执登记。

226项历史基线和1178项中间检查已保存脚本快照；失败日志保留，未计入通过。夹具修正包括原点胶1标志默认true的测试初态、补充反馈时清除之前false轴响应、原停止参数false/true及拒绝新载具时不发生构造的断言，业务源码不变。

后续按[19段服务/实体/生命周期接续源码](transport-unit-services-next-evidence.json)继续原TuService/子实体/动作服务/产品/程式/池/域/SDK生命周期、原构建和配置/DLL、原生UI与设备验收。29源码组和13目标仍保留未完成状态。
