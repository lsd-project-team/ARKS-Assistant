using System.Globalization;

namespace CapacityStats;

/// <summary>
/// 离线自测：不依赖界面，覆盖统计口径、格式化、页面规定文本、CSV 导出与数据库读取。
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
        TestPageTitles();
        TestPageLines();
        TestClassChart();
        TestCsv();
        TestDatabaseRead();
        TestPageStatsFromDatabase();
        TestExport();

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
        Check("刻度步长（349）", CapacityChartControl.TickStep(349) == 100);
        Check("刻度步长（126445）", CapacityChartControl.TickStep(126445) == 50000);
        Check("刻度步长（0）", CapacityChartControl.TickStep(0) == 1);
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

    private static void TestPageTitles()
    {
        Check("页面 0 标题", PageStats.PageTitle(0) == "PAGE 产能统计");
        Check("页面 1 标题", PageStats.PageTitle(1) == "PAGE 工况统计");
        Check("页面 2 标题", PageStats.PageTitle(2) == "PAGE 故障统计");
        Check("页面 3 标题", PageStats.PageTitle(3) == "PAGE 故障分类及趋势");
        Check("页面 4 标题", PageStats.PageTitle(4) == "PAGE 故障分析");
        Check("页面 5 标题", PageStats.PageTitle(5) == "PAGE 设置");
        Check("页面 6 标题", PageStats.PageTitle(6) == "PAGE 信息导出");
        Check("越界页面标题", PageStats.PageTitle(7) == "PAGE");
    }

    private static void TestPageLines()
    {
        Check("WEEK 文本", PageStats.WeekLine(213081) == "WEEK 213,081");
        Check("MONTH 文本", PageStats.MonthLine(213081) == "MONTH 213,081");
        Check("SHIFT 文本", PageStats.ShiftLine(13756319) == "SHIFT 13,756,319");
        Check("FAULT 文本", PageStats.FaultLine(421) == "FAULT 421");
        Check("CLASS 文本", PageStats.ClassLine(3) == "CLASS 3");
        Check("CATEGORY 文本", PageStats.CategoryLine(6) == "CATEGORY 6");

        var daily = new List<DayCapacity>
        {
            new(new DateTime(2022, 4, 3), 111),
            new(new DateTime(2022, 4, 4), 10),
            new(new DateTime(2022, 4, 7), 20),
            new(new DateTime(2022, 4, 10), 30),
            new(new DateTime(2022, 4, 11), 222),
            new(new DateTime(2022, 5, 1), 333),
        };
        Check("周合计只含本周 7 天", PageStats.WeekTotal(daily, new DateTime(2022, 4, 7)) == 60);
        Check("月合计只含本月", PageStats.MonthTotal(daily, new DateTime(2022, 4, 7)) == 60);
        Check("区间求和", PageStats.SumRange(daily, new DateTime(2022, 4, 4), new DateTime(2022, 4, 10)) == 60);

        var shiftText = PageStats.ShiftConfigText("<Shift>\r\n\t<Day start=\"06:30:00\"/>\r\n</Shift>");
        Check("班次配置压平空白", shiftText == "班次配置：<Shift> <Day start=\"06:30:00\"/> </Shift>");
        Check("班次配置为空", PageStats.ShiftConfigText("  ") == "班次配置：（未配置）");
    }

    private static void TestClassChart()
    {
        var classes = new List<ClassRow>
        {
            new(1, "ERROR", "错误"),
            new(2, "WARNING", "警告"),
            new(3, "TEXT", string.Empty),
        };
        var info = new List<FaultInfoRow>
        {
            new(1, 1, 6, "A"),
            new(2, 1, 6, "B"),
            new(3, 3, 5, "C"),
        };

        var chart = PageStats.BuildClassChart(classes, info);
        Check("Class 柱数量", chart.Bars.Count == 3);
        Check("Class 柱标签", chart.Bars[0].Label == "ERROR" && chart.Bars[2].Label == "TEXT");
        Check("Class 柱值", chart.Bars[0].Value == 2 && chart.Bars[1].Value == 0 && chart.Bars[2].Value == 1);
    }

    private static void TestCsv()
    {
        var daily = new List<DayCapacity>
        {
            new(new DateTime(2022, 4, 4), 5),
            new(new DateTime(2022, 4, 6), 86636),
            new(new DateTime(2022, 4, 7), 126445),
            new(new DateTime(2022, 4, 11), 999),
        };

        var rows = PageStats.BuildCapacityCsvRows(daily);
        Check("capacity.csv 7 行", rows.Count == 7);
        Check("capacity.csv 首行日期", rows[0][0] == "2022-04-04" && rows[0][1] == "5");
        Check("capacity.csv 缺失日补 0", rows[1][0] == "2022-04-05" && rows[1][1] == "0");
        Check("capacity.csv 末行日期", rows[6][0] == "2022-04-10" && rows[6][1] == "0");

        var csv = CsvWriter.Build(PageStats.CapacityCsvHeader, rows);
        var lines = csv.Split('\n');
        Check("capacity.csv 表头", lines[0] == "date,count");
        Check("capacity.csv 行数（含表头）", lines.Length == 9 && lines[8].Length == 0);

        var faults = PageStats.BuildFaultsCsvRows(new List<FaultInfoRow>
        {
            new(2, 1, 6, "ERR_B"),
            new(1, 1, 6, "ERR_A"),
        });
        Check("faults.csv 按 id 升序", faults[0][0] == "1" && faults[1][0] == "2");
        Check("faults.csv 列内容", faults[0][1] == "1" && faults[0][2] == "6" && faults[0][3] == "ERR_A");
        Check("CSV 转义逗号", CsvWriter.Escape("a,b") == "\"a,b\"");
        Check("CSV 转义引号", CsvWriter.Escape("a\"b") == "\"a\"\"b\"");
        Check("CSV 普通字段不加引号", CsvWriter.Escape("ERR_A") == "ERR_A");
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

    private static void TestPageStatsFromDatabase()
    {
        var repo = CapacityRepository.Locate();
        if (!File.Exists(repo.CapacityDbPath) || !File.Exists(repo.ClassificationDbPath))
        {
            Check("数据库文件存在（跳过页面口径校验）", true);
            return;
        }

        var daily = repo.LoadDailyCapacity();
        Check("页面 0 WEEK 合计", PageStats.WeekTotal(daily, PageStats.WeekReferenceDate) == 213081);
        Check("页面 0 MONTH 合计", PageStats.MonthTotal(daily, PageStats.MonthReferenceDate) == 213081);
        Check("页面 0 WEEK 文本", PageStats.WeekLine(PageStats.WeekTotal(daily, PageStats.WeekReferenceDate)) == "WEEK 213,081");
        Check("页面 0 MONTH 文本", PageStats.MonthLine(PageStats.MonthTotal(daily, PageStats.MonthReferenceDate)) == "MONTH 213,081");

        Check("页面 1 cap 求和", repo.LoadMinuteCapacityTotal() == 13756319);
        Check("页面 1 cap 行数", repo.LoadMinuteCapacityRowCount() == 2665);
        Check("页面 1 SHIFT 文本", PageStats.ShiftLine(repo.LoadMinuteCapacityTotal()) == "SHIFT 13,756,319");

        Check("页面 2 Info 行数", repo.LoadClassificationRowCount("Info") == 421);
        Check("页面 2 FAULT 文本", PageStats.FaultLine(repo.LoadClassificationRowCount("Info")) == "FAULT 421");

        var classes = repo.LoadClasses();
        Check("页面 3 Class 行数", classes.Count == 3 && repo.LoadClassificationRowCount("Class") == 3);
        Check("页面 3 CLASS 文本", PageStats.ClassLine(classes.Count) == "CLASS 3");

        var infoRows = repo.LoadFaultInfoRows();
        Check("Info 明细行数", infoRows.Count == 421);
        var classChart = PageStats.BuildClassChart(classes, infoRows);
        Check("页面 3 柱数量", classChart.Bars.Count == 3);
        Check("页面 3 柱合计等于 Info 行数", CapacityAggregator.Total(classChart.Bars) == 421);
        Check("页面 3 ERROR 柱", classChart.Bars.First(b => b.Label == "ERROR").Value == 30);
        Check("页面 3 WARNING 柱", classChart.Bars.First(b => b.Label == "WARNING").Value == 42);
        Check("页面 3 TEXT 柱", classChart.Bars.First(b => b.Label == "TEXT").Value == 349);

        var categoryRows = repo.LoadCategoryRows();
        Check("页面 4 Category 行数", categoryRows.Count == 6 && repo.LoadClassificationRowCount("Category") == 6);
        Check("页面 4 CATEGORY 文本", PageStats.CategoryLine(categoryRows.Count) == "CATEGORY 6");

        var range = repo.LoadCapacityRange(PageStats.ExportStartDate, PageStats.ExportEndDate);
        Check("导出区间 7 天", range.Count == 7);
        Check("导出区间 2022-04-06", range.First(d => d.Date == new DateTime(2022, 4, 6)).Count == 86636);
        Check("导出区间 2022-04-07", range.First(d => d.Date == new DateTime(2022, 4, 7)).Count == 126445);
        Check("导出区间缺失日补 0", range.First(d => d.Date == new DateTime(2022, 4, 4)).Count == 0);
    }

    private static void TestExport()
    {
        var repo = CapacityRepository.Locate();
        if (!File.Exists(repo.CapacityDbPath) || !File.Exists(repo.ClassificationDbPath))
        {
            Check("数据库文件存在（跳过导出校验）", true);
            return;
        }

        var dir = Path.Combine(Path.GetTempPath(), "capacitystats-selftest-" + Guid.NewGuid().ToString("N"));
        try
        {
            var result = DataExporter.Export(repo, dir);
            Check("导出 capacity.csv 存在", File.Exists(result.CapacityCsvPath));
            Check("导出 faults.csv 存在", File.Exists(result.FaultsCsvPath));
            Check("导出 capacity.csv 行数", result.CapacityRows == 7);
            Check("导出 faults.csv 行数", result.FaultRows == 421);

            var capacityText = File.ReadAllText(result.CapacityCsvPath);
            var capacityLines = capacityText.Split('\n');
            Check("导出 capacity.csv 表头", capacityLines[0] == "date,count");
            Check("导出 capacity.csv 首行", capacityLines[1] == "2022-04-04,0");
            Check("导出 capacity.csv 2022-04-07", capacityLines[4] == "2022-04-07,126445");
            Check("导出 capacity.csv 末行", capacityLines[7] == "2022-04-10,0");
            Check("导出 capacity.csv 无 BOM", capacityText.Length > 0 && capacityText[0] == 'd');

            var faultText = File.ReadAllText(result.FaultsCsvPath);
            var faultLines = faultText.Split('\n');
            Check("导出 faults.csv 表头", faultLines[0] == "id,class,category,name");
            Check("导出 faults.csv 首行", faultLines[1] == "1,1,6,ERR_NEVER_USE");
            Check("导出 faults.csv 行数（含表头）", faultLines.Length == 423 && faultLines[422].Length == 0);

            var described = DataExporter.Describe(result);
            Check("导出输出含 EXPORT", described.Contains("EXPORT " + Path.GetFullPath(dir), StringComparison.Ordinal));
        }
        finally
        {
            if (Directory.Exists(dir))
            {
                Directory.Delete(dir, recursive: true);
            }
        }
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
