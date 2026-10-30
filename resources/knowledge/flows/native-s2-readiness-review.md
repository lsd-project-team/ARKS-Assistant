# 原 S2 就绪门槛与吸嘴多重状态核验

两轮各56项通过，共112项。运行未改动的16个原资源程序集及仓库实际SDK，每轮16个来源路径均匹配；213个源码声明、112个文件按原编码及UTF16偏移绑定，69个IL方法来自原主程序集和LanguageExt.Core。十二项新旧绑定核验全部通过。新增111个冻结输入，348个父输入复用，10344+111=10455。整体目标未完成。

## 实际观察

- 完整原System2Domain.CheckIsReady在OffLineWork、空硬件/空载具计划、关闭ToolBank/物理工具检测的公开配置下实测。关闭自检先经过原OpenBondHeadVaccum的离线返回，然后跳过缺失吸嘴架和空步骤；开启自检时缺失吸嘴架传播NullReferenceException。
- 原空吸嘴架真实构造、Add和查找；EditState.NewCreate使CanWorkProperly为false，但NozzleShelfProgram.SelfCheck及BondProgram.SelfCheck为true。
- 13行双门矩阵：控制器先FindAll(IsEnable)，流程总检查遍历全部步骤。仅禁用步骤时控制器false/流程true；禁用非法步骤加启用有效步骤时控制器true/流程false。名称为空、序号0、功能0或多功能均只被流程层拒绝。异形模式下空字符串/缺失焊点通过两门，null焊点只被流程层拒绝。缺失检测名通过两門。
- 12个实际拒绝及恢复门：ULM三坐标、焊头三坐标及标定派生相机偏移、Lvdt=0、吹气比例=0、启用未示教ToolBank、温漂点/取片偏移点为空。公开恢复每次使原S2再次就绪。空ToolBank参数在禁用时被接受；启用分支在空坐标检查处返回，未进入传感器访问。
- 注册的未示教、未编辑、mode999检测配置使PostBondProgram.CanWorkProperly为false，但完整离线S2就绪true；禁用且外配方仍true。原S2和BondProgram的IL均不调用检测就绪门。
- 两个真实槽位均OnBondHead时，SelfCheck和完整离线S2仍true，且无UI分派。原IL调用ListExtensions.Find返回LanguageExt.Option，再调用Option.Count，SDK实际Count只返回0或1；与>1比较无法拒绝多槽位。相同数据下GetToolOnBondhead使用LINQ Where/Count并实际抛出Exception。这是原SDK符号绑定造成的检查缺口。
- 每轮26次原消息分派经过公开MainForm.SendUiAction计数回调，回调不执行Action，未打开实际UI；另一次ApplicationException分派故障由原S2直接传播。

## 运行与边界

生产Task本轮零个，动作DoWork零次。完整S2就绪方法已执行，整机Machine.Start、回零Hardware SelfCheck、真实传感器/轴/相机、载具力控检查、MaterialOnBondhead处理、VM/视觉、SQL、实际UI、Retry、MSBuild/LC/Fody/部署仍待验收。原C#和csproj未修改，不将离线公开夹具下true作为真实生产完成。

候选v1编译CS0103失败，未启动原生进程；候选v2通过51项后，错误预期“多工具会被拒绝”失败，保存实际失败输出及完整候选，依据SDK IL修正验证预期。独立静态验证草稿因预期不存在的get_IO失败，保留草稿后改为实际get_PickerHolderSensor1。十二项阶段核验实际初始chunk be797f/session7624，终态write_stdin 0b9b2d/exit0；冻结观察误写同步receipt，audit明确纠正并保留原始记录。

下一步继续真实公开载具计划的BondProgram力控/延时/视觉点位门及整启动准备链；匹配PR复制与VM依赖、完整S2任务/业务与29组验收仍待补证。
