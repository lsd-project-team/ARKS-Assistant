# 原夹爪终止、Machine.Stop与输送轴命令

日期：2026-09-29。46项受控检查通过，9个原方法与完整Signal.cs、MachineEnum.cs参与执行。继承transport-pause的完整输送方法，加入原UnClamp、BlockCylinderDownAndDelay、固晶及等待段MoveBeltNoWaitArrive、模块SendRelativeMoveCommandBelt，以及原Machine.Stop、SetState、SetStopStateAlarm。

## 夹爪终止不向父方法返回失败结果

四种原UnClampMode分别执行；测试传感器返回未到位，对话框选择Abort。原UnClamp调用原Machine.Stop后以void返回。验证机器状态变成Stop、退出单步、关闭要料和顶针真空替身、焊后缺陷计数清零。随后父TransferBondToWaitingUnload继续执行，并返回Success。

固晶与等待段的原皮带控制器和模块转发方法都真实运行。两次Axis.SendRelativeMoveCommand替身调用时状态均为Stop；固晶配置距离17、基础速度80、倍率0.25，观测命令参数17和20。这里验证的是原调用链到轴对象接口，不是实际轴实现或运动板卡命令成功。

最后，父方法把材料对象从固晶段转移到等待段、刷新并调用Save替身；记录的Save调用状态仍为Stop。原Stop本身没有返回失败标志给UnClamp或输送父方法。外层TransportTask此轮没有运行，不据此断言其后续循环或其他生产线程的行为。

## 对照分支与失败边界

- Ignore：保持Working，夹爪输出一次，继续输送并保存。
- Retry：测试对话框首次返回Retry时把传感器设为到位；原重试路径再次输出，随后输送一次，保持Working。该传感器变化为明确测试安排。
- 原Stop依赖分别在构建状态日志、入日志队列、报警器停止、要料输出和顶针真空处抛出：异常经Task.WaitAll到父方法catch，返回Exception，没有皮带命令或Save。构建日志失败前仍Working，其余四处已提交Stop。
- 皮带配置为空：原UnClamp提示后直接返回，另一个挡料气缸任务仍调用；父方法继续到原皮带包装方法后才因设置缺失抛出，返回Exception。未调用原Stop，没有轴命令或Save。
- 正常传感器路径：无报警，保持Working，执行一次输送并保存。

## 方法与替身边界

真实执行原方法体、Thread、Task.Run/WaitAll及Signal事件句柄。MachineStateModel是volatile测试存储，I/O终端、轴对象、设置对象、日志、弹窗、保存与材料刷新为替身。未连接机械、未读写生产配置，未执行产品.NET Framework宿主。底层传感器输出、轴驱动安全门控、外层任务和真实并发仍需继续验证。

继承的传送传感器序列模拟正常完成；没有把Stop映射为轴替身停止运动。因此结果证明父方法在Stop后仍尝试调用轴接口，不证明实机继续运动。原Stop异常测试亦不等同于生产故障发生率。

下一步：将外层TransportTask的返回值处理与原Stop串联；解析实际BeltAxisX类型及驱动前门控；继续空跑消费者与供晶等待暂停。29组仍为部分复核。

运行：node scripts/test-transport-unclamp-stop.cjs。审计：node scripts/build-transport-unclamp-stop-audit.cjs --check。
