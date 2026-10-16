# 实体树、TuService与五子任务初始化：原启动及输送组合验证

1011项受控检查通过。原始实体/服务及初始化源码已在同一C#组合中运行；来源审计、统一回归及阅读器收尾分别登记，未完成部分继续保留。

本轮接回原始TuService的行列、八种工作顺序、坐标创建与状态屏蔽，普通和异形Substrate/Module/BondPosition构造、递归Refresh、BaseMatter类型及配置委派、OtherConfig.ClearInformation、TransportProgram.RefreshTransportUnit、TransportModule.Init和BaseSubSectionModule.BeltInit。五个模块字段保留原始声明与构造，通过显式类型别名接已组合模块。391条提取记录对应390段唯一源码，SingleConfig.ElementCoordinate在两种配置声明中复用。记录包括213方法、140属性、14枚举、22字段和2个结构体；23个原信号契约保留。

## 排列与配置

以独立的按坐标遍历模型检查七种矩阵形状、Normal/Snake、八个工作顺序和每个单元。源码RowAndColumn的Snake与Normal在正索引下给出相同行列；GetIndex右下向上的Snake也与Normal相同。左上向下的Snake依列总数奇偶改变初始方向，右下向左依行总数奇偶改变初始方向。测试记录原行为，未认定业务顺序正确。零列抛算术异常，未知工作顺序抛原错误，未知排列分别返回零行列或进入非Normal分支；越界没有统一守卫。

原构造流程生成6×6×2普通树，验证物理行列、WorkIndex、对应配置对象和父坐标引用。辅助坐标按原间距生成；数值变换由坐标适配器承接。普通CreateModule重复调用累加同索引Module；CreateBondPosition先清集合。非Multiple修改共享ModuleConfig及原坐标集合。异形构造按DownConfigs与名字创建子树，并取镜像和制程状态；Refresh保持实体身份而未重新取镜像。

## 状态屏蔽和递归异常

普通列表和LagerNumber矩阵均检查四种产品状态及基板/基岛编号。列表无匹配时保留旧状态；矩阵Find的元素为结构体，缺失时默认Enable而未抛异常。后续矩阵单元为空可留下先前屏蔽及当前编号；catch清配置、Save不回滚实体。ClearInformation或Save再次失败上抛。恢复成功后原Unit.Init仍调用两系统动作适配器。

坐标SDK构造失败在赋值前，Init失败在赋值后。29节点树的另一组15节点刷新在每个坐标构造/Init边界注入异常，验证新的坐标前缀、旧的后缀、实体身份，以及末尾视觉、测高和两系统偏移标志尚未清除。成功时坐标全部替换、树身份保留、标志清除，镜像仍保持原值。

原TransportProgram仅按点胶、Bond、等待顺序刷新三缓存；Loading与Unloading不访问，同一Unit别名会被刷新三次。第二个区段失败时第一段已完成、第二段部分写入、第三段未访问。

## 五子任务与实际启动链

原Task.Factory.StartNew启动五个实际Task，各先StopMove后BeltInit；在五个SDK停止观察门同时等待时，原WaitAll保持父任务未结束。释放门后每个子任务按原顺序完成；两个独立故障由AggregateException汇总，停止失败的子任务不进入归零。源BeltInit忽略GoHome返回值，包括Abort。

两条原UI路径验证初始化异常被原域catch处理后，外层仍启动真实供晶Task，输送生产器未启动，机器仍Working。原坐标构造/缓存Refresh异常也走此路径。正常搜索生成同一棵29节点树；原点胶1到2、点胶到Bond、Bond到等待、等待到出料、自动下料五阶段连续运行，三次递归Refresh共116次坐标创建，保留实体与父子身份，四次Save后移出载具。

## DLL接口与边界

[接口证据](transport-unit-services-sdk-evidence.json)用Mono.Cecil仅读取仓库Axis DLL及坐标工程obj/Debug DLL的元数据：GoHome返回ExcuteResult且HomePara默认null，坐标三参数构造与继承的Init(element, moduleEnum=0)，General枚举值1。构建缓存DLL不是部署版本证明。HomePara类型、SDK停止/归零/传感器、坐标变换、父配置/信息声明、OppositeSex.Config、产品/库/单例、动作注入、日志、弹窗与Save仍有适配器；实际SDK及原工程构建、部署配置/DLL、原生UI和设备验收未完成。1011项是本轮专项，先前1355项载具专项独立保留，二者不得相加当作新增覆盖。

验证命令：`node scripts/test-transport-unit-services-integration.cjs`、`node scripts/build-transport-unit-services-integration-audit.cjs --check`、`node scripts/build-transport-unit-services-sdk.cjs --check`。整体29组及13项要求仍未完成。
