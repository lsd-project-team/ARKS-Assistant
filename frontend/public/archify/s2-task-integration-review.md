# S2生产任务、报警选择与人工上下料集成复核

2026-09-29。59项检查通过，原生产源码未修改。

## 已实际执行的源码

原样提取13个完整方法：BondTask.DoWork、GetIncomingSignal、SendAway、CloseDispenseCylinder；S2DispenseActionNode.DoWork/IsDoWork；BondHeadController.MoveBondZToSafePos；System2Domain.WaitSingleStep；Machine.Stop/SetState/IsStop/IsPause/SetStopStateAlarm。直接编译仓库完整Signal和枚举源码，事件使用真实EventWaitHandle。定位、文件及片段哈希见s2-task-integration-test.json。

任务为同步DoWork调用。动作服务、插补、坐标、温漂和参照点补偿、模组安全位、焊头Reset、换嘴、UI、日志队列、硬件输出、Mapping保存均为可记录/故障注入替身。安全Z和Stop是原方法，但最底层轴、报警和真空调用仍是替身。正常流道放行后，ReleaseSignal夹具才将测试状态设Stop以结束外层循环；这不是原生产信号的副作用，不把正常测试结尾Stop状态当成生产行为。S1占位方法未执行。

## 报警与重试的真实任务行为

- 正常顺序：吸嘴架回原位→模组安全位→焊头Reset→来料→三项补偿→模组安全位→周期统计→注入步骤→节点→产品Finish→焊后补偿归一化→可选顶针耗时保存→送走→刷新。
- 直接Abort/Exception：先原Machine.Stop，再原安全Z，配置启用时再胶盘回位，随后return；不完成当前动作、不放行。Stop关闭单步后，原域包装直接允许安全Z，不等待单步事件。
- Alarm→Abort同上；Alarm→Ignore结束当前动作并可放行；Alarm→Retry跳回同一节点的IsDoWork，重新关气缸并执行，不重新GetNextActionNode。
- 直接Retry进入下一次while并重新GetNextActionNode。测试动作服务在FinishCurrentActionNode之前保持当前索引；真实服务选择/排序未集成，不能据此保证实际返回同一实例。
- 直接Fail没有switch分支，会走FinishCurrentActionNode和正常尾部。这里使用脚本动作直接返回Fail；真实S2点胶控制器的Fail/Retry/Abort/Exception均先由真实点胶节点转Alarm。选择Ignore时动作可结束并放行，但焊点完成标记未写入。两层返回不能混淆。
- 节点WorkStart/WorkStop异常直接穿出任务，没有任务级Stop或安全Z补偿。Stop内部日志队列、清弹窗、报警、真空异常会阻止后续安全Z；安全Z异常会阻止胶盘回位；胶盘异常同样向外传播。
- 三项前置补偿返回false均直接退出，不调用Stop、不注入步骤、不放行。提前换嘴失败则调用Stop后退出。

## 门控、对象和停止后收尾

- Enable=false仍执行准备、补偿、注入、产品Finish及送走；只跳过动作循环等Enable分支。
- 节点门控false仍FinishCurrentActionNode；不关闭气缸、不执行节点。IsCloseCylinder=true会抑制任务的关闭气缸调用。
- 真实点胶门控跳过离线、禁用、仅S1启用焊点；null焊点异常直接穿出任务。
- 动作内部Stop后返回Success，任务仍完成当前动作；下一次WaitStart退出循环，随后执行模组安全位、Finish和归一化。SendAway检查Stop后抑制流道放行。
- 非产品对象且配置流道时，原DoWork先把旧对象传给InjectSteps，再重建TransportUnit。夹具记录到传入引用与后续全局对象不同；后续[真实动作控制器专项](action-controller-review.md)已执行原有参构造和Init：新载具会再次调用S2、S1的InjectSteps，因此此顺序不能推断正常新载具缺步骤；完整任务与真实服务的联合运行仍待验证。
- 补偿模式先重建测试载具再注入。可选顶针耗时保存位于归一化之后、放行之前。归一化、耗时保存或放行接口异常均发生在产品Finish之后，并向外抛出。

## 人工上下料与文件失败

无流道且载具为空：原GetIncomingSignal询问确认；选择Yes并且MapBelt得到非null对象才继续。取消或MapBelt后仍空则原Stop并退出。

无流道送走：可选SaveMapping→清空载具引用→设NoMaterial→提示人工拿走→Stop。

- Mapping保存抛异常时，载具引用保留，提示和Stop均不执行。文件系统本体未运行，本项验证调用顺序和异常传播。
- 提示调用抛异常时，载具引用已经清空，但后续Stop不执行。
- 正常人工拿走分支最终Stop，不发送流道放行信号。

## 验证命令与剩余范围

node scripts/test-s2-task-integration.cjs
node scripts/build-s2-task-integration-audit.cjs --check

59是断言数，不是穷尽路径覆盖率。仍未执行真实动作服务/排序注入、补偿算法、完整插补控制器、换嘴控制器、真实UI和文件保存、Task.Factory任务启动、多线程暂停恢复、原工程构建及设备。13个方法的提取不等于完整类执行。29组仍部分复核；下一步优先真实动作服务、产品对象绑定与完整构建依赖。
