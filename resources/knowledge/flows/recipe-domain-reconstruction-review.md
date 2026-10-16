# 配方重建与生产任务入口审计

日期：2026-10-06。状态：`source-confirmed-partial`。对应机器、配方和输送运行进度记录：[配方实时重载](native-recipe-live-reload-progress.json)、[输送环境](native-transport-environment-progress.json)。可复跑脚本：[register-recipe-domain-reconstruction-audit.cjs](../../.archify-work/register-recipe-domain-reconstruction-audit.cjs)，机器可读结果：[recipe-domain-reconstruction-audit.json](recipe-domain-reconstruction-audit.json)。

## 已确认的源码契约

- 配方选择先写入 `MachineConfigContext.RecipeID` 并保存机器配置。已有旧配方时，只有新旧 `RecipeID` 不同才调用 `ReLoadRecipe`；相同 ID 会跳过域重建，随后执行后台界面刷新。没有旧配方时会调用重载。
- `ReLoadRecipe` 先将 `PrInitSuccess` 置为 `false`，清理界面并按固定顺序重建 `ProductConfiguration → TransportProgram → BondProgram → System1Program → WaferSystemProgram → ProcessDomain`。离线模式在这一步后直接把 `PrInitSuccess` 置为 `true`；在线模式还会关闭并重建 VM 方案，加载当前配方的 PR 实体过程，执行 `LoadDispensePr`，成功后才置为 `true`。
- 重载的 `finally` 会隐藏提示并重新启用界面；异常分支会弹出初始化失败提示、记录日志并重新抛出。因此 `PrInitSuccess=false` 与 UI 恢复并不等同于 PR 或生产准备成功。
- `WaferSystemProgram.InitWaferSystemProgram` 会在单例重建前调用 `ClearWaferSubMemory`；是否保留静态适配器由 `IsClearStaticAdapter` 决定，这个初始化步骤有设备/内存副作用。
- `Machine.Start` 在 `PrepareMachineReadyToStart` 通过后设置 Working，依次启动输送、晶圆、可选 System1、动作节点初始化与 Bond、可选刮胶盘和翻转任务，最后检查两个 waffle 真空。输送域自身还会先初始化 TransportModule，在生产模式检查载具、映射物料，必要时启动上下料，再启动 TransportTask。

## 结论和边界

这条记录补上了“配方重载 → 域单例重建 → 生产任务启动”的顺序证据，并明确指出同一 `RecipeID` 的选择不会触发重建。它仍是原始源码的哈希锚定审计；没有调用配方对话框、`ReLoadRecipe`、VM、`Machine.Start`、输送模块、SQL、UI 续接或任何设备接口，也没有修改生产源码。已有运行记录只能证明受控的配方/输送替身和部分原始入口行为，不能推出现场生产成功。

## 源码索引

- `trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs`：配方选择、保存及同 ID 比较。
- `trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs`：域重建、离线/在线 PR 分支。
- `trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs`：生产启动顺序。
- `trunk/AKRS.ZX2200/TransportSystem/Models/TransportDomain.cs`：输送任务前置检查和启动顺序。

