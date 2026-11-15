# 搴撳瓨绠＄悊瑙ｅ喅鏂规

澶氬伐绋?.NET 8 瑙ｅ喅鏂规锛?
- `src/Inventory.Core`锛氬簱瀛樻牳蹇冨簱
- `src/Inventory.Cli`锛氬懡浠よ鍏ュ彛
- `tests/Inventory.SelfTest`锛?2 椤规帶鍒跺彴鑷祴

```
dotnet build
dotnet run --project tests/Inventory.SelfTest/Inventory.SelfTest.csproj
```

CLI 鐢ㄦ硶锛?
```
dotnet run --project src/Inventory.Cli -- <state.json> add <sku> <name> <qty> <price>
dotnet run --project src/Inventory.Cli -- <state.json> remove <sku> <qty>
dotnet run --project src/Inventory.Cli -- <state.json> low <threshold>
dotnet run --project src/Inventory.Cli -- <state.json> value
```
