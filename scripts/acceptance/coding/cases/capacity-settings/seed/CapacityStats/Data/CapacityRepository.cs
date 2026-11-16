using System.Globalization;
using Microsoft.Data.Sqlite;

namespace CapacityStats;

/// <summary>某一天的产能记录。</summary>
public sealed record DayCapacity(DateTime Date, long Count);

/// <summary>柱状图的一根柱子（周统计=一天，月统计=一周）。</summary>
public sealed record BarItem(string Label, long Value, DateTime Start, DateTime End);

/// <summary>柱状图数据：标题日期、柱子集合、统计口径。</summary>
public sealed record CapacityChart(string PeriodText, string Mode, IReadOnlyList<BarItem> Bars);

/// <summary>故障分类统计行。</summary>
public sealed record FaultCategoryRow(string Category, string CategoryDesc, int Count);

/// <summary>故障明细行。</summary>
public sealed record FaultDetailRow(DateTime Date, string Time, int Code, string Name, string ClassName, string CategoryName, string Desc);

/// <summary>工况（Log）统计行。</summary>
public sealed record StateRow(int State, int Count);

/// <summary>Yield 良率行。</summary>
public sealed record YieldRow(DateTime Date, string Id, int Count);

/// <summary>故障分类表（Class）的一行：id、名称、说明。</summary>
public sealed record ClassRow(int Id, string Name, string Desc);

/// <summary>故障分类表（Category）的一行：id、名称、说明。</summary>
public sealed record CategoryRow(int Id, string Name, string Desc);

/// <summary>故障信息表（Info）的一行，用于 faults.csv 导出。</summary>
public sealed record FaultInfoRow(int Id, int ClassId, int CategoryId, string Name);

/// <summary>
/// 数据库访问层：只读打开 AKRS.capacity.db / AKRS.Classification.db。
/// </summary>
public sealed class CapacityRepository
{
    public const string CapacityDbName = "AKRS.capacity.db";
    public const string ClassificationDbName = "AKRS.Classification.db";

    private readonly string _capacityDbPath;
    private readonly string _classificationDbPath;

    public CapacityRepository(string capacityDbPath, string classificationDbPath)
    {
        _capacityDbPath = capacityDbPath;
        _classificationDbPath = classificationDbPath;
    }

    public string CapacityDbPath => _capacityDbPath;

    public string ClassificationDbPath => _classificationDbPath;

    /// <summary>
    /// 依次在 环境变量 AKRS_DATA_DIR、程序目录 data、程序目录、工作目录 data、工作目录 中查找数据库。
    /// </summary>
    public static CapacityRepository Locate(string? explicitDataDir = null)
    {
        var candidates = new List<string>();
        if (!string.IsNullOrWhiteSpace(explicitDataDir))
        {
            candidates.Add(explicitDataDir!);
        }

        var env = Environment.GetEnvironmentVariable("AKRS_DATA_DIR");
        if (!string.IsNullOrWhiteSpace(env))
        {
            candidates.Add(env!);
        }

        var baseDir = AppContext.BaseDirectory;
        candidates.Add(Path.Combine(baseDir, "data"));
        candidates.Add(baseDir);
        candidates.Add(Path.Combine(Directory.GetCurrentDirectory(), "data"));
        candidates.Add(Directory.GetCurrentDirectory());

        foreach (var dir in candidates)
        {
            var cap = Path.Combine(dir, CapacityDbName);
            var cls = Path.Combine(dir, ClassificationDbName);
            if (File.Exists(cap) && File.Exists(cls))
            {
                return new CapacityRepository(cap, cls);
            }
        }

        var fallback = Path.Combine(baseDir, "data");
        return new CapacityRepository(Path.Combine(fallback, CapacityDbName), Path.Combine(fallback, ClassificationDbName));
    }

    private SqliteConnection Open(string path)
    {
        var builder = new SqliteConnectionStringBuilder
        {
            DataSource = path,
            Mode = SqliteOpenMode.ReadOnly,
            Cache = SqliteCacheMode.Shared,
        };
        var connection = new SqliteConnection(builder.ToString());
        connection.Open();
        return connection;
    }

    private static DateTime ParseDate(string text)
    {
        if (DateTime.TryParse(text, CultureInfo.InvariantCulture, DateTimeStyles.None, out var value))
        {
            return value.Date;
        }

        return DateTime.MinValue;
    }

    /// <summary>读取全部日产能，按日期升序。</summary>
    public IReadOnlyList<DayCapacity> LoadDailyCapacity()
    {
        var list = new List<DayCapacity>();
        using var connection = Open(_capacityDbPath);
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT date, count FROM Capacity ORDER BY date";
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            var date = ParseDate(reader.GetString(0));
            var count = reader.IsDBNull(1) ? 0L : reader.GetInt64(1);
            list.Add(new DayCapacity(date, count));
        }

