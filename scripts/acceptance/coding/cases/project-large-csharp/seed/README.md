# 库存管理解决方案

多工程 .NET 8 解决方案：

- `src/Inventory.Core`：库存核心库
- `src/Inventory.Api`：门面层
- `src/Inventory.Cli`：命令行入口
- `tests/Inventory.SelfTest`：18 项控制台自测

```
dotnet build
dotnet run --project tests/Inventory.SelfTest/Inventory.SelfTest.csproj
```

CLI 用法：

```
dotnet run --project src/Inventory.Cli -- <state.json> add <sku> <name> <qty> <price>
dotnet run --project src/Inventory.Cli -- <state.json> remove <sku> <qty>
dotnet run --project src/Inventory.Cli -- <state.json> low <threshold>
dotnet run --project src/Inventory.Cli -- <state.json> value
```
