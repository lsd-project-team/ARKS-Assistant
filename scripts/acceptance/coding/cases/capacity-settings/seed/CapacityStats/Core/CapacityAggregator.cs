using System.Globalization;

namespace CapacityStats;

/// <summary>
/// 产能统计口径（纯逻辑，可离线自测）。
/// 周统计：以选中日期所在自然周（周一起）的 7 天为柱，柱值为当天产能。
/// 月统计：以选中日期所在自然月的各自然周（周一起）为柱，柱值为该周产能合计。
/// </summary>
public static class CapacityAggregator
{
    public const string WeekMode = "周统计";
    public const string MonthMode = "月统计";

    public static DateTime StartOfWeek(DateTime date)
    {
        var day = date.Date;
        var offset = ((int)day.DayOfWeek + 6) % 7; // 周一 = 0
        return day.AddDays(-offset);
    }

    public static DateTime StartOfMonth(DateTime date) => new(date.Year, date.Month, 1);

    public static DateTime EndOfMonth(DateTime date) => new DateTime(date.Year, date.Month, 1).AddMonths(1).AddDays(-1);

    /// <summary>周统计：选中日期所在自然周 7 天。</summary>
    public static CapacityChart BuildWeek(IReadOnlyList<DayCapacity> daily, DateTime selected)
    {
        var map = ToMap(daily);
        var start = StartOfWeek(selected);
        var bars = new List<BarItem>(7);
        for (var i = 0; i < 7; i++)
        {
            var day = start.AddDays(i);
            map.TryGetValue(day, out var value);
            bars.Add(new BarItem(day.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture), value, day, day));
        }

        return new CapacityChart(selected.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture), WeekMode, bars);
    }

    /// <summary>月统计：选中日期所在自然月，按自然周（周一起）汇总。</summary>
    public static CapacityChart BuildMonth(IReadOnlyList<DayCapacity> daily, DateTime selected)
    {
        var map = ToMap(daily);
        var monthStart = StartOfMonth(selected);
        var monthEnd = EndOfMonth(selected);
        var cursor = StartOfWeek(monthStart);
        var bars = new List<BarItem>();
        while (cursor <= monthEnd)
        {
            var weekEnd = cursor.AddDays(6);
            long sum = 0;
            for (var i = 0; i < 7; i++)
            {
                var day = cursor.AddDays(i);
                if (day < monthStart || day > monthEnd)
                {
                    continue;
                }

                if (map.TryGetValue(day, out var value))
                {
                    sum += value;
                }
            }

            bars.Add(new BarItem(MonthBarLabel(cursor, monthStart), sum, cursor, weekEnd));
            cursor = cursor.AddDays(7);
        }

        return new CapacityChart(selected.ToString("yyyy-MM", CultureInfo.InvariantCulture), MonthMode, bars);
    }

    /// <summary>月统计的柱标签：本月内的周显示 MM-dd，跨月首周显示完整日期。</summary>
    public static string MonthBarLabel(DateTime weekStart, DateTime monthStart)
        => weekStart.Month == monthStart.Month
            ? weekStart.ToString("MM-dd", CultureInfo.InvariantCulture)
            : weekStart.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);

    public static CapacityChart Build(IReadOnlyList<DayCapacity> daily, DateTime selected, string mode)
        => string.Equals(mode, MonthMode, StringComparison.Ordinal) ? BuildMonth(daily, selected) : BuildWeek(daily, selected);

    /// <summary>把选中日期平移到上一/下一周期（周统计 ±7 天，月统计 ±1 月）。</summary>
    public static DateTime Shift(DateTime selected, string mode, int direction)
    {
        if (string.Equals(mode, MonthMode, StringComparison.Ordinal))
        {
            return selected.AddMonths(direction);
        }

        return selected.AddDays(7 * direction);
    }

    /// <summary>坐标轴上限：取 10K 的整数倍，且不低于数据最大值。</summary>
    public static long AxisMax(long maxValue)
    {
        const long step = 10_000;
        if (maxValue <= 0)
        {
            return step;
        }

        var ticks = (maxValue + step - 1) / step;
        return ticks * step;
    }

    /// <summary>把数值格式化为 12.3K / 1.2M 形式。</summary>
    public static string FormatShort(long value)
    {
        if (value >= 1_000_000)
        {
            return (value / 1_000_000d).ToString("0.#", CultureInfo.InvariantCulture) + "M";
        }

        if (value >= 1_000)
        {
            return (value / 1_000d).ToString("0.#", CultureInfo.InvariantCulture) + "K";
        }

        return value.ToString(CultureInfo.InvariantCulture);
    }

    public static long Total(IEnumerable<BarItem> bars)
    {
        long total = 0;
        foreach (var bar in bars)
        {
            total += bar.Value;
        }

        return total;
    }

    public static long Max(IEnumerable<BarItem> bars)
    {
        long max = 0;
        foreach (var bar in bars)
        {
            if (bar.Value > max)
            {
                max = bar.Value;
            }
        }

        return max;
    }

    private static Dictionary<DateTime, long> ToMap(IReadOnlyList<DayCapacity> daily)
    {
        var map = new Dictionary<DateTime, long>();
        foreach (var item in daily)
        {
            if (item.Date == DateTime.MinValue)
            {
                continue;
            }

            map[item.Date.Date] = map.GetValueOrDefault(item.Date.Date) + item.Count;
        }

        return map;
    }
}
