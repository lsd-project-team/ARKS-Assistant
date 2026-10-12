# 界面急停按钮：原事件与状态刷新

日期：2026-09-29。27项检查通过，纳入45份原成员片段；不是这些成员的全部分支覆盖。继[急停与Abort报告](emergency-abort-review.md)后，本轮直接执行原BtEmergencyStop_ItemClick及原界面状态方法，避免把未确认的Machine.EmergencyStop调用链当作按钮行为。

## 按钮实际路径

Designer将BtEmergencyStop.ItemClick绑定到BtEmergencyStop_ItemClick，并把按钮加入ribbonPageGroup11。该事件只读取Axis列表，Parallel.ForEach调用每轴StopMove(false,true)，没有调用Machine.EmergencyStop、Stop或三个Abort，也没有本地try/catch。

| 原界面状态 | 急停按钮Enabled | 配方加载Enabled | 直接调用急停事件后的状态 |
|---|---|---|---|
| Working | false | false | Working |
| Pause | false | false | Pause |
| Stop | true | true | Stop |

三个状态下直接调用均只完成受控轴命令；同时存在的点胶、固晶、供晶三个真实Running Task仍保持Running，原关闭判定仍false。随后再次调用原ChangeUiByState，按钮标志保持原样，没有自动出现停止提示。事件也不退出单步、不重置焊后计数。

**直接调用处理器不是实际点击禁用按钮。** Working/Pause行用于验证原方法体及界面状态分支，不能声称用户能在这两个状态点击按钮。Native DevExpress消息分派、其他界面入口及硬件急停电路没有在本轮运行。

## 异常与同步边界

- 硬件查询异常直接抛InvalidOperationException；null列表抛ArgumentNullException。
- null轴或轴命令异常由Parallel包装为AggregateException，没有本地Stop、Abort或错误弹窗恢复。部分轴是否已执行不作保证。
- 空列表正常返回，仍不改变Working；重复事件调用重复轴命令，无本地重复调用保护。
- 单轴替身用有界事件阻塞时，原处理器等待Parallel完成才返回。这证明方法调用同步等待，不是原生UI响应时间或现场驱动超时证明。

## 与Machine.EmergencyStop区分

额外比较使用已完成点胶Task与仍Running的固晶、供晶Task：直接执行原Machine.EmergencyStop会调用Stop和三个Abort，变成Stop并退出单步；普通界面刷新启用急停和配方按钮，但两个受控任务仍Running，关闭判定仍false。这个比较不能证明按钮会走该链。

全trunk的C#文本扫描排除bin/obj后，目前只发现EmergencyStop后接左括号的一个精确词元出现，即其定义；未见同名直接调用文本。扫描清单摘要和出现位置由审计生成器固化。反射、外部程序集、委托间接调用及运行时版本不在这个否定结论范围。

## 检查构成与复现

- 三种状态×界面标志、原事件、任务存活、刷新四项：12项。
- 四类故障×异常传播和界面/任务保持两项：8项。
- 空轴、重复调用、单步/计数保留：3项。
- Machine方法对照：2项；同步等待：2项。合计27项，8条结构化观测。

运行`node scripts/test-emergency-entry.cjs`；核对`node scripts/build-emergency-entry-audit.cjs --check`。源码片段、实际Singleton/JSON程序集、脚手架及报告均绑定SHA256。

轴操作、UI控件、域容器、状态setter和业务任务体为替身，Task与Parallel为真实Framework对象。生产源码未修改，本报告不构成安全认证或物理急停验收。全产品构建、生产并发、原生UI和现场仍待验收，29组仍部分复核。下一步继续追实际硬件输入、报警及停止触发链，并区分软件按钮、驱动停轴与硬件安全回路。
