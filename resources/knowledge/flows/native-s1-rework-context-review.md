# 原胶检选择映射、ReDispense 枚举故障与消息重做上下文

两个全新 Framework CLR accepted 宿主各47个不同断言通过，18个原方法 IL、9个原源码哈希冻结；两轮结果和标签严格一致。父5500+新增71=5571冻结绑定。实际执行原 PostBondEpoxyCheck、绑定原 receiver 的私有 ReDispense/EpoxyApplicationDefect，以及原公开调度方法，没有复制这些实现。没有启动原 S1 任务或执行整个胶检动作；wholeTaskRetryExecuted=false、wholeConcreteActionRetryReturned=false。

## 输入与原选择映射

实际完整 S1/Transport/SDK 构造器和四实体载具树，Machine OffLineWork/Stop、SDK硬件空、safeDoor=false、Belt。公开原 Repository.Add 注册 PostBondInspection，实际 default PREntity 构造器后公开 SetName/AddVisionEntity 注册 PR；没有调用带名字的 PR 构造器创建算法、相机、模板或 VM 运行。原仓库 Find 返回这些实际对象，未写私有单例或路径。

原 PostBondEpoxyCheck 接收明确的测试输入 null、空列表，以及显式 caller hardware=null。公开 VisionAlarmLockFunc 提供测试 DialogResult，未构造或操作真实 UI/人工决策；原 PostBondCheckHand 自行把选择转换为原 ExcuteResult。不能把这种原映射验证说成真实视觉结果或完整 Retry 生产成功。

|实际原输入/公开测试选择|原结果|
|---|---|
|null结果 / OK|Success|
|null结果 / Ignore|Fail|
|null结果 / Abort|Abort|
|null结果 / Retry|Retry|
|null结果 / Cancel|原“检测未知错误”异常|
|期望数1/实际空列表 / Retry|Retry|
|PR名字缺失|在调用公开报警委托之前抛出原缺PR异常|
|期望数0/空列表/公开关闭数据导出|原Success，不访问硬件、不调用报警；不代表检测质量合格|
|PR存在/公开报警委托自然null|原PostBondCheckHand 的 NullReferenceException|

每轮6次测试选择收到同一个真实 PR、显式 null caller hardware；后续私有胶检结果 helper 的失败没有增加这个计数。原 EpoxyApplicationDefect 在实际 defect-only 上下文中直接绑定调用，先执行真实 DispenseVisionController.GetHardware，再调用 PostBondEpoxyCheck；空硬件下工厂抛原 NullReferenceException，原栈包含这两个方法，未到选择映射。这个原硬件前提没有用假 PRHardware 或替换控制器绕过。

## 三个由原排序建立的上下文

每个上下文公开配置三个启用步骤 focus/other/last，绑定同一真实 bp；other/last 的胶型与胶检名字均Null，只参与剩余步骤字典。focus分别为 dispense-only、defect-only、both-names。原 Init/InjectSteps/GetNext/FinishCurrent 自行生成并推进13条消息；测试只反射读取 WorkMessages，没有插入、替换或私有写入消息。通过原 bp.S1FinishedStep 和原 FinishCurrent 把三个步骤与全部消息预置已完成，这是明确的重做测试前提，不是实际执行这13个动作。

原 GetActionNodeMessageByProcess:714–730 的 if/else：胶型非Null产生点胶消息；否则胶检非Null才产生胶检消息。三种配置各只有一个 focus 处理消息，both-names 仍只产生点胶。实际返回与原 IL 一致，未把两个步骤或两种动作人工合并为同一步。

原 ReDispense:204–209 在 foreach(S1RemainingSteps.Keys) 内写回 S1RemainingSteps[key]=false。原 Framework CLR 4.0.30319.42000 的 Dictionary 写入使 Keys 枚举器版本失效；三个上下文均第一次写入 focus=false 后，在下一次 KeyCollection.Enumerator.MoveNext 抛 InvalidOperationException。其余 other/last 保持 true，13个消息仍全部 Finished，原 GetNext 返回 null；失败栈没有 SetActionNodeReWork。ReDispense 的 finally 只是释放枚举器，不能将异常恢复成正常重做。

