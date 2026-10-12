# 原焊点与检测自身汇总：完整启动、实体树与输送组合验证

1209项受控检查通过。原SingleBondPositionConfig五状态、BondPositionConfig准备汇总和PostBondInspection两状态的构造、重置及只读汇总，已经接入原UI、产品准备、实体树、原坐标、生产器、真实供晶Task/Stop及五阶段输送。统一回归与阅读器结果由独立回执登记；全部16工程、29组、1436个C#文件及13项要求仍未完成。

此前1144项断言全部重新执行，名称、顺序及判断条件保留，再在同一Run执行20项两条UI和45项原汇总检查。新增组合的Setup和Grid为健康场景显式设置原焊点状态Able；原构造与Reset未改。旧检测true/false输入迁移到PostBond.State，原IsAssistantSucceed只读汇总参与执行。历史独立45/20项准备不是额外覆盖，不与1209相加。469条提取记录对应468段唯一源码，含251方法、177属性、17枚举、22字段、2结构体及23信号契约；旧171个正式输入和176个准备输入保持原哈希。

## 原焊点默认值、空集合与异常

原单焊点构造和Reset创建五个新的状态对象：前三项UnAble，后两项ForBidden。GetAssistantStates每次新建列表，成员仍为共享状态对象。每个UnAble或null状态使原汇总返回false；ForBidden和未知枚举值通过。Reset替换所有五个状态对象并保留名称。这些是源码行为，尚不构成示教业务需求验收。

原BondPositionConfig.IsBpAssistanceFinish逐项检查并对首个未教配置显示包含名称的原提示。空列表返回true且无提示；null列表或已教项后的null元素抛异常；较早未教项可返回false并掩盖后续null。对话框适配器抛异常时，原包装器将其传播，而非转换为false。

两条原UI分别证实未教、null状态、null列表/元素与早期未教后null阻断模块、生产器和供晶，机器为Stop且尚未进入TransportDomain.catch。空列表通过原准备并创建实际零焊点树，生产器及供晶启动。健康Setup/Grid的显式已教输入不代替默认未教负例。

## 原检测状态及启用标志

原PostBondInspection构造和Reset使PostBond为UnAble、BacksideCrackDetection为ForBidden，启用标志默认false。原汇总对每个UnAble/null返回false，对ForBidden/未知枚举值返回true；状态列表每次新建，Reset替换两个状态对象并保留启用标志。

PostBond已教且backside保持ForBidden时通过。IsDetectBacksideCrack=true不会自动重置状态，false也不会绕过显式backside.UnAble。两条UI验证默认检测、禁用backside但显式UnAble、仓库读取异常均在准备阶段阻断；启用backside且仍ForBidden时，异形一焊点树与真实任务启动。原可选检测查找和异形递归直接读取这些原汇总，结果布尔字段适配器已经移除。

## 完整旧回归与边界

旧1144项实体、世界坐标和偏移数值、产品/异形缓存、16状态、递归示教、可选查找短路、Save早期异常及缓存重试、原五Task/WaitAll、两条UI的29节点树、五阶段输送、三次Refresh、异常前缀和Stop/Pause检查全部重新执行。所有新增检查在原RunCore内执行，资源只在完整Run的finally中清理。

源码方法、属性、状态默认值原文提取。配置基础声明、真实检测仓库/JSON、产品单例创建加载/Save、VM、弹窗、动作、日志和SDK仍有适配器。下一步接入原检测仓库及BaseSettingRepository的加载、查找、过滤、保存与PR联动；产品完整声明、真实单例、VM/动作/SDK、原工程构建、部署配置/DLL、原生UI和设备继续待验证。所有29组继续部分复核。

验证命令：`node scripts/test-transport-inspection-readiness-integration.cjs`、`node scripts/build-transport-inspection-readiness-integration-audit.cjs --check`。整体目标继续进行中。
