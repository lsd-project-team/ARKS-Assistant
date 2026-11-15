using System.Text.Json;

namespace Inventory.Core;

public sealed class InventoryService
{
    private readonly string _path;
    private readonly List<Item> _items;

    public InventoryService(string path)
    {
        _path = path;
        _items = File.Exists(path)
            ? JsonSerializer.Deserialize<List<Item>>(File.ReadAllText(path)) ?? new List<Item>()
            : new List<Item>();
    }

    public IReadOnlyList<Item> Items => _items;

    public Item Add(string sku, string name, int quantity, decimal price)
    {
        if (string.IsNullOrWhiteSpace(sku)) throw new ArgumentException("SKU 不能为空");
        if (string.IsNullOrWhiteSpace(name)) throw new ArgumentException("名称不能为空");
        if (quantity < 0) throw new ArgumentOutOfRangeException(nameof(quantity));
        if (price < 0) throw new ArgumentOutOfRangeException(nameof(price));
        if (_items.Any(item => item.Sku == sku)) throw new InvalidOperationException("SKU 已存在");
        var item = new Item { Sku = sku, Name = name, Quantity = quantity, Price = price };
        _items.Add(item);
        Save();
        return item;
    }

    public Item Remove(string sku, int quantity)
    {
        if (quantity <= 0) throw new ArgumentOutOfRangeException(nameof(quantity));
        var item = Find(sku);
        if (item.Quantity < quantity) throw new InvalidOperationException("库存不足");
        item.Quantity -= quantity;
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
        if (threshold < 0) throw new ArgumentOutOfRangeException(nameof(threshold));
        return _items.Where(item => item.Quantity <= threshold).OrderBy(item => item.Sku).ToList();
    }

    public decimal TotalValue()
    {
        return _items.Sum(item => item.Quantity * item.Price);
    }

    private void Save()
    {
        var directory = Path.GetDirectoryName(Path.GetFullPath(_path));
        if (!string.IsNullOrEmpty(directory)) Directory.CreateDirectory(directory);
        File.WriteAllText(_path, JsonSerializer.Serialize(_items, new JsonSerializerOptions { WriteIndented = true }));
    }
}
