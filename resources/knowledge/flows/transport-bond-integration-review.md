# 原Bond到等待区控制器链接入完整输送生产器

2026-09-30：310项受控断言通过。完整原TransferBondToWaitingUnload、UnClamp、挡料延迟、两段皮带包装及基础轴包装，接入完整九任务Start、原UI/准备/启动与真实供晶Task和完整Stop。组合编译含87原方法、39属性、6枚举、13字段，共145原片段；66份测试/依赖来源、23种真实信号契约与46段专题快照可核验。编译范围不等于所有方法和分支都已执行。

生产源码未修改。原Task.Run、Task.WaitAll、事件等待、goto重试、返回码和异常边界均保留。其他八条传输方法、传感器/轴驱动、日志、程式Refresh/Save、UI及域/SDK生命周期仍为明确替身；本轮不证明原项目构建、原生UI或设备验收。

## 原调用链与共享状态

两个原UI按钮各经过六种上料配置。其余输送任务在命名替身入口屏障处持有，只放行Bond到等待区任务；原Controller方法经真实AllowBondTransferToWaitingUnloadSignal等待，运行原代码中的两个子Task、原解夹和两轴包装，转移区段物料并调用Save替身，再返回原外层switch。

原TransportController.TransportProgram表达式使用同一个程式单例；区段状态、传输态、TransportUnit属性，皮带距离/速度/解夹模式与解夹延迟均编译原成员。参数成员不包含原Dataset继承、元属性校验、加载与保存生命周期。原默认距离700、速度比例0.5、RisingAndVacuum解夹模式及Ready传输态已直接检查；运动场景另设距离17/23和比例0.25/0.5，基础轴包装用驱动速度80计算20/40。

完整生产器中的两个子Task确实运行，记录到不同Task身份，并由原Task.WaitAll等待。物料刷新/保存、两轴驱动和控制器传感器是替身边界。外层Task与供晶LongRunning Task的实际句柄保留并等待，池线程不Join。测试临时把线程池最小工作线程数提高至至少64，结束恢复；不能当作生产线程池设置。

供晶需料信号和Bond传输信号使用同一个原契约池，却不能互相代替。实际供晶Task收到需料后发取料许可，输送仍等待其自己的事件；发传输事件才进入原Controller后续动作。取料事件为AutoReset、需料为ManualReset、Bond传输事件为AutoReset，全部23契约延续核验。

## 暂停与停止

Pause在原外层WaitStart之前生效时，预置传输事件仍不能进入控制器；恢复Working后消费事件并完成传输。已进入原Signal.Wait的事件等待后再Pause，发事件仍可让控制器调用轴、转料和Save，观察到这些动作发生在Pause；外层仅在下一次循环入口阻塞。

稳定Stop发生在信号等待期间，Controller返回Abort，外层再次调用完整Stop，不下发轴命令或转料。事件已接受后再Stop，控制器没有新的停止门控，两轴命令、内存转移、Save及外层Success仍发生在Stop。Stop不等待控制器，也不跳过原Task.WaitAll：两条子任务在硬件替身处都被持有时，Stop已返回而父任务仍等待；放行后仍可在Stop转料保存。

以上时序由明确的事件/操作屏障与目标Task状态读取确定。不是从全局读次数推断某个任务阶段，也不是对现场调度或设备运动时序作唯一性保证。

## 解夹Abort仍可返回传输Success

四种原解夹模式均令传感器替身报告不到位。在报警提示返回前，真实供晶Task仍能处理需料并发许可；提示返回Abort时，原UnClamp子任务调用完整Stop然后正常return。Task.WaitAll看到子任务正常完成，原TransferBondToWaitingUnload继续两轴、转料、Save，返回Success；外层记录Success后在下一次状态门控退出。

观察到完整Stop复位需料、结束实际供晶Task，但此前的允许取料事件仍保留。原Stop没有复位该许可，本轮检查实际事件句柄，未用并发公开State推断事件消费。

| 原模式 | 验证到的输出顺序 |
| --- | --- |
| Vacuum | 真空false |
| Rising | 升轨false |
| VacuumAndRising | 真空false，然后升轨false |
| RisingAndVacuum | 真空false，然后升轨false |

两个混合枚举值在当前原方法中的实际输出顺序相同。这里只报告源码与调用序列，未对真实电气极性或机械顺序作判断。Ignore继续成功；Retry在同一个解夹子Task中重新输出，传感器替身转正常后继续。front1为必需传感器，front2/back1为可空；缺必需传感器进入Controller异常返回与外层Stop。

## 轴返回码、卡料与重试

两轴分别覆盖SDK替身的13个ExcuteResult值。原两个皮带包装和基础轴包装均为void，忽略相对运动调用的返回码；即使替身返回Fail/Abort/Exception等，两轴仍都被调用并转料保存。驱动抛异常则不同，进入原catch并由外层Stop。真实SDK的内部副作用、运动成功、单位与完成标志未验收。

Bond卡料Retry跳到retry1，重跑解夹和Bond轴；等待区卡料Retry跳到retry2，只再跑等待区轴。Abort返回后由完整生产器外层Stop。Ignore会继续内存转移与Save：Bond卡料Ignore可没有运行等待区轴，等待区卡料Ignore可没有正常入口物料检测。不得用内存状态或Save调用证明物料已实际送达。

## 部分提交与异常层次

在事件已接受、子任务输出/挡料/传感器、WaitAll后、两轴、出口/入口传感器、Refresh、提交日志、Save及保存后日志注入故障。正常内层catch记录异常并提示，返回Exception；完整外层switch调用Stop，Task以RanToCompletion结束，原UI已返回且不进入UI catch。挡料子任务抛错时，原WaitAll仍等解夹兄弟任务完成后才进入catch。

Refresh替身在入口抛错时，原代码已把同一个TransportUnit赋给等待区并设置HasMaterial，还没有清空Bond；两个区段引用同一个单元、都显示有料。提交日志、Save或保存后日志抛错时，内存转料已完成，外层仍Stop。Save替身不写磁盘，所以不能证明保存完成或磁盘原子性；Refresh替身也不覆盖真实单元更新中的内部副作用。

内层日志或异常提示本身抛错，会跳过正常Exception返回，转入外层catch。外层返回Exception/Abort日志在Stop之前抛错，也跳过Stop。Stop日志构造在状态提交前抛错时，Working与实际供晶Task保留；清弹窗或报警在Stop状态写入后抛错时，供晶自然退出。外层catch自身日志/提示再抛错，真实Task变Faulted，异常已显式观察。外层catch正常处理时可留下RanToCompletion、Working和其他活动Task，不能把任务完成当作设备停止。

## 手动调用与配置边界

同一原Controller直接在稳定Stop下调用，自动模式经真实信号门控返回Abort；isManual=true跳过事件，仍两轴/转料/Save，并在收尾再次UnClamp。IsTransportConfigured=false时，原UnClamp走关闭真空替身，两轴包装仍被调用。这是直接API行为，不证明完整UI包装会在禁用输送配置下启动本生产器。

## 复现与剩余项

`node scripts/test-transport-bond-integration.cjs`执行310项唯一断言；`node scripts/build-transport-bond-integration-audit.cjs --check`核验66来源、145原片段、23信号契约和46段专题快照。统一回归和四种宽度阅读器验证另存回执。

下一步原等待区到出料皮带控制器继续接入同一完整生产器；其他原传输、载具检查/MapMaterial、原Provider日志、程序/池/域/SDK生命周期继续保留。原项目构建、现场DLL/配置、原生UI与设备验收仍待完成，29个源组保持partial。本专题不提高总体完成比例。
