# 真实Stop、状态包装与事件信号集成复核

2026-09-29。60项检查通过，原生产源码未修改。

## 本轮比上一轮增加什么

保留S1任务/入料/节点/安全移动/域单步六个原方法，进一步提取ZX2200 Machine.Stop、SetState、IsStop、IsPause、SetStopStateAlarm五个原方法，共11个方法原文编译；另直接编译完整原Signal.cs和MachineEnum.cs。Signal使用真实.NET EventWaitHandle，不是模拟等待返回值。位置、原文件及片段哈希见machine-stop-signal-test.json。

S1失败路径现在实际进入原Stop和状态/报警包装，原WaitStart和WaitSingleStep也实际执行。任务仍直接同步调用DoWork；动作排序/注入服务、插补、坐标、机器状态单例存储、统计队列、UI、报警器、上料输出、真空和配置为替身。不是完整生产类或原工程构建。全局Signal和StepSignal适配器仅转调仓库Signal原实现。S2占位方法未执行。枚举说明字符串使用替身扩展，不验证生产日志文字。

## Stop执行与异常边界

正常顺序为SetState(Stop)→清弹窗→停止报警→关闭单步→需晶信号ReSet→在线模式关闭要料→关闭顶针真空→逐项清零焊后缺陷计数。通过真实事件检查需晶信号复位；未验证任何物理输出。

- SetState先构造日志实体，再写状态，最后加入日志队列。构造抛异常时状态不变；队列抛异常时状态已Stop，但其余停止清理尚未执行。
- Stop本体无局部try/finally。对日志构造、日志入队、清弹窗、获取报警器、报警器设置、关闭要料、关闭真空分别注入异常，均中断剩余步骤。与S1任务串联后，这些异常继续穿出任务，不进入任务Finish或放行。
- SetStopStateAlarm条件为列表null或Any；null进入分支后索引访问产生NullReferenceException，状态已Stop、单步仍开，后续未执行。空列表则跳过；多报警器只操作第一项。
- 关闭单步之后，如果真实需晶事件句柄已被释放，ReSet抛ObjectDisposedException，在线要料和真空关闭均不执行。释放句柄是故障注入，不宣称生产中已有释放路径。
- 真空关闭之后，焊后计数列表遇到null条目会留下前项已清零、后项未清零的部分状态。
- 离线模式只在报警包装中旁路；Stop仍调用在线要料和真空依赖。非在线配置仅跳过要料输出。已是Stop时不新增状态日志，但重复执行清理。
- S1节点失败后先执行安全移动，再执行真实Stop。第二次安全Z抛异常时Stop没有被调用，测试状态仍Working、单步仍开、真空关闭未调用。这里只说明软件调用和测试状态，不推断现场机械状态。

## 真实Signal行为

1. 稳定Stop令WaitStart返回false；Working、Operate、Teaching、Preparing均直接放行。
2. 暂停循环内读到Stop返回false。但若状态依次在四个读取点为Working→Pause→Pause→Stop，Stop出现在下一次while条件读取，则循环退出后返回true。用可脚本化状态getter确定性复现此读取交错，说明控制流存在该窗口；未执行生产多线程竞态或证明实际发生频率。
3. Wait()自动复位事件被消费后会重置State；Wait(int outTime)直接使用recycleTime等待，忽略outTime，且不重置State。测试负outTime仍不抛、已置位自动事件被消费后State仍Set而第二次等待失败。
4. 构造initialState=true只初始化事件，公开State仍默认ReSet。直接写State=Set不会设置事件，直接写State=ReSet也不会复位已置位事件。
5. ManualReset事件在多次等待后保持置位，ReSet同时复位句柄及State。
6. 原WaitSingleStep仅检查单步标志，不检查MachineState；机器Stop但单步标志仍开时可消费预置事件并返回true。单步关闭则不消费事件、直接false。
7. 正常Stop关闭单步后：直接WaitStart和WaitSingleStep均false，而原System1Domain.WaitSingleStep因为单步已关闭直接返回true。这三个接口不能混为同一停止契约。

## 自动核验与剩余工作

运行node scripts/test-machine-stop-signal.cjs，再运行node scripts/build-machine-stop-signal-audit.cjs --check。60为断言数，不代表状态空间或完整线程覆盖。测试有30秒进程上限；没有启动生产任务线程或硬件。

仍需真实动作服务/步骤注入、实际MachineStateModel持久化与并发可见性、真实统计队列/日志实体与报警器实现、所有信号调用方、S2生产任务完整链路、编译/部署和设备退出验收。读取交错测试不替代并发压力测试；仅仓库Signal源码及本地.NET运行时得到验证。
