# 供晶启动初始化失败、残留状态与再次启动

后续集成（2026-09-30）：[原范围、完整初始化与真实供晶启动](wafer-range-init-review.md)的105项检查已将原Start、原初始化/位置/消费者和原Stop串联，验证失败后再启动及同步串行UI替身下的双Start竞争。实际MainForm/上层生产入口、SDK和设备仍未验收。本文原9项或47项隔离测试范围不扩大。


本专题补齐启动调度报告中 Block.StartInit 的局部缺口。源码静态复核及9项原方法隔离检查，不是WinForms、真实工作线程或设备验收。

## 入口与异常边界

[WaferSubSystemTask.Start](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1373)只排除Running；null或其他状态进入初始化。先StartInit，后清PreviousNeedChipName、设置Working、提交并赋值新Task。初始化同步异常跳过后三项，旧Task引用和PreviousNeedChipName在此方法保持原值。catch只弹窗，不调用Stop、不重抛原异常；弹窗自身若抛异常则向外传播。Running分支只设置Working。

因此，在[Machine.Start](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L261)已经设置Working并启动输送之后，供晶初始化失败而弹窗正常返回，外层仍可继续点胶、固晶等后续调用。不能把供晶Start的正常返回当作供晶线程已启动。此组合为静态调用链结论，9项测试不执行供晶任务入口。

[MainForm委托注册及PostAction](../../trunk/AKRS.ZX2200/Main/Controls/MainForm.cs#L50)将SendUiAction绑定到Invoke；这里是同步UI调用，不是BeginInvoke。异常具体包装、窗口句柄与多订阅行为未进行真实UI验证。

## 已经改变的状态与未回滚的引用

[StartInit](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L1193)先写isFirstSearch=true、countBlankNum=0、isNeedAheadChangeTablet=false，再依次调用晶圆图、华夫图、单颗和九点初始化。任一同步异常保留此前修改，后面的初始化不执行。

[晶圆图初始化](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L1551)先把新对象赋给WaferMapII，再CreateForm、Show、Hide；后三步抛异常时引用已非null，本方法没有Dispose或清空引用。再次StartInit仅检查null，因而跳过这组三步。不能认定非null对象已完成初始化。构造器本身失败则赋值尚未完成，需与后续方法失败区分。

[华夫图初始化](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L1570)同样先赋值再Show/Hide；Show/Hide失败后的重试跳过既有引用。本地无清理不等于已证明外部实现泄漏了硬件资源。

[单颗与九点初始化](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L1587)：单颗方法为空；九点先重置方向、行号和四处Exist，再调用ResetNineDiesData。[九点数据重置前段](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchNine.cs#L537)先清九颗Exist，再读实际位置和行列间距生成坐标；这些后续读取失败不能回滚已清标志。本段只静态复核，坐标/硬件读取未在本测试执行。

另一个[换片成功入口](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L488)也调用StartInit；不能直接套用Start的catch边界，换片外层失败传播仍须单独闭合。

## 验证与剩余清单

运行 `node scripts/test-wafer-start-init.cjs`：从源码提取StartInit及两种图初始化原方法，UI委托同步执行，窗口依赖及单颗/九点子方法使用替身。9项检查通过：正常顺序、缺失UI委托，以及CreateForm、两种Show/Hide、单颗和九点调用处7类异常。每类异常检查先前标志和窗口引用保留、后续调用截断，并再次调用核对跳过非null窗口初始化。单颗异常是调用方防护场景，不代表当前空实现会自行抛异常。

- 已完成：启动初始化的本地顺序、异常捕获、引用残留和重试跳过行为。
- 未完成：真实窗口构造/Invoke异常、关闭后对象复用、实际窗口资源释放。
- 未完成：WaitingToRun重复启动、Start/Stop并发及工作线程故障通知与退出。
- 未完成：换片入口异常传播、九点坐标依赖、真实配置和设备验收。

模块仍为29组部分复核、0组完整验收。证据见[源码快照](wafer-start-init-evidence.json)，接入统一模块阅读器。
