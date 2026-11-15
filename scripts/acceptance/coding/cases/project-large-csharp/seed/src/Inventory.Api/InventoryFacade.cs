using Inventory.Core;

namespace Inventory.Api;

public sealed class InventoryFacade
{
    private readonly InventoryService _service;

    public InventoryFacade(string statePath)
    {
        _service = new InventoryService(statePath);
    }

    public InventoryService Service => _service;

    public Item Add(string sku, string name, int quantity, decimal price)
    {
        return _service.Add(sku, name, quantity, price);
    }

    public Item Remove(string sku, int quantity)
    {
        return _service.Remove(sku, quantity);
    }

    public IReadOnlyList<string> LowStock(int threshold)
    {
        return InventoryReports.LowStockLines(_service.LowStock(threshold));
    }

    public string Value()
    {
        return InventoryReports.ValueLine(_service.TotalValue());
    }
}
