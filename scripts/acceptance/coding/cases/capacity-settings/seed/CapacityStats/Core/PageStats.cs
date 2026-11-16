using System.Globalization;

namespace CapacityStats;

/// <summary>
/// 页面统计口径（纯逻辑 + 数据访问组合，可离线自测）。
/// 7 个页面的规定文本都在这里生成，界面只负责显示。
/// </summary>
public static class PageStats
{
    /// <summary>页面 0 的周统计基准日：2022-04-07 所在自然周（2022-04-04 ~ 2022-04-10）。</summary>
    public static readonly DateTime WeekReferenceDate = new(2022, 4, 7);

    /// <summary>页面 0 的月统计基准月：2022-04。</summary>
    public static readonly DateTime MonthReferenceDate = new(2022, 4, 7);

    /// <summary>信息导出 capacity.csv 的区间起点。</summary>
    public static readonly DateTime ExportStartDate = new(2022, 4, 4);

    /// <summary>信息导出 capacity.csv 的区间终点。</summary>
    public static readonly DateTime ExportEndDate = new(2022, 4, 10);

    public const string CapacityCsvName = "capacity.csv";
    public const string FaultsCsvName = "faults.csv";

    public static readonly string[] CapacityCsvHeader = { "date", "count" };
    public static readonly string[] FaultsCsvHeader = { "id", "class", "category", "name" };

    /// <summary>页面标题：严格为 `PAGE &lt;页面名&gt;`。</summary>
    public static string PageTitle(int index)
        => index >= 0 && index < UiText.NavItems.Length ? "PAGE " + UiText.NavItems[index] : "PAGE";

    /// <summary>页面 0 的周合计文本：`WEEK &lt;2022-04-07 所在周总计&gt;`。</summary>
    public static string WeekLine(long total) => "WEEK " + UiText.Count(total);

    /// <summary>页面 0 的月合计文本：`MONTH &lt;2022-04 月总计&gt;`。</summary>
    public static string MonthLine(long total) => "MONTH " + UiText.Count(total);

    /// <summary>页面 1：`SHIFT &lt;cap 表全部 count 之和&gt;`。</summary>
    public static string ShiftLine(long total) => "SHIFT " + UiText.Count(total);

    /// <summary>页面 2：`FAULT &lt;Info 表行数&gt;`。</summary>
    public static string FaultLine(int rows) => "FAULT " + UiText.Count(rows);

    /// <summary>页面 3：`CLASS &lt;Class 表行数&gt;`。</summary>
    public static string ClassLine(int rows) => "CLASS " + UiText.Count(rows);

    /// <summary>页面 4：`CATEGORY &lt;Category 表行数&gt;`。</summary>
    public static string CategoryLine(int rows) => "CATEGORY " + UiText.Count(rows);

    /// <summary>按自然周（周一起）汇总区间内每天的产能。</summary>
    public static long SumRange(IReadOnlyList<DayCapacity> days, DateTime start, DateTime end)
    {
        long total = 0;
        foreach (var day in days)
        {
            if (day.Date.Date >= start.Date && day.Date.Date <= end.Date)
            {
                total += day.Count;
            }
        }

        return total;
    }

    /// <summary>周合计：基准日所在自然周（周一起 7 天）。</summary>
    public static long WeekTotal(IReadOnlyList<DayCapacity> days, DateTime reference)
    {
        var start = CapacityAggregator.StartOfWeek(reference);
        return SumRange(days, start, start.AddDays(6));
    }

    /// <summary>月合计：基准日所在自然月。</summary>
    public static long MonthTotal(IReadOnlyList<DayCapacity> days, DateTime reference)
    {
        var start = CapacityAggregator.StartOfMonth(reference);
        var end = CapacityAggregator.EndOfMonth(reference);
        return SumRange(days, start, end);
    }

    /// <summary>按 Class 生成柱状图：每根柱 = 该 Class 的 Info 条数。</summary>
    public static CapacityChart BuildClassChart(IReadOnlyList<ClassRow> classes, IReadOnlyList<FaultInfoRow> infoRows)
    {
        var counts = new Dictionary<int, long>();
        foreach (var row in infoRows)
        {
            counts[row.ClassId] = counts.GetValueOrDefault(row.ClassId) + 1;
        }

        var bars = new List<BarItem>();
        foreach (var cls in classes.OrderBy(c => c.Id))
        {
            var label = string.IsNullOrWhiteSpace(cls.Name) ? cls.Id.ToString(CultureInfo.InvariantCulture) : cls.Name;
            var value = counts.GetValueOrDefault(cls.Id);
            bars.Add(new BarItem(label, value, DateTime.MinValue, DateTime.MinValue));
        }

        return new CapacityChart("Class", "故障分类", bars);
    }

    /// <summary>capacity.csv 的数据行：区间内每天一行，缺失日期 count 写 0。</summary>
    public static IReadOnlyList<string[]> BuildCapacityCsvRows(IReadOnlyList<DayCapacity> days)
    {
        var map = new Dictionary<DateTime, long>();
        foreach (var day in days)
        {
            if (day.Date == DateTime.MinValue)
            {
                continue;
            }

            map[day.Date.Date] = map.GetValueOrDefault(day.Date.Date) + day.Count;
        }

        var rows = new List<string[]>();
        for (var date = ExportStartDate; date <= ExportEndDate; date = date.AddDays(1))
        {
            rows.Add(new[]
            {
                date.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
                map.GetValueOrDefault(date).ToString(CultureInfo.InvariantCulture),
            });
        }

        return rows;
    }

    /// <summary>faults.csv 的数据行：Info 表全部行，按 id 升序。</summary>
    public static IReadOnlyList<string[]> BuildFaultsCsvRows(IReadOnlyList<FaultInfoRow> rows)
        => rows.OrderBy(r => r.Id)
            .Select(r => new[]
            {
                r.Id.ToString(CultureInfo.InvariantCulture),
                r.ClassId.ToString(CultureInfo.InvariantCulture),
                r.CategoryId.ToString(CultureInfo.InvariantCulture),
                r.Name,
            })
            .ToList();

    /// <summary>页面 5 的说明文本（班次配置）。</summary>
    public static string ShiftConfigText(string raw)
    {
        var flat = (raw ?? string.Empty).Replace("\r", " ").Replace("\n", " ").Replace("\t", " ").Trim();
        while (flat.Contains("  ", StringComparison.Ordinal))
        {
            flat = flat.Replace("  ", " ", StringComparison.Ordinal);
        }

        return string.IsNullOrEmpty(flat) ? "班次配置：（未配置）" : "班次配置：" + flat;
    }
}
