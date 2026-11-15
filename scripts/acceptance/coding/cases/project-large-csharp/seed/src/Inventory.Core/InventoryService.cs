namespace Inventory.Core;

public sealed class InventoryService
{
    private readonly string _path;
    private readonly List<Item> _items;
    private readonly List<InventoryEvent> _events = new();

    public InventoryService(string path)
    {
        _path = path;
        _items = JsonStore.Load<Item>(path);
    }

    public IReadOnlyList<Item> Items => _items;

    public IReadOnlyList<InventoryEvent> Events => _events;

    public Item Add(string sku, string name, int quantity, decimal price)
    {
        Guard.NotBlank(sku, "SKU");
        Guard.NotBlank(name, "名称");
        Guard.NonNegative(quantity, nameof(quantity));
        Guard.NonNegative(price, nameof(price));
        if (_items.Any(item => item.Sku == sku))
        {
            throw new InvalidOperationException("SKU 已存在");
        }
        var item = new Item { Sku = sku, Name = name, Quantity = quantity, Price = price };
        _items.Add(item);
        _events.Add(InventoryEvents.Created(sku, quantity));
        Save();
        return item;
    }

    public Item Remove(string sku, int quantity)
    {
        if (quantity <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(quantity));
        }
        var item = Find(sku);
        if (item.Quantity < quantity)
        {
            throw new InvalidOperationException("库存不足");
        }
        item.Quantity -= quantity;
        _events.Add(InventoryEvents.Removed(sku, quantity));
        Save();
        return item;
    }

    public Item Find(string sku)
    {
        return _items.FirstOrDefault(item => item.Sku == sku)
            ?? throw new KeyNotFoundException($"找不到 SKU: {sku}");
    }

    public IReadOnlyList<Item> LowStock(int threshold)
    {
        if (threshold < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(threshold));
        }
        return _items.Where(item => item.Quantity <= threshold).OrderBy(item => item.Sku).ToList();
    }

    public decimal TotalValue()
    {
        return _items.Sum(item => item.Quantity * item.Price);
    }

    private void Save()
    {
        JsonStore.Save(_path, _items);
    }
}
