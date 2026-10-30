# S1生产任务与点胶节点集成复核

2026-09-29。30项同步隔离检查通过。生产源码未修改。

## 实际执行范围

提取并原样编译六个方法：DispenseWorkTask.DoWork/GetInputSignal，S1DispenseActionNode.DoWork/IsDoWork，DispenseController.MoveToSafePos，System1Domain.WaitSingleStep。任务循环实际调用真实节点门控、节点方法及安全移动包装，不再仅静态拼接任务出口。方法位置和文件/片段哈希见 s1-task-integration-test.json。

动作服务排序、步骤注入、焊点完成状态、Machine.Stop内部、信号内部、插补控制器、坐标变换、统计与UI回调均为明确替身；轴运动仅记录调用。直接同步调用DoWork，未启动原Task.Factory任务，也未运行完整生产类、线程并发或设备。基础夹具的S2占位方法会抛NotSupportedException，本组不调用它们，也不计作S2覆盖。

## 已复现的执行顺序

- 正常：初始化→初次安全移动→入料预点胶并消费入料信号→注入步骤→节点门控/执行→焊点完成标记→动作完成→末次安全移动→放行→任务Finish。入料等待与节点内预点胶各执行一次。
- 插补返回Fail、Alarm、Abort、Exception或Retry，均先被真实节点转换成Alarm；任务随后安全移动，再调用Stop替身，且不完成动作或放行。因此控制器Retry与节点直接Retry不是同一条分支。
- 插补/统计抛异常由节点返回Exception，任务进入安全移动和Stop；统计失败时焊点完成标记已经保留。
- WorkStart、WorkStop和S1刷新回调异常可直接穿出真实任务方法，未走任务尾部安全移动、Stop或放行。
- 节点失败后的第二次安全Z调用抛异常，真实任务方法随即退出，后面的Stop调用没有发生。这是包装层调用顺序复现，不代表设备物理停止状态。
- 初始安全移动失败及null焊点门控异常同样直接穿出任务，没有本地Stop补偿。
- 禁用焊点、仅S2启用、已完成步骤会跳过节点但完成动作。直接返回Retry的脚本节点会再次获取当前动作；“仍返回同一节点”是动作服务替身的显式契约，不能据此宣称真实排序器已集成。
- 入料预点胶Fail或已停止返回：再次安全移动后退出，不另调Stop；非法入料信号状态抛异常。
- Enable=false仍可执行尾部安全移动、放行和Finish。内层WaitStart=false且IsStop=false时仍放行；这是条件组合测试，未证明真实Signal能产生这一组合。
- 末尾IsStop=true抑制放行但不阻止Finish；无产品对象时先重建再注入；离线模式跳过入料与轴安全移动。

## 检查与剩余范围

运行 node scripts/test-s1-task-integration.cjs；再运行 node scripts/build-s1-task-integration-audit.cjs --check。30项是断言数，不是路径覆盖率或项目完成比例。

未覆盖：真实动作排序器/步骤注入/输送对象、Machine.Stop内部副作用、原Signal等待与暂停/恢复并发、ReSet持续等待和取消、完整插补控制器、实际SDK、物理阀和运动退出、S2完整生产任务集成、原生产工程构建。29组继续部分复核。下一步应替换服务与停止边界为真实实现，并补S2任务分支；不能把本组结果作为设备验收。
