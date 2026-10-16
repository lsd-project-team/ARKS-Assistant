# 原坐标计算、产品配置与异形缓存：启动及输送组合验证

1031项受控检查通过。三个原坐标文件直接编译，产品、异形配置与程式的生命周期方法接入既有实体树、两条UI入口、真实供晶Task和五阶段输送组合。统一回归与阅读器验证由独立回执登记；整体29组与13项要求仍未完成。

本轮保留先前1011项实体/服务断言，加入20项组合检查。420条提取记录对应419段唯一源码，包括237方法、143属性、16枚举、22字段、2结构体及23个信号契约；SingleConfig.ElementCoordinate在两个配置声明中复用。这些数字描述编译组合，不代表每个成员的所有分支均被覆盖，也不能与独立1355项载具或113/29项准备探针相加。

## 坐标计算与刷新失败

BaseCoordinateSystem、GeneralCoordinateSystem、ElementCoordinate三个文件未经修改参与Add-Type编译，原递归转换沿真实Unit/Substrate/Module/BondPosition父坐标运行。用独立预期值验证π/2旋转后的世界点(-11,35,62)、System1偏移后的(-10,37,65)和两系统累计偏移后的(-6,42,71)，同时验证往返转换、重复偏移守卫及父引用。更新焊点配置后原Refresh保留实体、重建坐标并清偏移标志，世界点为(-10,36,64)。没有上层坐标的机器根自身变换不参与原世界转换。

第三个坐标构造观察门失败时，Unit和Substrate已换成新坐标，Module及焊点保留旧父链，焊点世界点仍取旧链。观察门在原构造后、调用者赋值前触发；这证明该注入位置的部分提交，不证明SDK构造内部故障。通过继承入口直接向原Init传null，验证原方法先清Own/Upper样本，再空引用失败，旧Distance仍保留。原Init内部失败与适配器入口前的观察门故障分别记录。

## 产品、程式与异形配置缓存

原ProductConfiguration.IsTransportUnitReady在两条UI入口检查显式示教结果输入，false时不创建坐标、不启动模块/生产器或供晶Task，机器为Stop。这里的示教结果仍是适配器字段；原TransportUnitConfig.GetAssistantResult及普通/异形示教汇总尚未运行集成。

原产品Init/Clear重置映射到适配器的静态实例槽并更新配置路径，旧接收者的GetConfigByType仍读取当前全局配置；未知类型返回null。原TransportProgram.Init同样清实例槽并设置程式路径。后续对象创建是适配器的行为，原SDK单例文件加载、序列化和磁盘保存未执行。

原OppositeSex.Config/GetConfig按ConfigName查找，找不到时先向当前配置集合添加，再调用当前产品Save。两条UI入口分别验证保存失败：新配置仍留在内存，原域catch后输送生产器未启动，外层仍启动供晶Task。停止并重启同一配置后，即使Save适配器仍设置为失败，缓存命中绕过Save，实体树和生产器正常启动；累计Save调用仍为一次。这是未持久化内存缓存影响重试的源码行为，未据此认定设备生产可用。

## SDK契约和剩余边界

[点类型接口证据](transport-coordinate-product-sdk-evidence.json)使用Mono.Cecil仅读取仓库Infrastructure DLL的14个构造/运算方法IL，确认2D/3D默认坐标为零，显式构造参数及逐轴运算返回新对象。共享点适配器采用这些契约。既有连续链所需的(10,20,30)作为显式配置输入，旧1011专项的149个输入文件保持原哈希。原坐标源码运行不等于原点SDK、属性变更织入或部署DLL已执行。

VM校准/加载/保存、单例创建和文件加载、Save、弹窗、日志、硬件SDK、动作注入、配置与基础声明及示教汇总仍有适配器。原工程构建、部署配置/DLL核对、原生UI和设备验收继续待完成。此前14段生命周期接续均在本组合编译，历史接续文件仍保留其1011项上下文；下一步进入真实示教汇总及其配置/仓库依赖。

验证命令：`node scripts/test-transport-coordinate-product-integration.cjs`、`node scripts/build-transport-coordinate-product-integration-audit.cjs --check`、`node scripts/build-transport-coordinate-product-sdk.cjs --check`。
