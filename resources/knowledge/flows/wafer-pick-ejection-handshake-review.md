# 供晶—取片—顶针：握手和失败传播

更新：2026-09-28。范围是正常自动生产的供晶请求、可取料、翻转中转及取片顶针调用；未执行设备。下列结论只覆盖列出的源码调用点，不代表全部工艺和外部运动库已验证。

## 工作步骤摘要（先分析，后绘图）

1. PickActionNode.PrepareBeforePickAction 在首次启动设置所需芯片名，再 Set IsBondNeedChipSignal；翻转工艺新产品另有再次请求分支。供晶独立空跑也可自行 Set，不能把所有请求都归给固晶线程。
2. WaferSubSystemTask.Dowork 等待需料；按需换料、NextDie 搜晶及真空准备后，先复位需料，再 Set IsWaferAllowPickSignal。换料或搜索失败有重新换料/重新选点分支，最终失败会抛异常。
3. 非翻转取片按载体和相机决定在哪里等供晶信号；翻转工艺由 FlipTask 先消费供晶信号，完成中转后发 IsFlipTableAllowPickSignal，固晶等待后者。不是所有工艺都由 PickActionNode 在同一点消费 IsWaferAllowPickSignal。
4. 实际取片中，只有 PickTypeEnum.CarrierWithWafer 进入 EjectionLift。同步顶直接调用 SynchronousEjection；非同步顶启动 Task 执行 MoveEjectToLiftPosition，然后 ejectTask.Wait。
5. 取片节点检查 WaitStart 后，将后续需料/翻转确认放进不等待完成的 Task.Run，并可立即返回 Success。随后发送是否成功、何时送达，不能由节点 Success 推出。

## 等待与失败分支

|调用点|条件与处理|不能推断的行为|
|---|---|---|
|供晶 Wait 需料返回 false|goto WaitBondNeed，再由外层 WaitStart 决定退出/继续|不是无条件立即 return|
|ChangeTabletAuto=false|先尝试写 AlarmLogEntity 到 DBService，再抛换料失败|数据库实现/写入成功不由调用点证明|
|NextDie=false|IsNeedChange、载体和搜索模式决定 goto NeedChange 或重新选点；未被分支处理则抛搜晶失败|没有本层统一次数上限；不等于每次失败都停止|
|供晶 try 抛异常|先显示错误对话框，返回后调用 Machine.Stop|不是进入 catch 就先 Stop；对话框未返回或再抛异常时，后面的 Stop 尚未执行|
|非翻转 StaticWaffle 且开启换盒避让|循环 Wait(100)；需换盒时首次移避让位、Pause；循环内见 Stop 返回 Abort|100 是实参，但 Wait(int outTime) 实现实际使用 recycleTime；没有整个循环总超时|
|其他非翻转工艺|WaferCamera 或 StaticWaffle 才在该方法等供晶信号；其余相机在别处等待，需分别展开|不能解释为其他相机完全不等待|
|翻转工艺|固晶等 IsFlipTableAllowPickSignal；FlipTask 发它后等 IsBondPickSucceedSignal|不是直接等待供晶信号的同一路径|
|WaitAllowBondPickSignal|最终还执行 WaitStart；false→Abort，调用者返回 Abort|Pause/Stop 检查与事件消费不是原子事务|
|顶针 Task 或同步调用抛异常|Pick 内 catch 提示并 rethrow；外层 DoWork catch 记录提示并返回 Exception，finally 执行状态/WorkStop；若这些处理正常返回，BondTask 的 Exception 分支 Stop|不能说此异常经过 pickRes==Exception 分支缩回顶针；抛异常直接跳过返回码 switch|

无参 Signal.Wait 的公共轮询语义见[料仓专题](bin-failure-handshake-recovery-review.md)；固晶接收 Exception 后的安全位/助焊归位见[固晶交接专题](bond-transport-failure-handshake-review.md)。异常处理和 finally 自身也可能抛出，不承诺所有停止/归位都完成。

