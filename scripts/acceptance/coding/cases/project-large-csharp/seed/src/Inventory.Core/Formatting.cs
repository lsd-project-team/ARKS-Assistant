using System.Globalization;

namespace Inventory.Core;

public static class Formatting
{
    public static string Money(decimal value)
    {
        return value.ToString("0.##", CultureInfo.InvariantCulture);
    }
}
