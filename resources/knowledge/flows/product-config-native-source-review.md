# 原始产品配置与实际 SDK 原生数据验证

36 项独立断言通过；仓库 `libs` 与 `bin/Debug` 两份实际 SDK 在独立 Windows .NET Framework 进程中各运行一次，共 72 次断言执行。该数字不计作 72 种行为，也不加入已冻结的 1303 项组合。当前阅读器仍为 39 专题、3405 段专题快照，全部 29 个源码组仍为部分完成。

22 个完整原始文件不经改写，由现有 Roslyn 与显式 Framework 元数据引用编译：六个原仓库/基础模型/AOP/状态文件、ProductConfiguration、TuEnum、13 个配置文件和 ElementCoordinate。另插入此前核对的八个原检测示教成员及 JsonIgnore 属性。完整 ProductConfiguration 的七个初始化声明与正确命名空间的 EditStateEnum 已执行；这个枚举与 BaseDsSetting 的同名枚举保持不同类型身份。OppositeSexConfiguration 的 `new ()` 原样编译，未降级源码语法。

实际 SDK 的 Singleton、JSON helper 与 AKRSPoint3D 执行；原 ElementCoordinate、原配置初始化/就绪检查/ResetAssistantStates、原仓库加载与两条 OppositeSexConfig 检测汇总形成数据组合。原 ArrayConfig 的数量默认为 1，但坐标列表为空；OtherConfig 列表为空且矩阵为 null。原异形根为 300×300、Z=20、锁定且无子节点，原异形就绪检查拒绝它。原 TU 的 16 个示教状态中，TUPosition 为 UnAble，其余为 Forbidden；仅将 TUPosition 置为 Able 后，普通 TU 路径通过。

实际原生加载的关键结果：

- 省略 TUPosition 或无效的枚举字符串保留 UnAble，拒绝启动；TUAdjust 的无效枚举保留 Forbidden，在 TUPosition 合格时通过；未知数字枚举 99 也通过只拒绝 UnAble 的原汇总。
- 显式 null 替换 TUPosition 或整个 TransportUnitConfig 后，原就绪方法抛 NullReferenceException；省略顶层配置则保留原初始化对象并拒绝。
- 无效产品 EditState 枚举保留 NewCreate，不妨碍已保存的合格 TU。无效 `SafeHeight` 数字字符串的效果依 JSON 成员顺序而异：原保存顺序中的早期错误保留高度 5，却中断后续 TU 成员读取，TUPosition 留在 UnAble；把该成员移到 TU 对象末尾，已读取的 Able 保留，就绪检查通过。两种输入都是合法 JSON 的成员转换错误，不能统一描述成“仅跳过坏成员”。
- 原产品静态构造函数设置程式路径；仅改变路径依赖不重新运行静态构造函数。原 Init 同时更新文件路径和清除真实泛型单例缓存；Clear 仅清除缓存。缺失或 null 对象恢复原默认配置，缺失对象不创建 JSON 文件。实际 Save 创建带类型元数据的对象文件，并保留源 JsonIgnore；目录创建失败向外传播，已缓存对象保留。
- 原 OppositeSexConfig 两条检测 getter 经原仓库和实际 typed JSON 读取示教状态。无效背崩枚举保留 Forbidden 并通过；无效 PostBond 枚举保留 UnAble 并拒绝。

源码范围与测试/运行日志、编译产物哈希见 [测试清单](product-config-native-source-test.json)、[来源审计](product-config-native-source-audit.json) 和 [准备进度](product-config-native-source-progress.json)。初版对无效数字的预期被真实运行否定；最终断言依据分别运行的实际状态修正。

限制：这是显式 Framework 引用下的源码子集 DLL，尚非原工程构建。编译没有运行 Fody；原 AOP 的未使用事件警告保留。Path/Recipe、PR、UI 提示、参数日志/属性声明、SingleBondPositionConfig 类剩余成员、TuService 蛇形映射与物料实体依赖仍为适配器；两个未测试的适配器入口主动抛异常，不能用作已验证功能。剩余检测字段也是适配器。原两条 UI/实体/生产生命周期组合尚未迁移到本原生产品数据配置，部署、原生 UI、真实设备及全部 13 项要求仍待验收。

下一项：在保持 1303 项历史回归范围不变的前提下，迁移原产品初始化声明、正确枚举类型与实际默认配置到完整启动/实体组合，并继续原 SingleBondPositionConfig、Fody/AOP、真实外部依赖和部署验收。
