# 安全门到点胶来料等待的暂停响应

日期：2026-09-29。16项受控检查通过，编译执行8个未改写的原方法：门传感器读取、门控检查、Pause、IsWorking、IsPause、IsStop、SetState和DispenseWorkTask.GetInputSignal。运行于随附PowerShell的现代.NET，不是产品.NET Framework宿主。

## 已验证的顺序

- 原安全门读取按名称“门控”查找Sensor，然后调用GetInputValue。Working且门打开时，经原Pause和SetState进入Pause；门关闭时保持Working。缺失传感器或读取异常在状态切换前传播。
- 原SetState先赋新状态，再添加状态日志。真实BlockingCollection已停止接收时，添加抛异常，但状态已经是Pause。日志实体内容及状态容器为替身。
- 在原GetInputSignal真实线程中，门触发Pause后，观察到至少四次状态读取而预点胶调用仍为0、来料信号仍Set，线程继续轮询。关闭门不会自行恢复；显式设Working后，预点胶一次并消费信号。
- 从Pause显式设为Stop后，原循环跳过暂停分支，先执行一次预点胶，再检查Stop而返回false；来料信号不消费。此处测试的是状态变化，不是完整Machine.Stop方法。
- 预点胶替身被屏障阻塞时，门触发Pause不会中断该调用。释放屏障返回Success后，第二次暂停检查保留来料信号并继续等待；恢复Working后再执行一次预点胶，然后才消费信号。
- 若被阻塞的预点胶返回Fail，原方法先返回false，不等待第二次暂停检查。无效来料信号则在预点胶之后抛异常，不自行设Stop。

## 证据边界与剩余工作

原方法片段由源码自动提取并记录完整文件和片段哈希。Sensor驱动与硬件仓库、预点胶动作体、状态容器及信号字段是明确替身；线程和同步屏障真实运行，所有线程有超时和清理。预点胶调用次数不等于物理点胶次数。

仅验证来料等待方法，不是完整DispenseWorkTask.DoWork、真实Signal.WaitStart或所有动作内部的暂停语义。传感器极性、实际硬件读取、完整生产并发和机械停止仍未验收。已有S1完整任务替身测试不能代替这些缺口。Signal的实际实现位于trunk/AKRS.Galaxy2.Machine/Models/Signal.cs，既有[真实Stop与信号报告](machine-stop-signal-review.md)已用完整原Signal类完成60项限定检查，包括稳定状态与脚本化读取交错。本轮没有替代或重复宣称这些成果。下一步将安全门触发接入已有真实Signal与完整S1任务测试，补动作执行期间的暂停响应；仍需区分受控交错与生产竞态。

运行：`node scripts/test-safe-door-pause.cjs`。审计：`node scripts/build-safe-door-pause-audit.cjs --check`。测试未修改生产源码或设备配置；29组仍保持部分复核。
