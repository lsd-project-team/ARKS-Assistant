# 原注册节点条件与Pick离线返回

两次隔离Framework CLR运行各584项检查、544次原IsDoWork调用通过，标签、顺序、结果完全一致，共1168次检查。已覆盖全部34种注册节点接收者：33个原重写方法及Interactive继承的ActionNode.IsDoWork。另执行一次原Pick.DoWork离线短返回/轮。16工程、29组、1436文件、13项整体目标未完成。

15种公开状态条件×34节点=510次普通条件调用/轮。使用原公开Init/GetNext选择及Finish推进，由公开构造生成真实载具、基板、基岛、焊点与三个步骤；私有上下文只读。公开配置、信息标志、EntityState、剩余步骤字典及MachineWorkMode参与真实判断。条件包括视觉/识别/测高已完成、校正关闭、识别关闭、测高关闭/空测高点、实体成功、步骤已完成、禁用、仅S1、仅S2、离线及浸胶关闭。硬件仓库为空，无私有上下文写入或SDK替换。

## 原条件差异

S2SubstrateMeasureHeightActionNode、S2ModuleMeasureHeightActionNode在正常双系统基线返回true，公开OnlyBond（EnableInSystem2）状态却返回false；原守卫对该状态检查与S2载具及焊点测高不同。这是已复现的原行为，未修改生产源码。

离线模式并非统一拒绝IsDoWork：S2基板、基岛、焊点测高及点胶返回false；S2载具测高与Pick仍返回true。S1载具视觉仍接受AdjustType=None；S1载具测高忽略MeasureHeightInSystem1关闭；S2焊点测高忽略MeasureHeightInSystem2关闭。S2焊点视觉和测高在全部剩余步骤完成后仍可返回true。S2基板视觉要求EntityState=Process。Interactive的继承基础条件在15场景均返回true。这些判定只表明条件层行为，不代表动作或完整生产任务完成。

## 公开载具移除后的缓存

有效选择之后公开将当前Section.TransportUnit置null，随后原34个IsDoWork调用/轮。S1除Interactive之外14种节点抛异常；S2载具视觉、载具测高及载具身份3种节点抛异常，总17次异常。Interactive仍返回true，另16种S2下级节点仍从之前选择的缓存基板/基岛/焊点上下文返回true。测试在本组之前未重新InitCurrentMessage，结束恢复公开载具；这是明确的缓存寿命边界，不能据此认定后续DoWork安全。

## 原Pick离线DoWork

原Pick在RecordTime日志调用后检查OffLineWork并立即返回Success，早于WorkStart、State=Running及try/finally。公开事件回调计数均为0，初始Idle状态保持，WorkStop不触发。每轮仅一次原Pick调用；其他33种具体节点DoWork未执行。本轮没有运行准备动作、轴/相机/VM、等待/信号或原生产Task。前序Interactive五次短DoWork仍属独立历史范围。

## 来源与证据

146个原声明、71个严格解码原文件绑定完整符号、UTF16位置及原字节SHA。34个运行方法的实际DeclaringType与源符号一致，其中一个继承基础方法。35个静态Cecil方法为34个IsDoWork及完整Pick.DoWork，35不是544次运行调用的数量。IsDoWork静态调用中没有Move/Wait/FindModel/DoWork；完整Pick方法含设备路径，当前只证明明确离线早返回。

两份宿主源与162真实引用编译成功后运行，两轮实际加载各16个保真资源原源码程序集，32个物理文件SHA核对。六步条件/来源/IL与配方、动作、算法、阅读器、虚分派父绑定通过。102新增冻结输入，283既有输入复用不增数，9734+102=9836；正式冻结1328及历史报告、阅读器、语义图不变，来源台账不是执行覆盖率。

保留三份完整候选：首份因宿主局部变量重名CS0136编译失败、未运行；第二份301项后因预期矩阵遗漏S2基板视觉Process守卫失败，按原源码纠正宿主预期；第三份550项普通条件已通过，保存后另扩展34次载具移除条件。原生产C#/csproj及历史证据均未修改。

原程序集未经过完整原工程LC/Fody/MSBuild/部署，真实UI/SQL/VM/设备、其他节点DoWork、任务等待/Retry/Pause/异常退出、组件Add/PR复制和完整29组业务解释仍待验收。下一步沿原任务循环检查条件、上下文、短返回、重试与退出的关系，并继续验证可运行非设备分支。整体目标未完成。

只读复验：`node --max-old-space-size=4096 scripts/verify-native-node-preconditions.cjs`、`node scripts/verify-native-node-preconditions-bindings.cjs`。冻结输出禁止覆盖，新实验另建目录。
