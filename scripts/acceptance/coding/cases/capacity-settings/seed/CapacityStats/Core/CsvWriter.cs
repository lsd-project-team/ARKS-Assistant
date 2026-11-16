using System.Globalization;
using System.Text;

namespace CapacityStats;

/// <summary>
/// CSV 写出：表头 + 数据行，UTF-8 无 BOM，LF 换行；含逗号/引号/换行的字段按 RFC 4180 加引号转义。
/// </summary>
public static class CsvWriter
{
    public static string Build(IReadOnlyList<string> header, IEnumerable<IReadOnlyList<string>> rows)
    {
        var sb = new StringBuilder();
        sb.Append(JoinRow(header)).Append('\n');
        foreach (var row in rows)
        {
            sb.Append(JoinRow(row)).Append('\n');
        }

        return sb.ToString();
    }

    public static string JoinRow(IReadOnlyList<string> fields)
    {
        var parts = new string[fields.Count];
        for (var i = 0; i < fields.Count; i++)
        {
            parts[i] = Escape(fields[i] ?? string.Empty);
        }

        return string.Join(",", parts);
    }

    public static string Escape(string value)
    {
        var needsQuote = value.Contains(',', StringComparison.Ordinal)
            || value.Contains('"', StringComparison.Ordinal)
            || value.Contains('\n', StringComparison.Ordinal)
            || value.Contains('\r', StringComparison.Ordinal);
        if (!needsQuote)
        {
            return value;
        }

        return "\"" + value.Replace("\"", "\"\"", StringComparison.Ordinal) + "\"";
    }

    /// <summary>把内容写入文件（目录不存在时自动创建）。</summary>
    public static void WriteFile(string path, string content)
    {
        var dir = Path.GetDirectoryName(Path.GetFullPath(path));
        if (!string.IsNullOrEmpty(dir))
        {
            Directory.CreateDirectory(dir);
        }

        File.WriteAllText(path, content, new UTF8Encoding(encoderShouldEmitUTF8Identifier: false));
    }

    /// <summary>把数值格式化为不带千分位的整数文本。</summary>
    public static string Number(long value) => value.ToString(CultureInfo.InvariantCulture);
}
