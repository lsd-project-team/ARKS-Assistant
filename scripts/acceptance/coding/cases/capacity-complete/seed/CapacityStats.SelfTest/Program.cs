using System.Globalization;

namespace CapacityStats;

/// <summary>
/// 离线自测：不依赖界面与数据库文件，覆盖统计口径、格式化与数据库读取。
/// 运行：dotnet run --project CapacityStats.SelfTest
/// </summary>
internal static class Program
{
    private static int _passed;
    private static int _failed;

    private static int Main()
    {
        Console.OutputEncoding = System.Text.Encoding.UTF8;

        TestStartOfWeek();
        TestWeekChart();
        TestMonthChart();
        TestShift();
        TestAxisAndFormat();
        TestSummaryLine();
        TestDatabaseRead();

        Console.WriteLine($"通过 {_passed} 项，失败 {_failed} 项");
        return _failed == 0 ? 0 : 1;
    }

    private static void TestStartOfWeek()
    {
        Check("周一为一周起点", CapacityAggregator.StartOfWeek(new DateTime(2022, 4, 7)) == new DateTime(2022, 4, 4));
        Check("周日归入上一周", CapacityAggregator.StartOfWeek(new DateTime(2022, 4, 10)) == new DateTime(2022, 4, 4));
        Check("月初边界", CapacityAggregator.StartOfWeek(new DateTime(2022, 3, 1)) == new DateTime(2022, 2, 28));
    }

    private static void TestWeekChart()
    {
        var daily = new List<DayCapacity>
        {
            new(new DateTime(2022, 4, 4), 10),
            new(new DateTime(2022, 4, 6), 20),
            new(new DateTime(2022, 4, 7), 30),
            new(new DateTime(2022, 4, 11), 99),
        };

        var chart = CapacityAggregator.BuildWeek(daily, new DateTime(2022, 4, 7));
        Check("周统计 7 根柱", chart.Bars.Count == 7);
        Check("周统计首柱为周一", chart.Bars[0].Label == "2022-04-04");
        Check("周统计末柱为周日", chart.Bars[6].Label == "2022-04-10");
        Check("周统计柱值取当天", chart.Bars[2].Value == 20 && chart.Bars[3].Value == 30);
        Check("周统计缺失日为 0", chart.Bars[4].Value == 0);
        Check("周统计合计", CapacityAggregator.Total(chart.Bars) == 60);
        Check("周统计周期文本", chart.PeriodText == "2022-04-07" && chart.Mode == CapacityAggregator.WeekMode);
    }

    private static void TestMonthChart()
    {
        var daily = new List<DayCapacity>
        {
            new(new DateTime(2022, 3, 1), 100),
            new(new DateTime(2022, 3, 7), 200),
            new(new DateTime(2022, 3, 8), 300),
            new(new DateTime(2022, 3, 31), 400),
            new(new DateTime(2022, 4, 1), 999),
        };

        var chart = CapacityAggregator.BuildMonth(daily, new DateTime(2022, 3, 15));
        Check("月统计按自然周分柱", chart.Bars.Count == 5);
        Check("月统计首周只含本月天数", chart.Bars[0].Value == 100);
        Check("月统计第二周", chart.Bars[1].Value == 200);
        Check("月统计第三周", chart.Bars[2].Value == 300);
        Check("月统计末周", chart.Bars[4].Value == 400);
        Check("月统计不跨月", CapacityAggregator.Total(chart.Bars) == 1000);
        Check("月统计周期文本", chart.PeriodText == "2022-03" && chart.Mode == CapacityAggregator.MonthMode);

        var feb = CapacityAggregator.BuildMonth(daily, new DateTime(2022, 2, 10));
        Check("无数据月份仍给出周柱", feb.Bars.Count == 5 && CapacityAggregator.Total(feb.Bars) == 0);
    }

    private static void TestShift()
    {
        var date = new DateTime(2022, 3, 31);
        Check("周统计上一周", CapacityAggregator.Shift(date, CapacityAggregator.WeekMode, -1) == new DateTime(2022, 3, 24));
        Check("周统计下一周", CapacityAggregator.Shift(date, CapacityAggregator.WeekMode, 1) == new DateTime(2022, 4, 7));
        Check("月统计上一月", CapacityAggregator.Shift(new DateTime(2022, 1, 31), CapacityAggregator.MonthMode, -1) == new DateTime(2021, 12, 31));
        Check("月统计下一月", CapacityAggregator.Shift(date, CapacityAggregator.MonthMode, 1) == new DateTime(2022, 4, 30));
    }

