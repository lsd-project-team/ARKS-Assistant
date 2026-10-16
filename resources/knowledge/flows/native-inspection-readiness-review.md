# 原检测配置持久化、重载选择与就绪检查

两轮独立Framework CLR各108项检查通过，标签、顺序和结果一致。每轮原检测仓库Add十二次、Save两次、Load三次、Remove两次，十二个真实配置经原JSON重载成新对象；另原PR JSON往返一项。十二行就绪矩阵和三次重载后完整原胶检DoWork证实：原S1与流程就绪检查不拦截这些检测配置，未示教的模式1/999及禁用且不属于当前配方的模式1均仍被选择，提交步骤并返回Success，没有实际检测。16工程、29组、1436文件、13项整体目标未完成。

## 原Add/Save/Load与PR边界

原PostBondInspection(name)构造十二个配置：模式0/1/999×PostBond未示教/完成×EditState NewCreate/Completely。配置加入实际RecipeID，胶量数量0.5，背崩默认ForBidden，运行计数设7。实际调用原PostBondInspectionRepository.Add；CopyName明确为不存在的来源名，真实PR仓库仅有一个无关原PREntity，故没有匹配复制来源，不执行CopyPREntity/VM。原Add仍真实Save整个PR仓库，再把配置加入列表；这不是只改公开列表的替代Add。

随后原Save写实际带$type/$values的十二项配置JSON，原Load替换列表，全部新配置与原对象引用不同。模式、编辑状态、示教状态、数量、RecipeID保留；JsonIgnore的CurrentDefectNumber由7变0。原配置路径与PR路径均由实际宿主Application.StartupPath自然落在独立目录，没有路径替换或私有单例写入。两轮保存前配置/PR文件均留快照。

用与原VisionEntityRepository.GetInstance相同的实际SDK ReadGenericObject反序列化PR文件，取得新原PREntity及同一具体Xld算法类型；没有替换运行中的PR单例，也没有初始化VM procedure或图像。原Add的匹配复制来源分支仍未验收：其原代码会复制PR文件、Clone并InitVmProcedure。原Remove两次的四个衍生PR名称均不存在，只走原DeletePREntity缺失早返回，保留无关PR；没有声称真实PR复制/删除整个生命周期完成。

原Remove不保存检测仓库。第一次Remove后原Load重新恢复该项和十二项列表；第二次Remove后明确原Save/Load，才持久化为十一项。未执行UI管理器外层保存，不据这些直接调用推断界面一定丢失删除。

## 就绪矩阵与原方法范围

实际配置IsAssistantSucceed只遍历PostBond和BacksideCrackDetection，遇null或UnAble拒绝；模式/编辑状态/真实PR示教不在此方法检查。十二行矩阵的结果因此只随PostBond的公开State变化。额外原非法示教枚举999被接受，null示教对象被拒绝。

原OppositeSexConfig开启EpoxyCheck/AfterBond时按名称Find检测配置，再返回其IsAssistantSucceed；关闭检查即使名称缺失也返回true，开启且缺失则false。使用真正原类型，文件名OppositeConfig与类名不同；宿主别名没有重建原类型。

原BondProgram.PostBondProgram.CanWorkProperly只按实际Find出的检测项EditState==Completely判断，未示教和非法模式在编辑完成时仍返回true；有示教但编辑NewCreate时false。它没有调用检测模式或IsAssistantSucceed。这个就绪检查与S1节点是否实际检测是不同层次。

原System1Domain.CheckIsReady在IsSystem1Configrated=true时，只核对真实仓库点胶头、预点胶及胶水。本轮点胶头各公开示教状态明确设Able、预点胶Off、胶水原对象存在，使这些前提成立；是公开数据夹具，不代表物理标定完成。十二个重载检测配置均不影响此原方法返回true。

原ProcessDomain.CheckIsReady只遍历S2SystemProcess，S2计划为空时十二行均true。额外S1步骤名空、Index=0、焊点与检测名缺失，也被此门接受。这里证明指定原门的检查缺口，不证明完整Machine.Start会通过其他Wafer/S2/产品/轴/视觉/磁盘等门。完整Machine.CheckOperatingEnvironment与PrepareMachineReadyToStart仅静态绑定，未运行；设备回零SelfCheck包含真实回零、灯光、运动与UI，本轮未执行。

## 重载后的真实选择与模式缺口

每个配置进入普通公开原载具的一条步骤，四层视觉/测高/身份完成标志是明确夹具；原Init/GetNext创建消息并选择真实注册S1DispenseDefectActionNode，CurrentPostBondInspection与原Load出来的实际对象同引用。十二项IsDoWork均true，因为该方法检查焊点状态和步骤字典，未校验检测配置的示教、EditState或模式。

对未示教/未编辑完成的模式1和999实际调用完整原DoWork两次。原节点在OffLineWork先提交步骤，switch未实现这些模式，正常公开刷新计数后返回Success；当前消息仍未完成，实际检测未发生。模式0视觉路径没有运行。

再把重载的模式1配置公开IsEnable=false、RecipeIDList清空。原GetDataSourceByCurrentRecipe和Filter把它排除，但全局Find仍返回它；原S1消息选择、两个就绪门及IsDoWork仍接受。第三次完整原DoWork仍提交并Success。这个外配方/禁用项实验是公开数据变更，未执行UI禁用管理器；不能以UI列表过滤认定运行查找也过滤。

## 查找清理导致的临时就绪

原PostBondProgram.Find逐项处理公开名称列表，找不到时RemoveAt(i)，随后for仍i++，会跳过刚移到i位置的下一项。公开列表[missing-a, missing-b,真实NewCreate配置]连续调用CanWorkProperly三次：第一次删除missing-a但仍取得真实未就绪配置，false；第二次删除missing-b却跳过真实配置，返回空结果使就绪true；第三次取得剩余真实配置，false。原查询同时修改列表，false/true/false为实际稳定重放结果，未声称全启动在该瞬间必然通过。

## 来源、失败记录与后续

191个完整原声明、98个严格原文件，符号/UTF16偏移/文本/字节SHA一致。三个实际原程序集94个完整静态IL方法绑定泛型仓库、检测Add/Remove/示教、PR保存/复制/删除、S1/流程/焊后/异形就绪、消息选择及前序节点/Task方法。94是静态方法数，不是本轮执行方法数；生产Task本轮零个，原Machine.Start/硬件SelfCheck未运行。

宿主162引用编译通过后运行，两轮各绑定16个保真资源原程序集，32个文件SHA核验。初宿主混用两个EditStateEnum及误用文件名类，真实编译exit1，后续runner也在编译门拒绝，未启动原生进程；完整候选保留。使用真实基类编辑枚举/实际OppositeSexConfig别名修正宿主。独立IL检查器曾有多余括号语法错误，草稿保留，修正单个符号后通过；原生结果与生产源码未改。

十一项新原生/来源/IL及前序胶检、停止恢复、步骤、Task、条件、配方、动作、算法、阅读器和虚分派冻结核验通过。94新增输入，332旧输入复用不增数，10250+94=10344；原1328与全部历史报告、阅读器保持。完整业务仍未完成。

下一步继续原S2动作控制器/BondProgram的实际就绪与检测依赖、完整启动的各门及复制PR/VM前提，然后推进真实检测/Retry、SQL/UI/设备和原工程MSBuild/LC/Fody/部署。整体目标未完成。

只读复验：node --max-old-space-size=4096 scripts/verify-native-inspection-readiness.cjs；node scripts/verify-native-inspection-readiness-bindings.cjs。冻结运行目录禁止覆盖，新实验另建目录。
