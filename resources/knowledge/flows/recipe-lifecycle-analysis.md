# ZX2200 配置与配方生命周期

## 实际路径

`ZX2200PathConfig` 把产品、制程、输送、点胶、固晶和晶圆程序映射到当前 `RecipeDirPath` 下的 JSON 文件。`ProductConfiguration` 的默认文件是 `ProductConfiguration.json`；`ProcessDomain` 的默认文件是 `ProcessProgram.json`。对象使用 Singleton 和文件路径保存，不是数据库中的单一事务。

编辑界面 `UcProcessStep` 直接修改 `ProcessDomain.S1SystemProcess` / `S2SystemProcess`，并在排序、复制、删除、自动生成或确认操作后调用 `ProcessDomain.Save()`。产品编辑界面修改 `ProductConfiguration` 的 TransportUnit、Substrate、Module、BondPosition 和 OppositeSex 配置后调用 `Save()`。

`ProcessDomain.IsEnableToWork` / `CheckIsReady` 在生产开始前检查步骤是否存在、序号是否为 0、焊点是否为空、Component/Defect/Epoxy 是否恰好选择一个，以及点胶压力补偿后的范围。启用 Flip 模块时，源码还限制有效组件数量。失败会提示并阻止生产启动。

通过检查后，`S1ActionNodeController.Init` 和 `S2ActionNodeController.Init` 读取启用步骤，按 WorkProcess、WorkProcessModule、位置和步骤顺序生成动作消息；运行时 `GetNextActionNode` 找到第一个未完成消息，具体动作完成后再改变 Finished 状态。配置文件的保存、动作消息的完成和物理动作成功是三个不同阶段。

运行记录由统计服务和各域状态对象写入；`Machine.DataSave` 会集中保存设备参数、晶圆程序、Bond/S1 参数、ProductDomain、ProductConfiguration、Transport 和视觉配置。源码没有显示这些保存操作构成跨文件事务或物理动作回滚。

## 关键证据

- `Infrastructure/Models/Path/ZX2200PathConfig.cs:35–187,313`：程序文件路径。
- `TransportUnitSystem/ProductConfiguration.cs:22–82`：产品配置对象、默认路径和清除 Singleton。
- `Main/Machine/Process/ProcessDomain.cs:22–40,179–277`：制程文件、就绪校验、保存。
- `Main/Machine/Process/UcProcessStep.cs:358–366,665–680,748–768`：步骤编辑、排序、保存和自动生成。
- `Main/Machine/MachineSupport/Machine.cs:352–403`：集中 DataSave。
- `Main/Machine/Process/S1ActionNodeController.cs:168–285,708–815`：S1 动作生成、完成、重做。
- `Main/Machine/Process/S2ActionNodeController.cs:92–234,715–874,1033–1115`：S2 动作生成和状态推进。

对应图：[recipe-lifecycle-workflow.html](recipe-lifecycle-workflow.html)，源文件：[recipe-lifecycle-workflow.archify.json](recipe-lifecycle-workflow.archify.json)。
