# 浠诲姟锛氬ぇ鍨?C# 瑙ｅ喅鏂规澧炲姞琛ヨ揣鍔熻兘

宸ヤ綔鍖烘槸涓€涓宸ョ▼ .NET 8 瑙ｅ喅鏂规锛?
- `src/Inventory.Core`锛氬簱瀛樻牳蹇冨簱锛堟坊鍔?鍑哄簱/浣庡簱瀛?鎬诲€?JSON 鎸佷箙鍖栵級锛?- `src/Inventory.Cli`锛氬懡浠よ鍏ュ彛锛?- `tests/Inventory.SelfTest`锛?6 椤规帶鍒跺彴鑷祴锛岀洰鍓嶅叏閮ㄩ€氳繃锛?- `Inventory.sln` 寮曠敤浠ヤ笂宸ョ▼銆?
瑕佹眰锛堜笉寰椾慨鏀?`tests/Inventory.SelfTest/Program.cs`锛夛細

1. `InventoryService` 澧炲姞 `Restock(string sku, int quantity)`锛?   - `quantity <= 0` 鎶?`ArgumentOutOfRangeException`锛?   - SKU 涓嶅瓨鍦ㄦ姏 `KeyNotFoundException`锛?   - 澧炲姞搴撳瓨骞舵寔涔呭寲锛岃繑鍥炴洿鏂板悗鐨?`Item`銆?2. CLI 澧炲姞鍛戒护锛歚<state.json> restock <sku> <qty>`锛屾垚鍔熻緭鍑?   `RESTOCKED SKU=<sku> QTY=<鏂版暟閲?`锛涢敊璇蛋 stderr 骞朵互閫€鍑虹爜 2 缁撴潫銆?3. 淇濇寔鐜版湁 add/remove/low/value 琛屼负涓庤緭鍑烘牸寮忥紱README 琛ュ厖 restock 鐢ㄦ硶锛涗笉瑕佺暀 TODO/鍗犱綅銆?
瀹屾垚鍓嶈繍琛岋細

```
dotnet build
dotnet run --project tests/Inventory.SelfTest/Inventory.SelfTest.csproj
```

瑕佹眰鏋勫缓 0 閿欒 0 璀﹀憡锛岃嚜娴?12 椤瑰叏閮?PASS銆?