# Main 程式节点初始化与 Singleton 重置复核

本轮沿 `UcMainSystem.Production.cs` 的 `InitProgramNodes` 继续展开六个初始化方法，并核对每个对象的文件路径声明。入口实际顺序是：`ProductConfiguration` → `TransportProgram` → `BondProgram` → `System1Program` → `WaferSystemProgram` → `ProcessDomain`。

六个方法都重新设置继承的 `Singleton<T>.FilePath`（Product 使用 `Path.Combine(PathConfig.RecipeDirPath, ...)`），随后把继承的 `instance` 设为 `null`，因此入口每次重载都会丢弃当前单例引用，之后的 `GetInstance()` 才会按各自路径重新获取对象。`WaferSystemProgram.InitWaferSystemProgram` 还有前置副作用：根据 `MachineSoftwareConfiguration.IsClearStaticAdapter` 调用 `ClearWaferSubMemory()` 或 `ClearWaferSubMemory(true, false)`；清理完成后才重置单例。它捕获异常后只用原消息创建新异常，原始堆栈不会保留。

路径对应关系为：

- `ProductConfiguration.json`
- `TransportSystemProgram.json`
- `BondProgram.json`
- `DispenseProgram.json`
- `WaferSystemProgram.json`
- `ProcessProgram.json`

对原工程已有 `AKRS.Galaxy2.Infrastructure.dll` 做只读元数据检查还确认：`Singleton<T>` 是抽象泛型类型，`T` 要求引用类型和无参构造，包含静态 `locker`、`instance`、`FilePath` 字段及静态 `GetInstance()`、`Load()` 方法。随后用隔离测试类型调用真实 `GetInstance/Load`：合法 JSON 会被读取，重复获取复用同一引用，`Load()` 会替换引用；缺失或损坏 JSON 会返回默认构造对象，损坏输入同时记录 Newtonsoft 解析错误。详见 [Singleton 实际读盘复核](singleton-load-probe-review.md)。真实生产配方、SDK 或运行中重载仍未执行，所以 Main 模块仍处于部分复核。

- 机器审计：[main-init-program-nodes-audit.json](main-init-program-nodes-audit.json)
- 入口源码：[UcMainSystem.Production.cs](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L124)
- 路径源码：[ZX2200PathConfig.cs](../../trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs#L69)
