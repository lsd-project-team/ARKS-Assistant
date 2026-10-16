# 原始机器停止、急停与日志队列核验

70项原生CLR4.0.30319.42000检查通过，宿主EXE、完整运行结果、55个选定原方法IL及固定数据仓库JSON独立重放一致。新增42份冻结绑定父3376份，共3418份；原Main1137源码/资源产物与16个源码/资源程序集实际加载位置、SHA一致。生产C#、机器/任务类型、SDK单例、队列、路径和构造器未替换。整体16工程/29组/1436文件/13项仍未完成。

## 退出异常确实来自原始任务

[Machine.EmergencyStop](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L383)按空轴列表Parallel.ForEach→Machine.Stop→S1 Abort→S2 Abort→Wafer Abort执行。本轮轴列表是实际SDK空仓库返回的空List，原循环体Axis.StopMove没有执行。源代码与IL均无保护整个急停链的catch/finally。

- S1 Task尚不存在时，原急停完成Stop清理后在[S1 AbortThread](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L210)空引用。实际异常栈包含S1 Abort和Machine.EmergencyStop；由后续无catch的顺序IL可判断S2/晶圆Abort无法继续到达，不用其空方法“没有副作用”作为跳过证据。
- 为验证运行中Dispose，不启动Pause/Working业务循环，而在Stop下用原Start运行包含100000条真实SingleProcessStep的原Init。任务由完整原Start创建，Running来自原排程初始化，没有人工Task字段赋值、替身Task或私有状态写入。原急停的Stop清理已完成，S1 Dispose抛InvalidOperationException；原任务随后自行完成Init、在原Stop门控退出并达到RanToCompletion。排程条数由1×1载具结构下目录四层节点数量+100000单步骤动作独立核对；大数据仅用于提供可观察运行窗口，不是生产性能估计。
- 对已完成、已Faulted的原S1 Task调用急停，Dispose允许返回；原S2 AbortThread和[Wafer AbortWaferSubThread](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1431)均为空方法。急停不恢复此前Faulted，也不清除Task引用。

实际Framework64 mscorlib路径与宿主typeof(Task).Assembly.Location一致，Task.Dispose(bool)原IL先检查IsCompleted、未完成时抛InvalidOperationException，没有Cancel调用。这与原任务上的实际异常相符；未把Task.Dispose误写为线程取消。本轮2个原业务Task：1完成、1因原ProcessSteps=null/Init getter失败而Faulted。前一阶段100仅验证无任务/已完成Abort，本阶段补到真实运行中Init场景；业务动作执行中/Pause等待中的急停仍未验证。

## “已关闭”判断会受配置和Task状态影响

