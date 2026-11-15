using System.Text.Json;

namespace Inventory.Core;

public static class JsonStore
{
    private static readonly JsonSerializerOptions Options = new() { WriteIndented = true };

    public static List<T> Load<T>(string path)
    {
        if (!File.Exists(path))
        {
            return new List<T>();
        }
        return JsonSerializer.Deserialize<List<T>>(File.ReadAllText(path)) ?? new List<T>();
    }

    public static void Save<T>(string path, IEnumerable<T> items)
    {
        var directory = Path.GetDirectoryName(Path.GetFullPath(path));
        if (!string.IsNullOrEmpty(directory))
        {
            Directory.CreateDirectory(directory);
        }
        File.WriteAllText(path, JsonSerializer.Serialize(items, Options));
    }
}
