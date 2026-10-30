# 失效料仓名称：查找、解引用和任务异常边界

更新：2026-09-28。限定上下料自动任务进入当前层移动、有料盒分支；不宣称全工程最早的配置访问点。

## 可确认的执行链

1. LoaderBinProgram.LoaderBin / UnLoaderBinProgram.UnloaderBin 每次属性访问都用当前名称调用相应Repository.GetLoaderBin；后者委托BaseSettingRepository.Find。Find按Name相等查找，没有缺失后的默认对象或配置补齐。未匹配时返回null。空名称是否匹配取决于列表内容，不能把空字符串一概当作未匹配。
2. 上下料Start先检查Enable、DryCycle，再按任务null或非Running创建Task.Run。委托内部while(IsWorking())，首次进入调用MoveToCurrentPlaceLayer。
3. 此方法先检查IsCurrentBinOnTable；该条件为true后立即调用IsOutOfTabletLimit。上料读取LoaderBin.LayerNum，下料读取UnloaderBin.LayerNum；没有?.或null判断。前置对象/仓库均正常但名称未匹配时，该路径会因null的LayerNum访问抛异常。
4. 因该层数判断在当前分支MoveToCurrentBin及MoveToTabletLevel之前，空引用打断这些后续调用；不能推断此前整个系统没有其他动作。料盒不存在分支的人工处理是另一条路径，本专题不把它折叠成此异常。
5. 异常沿当前调用返回到各自Task.Run委托内try/catch；catch仅显示“上料仓上料线程异常”或“下料仓下料线程异常”。无显式Machine.Stop、重新启动或恢复信号。提示正常返回后委托结束；若提示本身抛异常则另当别论。
6. 首次调用失败会跳过紧随其后的LoaderAllowPushSignal.Set或UnloaderAllowPushSignal.Set和firstStart=false。因此本次启动不会通过该语句发出允许推料信号；不据此断言信号在所有线程中始终未置位。

## 不可混淆的两类失败

|失败形式|当前任务处理|是否是相同传播路径|
|---|---|---|
|控制器正常返回ExcuteResult.Abort|switch调用Machine.Stop然后return|显式停止路径|
|控制器抛异常，例如此处null.LayerNum|委托内部catch显示错误，正常返回后退出|不是Abort分支；不能视作自动全机Stop|

Start不等待工作委托结束，ConfigureAwait(false)调用后也未await；不能把委托内捕获的异常当作TransportDomain.StartTask同步catch一定会捕获的异常。整个设备接下来是等待、退出还是继续，要结合其他任务、信号等待与并发Stop来源判断。

## 工程交接待办

- [ ] 在隔离环境测试已删除名称、名称不匹配、列表为空、料盒有/无输入组合。
- [ ] 关联推料信号所有发送者/消费者及等待超时，判定故障后的全机状态。
- [ ] 独立核对仓库加载抛异常、TransportProgram为空等不同根因。
- [ ] 是否新增启动前配置校验属于后续修复设计；本轮仅分析，没有修改业务代码。

## 源码证据

- [binmissing-loader-program 12–35](../../trunk/AKRS.ZX2200/TransportSystem/Models/Programs/LoaderBinProgram.cs#L12) · [查看源码快照](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binmissing-loader-program)
- [binmissing-unloader-program 18–41](../../trunk/AKRS.ZX2200/TransportSystem/Models/Programs/UnLoaderBinProgram.cs#L18) · [查看源码快照](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binmissing-unloader-program)
- [binmissing-loader-repository 45–48](../../trunk/AKRS.ZX2200/TransportSystem/Models/DatasetModels/StockBin/LoaderBinRepository.cs#L45) · [查看源码快照](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binmissing-loader-repository)
- [binmissing-unloader-repository 45–48](../../trunk/AKRS.ZX2200/TransportSystem/Models/DatasetModels/StockBin/UnLoaderBinRepository.cs#L45) · [查看源码快照](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binmissing-unloader-repository)
- [binmissing-find 100–105](../../trunk/AKRS.ZX2200/Infrastructure/Models/BaseModels/BaseSettingRepository.cs#L100) · [查看源码快照](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binmissing-find)
- [binmissing-loader-limit 348–363](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/LoaderBinController.cs#L348) · [查看源码快照](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binmissing-loader-limit)
- [binmissing-unloader-limit 294–298](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/UnLoaderBinController.cs#L294) · [查看源码快照](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binmissing-unloader-limit)
- [binmissing-loader-current 449–462](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/LoaderBinController.cs#L449) · [查看源码快照](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binmissing-loader-current)
- [binmissing-unloader-current 402–415](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/UnLoaderBinController.cs#L402) · [查看源码快照](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binmissing-unloader-current)
- [binmissing-loader-worker 49–130](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/LoaderTask.cs#L49) · [查看源码快照](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binmissing-loader-worker)
- [binmissing-unloader-worker 41–128](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/UnloaderTask.cs#L41) · [查看源码快照](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=binmissing-unloader-worker)
