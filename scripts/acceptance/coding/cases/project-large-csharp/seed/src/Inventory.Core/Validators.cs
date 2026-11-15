namespace Inventory.Core;

public static class Guard
{
    public static string NotBlank(string value, string name)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            throw new ArgumentException($"{name} 不能为空");
        }
        return value;
    }

    public static int NonNegative(int value, string name)
    {
        if (value < 0)
        {
            throw new ArgumentOutOfRangeException(name);
        }
        return value;
    }

    public static decimal NonNegative(decimal value, string name)
    {
        if (value < 0)
        {
            throw new ArgumentOutOfRangeException(name);
        }
        return value;
    }
}
