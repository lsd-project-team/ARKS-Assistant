using System.Globalization;

namespace CapacityStats;

/// <summary>
/// 界面文案与格式化的纯函数集合（可离线自测）。
/// </summary>
public static class UiText
{
    public const string AppTitle = "产能统计 [1.1.5.4]";

    public static readonly string[] NavItems =
    {
        "产能统计",
        "工况统计",
        "故障统计",
        "故障分类及趋势",
        "故障分析",
        "设置",
        "信息导出",
    };

    public static string DateText(DateTime date) => date.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);

    public static string MonthText(DateTime date) => date.ToString("yyyy-MM", CultureInfo.InvariantCulture);

    /// <summary>标题下方日期：周统计显示 yyyy-MM-dd，月统计显示 yyyy-MM。</summary>
    public static string PeriodText(DateTime date, string mode)
        => string.Equals(mode, CapacityAggregator.MonthMode, StringComparison.Ordinal) ? MonthText(date) : DateText(date);

    public static string Count(long value) => value.ToString("N0", CultureInfo.InvariantCulture);

    public static string Average(long total, int bars) => bars <= 0 ? "0" : Count(total / bars);

    /// <summary>柱状图下方的统计说明行。</summary>
    public static string SummaryLine(CapacityChart chart)
    {
        var total = CapacityAggregator.Total(chart.Bars);
        var max = CapacityAggregator.Max(chart.Bars);
        var peak = chart.Bars.FirstOrDefault(b => b.Value == max);
        var peakText = peak is null ? "-" : peak.Label;
        return $"{chart.Mode}：合计 {Count(total)} 个，日均 {Average(total, chart.Bars.Count)} 个，峰值 {Count(max)} 个（{peakText}）";
    }

    public static string StateName(int state) => state switch
    {
        0 => "停机",
        1 => "待机",
        2 => "运行",
        3 => "报警",
        _ => "状态 " + state.ToString(CultureInfo.InvariantCulture),
    };
}
