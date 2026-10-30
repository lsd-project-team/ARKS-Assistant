# S1/S2动作控制器初始化、排序与筛选复核

本轮80项隔离检查通过，执行33个未改写原方法与完整ActionNodeMessage。生产源码未改动。

## 执行范围

每套控制器执行Init、GetSubstrateCount、GetModuleCount、SortActionNodeByModule、GetActionNodeMessageByProcess、GetWorkBondPosition、RemoveOtherStep及八种排序（各15个）；S2另执行RemoveDisableActionNode、SortRelativeBond；另执行MathHelper.GetCycleList。提取收据和审计保存完整文件哈希、方法行号及片段哈希。

域单例、配置容器、动作仓库、载具几何、器件仓库和异形数量助手为夹具；启用步骤访问器以FindAll(IsEnable)模拟源码表达式，并非整类运行。实际消息类来自原文件。测试不执行控制器外部事件、任务线程、UI、SDK或设备。

## 初始化与排序

- S1：清空队列→排序→异形筛选→清空当前消息。S2：清空队列→清空ProcessStep→排序→异形筛选→禁用筛选→相对贴片重排。两套都在步骤为空时提前返回，因此S1旧当前消息、S2旧ProcessStep可保留。
- 步骤底层列表为null时，模拟原表达式的访问器先FindAll而抛异常；Init队列已清空。不能把方法内null判断当成底层列表保护。
- 两套4种作业优先级×2种步骤/位置优先级，共16种组合均运行；在2基板×2基岛、2步骤的样本中，每种8个生产动作且排除禁用步骤，逐条核对生产动作的步骤/基板/基岛次序。此断言不等于所有准备动作排列、所有配置组合的穷尽验证。
- 载具优先/步骤优先按步骤→基板→基岛；基板优先/步骤优先按基板→步骤→基岛；位置优先样本按基板→基岛→步骤；基岛/焊点优先的样本也按基板→基岛→步骤生成生产动作。
- 焊点去重按名称GroupBy，保留首次出现的步骤对象；重复null名称也归为一组。
- S1分段把不属于GetFirstMatrixIndex的消息放前，插入Interactive，再放属于该集合的消息；载具级消息保留。未知主模式在分段下仍可只生成Interactive。
- S2开启批次数为1时，载具优先按基板分批，基板优先按基岛分批；关闭批次数时采用对应总数。未知主模式可生成空队列而不报错。

## 动作生成的优先级

- S1：胶型非字面量Null→点胶；否则检测非Null→检测；仅配置器件不生成动作。C# null与字符串Null不同，null胶型仍可生成点胶动作。
- S2：器件→检测→胶型。器件查找失败或类型错误直接抛异常，不回退到检测/点胶；Init此前已生成的准备消息保留。
- 非翻转器件不加入DipFlux；翻转且AfterAccuracyMode时Pick→UpLook→DipFlux→SubstrateCamera→Bond，Off不加入DipFlux，其他沾胶模式为Pick→DipFlux→UpLook→SubstrateCamera→Bond。六种翻转/沾胶组合按完整名称序列验证。
- null器件名会进入仓库查询；本测试Dictionary仓库以ArgumentNullException失败，仅证明调用到该夹具，不宣称实际仓库必然抛同一异常。

## 异形与禁用筛选

- 异形筛选移除超出基板/基岛范围或已知步骤焊点不存在的消息，保留载具级消息；步骤名称查不到时会继续保留该消息。负下标未由上限判断拦截，索引时抛异常。
- S2仅在LagerNumber为true时做禁用筛选；实际载具null则原样返回。
- 禁用基板仅移除基板级消息，禁用基岛仅移除基岛级消息，焊点消息按焊点自己的状态筛选；测试证实上层Disable不会级联删除下层Product焊点消息。后续动作是否另有门控不在本结论范围。
- 筛选会原地按WorkIndex排序载具集合，再按消息序号减一访问列表，未按WorkIndex值查找。样本WorkIndex 10/20仍以消息1访问排序后的第一个对象。
- 步骤/焊点缺失、载具数量不足均可抛异常；此前已删除的消息不会回滚。

## 相对贴片重排

- 相对焊点配置只Find第一个同名步骤，先删除该步骤所有BondPositionVisionActionNode，再在对应Pick之前插入视觉消息，并保留基板/基岛。第二个同焊点步骤不会被同样处理。
- 重复重排在本样本不累积视觉消息。只有点胶而没有Pick的相对步骤会丢失原视觉消息且不补插。
- 相对配置找不到步骤会加入null。所测样本先移除有效步骤视觉消息，RemoveAll谓词因无视觉消息而短路，随后有效步骤视觉消息重新插入，再在缺失步骤插入阶段抛空引用；不会整体回滚。不能笼统称作固定在移除阶段失败。

## 分批算法的静态边界

原GetCycleList(5,2)得到[0,1]、[2,3]、[4]；totalNumber<=0不进入循环。源码显示totalNumber>0且cycleNumber<=0时，内层不执行而外层i--抵消for自增，循环无法推进并持续添加空列表。该路径仅作源码推导，未运行无限循环。是否有上游配置校验确保正值仍须追踪，不能直接宣称生产可达。

## 验证命令与剩余范围

node scripts/test-action-sort.cjs
node scripts/build-action-sort-audit.cjs --check

80为断言数，不是覆盖百分比。仍需真实配置加载及数值校验、原异形数量助手与分段矩阵算法、控制器与完整生产任务联合运行、配方切换/暂停恢复、线程可见性、全工程构建与设备。29组保持部分复核。

后续输入边界已补[批次数配置专项](cycle-config-review.md)：原生界面声明MinValue=1；完整原配置类配合项目Newtonsoft DLL可接受并往返0和负数，事件自身未校验下限。真实单例加载及全部门控仍未端到端执行，不据此宣称生产故障已复现。
