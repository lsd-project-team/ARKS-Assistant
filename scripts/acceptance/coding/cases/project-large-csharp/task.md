# 任务：大型 C# 解决方案增加补货功能

工作区是一个多工程 .NET 8 解决方案：

- `src/Inventory.Core`：库存核心库（添加/出库/低库存/总值/JSON 持久化）；
- `src/Inventory.Api`：门面层 `InventoryFacade`；
- `src/Inventory.Cli`：命令行入口（通过 Facade 调用）；
- `tests/Inventory.SelfTest`：18 项控制台自测，目前全部通过；
- `Inventory.sln` 引用以上工程。

要求（不得修改 `tests/Inventory.SelfTest` 下的自测文件）：

1. `InventoryService` 增加 `Restock(string sku, int quantity)`：
   - `quantity <= 0` 抛 `ArgumentOutOfRangeException`；
   - SKU 不存在抛 `KeyNotFoundException`；
   - 增加库存并持久化，返回更新后的 `Item`。
2. `InventoryFacade` 增加 `Restock`，保持门面层与 Core 一致。
3. CLI 增加命令：`<state.json> restock <sku> <qty>`，成功输出
   `RESTOCKED SKU=<sku> QTY=<新数量>`；错误走 stderr 并以退出码 2 结束。
4. 保持现有 add/remove/low/value 行为与输出格式；README 补充 restock 用法；不要留 TODO/占位。

完成前运行：

```
dotnet build
dotnet run --project tests/Inventory.SelfTest/Inventory.SelfTest.csproj
```

要求构建 0 错误 0 警告，自测 18 项全部 PASS。
