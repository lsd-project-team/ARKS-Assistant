# ZX2200/TransportSystem：并行搬运与状态记忆

2026-09-28。部分复核；与[传输主流程专题](transport-semantic-revalidation.md)及[载具模型](transport-unit-module-review.md)共同阅读。本轮重点是任务入口、状态清理和存活判定，不代替全部电机/气缸/传感器内部验收。

## 入口与并行任务

Start按LoadConfiguration创建独立Task：联机模式创建送板机到入料段任务；None模式依据点胶载台已有料状态提示人工并可能发来料信号；其他非LoaderBin模式创建皮带到点胶任务；LoaderBin创建料仓到点胶任务。任务分别按null或非Running决定是否创建，不是等待上一个任务结束后才启动下一个。[TransportTask.cs:115](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L115)；[模式分支178–330](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L178)。

联机任务等待PrepareFeeding，再调用TransferAutoLoaderToLoading；NoStart等待、Abort调用Stop、Success清PrepareFeeding。switch未单列Exception结果；外层抛异常只弹窗后离开任务，没有该catch内的Stop。[115–174](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L115)。这是该任务的行为，不泛化为每个搬运任务的错误处理。

点胶1→点胶2即使注释称本次不用，仍会创建任务并调用控制器；Success发TransferToDispense2FinishedSignal。[430–467](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L430)。控制器要求有料，自动模式等待AllowDispense1TransferToDispense2Signal，false返回Abort；手动模式要求Divide且载具在第一段。随后实际调用松夹、挡料气缸、皮带等待到位、夹紧，更新Ready/IsTuInDispense1=false、移动TU坐标、置IsNeedPreDispense=true并返回Success。该方法无本地catch，因此不是空占位；但本轮不证明下层运动函数实际成功。[1186–1259](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1186)。

## 清空不等于物理下料

InitializeTS拒绝Working/Pause状态，人工Yes后执行推杆/安全位/气缸操作，再把五段记忆置NoMaterial、五个TU引用置null并Save，最后要求人工拿走载具。它不自动证明载具已离开机器；无本地catch/finally回滚。[TransportController.cs:159–224](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L159)。

## 尚未完成

- 完成其他搬运任务错误分支及信号生命周期逐项对照；核实存活检查对实际界面和操作判断的影响。
- 下层运动、硬件映射、断电记忆恢复和数据库/文件保存实现待补；静态检查不等于设备运行。

## IsAlive不是完整健康检查

非料仓分支检查5个任务均非null且Running；料仓分支也要求transferLoadBeltToDispense1Task，但Start的LoaderBin分支创建的是transferLoaderBinToDispense1Task，不创建该皮带任务。如果从无历史任务的初始状态进入料仓模式，这个多出的null条件会使IsAlive返回false，即使实际料仓任务已运行。料仓分支同时未包含transferBondToWaitingUnloadTask；联机送板/自动下料任务也不在两个返回式中。[IsAlive897–929](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L897)；[启动207–330](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L207)。

None模式在等待区到出料分支直接return；料仓/皮带分支各自创建对应下料任务。因此不能把某组固定Running条件当作所有模式的完备任务清单。[602–675](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L602)。已定位的界面调用将IsAlive映射为黄色/透明按钮；这里只证明该界面用途，不断言全项目没有其他调用。[FrmSignalDisplay73–78](../../trunk/AKRS.ZX2200/Main/Controls/FrmSignalDisplay.cs#L73)。

## 料仓握手和层号链补充

已补上料/下料任务与输送任务之间的ManualReset/AutoReset交接、层号更新责任、暂停及异常差异。详见[逐步源码复核](loader-unloader-handshake-source-review.md)。本补充没有证明底层运动或实机时序正确。

## 料仓输送控制器内部步骤

已补传感器循环、推杆和皮带包装、局部重试、Ignore返回Success与部分回滚差异。见[控制器逐步复核](bin-transfer-controller-source-review.md)。下一重点是全局停止对这些循环及后台缩回任务的真实作用；实机效果仍待验证。

## 层位移动与保存边界

已核实层位公式、A/B切仓顺序、上下料返回值传播差异，以及配方程序文件与外部Singleton保存边界。见[层位移动与持久化复核](bin-layer-motion-persistence-review.md)。调用返回与层号记忆不能作为物理到位证明；仓库内部加载、硬件契约及恢复实测仍待完成。

## 名称选择与库加载提交

已补[料仓配置选择链](bin-configuration-selection-review.md)：下拉启用过滤、生产Find、关闭提交和设备库/配方文件边界；父界面门控与外部写盘契约仍待验收。