## 取片后异步通知

- 非翻转：Task 委托内再判断非补偿模式；SendSignalToWaferTable 在下一芯片与当前同名且非 null 时刷新 Map、更新名称并请求；否则 AccuracyMode=Off 时可更新为下一名称并请求。其他分支不在此发请求，芯片切换还涉及视觉/中转节点，后续追踪。
- 翻转：SendSignalToFlipTable 在焊头离开翻转区域后才 Set IsBondPickSucceedSignal。Pause 时重置计时并 Sleep(20)；超过10秒显示忽略/退出；忽略重置计时，退出 Stop 并 return。区域内 Thread.Yield 后继续。
- 该翻转通知循环没有显式 Stop 检查；故不能把 Machine.Stop 当成此后台通知任务必然立即终止的证明。
- 两种 Task.Run 均未在当前 DoWork 中 await/Wait 或保存 Task 供其处理结果；委托后续抛异常不回到启动它的外层 catch。全局异常观察者是否停止设备尚待追踪。节点返回成功也不证明翻转确认已经发送。

## 顶针信号名称不能代替实际调用证据

当前 trunk C# 具名引用扫描中，IsBondNeedEjectionSignal 只见 SignalPool 属性定义与 SignalList.Add；IsEjectionComplete 只见属性定义。此次实际取片路径是直接调用或 Task.Wait，而非这两个信号构成的请求/完成协议。扫描不覆盖反射、别名、外部 DLL 和其他语言，不能据此宣布信号全系统无用途。

## 源码索引

全部证据 ID 以 waferflow- 开头，登记至[源码阅读器](module-source-explorer.html)。路径相对 trunk/AKRS.ZX2200，Signal 相关另标。

|ID 后缀|文件与行号|
|---|---|
|request|BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs:55–114|
|wafer-wait|WaferSubSystem/Tasks/WaferSubSystemTask.cs:64–83|
|search|WaferSubSystem/Tasks/WaferSubSystemTask.cs:132–256|
|ready|WaferSubSystem/Tasks/WaferSubSystemTask.cs:258–325|
|wafer-catch|WaferSubSystem/Tasks/WaferSubSystemTask.cs:369–385|
|wait-policy|BondSystem/Models/Parameter/System2RunTimeProvider.cs:337–406|
|pick-wait|BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs:204–213|
|notify|BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs:470–514|
|notify-methods|BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs:571–672|
|eject|BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs:715–768|
|pick-eject|BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs:587–696|
|pick-result|BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs:331–351|
|flip-wait|WaferSubSystem/Tasks/FlipTask.cs:92–104|
|flip-ready|WaferSubSystem/Tasks/FlipTask.cs:218–254|
|timed-wait|trunk/AKRS.Galaxy2.Machine/Models/Signal.cs:153–169|
|definitions|trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs:132–157|
|list|trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs:196–216|

## 待闭合项

1. 非 WaferCamera 分支的延迟等待、视觉重取与切换芯片请求，逐入口核对，不能合并成无条件请求下一片。
2. 同步顶/运动控制器内部的到位、停止和超时契约，外部轴库只凭调用点无法证明。
3. 通知任务重叠、共享 component/nextComponentName 变化、Stop 后继续发信号的可达性，需要逐写入点与并发日志验证。
4. 数据库失败、提示未返回、异步任务异常观察和设备故障注入尚未验收。

## 图示与交付

[Archify交互时序图](wafer-pick-handshake-sequence.html) · [规范](wafer-pick-handshake-sequence.archify.json) · [交付收据](wafer-pick-handshake-sequence.review.json)。图仅示首次请求、非翻转、晶圆相机与Wafer取片条件路径；异步通知可能早于或晚于Success，纵向位置不是强制调度保证。

补充入口证据 waferflow-entry：PickActionNode.cs:156–182，DoWork调用PrepareBeforePickAction。