[Machine.IsAllowTaskClosed](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs#L201)重建WorkTasks字段，S1配置true采16槽，false采15槽；首次各槽null时返回true。实际S1 Init任务Running且配置true时返回false；在这个真实任务仍Running的观察窗口把配置改为false，原方法漏掉它并返回true；恢复配置true再次返回false。这里是明确的配置切换/直接原任务启动测试，不推断常规Machine.Start在关闭S1配置时还会启动它。

实际Completed与Faulted任务都会被接受为closed，字段引用仍在。方法只检查TaskStatus.Running；Created/WaitingToRun/WaitingForActivation的接受边界属于源码判断，本轮没有赋入人为Task来制造这些状态，也没有把Faulted等同业务成功。原Machine.Start的只读IL另外确认：S2 ActionNodesService.Init在BondTask.Start之前，补足此前“BondTask.DoWork没有Init”与正常生产调用方的区别；完整Machine.Start和Ready/设备步骤本轮未执行。

## 状态先变，日志拥塞会挡住后续停止清理

[Machine.SetState](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.StateRelated.cs#L52)状态不同才创建真实ParameterChangeLogEntity，先写MachineState，再加入[StatisticsService原BlockingCollection](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L53)。原集合容量500。静态初始化只建集合，原数据库保存Thread始终null；没有启动保存线程、替换队列或连接数据库。

1. Pause/Continue/Stop实际改变原状态并各队入一条日志；重复同态Pause不入队。Continue在未配置安全门时只改Working，S1/S2首次点胶标记仍false，不创建业务Task。启用安全门而原仓库无门控Sensor时，原Continue在GetInputValue空引用，状态保持Pause、没有日志；本轮没有实际门控读取。
2. 实际原队列用500个原ParameterChangeLogEntity填满后，在独立测试线程调用完整Machine.Stop：State已是Stop，线程在100ms观察窗口内不返回，SingleStep/需片信号/两个焊后计数仍未清理。用原TryTake释放一个槽后，Stop返回并完成清理；新状态日志排在剩下499项之后。此处证明背压可延迟清理且能释放，不声称永久死锁或生产队列当前已满。
3. 同样队列满，但机器原状态已经Stop时，SetState不Add，完整Stop立即走后续清理，500项数据保持。这说明是否阻塞取决于状态是否变化。
4. 最后用真实原队列CompleteAdding制造封闭生产者故障。Stop及EmergencyStop均在State已变Stop后因Add抛InvalidOperationException，清理尚未发生。再以相同Stop状态急停，绕过Add并完成清理；队列仍封闭、原任务仍Faulted。原源码检索未发现该队列的CompleteAdding生产调用，故这是明确的隔离故障输入，不是现场事件证据。

数据库消费者是否被正常启动、其SQL错误/吞吐与生产满队列的条件仍待核验；这里只验证原集合及机器调用次序。实际日志DateTime.Now未序列化到对比结果中，运行输出记录三条真实状态消息；被保存仓库模型CreateTime用显式固定普通公开数据，JSON字节重放一致。

## Stop设备分支和部分副作用

[Machine.Stop](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L347)依次设置状态、清空原报警注册表、设置报警停止态、退出SingleStep、重置Bond需片、按Online配置关闭上游要料、关闭顶针气路、焊后计数归零。原报警注册表为空，未创建/注册控件；报警方法在OffLineWork返回。完整WaferSubModule真实构造4个模组，Eject的轴/电气引用来自实际空仓库为null；原CloseEjectionTableVacuum在实参读取后进入原ResetCyc的OffLineWork门控，成功返回，没有电气动作。

LoadConfiguration=Online时，上游SetLoadingTableNeedTabletSignal没有OffLineWork门控，null Electric调用失败；State、SingleStep与需片重置已经提交，后面的两个焊后计数仍为11/12。改回Belt、在已Stop状态再调用原Stop即可完成计数清理。这个输入组合证明离线模式并非每个设备模块方法的统一门控，没有向原硬件仓库写入替身或实际输出电气信号。

## 冻结证据与核验修正

65项先通过，追加5项配置/故障/同态重试检查成为70，原65名称顺序保留为子序列。两个早期只读检查失败保存：PS5 JSON数组额外嵌套被原Emergency存在性守卫拒绝；OrderedDictionary按属性分组误报重复，改用显式键，最终55个签名唯一。早期58记录把mscorlib重复捕获，最终使用一次实际Framework64路径。一次诊断命令引号错误导致未生成临时脚本，未执行任何新宿主或改生产代码。

初次完整冻结/重放流水线6032a7最终exit1，原因是冻结核验脚本误期望Stop无任何handler；实际foreach编译为只释放枚举器的Finally，try132-163/handler163-178。前面的SetState/日志/信号步骤不在这个范围，Stop没有catch处理其退出链。另一个无赋值字符串守卫把DispenseTask==null误判成赋值。原失败脚本继续冻结，另建[accepted核验脚本](../../scripts/verify-native-machine-stop-accepted.cjs)精确修正这两条检查，原70运行表达式、宿主、IL和EXE不变。保留首次35项登记文件，再追加7项新冻结记录为42；先前35条绑定没有修改。67645终端实际exit0接受完整重放和父100递归核验，不把先前失败流水线改写为成功。

见[测试](native-machine-stop-test.json)、[审计](native-machine-stop-audit.json)、[进度](native-machine-stop-progress.json)。本70与100/180/251/58、正式1328、受控278/目录119和98/124各自独立，不相加认定整体覆盖。LC5/Fody2/VM5失败、388资源1498条与40专题3817快照不变。接下来继续实际数据库保存线程/停止调用方、生产配方重建入口、其他等待/异常传播、在线节点下层算法、就绪负分支、PR/校准/测量、IO及完整构建/部署/UI/设备。
