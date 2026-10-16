# 原载具范围、搜索初始化与真实供晶启动

105项受控检查通过。原范围属性、配置替换、完整搜索初始化、两种地图初始化、九点初始化与供晶Start，已接入原位置生成、搜索、消费者和Stop。抽取63个原方法、19个属性、2个枚举与3个字段；生产源码未改。

## 配置切换与旧步距

Block的圆心、半径、形状与四条矩形边直接读取当前CarrierWithWaferConfig。有效半径为半径加偏移；圆心和边缘返回原对象引用，因此对象内部变更立即影响下一次范围判断。负半径在原圆形公式中仍按平方判定，NaN不通过，正无穷可覆盖本测试的有限点。未知形状枚举进入圆形与矩形的组合判断，圆形拒绝会短路矩形空引用访问。

非晶圆配置及null配置使用Circular与零半径、新建零点；原圆形范围只放行原点。真正的载具配置类构造、默认值、UI编辑和反序列化仍为未覆盖边界，本测试配置是显式输入。

SetCurrentCarrier仅替换配置引用，不重置isFirstSearch、不重新计算步距，也不保存。实验证明切换后范围立即变新，但后续搜索仍使用旧步距；收窄新范围可令旧步距耗尽，放宽后仍按旧步距前进。StartInit只将首搜标志置true，原StartInitSingle为空，不立即重算步距。下一次GetNextPosition首搜才使用新间距。

## 初始化顺序与残留

StartInit先写首搜、空计数和提前换片标志，再顺序执行晶圆图、华夫图、空单颗初始化和原九点初始化。独立的isNeedChangeCarrier、isNeedChangeCarrierMap不被此方法清除。

两种地图构造成功后先赋引用，再CreateForm／Show／Hide；构造失败与后续生命周期失败留下的引用不同。八个初始化故障点已验证后续截断，且前三个状态写入保留。重试仅检查地图引用是否null，因此会跳过此前CreateForm或Show／Hide失败的非null对象。

原九点初始化清行号、方向和各Exist，再调用原ResetNineDiesData。在本配置下，该方法重复读取G0共17次，按原行列间距计算九个位置。首个坐标读取失败时各存在标志已清，位置仍旧；间距缺失时中心位置可先写入，邻居位置仍旧。初始化过程中执行原Stop不取消后续位置读取。本方法未派发XY，也未保存单颗步距。

## 原Start与真实Task

原WaferSubSystemTask.Start已编译原文执行，业务委托运行原Dowork、原位置生成和搜索链；线程命名工具为记录替身。正常Start先完成初始化并清PreviousNeedChipName，再SetState(Working)、创建LongRunning Task。实际消费者收到真实信号后完成原取料许可并退出。

- 初始化失败被Start的catch提示；旧Task引用、PreviousNeedChipName和原状态保留，但已发生的初始化写入和地图引用保留。提示本身抛异常会向外传播。
- 失败后再Start会跳过留存的失败地图生命周期，并能启动实际消费者；这不证明留存地图已正确创建。
- 旧Task处于Running时保留该任务，跳过初始化及PreviousNeedChipName清空；仍写Working。已用真实等待中的消费者Task验证。
- 初始化读取中执行完整原Stop后，Start仍写Working并创建工作Task。测试随后再执行原Stop，已确认该真实工作线程退出且未发许可。
- 两个真实调用Task在同步UI分派入口设Barrier，强制两次原Start都越过旧Task判断。地图回调在替身中串行执行，地图仅创建一次，但仍创建两个不同Task ID的实际消费者工作线程，对象字段只保留其中一个。执行原Stop并逐一Join两个工作线程后，两者均退出且未发取料许可。

该并发实验包含真实Task、真实事件、原初始化／消费者／Stop，不证明生产UI、定时器或完整Machine.Start能够形成该交错，也不证明设备安全停止。两次调用同时越过判断的时间窗口由受控Barrier提供。

## UI与外部边界

当前MainForm构造注册SendUiAction到PostAction，PostAction调用Invoke；三段原文为单独静态证据，不计作本测试执行方法。正常测试用同步串行回调替身，不运行WinForms窗口。另一个显式延迟回调替身验证“委托延迟时原初始化先结束”的依赖行为；它不代表当前MainForm使用异步UI分派。真实窗口构造、句柄、Invoke包装异常、重复订阅、关闭后复用和资源释放仍未验收。

## 复现与后续

`node scripts/test-wafer-range-init.cjs`执行105项检查；`node scripts/build-wafer-range-init-audit.cjs --check`校验41个测试来源、87段原代码及三个原信号声明，并绑定专题原文和报告哈希。线程均有等待上限与收尾Join。

载具配置类、地图控件、UI分派、坐标运算、标定、视觉、驱动/I-O、等待与保存依赖仍有替身。下一步向上接完整Machine.Start、TransportDomain.StartTask及模式切换调用者，验证供晶初始化失败和Stop交错如何影响其他任务；继续实际配置/DLL、原项目构建、原生UI与设备验收。29组模块仍部分复核。
