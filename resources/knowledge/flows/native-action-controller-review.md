# 完整原动作目录、域与控制器的原生验证

251项原生CLR4.0.30319.42000检查通过；重编译测试EXE和全部JSON结果逐字一致。完整Main1137份原Compile源码/资源产物与16个原源码资源程序集绑定真实物理位置。37个原始具体节点类型、S1/S2两个完整域通过实际SDK SingletonNoSave构造。没有编译节点替身，也没有改写原源码、路径字段、SDK单例或业务类型。

## 本次补齐的边界

此前目录119项用了具体节点构造替身。本次只迁移首条程序集身份断言及其名称，另外118条表达式/名称/顺序保持；同样119条目录检查现在执行37个原始节点的完整构造器。构造并不代表执行节点DoWork。域本身的任务、硬件模块控制器和动作控制器均由原构造器创建，任务尚未启动。

只读IL先检查Main内127个精确签名方法及两个SDK的相关路径：SingletonNoSave使用Activator.CreateInstance，硬件仓库静态构造会ReadHardwares，缺少Hardware.json时返回空集合。原PathConfig使用宿主Application.StartupPath；运行前断言Hardware.json和AntiCollisionSystem.json均在宿主目录下且不存在，再通过公开HardwareRepositoryService.Hardwares初始化实际仓库。测试前后集合均为空、两个配置文件未创建，未执行硬件连接、初始化、轴、相机或设备动作。IL检查只展开记录的精确内部签名，未声称覆盖全部外部调用/动态分派/委托。

两个完整动作控制器各执行公开Init的4种WorkProcess×2种WorkProcessModule，共16份原排程，每份53条消息：2基板×2基岛×2启用检测步骤，禁用步骤排除。独立预期核对步骤/位置遍历顺序及BondPositionFirst/PositionFirst的逐焊点前置动作交错；重复Init保持集合对象及内容、不追加。此处不执行具体动作。完整S2自检验证普通有效焊点、禁用步骤忽略、异形配置跳过焊点校验和null列表在弹窗前异常，未执行会弹窗的负分支。

普通TransportUnit的有参原构造器建立真实实体/坐标树并调用两个实际域的步骤注入。非多重配置会把此前Count2归一为1，形成1基板×1基岛×2焊点；本次核对原构造行为而非绕过构造或使用未初始化对象。坐标仓库使用原默认宿主路径，未执行VM校准。

## 已复现的数据状态边界

1. [S2返工](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1098)只重置第一个匹配消息，重复消息保持Finished；返工列表后项缺失抛ActionNode Sort Error，先前的重置已经生效。元组重载按显式步骤名匹配当前基板/基岛。
2. [相对固晶排序](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1440)移除原视觉消息并在每次Pick前新建视觉消息，原完成标志丢失，非相对视觉标志保留；同一焊点的多个工序只选首个启用工序。后面的相对焊点未找到工序时异常，前面的视觉移除已生效。
3. [S1步骤注入](../../trunk/AKRS.ZX2200/Main/Machine/Process/S1ActionNodeController.cs#L859)及[S2步骤注入](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1408)只追加未有键；保留完成状态，也保留已从工序清单删除的旧键。新工序追加在旧键旁，匹配的null工序名经Dictionary操作抛ArgumentNullException。
4. S2空Init清空排程但保留旧CurrentBondActionNode；Finish对空排程越界。null工序列表在清空后异常；FinishCurrentActionNode没有当前消息时空引用。

以上是明确隔离数据上的原程序集结果，不推断设备现场事故。返工/相对排序/Finish用反射读写WorkMessages/CurrentBondActionNode这一普通测试消息状态；公开Init和实体注入直接使用实际域、目录、配置与单例。反射没有替换路径、单例、构造器或实现。这些结果尚不覆盖当前消息与真实输送域的完整衔接。

## 证据与剩余

首轮宿主编译actualexit1/25条错误：ActionNodeMessage的命名空间与文件位置不同，HardwareRepository内部类型不能直接访问。补充实际Services命名空间并改用公开原SDK查询入口后通过；失败测试源码和日志保留，原业务源码未动。先通过211项，再增加独立排序预期和真实树注入共40项；原211条名称/顺序是251项的子序列。本次冻结33份新增文件，父3259份，共3292份；只读IL重放相同。见[测试](native-action-controller-test.json)、[审计](native-action-controller-audit.json)、[进度](native-action-controller-progress.json)。

不合并正式1328、旧受控278/目录119、原生58/98/124或40专题3817快照。原完整MSBuild、许可证/织入、VM依赖、完整启动/输送域衔接、具体DoWork、就绪负分支、暂停停止、下层算法与部署/UI/设备仍待验收；LC5/Fody2/VM5失败和388资源1498条通过证据保持。整体16工程/29组/1436文件/13项仍未完成。
