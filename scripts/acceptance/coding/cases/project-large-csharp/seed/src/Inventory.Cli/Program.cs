using System.Globalization;
using Inventory.Api;
using Inventory.Core;

if (args.Length < 2)
{
    Usage();
    return 2;
}

try
{
    var facade = new InventoryFacade(args[0]);
    switch (args[1].ToLowerInvariant())
    {
        case "add" when args.Length == 6:
        {
            var item = facade.Add(args[2], args[3],
                int.Parse(args[4], CultureInfo.InvariantCulture),
                decimal.Parse(args[5], CultureInfo.InvariantCulture));
            Console.WriteLine($"ADDED SKU={item.Sku} QTY={item.Quantity} PRICE={Formatting.Money(item.Price)}");
            return 0;
        }
        case "remove" when args.Length == 4:
        {
            var item = facade.Remove(args[2], int.Parse(args[3], CultureInfo.InvariantCulture));
            Console.WriteLine($"REMOVED SKU={item.Sku} QTY={item.Quantity}");
            return 0;
        }
        case "low" when args.Length == 3:
        {
            var lines = facade.LowStock(int.Parse(args[2], CultureInfo.InvariantCulture));
            if (lines.Count == 0)
            {
                Console.WriteLine("LOW none");
            }
            else
            {
                foreach (var line in lines)
                {
                    Console.WriteLine(line);
                }
            }
            return 0;
        }
        case "value" when args.Length == 2:
        {
            Console.WriteLine(facade.Value());
            return 0;
        }
        default:
            Usage();
            return 2;
    }
}
catch (Exception error) when (error is ArgumentException or InvalidOperationException or KeyNotFoundException or FormatException)
{
    Console.Error.WriteLine($"ERROR: {error.Message}");
    return 2;
}

static void Usage()
{
    Console.Error.WriteLine("用法: Inventory.Cli <state.json> add <sku> <name> <qty> <price>");
    Console.Error.WriteLine("      Inventory.Cli <state.json> remove <sku> <qty>");
    Console.Error.WriteLine("      Inventory.Cli <state.json> low <threshold>");
    Console.Error.WriteLine("      Inventory.Cli <state.json> value");
}