    private static void TestAxisAndFormat()
    {
        Check("轴上限取 10K 整数倍", CapacityAggregator.AxisMax(126445) == 130000);
        Check("轴上限空数据", CapacityAggregator.AxisMax(0) == 10000);
        Check("轴上限整倍数不额外加档", CapacityAggregator.AxisMax(130000) == 130000);
        Check("K 格式", CapacityAggregator.FormatShort(126445) == "126.4K");
        Check("M 格式", CapacityAggregator.FormatShort(1_500_000) == "1.5M");
        Check("小数值格式", CapacityAggregator.FormatShort(999) == "999");
        Check("日期文本", UiText.DateText(new DateTime(2022, 4, 7)) == "2022-04-07");
        Check("周期文本（周）", UiText.PeriodText(new DateTime(2022, 4, 7), CapacityAggregator.WeekMode) == "2022-04-07");
        Check("周期文本（月）", UiText.PeriodText(new DateTime(2022, 4, 7), CapacityAggregator.MonthMode) == "2022-04");
        Check("导航项数量", UiText.NavItems.Length == 7);
        Check("导航项顺序", UiText.NavItems[0] == "产能统计" && UiText.NavItems[6] == "信息导出");
    }

    private static void TestSummaryLine()
    {
        var chart = new CapacityChart("2022-04-07", CapacityAggregator.WeekMode, new List<BarItem>
        {
            new("2022-04-04", 0, new DateTime(2022, 4, 4), new DateTime(2022, 4, 4)),
            new("2022-04-05", 0, new DateTime(2022, 4, 5), new DateTime(2022, 4, 5)),
            new("2022-04-06", 86636, new DateTime(2022, 4, 6), new DateTime(2022, 4, 6)),
            new("2022-04-07", 126445, new DateTime(2022, 4, 7), new DateTime(2022, 4, 7)),
            new("2022-04-08", 0, new DateTime(2022, 4, 8), new DateTime(2022, 4, 8)),
            new("2022-04-09", 0, new DateTime(2022, 4, 9), new DateTime(2022, 4, 9)),
            new("2022-04-10", 0, new DateTime(2022, 4, 10), new DateTime(2022, 4, 10)),
        });

        var line = UiText.SummaryLine(chart);
        Check("统计行含合计", line.Contains("213,081", StringComparison.Ordinal));
        Check("统计行含峰值日期", line.Contains("2022-04-07", StringComparison.Ordinal));
        Check("统计行含日均", line.Contains("30,440", StringComparison.Ordinal));
    }

    private static void TestDatabaseRead()
    {
        var repo = CapacityRepository.Locate();
        if (!File.Exists(repo.CapacityDbPath) || !File.Exists(repo.ClassificationDbPath))
        {
            Check("数据库文件存在（跳过数据校验）", true);
            return;
        }

        var daily = repo.LoadDailyCapacity();
        Check("读取日产能记录", daily.Count > 0);
        Check("最新日期为 2022-04-07", repo.LatestCapacityDate() == new DateTime(2022, 4, 7));

        var week = CapacityAggregator.BuildWeek(daily, new DateTime(2022, 4, 7));
        Check("数据库周统计 2022-04-06", week.Bars.First(b => b.Label == "2022-04-06").Value == 86636);
        Check("数据库周统计 2022-04-07", week.Bars.First(b => b.Label == "2022-04-07").Value == 126445);
        Check("数据库周统计合计", CapacityAggregator.Total(week.Bars) == 213081);

        var month = CapacityAggregator.BuildMonth(daily, new DateTime(2022, 3, 15));
        Check("数据库月统计 2022-03 首周", month.Bars[0].Value == 152560 + 186765);
        Check("数据库月统计 2022-03 第二周", month.Bars[1].Value == 232864 + 224804 + 218640 + 230115 + 245936 + 237313 + 233233);
        Check("数据库月统计 2022-03 合计", CapacityAggregator.Total(month.Bars) == 1491684 + 1317658 + 282011 + 42841);

        var april = CapacityAggregator.BuildMonth(daily, new DateTime(2022, 4, 7));
        Check("数据库月统计 2022-04 首周", april.Bars[0].Value == 86636 + 126445);
        Check("数据库月统计 2022-04 合计", CapacityAggregator.Total(april.Bars) == 213081);

        var minutes = repo.LoadMinuteCapacity(new DateTime(2022, 4, 7));
        Check("读取分钟产能", minutes.Count == 12 && minutes[0].Time == "15:30:00");

        var categories = repo.LoadFaultCategories();
        Check("故障分类统计非空", categories.Count > 0 && categories.Sum(c => c.Count) == 28459);

        var details = repo.LoadFaultDetails(5);
        Check("故障明细读取", details.Count == 5 && details[0].Date == new DateTime(2022, 4, 7));

        var states = repo.LoadStateStatistics();
        Check("工况状态统计", states.Sum(s => s.Count) == 28459);

        var shift = repo.LoadShiftConfig();
        Check("班次配置读取", shift.Contains("06:30:00", StringComparison.Ordinal));

        var yieldRows = repo.LoadYield();
        Check("良率记录读取", yieldRows.Count == 187);
    }

    private static void Check(string name, bool condition)
    {
        if (condition)
        {
            _passed++;
            Console.WriteLine("PASS " + name);
        }
        else
        {
            _failed++;
            Console.WriteLine("FAIL " + name);
        }
    }
}
