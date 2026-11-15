using Inventory.Core;

var failures = 0;
var passes = 0;

void Check(string name, Action action)
{
    try
    {
        action();
        passes++;
        Console.WriteLine($"[PASS] {name}");
    }
    catch (Exception error)
    {
        failures++;
        Console.WriteLine($"[FAIL] {name}: {error.Message}");
    }
}

string TempState() => Path.Combine(Path.GetTempPath(), $"inventory-selftest-{Guid.NewGuid():N}.json");

Check("添加商品", () =>
{
    var service = new InventoryService(TempState());
    var item = service.Add("A", "Widget", 10, 2.5m);
    if (item.Quantity != 10 || item.Price != 2.5m) throw new Exception("字段不正确");
});

Check("重复 SKU 拒绝", () =>
{
    var service = new InventoryService(TempState());
    service.Add("A", "Widget", 10, 2.5m);
    try { service.Add("A", "Other", 1, 1m); }
    catch (InvalidOperationException) { return; }
    throw new Exception("应拒绝重复 SKU");
});

Check("负数量拒绝", () =>
{
    var service = new InventoryService(TempState());
    try { service.Add("A", "Widget", -1, 1m); }
    catch (ArgumentOutOfRangeException) { return; }
    throw new Exception("应拒绝负数量");
});

Check("出库扣减", () =>
{
    var service = new InventoryService(TempState());
    service.Add("A", "Widget", 10, 2m);
    var item = service.Remove("A", 3);
    if (item.Quantity != 7) throw new Exception($"期望 7，实际 {item.Quantity}");
});

Check("库存不足拒绝", () =>
{
    var service = new InventoryService(TempState());
    service.Add("A", "Widget", 1, 1m);
    try { service.Remove("A", 2); }
    catch (InvalidOperationException) { return; }
    throw new Exception("应拒绝库存不足");
});

Check("找不到 SKU", () =>
{
    var service = new InventoryService(TempState());
    try { service.Remove("NOPE", 1); }
    catch (KeyNotFoundException) { return; }
    throw new Exception("应抛出 KeyNotFound");
});

Check("低库存筛选", () =>
{
    var service = new InventoryService(TempState());
    service.Add("A", "Widget", 2, 1m);
    service.Add("B", "Bolt", 10, 1m);
    var low = service.LowStock(3);
    if (low.Count != 1 || low[0].Sku != "A") throw new Exception("低库存结果错误");
});

Check("低库存为空", () =>
{
    var service = new InventoryService(TempState());
    service.Add("A", "Widget", 10, 1m);
    if (service.LowStock(3).Count != 0) throw new Exception("应为空");
});

Check("总值", () =>
{
    var service = new InventoryService(TempState());
    service.Add("A", "Widget", 10, 2.5m);
    service.Add("B", "Bolt", 2, 5m);
    if (service.TotalValue() != 35m) throw new Exception($"期望 35，实际 {service.TotalValue()}");
});

Check("持久化重载", () =>
{
    var path = TempState();
    new InventoryService(path).Add("A", "Widget", 10, 2.5m);
    var reloaded = new InventoryService(path);
    if (reloaded.Items.Count != 1 || reloaded.Items[0].Sku != "A") throw new Exception("重载失败");
});

Check("负阈值拒绝", () =>
{
    var service = new InventoryService(TempState());
    try { service.LowStock(-1); }
    catch (ArgumentOutOfRangeException) { return; }
    throw new Exception("应拒绝负阈值");
});

Check("空 SKU 拒绝", () =>
{
    var service = new InventoryService(TempState());
    try { service.Add(" ", "Widget", 1, 1m); }
    catch (ArgumentException) { return; }
    throw new Exception("应拒绝空 SKU");
});

ReportChecks.Run(Check);
FacadeChecks.Run(Check);

Console.WriteLine($"结果: {passes} PASS, {failures} FAIL");
return failures == 0 ? 0 : 1;
