# 自动换片重试与停止观察点

本轮提取完整[ChangeTabletAuto 1105–1366](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1105)，不改写方法，完成16项受控检查。状态模型、料层选择、初始化子方法、UI和硬件控制使用替身；测试证明调用顺序与分支行为，不证明物理动作发生、实际窗口生命周期或完整停止安全性。

## 已验证的三种重试

|分支|初始化false的目的地|受控Stop状态下观察|
|---|---|---|
|有料库，公共Operation|再次调用ChangeSucceedOperation，不重新选层或开向导|第1次初始化把状态变Stop，仍继续到第3次返回true|
|有料库，静态适配器无匹配槽|RetryChangeStaticAdapter，重新打开静态向导|每次false后重开向导，3次初始化对应3次向导|
|无料库，已有匹配静态槽|先直接初始化；false回ChangeMap|3次初始化对应2次向导|

对以上每个分支还验证：进入方法前已为Stop仍执行初始化；初始化抛异常立即逸出，不进入false的goto重试。静态向导Retry后Abort返回false、不会调用初始化。测试中的状态改变只写替身状态，不执行完整Machine.Stop；方法没有直接读取这一状态，结论不能扩展为所有下层动作均无停止保护。

初始化替身按false、false、true返回，使循环有确定终点；没有用测试次数声称生产循环有限。源方法的这些goto没有本地总次数、退避或Stop检查，子方法仍可能通过返回、异常、交互或其内部检查结束它。

## 其他准备路径

另外5项检查覆盖：

1. 有料库的晶圆路径在入口状态Stop时仍调用关闭真空、归还料片信息及初始化替身。
2. 找不到料层时Cancel抛异常，未调用放料/初始化；此前的关闭真空等前缀不能当作回滚。
3. 找不到料层时OK调用放料、料库标记位及提示后重新选层。
4. 当前层传感器false时写NullTablet、层号0并保存，再选层、放旧料和取新料；本地状态修改保留。
5. 无料库有效晶圆路径在Stop状态仍调用夹持气缸和扩膜准备替身，再初始化。

没有测试真实气缸、轴、真空、传感器反馈，也不把控制器方法调用当作动作成功。外围设备保护继续见[料库动作报告](magazine-transfer-review.md)。

## 外层停止检查在哪里

[Dowork外层](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L64)先经过Signal.WaitStart和需料等待，再调用换片；它不能自动中断已经进入的ChangeTabletAuto。异常如何到达弹窗、Stop及日志队列，复用[失败传播验证](state-queue-failure-review.md)。

[Signal.WaitStart](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L202)首次Stop返回false；Pause循环内检查Stop，离开Pause后返回true。这里是一个检查点，没有为之后全部换片操作持有互斥或取消凭据。本轮没有对所有调度交错穷举，也没有把此检查点等同于线程退出。

## 实际窗口构造不能用空壳替代解释

[FrmChangeTabletTeach构造函数](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L112)在非料库模式深拷贝当前料片、绑定数据，并调用InitControl。外层没有显式ShowDialog，不等于没有显示窗口。

[InitControl](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L134)先报警和询问，再请求顶针返回、扩膜下降、夹持气缸、夹具安全位和手动换料位；取走料片确认后先写NullTablet并保存，随后循环提示放新料，传感器满足才ShowDialog。多个Cancel出口设置Abort并Close；夹持气缸询问的Cancel只跳过下降，不是整个换片取消。

该方法catch在IsWorking时重新抛出仅含原Message的新Exception；非Working时提示错误，未在这个catch显式设置Abort。因此停止状态可能影响窗口内部异常传播；不能只从外层不检查Stop推断完整设备路径。此构造/InitControl段本轮仅静态复核，测试的窗口是返回脚本结果的替身，未验证WinForms、深拷贝或上述真实硬件调用。

## 验证与清单更新

`node scripts/test-wafer-change-retry.cjs` 输出16条检查、完整方法原文哈希及测试夹具哈希。编译运行使用内置PowerShell的.NET，未改生产源码。源码证据见[5段快照](wafer-change-retry-evidence.json)。

- 已完成：完整自动换片外层三种重试目的地、初始化false/异常差异，以及选层/传感器若干失败前缀的隔离验证。
- 已完成：定位外层WaitStart与换片内部无直接Stop检查的边界；补回构造函数内部ShowDialog和异常分支的静态解释。
- 未完成：窗口InitControl及完成按钮的隔离验证、真实配置/深拷贝、设备SDK等待取消、所有换片动作的实际停止效果。
- 后续需将新结论合并到对应换片图和语义台账并做浏览器复核；本轮是源码/控制流验证，没有重新验收图形或整机。
