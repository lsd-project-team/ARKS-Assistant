# 供晶要料消费者：暂停、停止与取料许可

日期：2026-09-29。71个受控场景、212项断言通过。执行原 `WaferSubSystemTask.Dowork()` 完整方法及原 `IsNeedChange` 表达式属性，使用完整原 Signal 类、MachineEnum 和真实线程/事件。生产源码未修改。

## 源码及运行边界

- `WaferSubSystemTask.cs:64–386` 完整 Dowork 逐字提取，未删减换料、搜晶失败、视觉重试、真空、单独空跑、记录数据和异常处理分支。
- 原 `IsNeedChange` 属性继续委托 `Block.IsNeedChangeCarrier()`，属性原文另行绑定。
- 需料信号严格匹配原 SignalPool：100ms轮询、ManualReset、初始false。允许取料信号为100ms、AutoReset、初始false。两个构造声明逐项核验。
- 本机运行时为 .NET 10.0.11。状态模型、Machine.Stop、载具仓库、ChangeTabletAuto、Block搜晶/换料标志、视觉、动作/真空、弹窗、DBService和Excel均为显式替身。
- Excel分支仅在内存中运行；原 FileInfo 路径没有被打开，未写入任何生产文件。运行不等于原Stop链、真实换料/搜晶算法、原生UI、驱动或设备验收。

## 暂停和停止结果

| 时间点 | 已验证行为 |
|---|---|
| 入口Stop | 不消费要料、不搜晶、不发取料许可；已经置位的ManualReset请求仍保留 |
| 入口Pause | WaitStart阻塞；恢复Working后完成一次搜晶并放行 |
| 已进入要料Signal.Wait后Pause | 仍消费要料、调用搜晶和真空接口，并发出允许取料事件；调用记录状态为Pause |
| 等待期间稳定Stop且无新事件 | 等待返回false，经外层检查退出，不调用搜晶或额外Stop |
| 接收日志、搜晶入口、真空入口处切换Pause或Stop | 原循环后续没有再次门控，仍更新前次芯片名、清除需料并发出取料许可 |
| 非单次模式 | 外部在许可发出后置Stop，下次外层循环退出，不执行IsSearchOne的Stop分支 |

状态切换测试使用显式线程屏障；进入事件等待测试先观察至少十次机器状态读取，Working且无事件时确认已进入原Wait轮询，再切换状态。没有用短暂睡眠推断等待位置。

## 材料与失败分支

- 24组载具/真空开关/单独空跑/离线组合覆盖 Wafer、Waffle、StaticWaffle；仅StaticWaffle、单独空跑且非离线条件触发原Z与XY调用路径。这里只验证调用路由。
- 旧芯片名变化、NullTablet和换料失败均经过原分支；缺少载具或搜晶失败进入原catch。成功时清除需料，失败发生在清除之前则保留请求。
- 搜晶失败后的非晶圆、WaferMap、整机DryCycle、视觉OK、Retry、范围外重新选点、Box及Abort路径分别运行。更换或重试次数由明确替身返回序列控制。
- 视觉Retry执行换料标志重置和参数保存；范围外会重复选择。Box路径的按位`&`仍会求值范围判断，但不会因范围外进入重选分支。
- 单独空跑在正常结束时刷新Map并增加次数；记录关闭、匹配失败、内存记录成功、匹配结果空数组分别运行。

## 信号提交与异常

1. 原顺序先 `IsBondNeedChipSignal.ReSet()`，再 `IsWaferAllowPickSignal.Set()`，最后记录日志、刷新Map或保存记录。
2. 已释放真实需料事件导致ReSet失败时，原catch弹窗并调用Stop；尚未尝试发出许可，需料公开State仍是Set，底层句柄已不可用。
3. 已释放真实许可事件导致Set失败时，需料已经成功清除，许可未能发出，随后catch调用Stop。这是“请求已清除、许可未发出”的部分完成状态。
4. 许可之后的日志、Map刷新或记录保存异常不能撤回已经置位的允许取料事件；测试逐项读取真实事件确认。
5. 原catch先显示错误弹窗，再调用Stop；弹窗本身异常会跳过Stop，Stop替身异常也向线程包装层传播。两者测试中状态保持Working。实际原Stop内部故障另有此前专项，本报告不将替身结果冒充真实Stop集成。

这些证据说明消费者自身的门控和信号先后边界，不证明设备必然继续运动。Block、动作控制器或驱动可能另有检查，需要继续向下接入原实现和现场配置。

## 复现与审计

- `node scripts/test-wafer-consumer-pause.cjs`
- `node scripts/build-wafer-consumer-pause-audit.cjs --check`
- 来源审计绑定6个文件、1个完整原方法、1个原属性、2个原信号声明及212个唯一断言名。
- 全套回归和阅读器最终结果见 `wafer-consumer-pause-integration-verification.json`；回执生成且通过后才算本增量收尾。

## 尚未完成

实际Block.NextDie、换料实现与下层动作/驱动门控、原Machine.Stop组合、真实供晶与固晶并发、完整正常启动和模式切换调用者、实际配置/DLL、原生UI、完整构建及设备验收仍待完成。29个模块组仍为部分复核。
