using Inventory.Core;

internal static class ReportChecks
{
    public static void Run(Action<string, Action> check)
    {
        check("报表低库存行", () =>
        {
            var lines = InventoryReports.LowStockLines(new[] { new Item { Sku = "A", Quantity = 2 } });
            if (lines.Count != 1 || lines[0] != "LOW SKU=A QTY=2") throw new Exception("低库存行错误");
        });

        check("报表总值行", () =>
        {
            if (InventoryReports.ValueLine(12.5m) != "VALUE=12.5") throw new Exception("总值行错误");
        });

        check("金额格式化", () =>
        {
            if (Formatting.Money(0m) != "0") throw new Exception("金额格式化错误");
        });

        check("事件工厂", () =>
        {
            var created = InventoryEvents.Created("A", 3);
            if (created.Kind != "created" || created.Sku != "A" || created.Quantity != 3)
            {
                throw new Exception("事件字段错误");
            }
        });
    }
}
