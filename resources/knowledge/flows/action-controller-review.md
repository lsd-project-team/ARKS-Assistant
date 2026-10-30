# 真实动作控制器、步骤字典与载具构造复核

2026-09-29。51项隔离检查通过；17个完整原方法/构造函数以及完整ActionNodeMessage源码；生产源码未修改。

## 实际调用类型与测试范围

System1Domain.ActionNodeController绑定Main/Machine/Process/S1ActionNodeController；System2Domain.ActionNodesService绑定同目录S2ActionNodeController。不是BondSystem/Services/System1ActionNodesService或DispenseSystem/Services/System2ActionNodesService这两个历史服务。域绑定在本轮审计中以源码行和哈希登记。

原文执行：两套InjectSteps/GetNextActionNode/FinishCurrentActionNode/Finish（8个）；S2 ChangeNameToActionNode/InitCurrentMessage（2个）；BondPosition两套FinishedStep/IsNeedStep（4个）；TransportUnit两个有参构造函数和Init（3个）。共17个。

消息列表和预选ProcessSteps由夹具提供，未运行控制器Init及排序/过滤；载具容器、动作仓库、图案/检测仓库、对话框是替身。S2当前载具访问器以World.Current模拟源码动态读取全局载具的语义，并非完整域实例。原载具构造中的几何生成、ModifyMatter、偏移与配置单例为替身，但两个系统的InjectSteps实际执行原方法。未与整套任务、线程、UI或设备集成。

## 消息推进与重试

- 两套普通节点均选择第一个未Finished消息；未完成时重复获取返回同一仓库动作实例。FinishCurrentActionNode只把当前消息Finished设true，不直接完成焊点步骤。完成后再获取会推进；相同动作名可复用同一对象处理另一消息。
- S2对UpLookCorrectionActionNode、SubstrateCameraCorrectionActionNode有特殊重复保护：上一次动作名与下一未完成消息同名即提示并抛异常。未完成节点直接重取被拦截；即使上一个消息已完成，紧邻同名消息仍被拦截。因此上一轮脚本服务中“直接Retry重取同一节点”不能泛化到这两类真实节点。
- 特殊重复异常发生前，CurrentBondActionNode已清空。测试下一次获取可以重新进入同一消息；未验证实际任务是否捕获并重启。
- 找不到动作仓库名称时返回null，但当前消息仍非null且未完成。任务将null视作全部动作结束的影响见S2任务报告；本轮直接执行控制器，未再串联任务。
- S2 ChangeNameToActionNode在检查ActionNodes==null之前调用Find，因此null仓库先触发NullReferenceException；名为missing的动作返回null后仍初始化上下文。
- 全部消息结束后当前消息为空，再FinishCurrentActionNode会抛空引用。产品Finish把消息Finished全部设false；S1清空当前消息，S2把当前消息设为WorkMessages[0]，所以空列表S2抛越界而S1允许。两者均允许null列表直接返回。

## 步骤字典

- 按焊点名称匹配，把缺失步骤键加入并设false；已有true或false不覆盖，也不清除旧键。重复步骤名合并为同一键。
- 不匹配的焊点不添加；null匹配步骤名抛异常，此前键保留；null载具直接抛异常。
- 原IsS1NeedStep/IsS2NeedStep直接索引字典，缺键抛KeyNotFoundException；FinishedStep通过索引赋true，可以创建此前不存在的键。

## S2当前上下文缓存

InitCurrentMessage先查ProcessStep，再查检测/图案仓库，随后在try内遍历当前载具基板、基岛、焊点。

- 新消息步骤名缺失时ProcessStep变null，但此前BondPosition和图案缓存不清空。
- 新载具找不到对应WorkIndex时，可保留旧基板和旧焊点引用。
- 当前全局载具null被遍历catch捕获并提示，旧焊点缓存保留；提示自身异常仍向外抛。
- 检测/图案仓库访问和强制转换在try之外；异常直接向外传播。图案类型错误时，检测缓存可能已经更新。

## 载具重建：已排除的错误推断

上一轮观察到BondTask先InjectSteps(旧载具)，之后在非产品分支new TransportUnit(System2)。这确有先后顺序和对象身份变化，但不等于新对象缺少步骤。

真实有参构造函数调用Init；Init依次执行几何初始化→ModifyMatter→S2.InjectSteps(this)→S1.InjectSteps(this)。枚举构造随后应用对应系统偏移；字符串原因构造不应用系统偏移。51项测试包含这条真实构造/注入链，并确认新载具两套步骤都存在、S2节点选择绑定新载具焊点且IsS2NeedStep正常。

“向旧对象注入，再人工替换为未注入的默认对象”确会在新对象IsS2NeedStep触发缺键，但它只是负面夹具，不能描述正常有参构造行为。无参构造源码用于反序列化且不调用Init；实际反序列化输入仍需单独核验。

构造失败也有边界：ModifyMatter异常阻止两套注入；S2注入过程中异常可留下部分S2键并阻止S1注入和偏移。测试借助ModifyMatter替身保留对构造中对象的观察引用；不宣称失败对象一定暴露给生产调用者。

## 验证与未完成项

node scripts/test-action-controller.cjs
node scripts/build-action-controller-audit.cjs --check

仍需全部排序/过滤/相对贴片重排、动作服务与完整任务集成、真实几何配置/ModifyMatter、配方切换与恢复路径、多线程状态可见性、全工程构建和实机。51项不代表控制器或模块完整覆盖。29组继续部分复核。
