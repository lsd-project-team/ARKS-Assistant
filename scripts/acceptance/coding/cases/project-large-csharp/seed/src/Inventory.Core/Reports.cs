namespace Inventory.Core;

public static class InventoryReports
{
    public static IReadOnlyList<string> LowStockLines(IEnumerable<Item> items)
    {
        return items.Select(item => $"LOW SKU={item.Sku} QTY={item.Quantity}").ToList();
    }

    public static string ValueLine(decimal value)
    {
        return $"VALUE={Formatting.Money(value)}";
    }
}
