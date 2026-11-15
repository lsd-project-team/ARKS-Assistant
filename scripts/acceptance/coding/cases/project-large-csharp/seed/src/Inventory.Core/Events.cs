namespace Inventory.Core;

public sealed record InventoryEvent(string Kind, string Sku, int Quantity, DateTime At);

public static class InventoryEvents
{
    public static InventoryEvent Created(string sku, int quantity)
    {
        return new InventoryEvent("created", sku, quantity, DateTime.UtcNow);
    }

    public static InventoryEvent Removed(string sku, int quantity)
    {
        return new InventoryEvent("removed", sku, quantity, DateTime.UtcNow);
    }
}