        return list;
    }

    /// <summary>读取某天的分钟级产能（cap 表）。</summary>
    public IReadOnlyList<(string Time, long Count)> LoadMinuteCapacity(DateTime date)
    {
        var list = new List<(string, long)>();
        using var connection = Open(_capacityDbPath);
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT time, count FROM cap WHERE date = $d ORDER BY time";
        command.Parameters.AddWithValue("$d", date.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture));
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            var time = reader.IsDBNull(0) ? string.Empty : reader.GetString(0);
            var count = reader.IsDBNull(1) ? 0L : reader.GetInt64(1);
            list.Add((time, count));
        }

        return list;
    }

    /// <summary>cap 表全部 count 之和（工况统计 SHIFT）。</summary>
    public long LoadMinuteCapacityTotal()
    {
        using var connection = Open(_capacityDbPath);
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT COALESCE(SUM(count), 0) FROM cap";
        var value = command.ExecuteScalar();
        return value is null or DBNull ? 0L : Convert.ToInt64(value, CultureInfo.InvariantCulture);
    }

    /// <summary>cap 表行数。</summary>
    public int LoadMinuteCapacityRowCount()
    {
        using var connection = Open(_capacityDbPath);
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT COUNT(*) FROM cap";
        var value = command.ExecuteScalar();
        return value is null or DBNull ? 0 : Convert.ToInt32(value, CultureInfo.InvariantCulture);
    }

    /// <summary>Capacity 表在 [start, end] 区间内按日期求和，缺失日期补 0。</summary>
    public IReadOnlyList<DayCapacity> LoadCapacityRange(DateTime start, DateTime end)
    {
        var map = new Dictionary<DateTime, long>();
        using (var connection = Open(_capacityDbPath))
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT date, count FROM Capacity WHERE date >= $s AND date <= $e ORDER BY date";
            command.Parameters.AddWithValue("$s", start.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture));
            command.Parameters.AddWithValue("$e", end.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture));
            using var reader = command.ExecuteReader();
            while (reader.Read())
            {
                var date = ParseDate(reader.GetString(0));
                var count = reader.IsDBNull(1) ? 0L : reader.GetInt64(1);
                map[date] = map.GetValueOrDefault(date) + count;
            }
        }

        var list = new List<DayCapacity>();
        for (var day = start.Date; day <= end.Date; day = day.AddDays(1))
        {
            list.Add(new DayCapacity(day, map.GetValueOrDefault(day)));
        }

        return list;
    }

    public IReadOnlyList<YieldRow> LoadYield()
    {
        var list = new List<YieldRow>();
        using var connection = Open(_capacityDbPath);
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT date, id, count FROM Yield ORDER BY date, id";
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            list.Add(new YieldRow(
                ParseDate(reader.GetString(0)),
                reader.IsDBNull(1) ? string.Empty : reader.GetString(1),
                reader.IsDBNull(2) ? 0 : reader.GetInt32(2)));
        }

        return list;
    }

    public IReadOnlyList<StateRow> LoadStateStatistics()
    {
        var list = new List<StateRow>();
        using var connection = Open(_capacityDbPath);
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT state, COUNT(*) FROM Log GROUP BY state ORDER BY state";
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            list.Add(new StateRow(reader.GetInt32(0), reader.GetInt32(1)));
        }

        return list;
    }

    /// <summary>读取 config 表中的班次定义（key = shift）。</summary>
    public string LoadShiftConfig()
    {
        using var connection = Open(_capacityDbPath);
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT value FROM config WHERE key = 'shift' LIMIT 1";
        var value = command.ExecuteScalar();
        return value as string ?? string.Empty;
    }

    /// <summary>按故障分类（Category）统计 Log 记录数。</summary>
    public IReadOnlyList<FaultCategoryRow> LoadFaultCategories()
    {
        var list = new List<FaultCategoryRow>();
        using var connection = Open(_capacityDbPath);
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT code, COUNT(*) FROM Log GROUP BY code";
        var counts = new Dictionary<int, int>();
        using (var reader = command.ExecuteReader())
        {
            while (reader.Read())
            {
                counts[reader.GetInt32(0)] = reader.GetInt32(1);
            }
        }

        var info = LoadInfoMap();
        var categories = LoadCategories();
        var totals = new Dictionary<int, int>();
        foreach (var pair in counts)
        {
            var categoryId = info.TryGetValue(pair.Key, out var entry) ? entry.CategoryId : 0;
            totals[categoryId] = totals.GetValueOrDefault(categoryId) + pair.Value;
        }

        foreach (var category in categories)
        {
            totals.TryGetValue(category.Key, out var count);
            list.Add(new FaultCategoryRow(category.Key.ToString(CultureInfo.InvariantCulture), category.Value, count));
        }

        if (totals.TryGetValue(0, out var unknown) && unknown > 0)
        {
            list.Add(new FaultCategoryRow("0", "未分类", unknown));
        }

        return list.OrderByDescending(r => r.Count).ThenBy(r => r.Category).ToList();
    }

    /// <summary>读取故障明细（Log 关联 Info/Class/Category）。</summary>
    public IReadOnlyList<FaultDetailRow> LoadFaultDetails(int limit = 500)
    {
        var info = LoadInfoMap();
        var classes = LoadLookup("Class");
        var categories = LoadCategories();
        var list = new List<FaultDetailRow>();
        using var connection = Open(_capacityDbPath);
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT date, time, code, COALESCE(desc, '') FROM Log ORDER BY date DESC, time DESC LIMIT $n";
        command.Parameters.AddWithValue("$n", limit);
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            var date = ParseDate(reader.GetString(0));
            var time = reader.IsDBNull(1) ? string.Empty : reader.GetString(1);
            var code = reader.GetInt32(2);
            var desc = reader.GetString(3);
            info.TryGetValue(code, out var entry);
            list.Add(new FaultDetailRow(
                date,
                time,
                code,
                entry?.Name ?? string.Empty,
                entry is null ? string.Empty : classes.GetValueOrDefault(entry.ClassId, string.Empty),
                entry is null ? string.Empty : categories.GetValueOrDefault(entry.CategoryId, string.Empty),
                string.IsNullOrEmpty(desc) ? entry?.Desc ?? string.Empty : desc));
        }

        return list;
    }

    /// <summary>Class 表全部行（按 id 升序）。</summary>
    public IReadOnlyList<ClassRow> LoadClasses()
    {
        var list = new List<ClassRow>();
        if (!File.Exists(_classificationDbPath))
        {
            return list;
        }

        using var connection = Open(_classificationDbPath);
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT id, COALESCE(name, ''), COALESCE(desc, '') FROM Class ORDER BY id";
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            list.Add(new ClassRow(reader.GetInt32(0), reader.GetString(1), reader.GetString(2)));
        }

        return list;
    }

    /// <summary>Category 表全部行（按 id 升序）。</summary>
    public IReadOnlyList<CategoryRow> LoadCategoryRows()
    {
        var list = new List<CategoryRow>();
        if (!File.Exists(_classificationDbPath))
        {
            return list;
        }

        using var connection = Open(_classificationDbPath);
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT id, COALESCE(name, ''), COALESCE(desc, '') FROM Category ORDER BY id";
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            list.Add(new CategoryRow(reader.GetInt32(0), reader.GetString(1), reader.GetString(2)));
        }

        return list;
    }

    /// <summary>Info 表全部行（按 id 升序），用于 faults.csv。</summary>
    public IReadOnlyList<FaultInfoRow> LoadFaultInfoRows()
    {
        var list = new List<FaultInfoRow>();
        if (!File.Exists(_classificationDbPath))
        {
            return list;
        }

        using var connection = Open(_classificationDbPath);
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT id, COALESCE(class, 0), COALESCE(category, 0), COALESCE(name, '') FROM Info ORDER BY id";
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            list.Add(new FaultInfoRow(reader.GetInt32(0), reader.GetInt32(1), reader.GetInt32(2), reader.GetString(3)));
        }

        return list;
    }

    /// <summary>分类库中某张表的行数（Info / Class / Category）。</summary>
    public int LoadClassificationRowCount(string table)
    {
        if (!File.Exists(_classificationDbPath))
        {
            return 0;
        }

        using var connection = Open(_classificationDbPath);
        using var command = connection.CreateCommand();
        command.CommandText = $"SELECT COUNT(*) FROM {table}";
        var value = command.ExecuteScalar();
        return value is null or DBNull ? 0 : Convert.ToInt32(value, CultureInfo.InvariantCulture);
    }

    private sealed record InfoEntry(int ClassId, int CategoryId, string Name, string Desc);

    private Dictionary<int, InfoEntry> LoadInfoMap()
    {
        var map = new Dictionary<int, InfoEntry>();
        if (!File.Exists(_classificationDbPath))
        {
            return map;
        }

        using var connection = Open(_classificationDbPath);
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT id, COALESCE(class, 0), COALESCE(category, 0), COALESCE(name, ''), COALESCE(desc, '') FROM Info";
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            map[reader.GetInt32(0)] = new InfoEntry(
                reader.GetInt32(1),
                reader.GetInt32(2),
                reader.GetString(3),
                reader.GetString(4));
        }

        return map;
    }

    private Dictionary<int, string> LoadCategories()
    {
        var map = LoadLookup("Category");
        return map;
    }

    private Dictionary<int, string> LoadLookup(string table)
    {
        var map = new Dictionary<int, string>();
        if (!File.Exists(_classificationDbPath))
        {
            return map;
        }

        using var connection = Open(_classificationDbPath);
        using var command = connection.CreateCommand();
        command.CommandText = $"SELECT id, COALESCE(desc, ''), COALESCE(name, '') FROM {table}";
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            var desc = reader.GetString(1);
            var name = reader.GetString(2);
            map[reader.GetInt32(0)] = string.IsNullOrEmpty(desc) ? name : desc;
        }

        return map;
    }

    /// <summary>数据库里最新的一条产能日期，用于界面初始定位。</summary>
    public DateTime? LatestCapacityDate()
    {
        using var connection = Open(_capacityDbPath);
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT MAX(date) FROM Capacity";
        var value = command.ExecuteScalar() as string;
        if (string.IsNullOrEmpty(value))
        {
            return null;
        }

        var date = ParseDate(value);
        return date == DateTime.MinValue ? null : date;
    }
}
