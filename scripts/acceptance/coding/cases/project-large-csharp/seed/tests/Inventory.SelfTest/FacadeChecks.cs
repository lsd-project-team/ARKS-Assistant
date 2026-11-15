using Inventory.Api;

internal static class FacadeChecks
{
    public static void Run(Action<string, Action> check)
    {
        check("Facade 低库存", () =>
        {
            var path = Path.Combine(Path.GetTempPath(), $"facade-{Guid.NewGuid():N}.json");
            var facade = new InventoryFacade(path);
            facade.Add("A", "Widget", 2, 1m);
            var lines = facade.LowStock(3);
            if (lines.Count != 1 || lines[0] != "LOW SKU=A QTY=2") throw new Exception("Facade 低库存错误");
        });

        check("Facade 总值", () =>
        {
            var path = Path.Combine(Path.GetTempPath(), $"facade-{Guid.NewGuid():N}.json");
            var facade = new InventoryFacade(path);
            facade.Add("A", "Widget", 2, 2.5m);
            if (facade.Value() != "VALUE=5") throw new Exception("Facade 总值错误");
        });
    }
}