这修正了初始静态预期：并非先把所有步骤重置再进入消息查找；实际更早在字典枚举处失败。未推断所有运行时版本、字典为空或不同键序列的行为，结论限定原 Framework CLR 与本轮三键实际上下文。

## 单独执行的原消息重做

另用原 Finish/GetNext/FinishCurrent 重新选中原消息，再直接调用原公开 SetActionNodeReWork([原Dispense,原Defect])。这一步是单独直接验证，不能声称它在上述 ReDispense 故障之后自然被调用。原方法按当前 Substrate/Module/ProcessStepName 查找两种动作，真实原排序没有该配对，抛原 ActionNode Sort Error。

|原focus配置|直接SetActionNodeReWork的提交|原GetNext|
|---|---|---|
|dispense-only|先找到点胶消息并置Finished=false，再因缺胶检消息抛错；12条仍Finished|再次返回原点胶节点，原IsDoWork因focus=false为true|
|defect-only|第一个点胶查找就失败，13条Finished保持|null|
|both-names|原排序仅点胶，部分提交与dispense-only相同|再次返回原点胶节点|

字典部分提交与消息部分提交是两个不同入口的原结果，不合成一条实际生产链。原 EpoxyApplicationDefect 静态上在结果Retry时调用 ReDispense 后才返回Retry；本轮没有跨过真实硬件工厂，更没有证明原任务 Retry→continue 成功。原 DoWork 的捕获/UI刷新、相机结果、物理补胶、生产退出仍需前提和后续核验。

~~~mermaid
flowchart TD
  A[原PostBondEpoxyCheck / null或数量不符] --> B[原PR仓库Find]
  B --> C[公开测试报警选择 / 非真实UI]
  C --> D[原选择映射 / Retry等]
  E[原具体EpoxyApplicationDefect直接绑定] --> F[原GetHardware / 实际缺失硬件]
  F --> G[原NullReference / 未到结果映射]
  H[原Init及三步调度 / 13消息] --> I[原私有ReDispense直接绑定]
  I --> J[Keys枚举 / 第一个step=false]
  J --> K[原InvalidOperation / 其余step true / 消息未重置]
  H --> L[单独调用原公开消息重做]
  L --> M[同一步缺配对 / Sort Error / 可能部分消息提交]
  D -.静态Retry调用链 / 本轮未串通.-> I
~~~

补充图不更新主阅读器8章节/89节点/101边或正式1328/旧40专题3817冻结记录。没有生产源码修改、私有消息写、动作/单例/SDK替身、真实 UI、相机结果、轴、物理点胶、SQL、完整原 MSBuild 或部署。

## 失败保存与验收范围

首个宿主编译漏用原 System2Configuration 的实际命名空间，诊断/输入保留。第二版成功编译后首个 CLR 宿主18断言通过，随后因误预期 Sort Error 而真实exit1；原目录、Probe、Cases、编译结果均保留。第三版诊断宿主38检查采集实际字典异常，仅用于解释和定位，不作为accepted47检查；旧诊断scope中的“全步骤重置”等文字不作为最终结论。第四版与重编译两轮成功emit SHA相同，两个全新accepted目录各47个固定断言通过，没有删改失败或诊断记录。

每个accepted宿主实际加载16个bound/replay保真资源程序集，runtime-map172项，162引用中10个直接原源码程序集引用。只声明result/标签一致，独立路径、日志和时间的完整stdout不声明字节一致。父返回门/保真资源验证在 guarded 流水线99528/fceb4a通过；审计不为子命令虚构独立会话。

继续原 Retry 整动作与任务传播、胶检配置和硬件前提、预点胶真实下层、S2安全/清零/补偿/UI前提与完整生产握手退出。在线设备/相机VM/SQL/LC/Fody/完整构建部署未验收，16工程/29组/1436文件/13项整体目标未完成。

见[测试](native-s1-rework-context-test.json)、[审计](native-s1-rework-context-audit.json)、[进度](native-s1-rework-context-progress.json)。
