using System.Drawing;
using System.Windows.Forms;

namespace CapacityStats;

/// <summary>
/// 主窗体：左侧导航 + 右侧 7 个页面。
/// 页面 0 为产能统计（日期切换 + 周/月柱状图 + WEEK/MONTH 规定文本），
/// 页面 3 为故障分类及趋势（按 Class 的柱状图），其余页面为规定文本 + 说明。
/// 内容区使用自绘面板，保证截图与布局在任意 DPI 下稳定。
/// </summary>
public sealed class MainForm : Form
{
    private static readonly Color PageBack = Color.FromArgb(243, 243, 243);
    private static readonly Color ModeBack = Color.FromArgb(180, 205, 235);
    private static readonly Color TextColor = Color.FromArgb(20, 20, 20);

    private readonly CapacityRepository _repository;
    private readonly IReadOnlyList<DayCapacity> _daily;

    private readonly NavPanel _nav;
    private readonly Panel _content;
    private readonly Label _titleLabel;
    private readonly CircleArrowButton _prevButton;
    private readonly CircleArrowButton _nextButton;
    private readonly Label _dateLabel;
    private readonly CapacityChartControl _chart;
    private readonly Label _summaryLabel;
    private readonly Label _weekButton;
    private readonly Label _monthButton;
    private readonly Label _statusLabel;

    private DateTime _selectedDate;
    private string _mode = CapacityAggregator.WeekMode;
    private int _selectedNav;

    public MainForm()
    {
        _repository = CapacityRepository.Locate();
        _daily = SafeLoadDaily();

        Text = UiText.AppTitle;
        Name = "MainForm";
        StartPosition = FormStartPosition.CenterScreen;
        ClientSize = new Size(738, 608);
        MinimumSize = new Size(640, 480);
        BackColor = PageBack;
        Font = new Font("Microsoft YaHei UI", 9f);
        AutoScaleMode = AutoScaleMode.None;

        _nav = new NavPanel
        {
            Name = "navPanel",
            Dock = DockStyle.Left,
            Width = 134,
            TopItems = UiText.NavItems.Take(5).ToArray(),
            BottomItems = UiText.NavItems.Skip(5).ToArray(),
            SelectedIndex = 0,
        };
        _nav.ItemClicked += (_, index) => SelectNav(index);
        _nav.BackClicked += (_, _) => SelectNav(0);

        _content = new Panel
        {
            Name = "contentPanel",
            Dock = DockStyle.Fill,
            BackColor = PageBack,
        };

        _titleLabel = new Label
        {
            Name = "titleLabel",
            Text = PageStats.PageTitle(0),
            Font = new Font("Microsoft YaHei UI", 24f, FontStyle.Regular),
            ForeColor = TextColor,
            BackColor = PageBack,
            TextAlign = ContentAlignment.MiddleCenter,
            AutoSize = false,
        };

        _prevButton = new CircleArrowButton { Name = "prevButton", PointLeft = false };
        _nextButton = new CircleArrowButton { Name = "nextButton", PointLeft = true };
        _prevButton.Click += (_, _) => ShiftPeriod(-1);
        _nextButton.Click += (_, _) => ShiftPeriod(1);

        _dateLabel = new Label
        {
            Name = "dateLabel",
            Font = new Font("Microsoft YaHei UI", 10.5f),
            ForeColor = TextColor,
            BackColor = PageBack,
            TextAlign = ContentAlignment.MiddleCenter,
            AutoSize = false,
        };

        _chart = new CapacityChartControl { Name = "capacityChart" };

        _summaryLabel = new Label
        {
            Name = "summaryLabel",
            Font = new Font("Microsoft YaHei UI", 9f),
            ForeColor = Color.FromArgb(70, 70, 70),
            BackColor = PageBack,
            TextAlign = ContentAlignment.MiddleLeft,
            AutoSize = false,
        };

        _weekButton = CreateModeButton("weekButton", CapacityAggregator.WeekMode);
        _monthButton = CreateModeButton("monthButton", CapacityAggregator.MonthMode);
        _weekButton.Click += (_, _) => SetMode(CapacityAggregator.WeekMode);
        _monthButton.Click += (_, _) => SetMode(CapacityAggregator.MonthMode);

        _statusLabel = new Label
        {
            Name = "statusLabel",
            Font = new Font("Microsoft YaHei UI", 8f),
            ForeColor = Color.FromArgb(110, 110, 110),
            BackColor = PageBack,
            TextAlign = ContentAlignment.MiddleLeft,
            AutoSize = false,
            Text = string.Empty,
        };

        _content.Controls.AddRange(new Control[]
        {
            _titleLabel, _prevButton, _nextButton, _dateLabel, _chart, _summaryLabel, _weekButton, _monthButton, _statusLabel,
        });

        Controls.Add(_content);
        Controls.Add(_nav);

        _selectedDate = PageStats.WeekReferenceDate;
        _statusLabel.Text = $"数据源：{Path.GetFileName(_repository.CapacityDbPath)} / {Path.GetFileName(_repository.ClassificationDbPath)}　共 {_daily.Count} 天记录";

        _content.Resize += (_, _) => LayoutContent();
        LayoutContent();
        SelectNav(0);
    }

    /// <summary>截图工具使用：切换导航页（0-6）。</summary>
    public void SelectTab(int index)
    {
        SelectNav(index);
    }

    /// <summary>当前选中的页面索引。</summary>
    public int SelectedPage => _selectedNav;

    private Label CreateModeButton(string name, string text) => new()
    {
        Name = name,
        Text = text,
        Font = new Font("Microsoft YaHei UI", 10.5f),
        ForeColor = TextColor,
        BackColor = ModeBack,
        TextAlign = ContentAlignment.MiddleCenter,
        AutoSize = false,
        Cursor = Cursors.Hand,
    };

    private IReadOnlyList<DayCapacity> SafeLoadDaily()
    {
        try
        {
            return _repository.LoadDailyCapacity();
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, "读取产能数据库失败：" + ex.Message, UiText.AppTitle, MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return Array.Empty<DayCapacity>();
        }
    }

    private void SelectNav(int index)
    {
        if (index < 0 || index >= UiText.NavItems.Length)
        {
            return;
        }

        _selectedNav = index;
        _nav.SelectedIndex = index;
        _titleLabel.Text = PageStats.PageTitle(index);
        RefreshPage();
    }

    private void ShiftPeriod(int direction)
    {
        _selectedDate = CapacityAggregator.Shift(_selectedDate, _mode, direction);
        RefreshPage();
    }

    private void SetMode(string mode)
    {
        _mode = mode;
        RefreshPage();
    }

    /// <summary>按当前页面刷新全部可见内容。</summary>
    private void RefreshPage()
    {
        var isCapacityPage = _selectedNav == 0;
        var isClassPage = _selectedNav == 3;

        _prevButton.Visible = isCapacityPage;
        _nextButton.Visible = isCapacityPage;
        _dateLabel.Visible = isCapacityPage;
        _weekButton.Visible = isCapacityPage;
        _monthButton.Visible = isCapacityPage;
        _chart.Visible = isCapacityPage || isClassPage;

        _weekButton.BackColor = _mode == CapacityAggregator.WeekMode ? ModeBack : PageBack;
        _monthButton.BackColor = _mode == CapacityAggregator.MonthMode ? ModeBack : PageBack;

        switch (_selectedNav)
        {
            case 0:
                RefreshCapacityPage();
                break;
            case 3:
                RefreshClassPage();
                break;
            default:
                _chart.Chart = null;
                _summaryLabel.Text = BuildPageSummary(_selectedNav);
                break;
        }
    }

    private void RefreshCapacityPage()
    {
        var chart = CapacityAggregator.Build(_daily, _selectedDate, _mode);
        _chart.Chart = chart;
        _dateLabel.Text = UiText.PeriodText(_selectedDate, _mode);

        var weekTotal = PageStats.WeekTotal(_daily, PageStats.WeekReferenceDate);
        var monthTotal = PageStats.MonthTotal(_daily, PageStats.MonthReferenceDate);
        _summaryLabel.Text = string.Join(
            "　",
            PageStats.WeekLine(weekTotal),
            PageStats.MonthLine(monthTotal),
            UiText.SummaryLine(chart));
    }

    private void RefreshClassPage()
    {
        try
        {
            var classes = _repository.LoadClasses();
            var infoRows = _repository.LoadFaultInfoRows();
            var chart = PageStats.BuildClassChart(classes, infoRows);
            _chart.Chart = chart;
            _summaryLabel.Text = string.Join(
                "　",
                PageStats.ClassLine(classes.Count),
                "按 Class 统计 Info 条数：" + string.Join("，", chart.Bars.Select(b => $"{b.Label} {UiText.Count(b.Value)}")));
        }
        catch (Exception ex)
        {
            _chart.Chart = null;
            _summaryLabel.Text = "读取分类数据库失败：" + ex.Message;
        }
    }

    private string BuildPageSummary(int navIndex)
    {
        try
        {
            switch (navIndex)
            {
                case 1:
                {
                    var total = _repository.LoadMinuteCapacityTotal();
                    var rows = _repository.LoadMinuteCapacityRowCount();
                    return string.Join(
                        "　",
                        PageStats.ShiftLine(total),
                        $"cap 表 {UiText.Count(rows)} 行分钟产能记录");
                }

                case 2:
                {
                    var infoRows = _repository.LoadClassificationRowCount("Info");
                    var classes = _repository.LoadClassificationRowCount("Class");
                    var categories = _repository.LoadClassificationRowCount("Category");
                    return string.Join(
                        "　",
                        PageStats.FaultLine(infoRows),
                        $"分类库：Class {UiText.Count(classes)} 行，Category {UiText.Count(categories)} 行");
                }

                case 4:
                {
                    var categories = _repository.LoadCategoryRows();
                    var infoRows = _repository.LoadFaultInfoRows();
                    var parts = categories.Select(c =>
                    {
                        var count = infoRows.Count(r => r.CategoryId == c.Id);
                        var name = string.IsNullOrWhiteSpace(c.Desc) ? c.Name : c.Desc;
                        return $"{name} {UiText.Count(count)}";
                    });
                    return string.Join(
                        "　",
                        PageStats.CategoryLine(categories.Count),
                        "按 Category 统计 Info 条数：" + string.Join("，", parts));
                }

                case 5:
                {
                    var shift = PageStats.ShiftConfigText(_repository.LoadShiftConfig());
                    return string.Join(
                        "　",
                        PageStats.PageTitle(5),
                        shift,
                        "数据目录：" + Path.GetDirectoryName(_repository.CapacityDbPath));
                }

                case 6:
                {
                    var capacityRows = _repository.LoadCapacityRange(PageStats.ExportStartDate, PageStats.ExportEndDate);
                    var infoRows = _repository.LoadFaultInfoRows();
                    return string.Join(
                        "　",
                        PageStats.PageTitle(6),
                        "导出命令：CapacityStats.exe --export <目录>",
                        $"{PageStats.CapacityCsvName}：{PageStats.ExportStartDate:yyyy-MM-dd} ~ {PageStats.ExportEndDate:yyyy-MM-dd} 共 {capacityRows.Count} 行",
                        $"{PageStats.FaultsCsvName}：Info 表共 {UiText.Count(infoRows.Count)} 行");
                }

                default:
                    return string.Empty;
            }
        }
        catch (Exception ex)
        {
            return "读取数据失败：" + ex.Message;
        }
    }

    private void LayoutContent()
    {
        var w = _content.ClientSize.Width;
        var h = _content.ClientSize.Height;
        if (w <= 0 || h <= 0)
        {
            return;
        }

        const int margin = 24;
        var inner = Math.Max(200, w - margin * 2);

        _titleLabel.SetBounds(margin, 12, inner, 56);

        const int arrowSize = 36;
        var centerX = margin + inner / 2;
        _prevButton.SetBounds(centerX - 150, 76, arrowSize, arrowSize);
        _nextButton.SetBounds(centerX + 114, 76, arrowSize, arrowSize);
        _dateLabel.SetBounds(centerX - 100, 76, 200, arrowSize);

        // 非产能统计页没有日期切换，图表上移，避免大片空白。
        var chartTop = _selectedNav == 0 ? 128 : 84;
        var chartBottom = h - 96;
        _chart.SetBounds(margin, chartTop, inner, Math.Max(120, chartBottom - chartTop));

        _summaryLabel.SetBounds(margin, chartBottom + 4, inner, 22);
        _statusLabel.SetBounds(margin, h - 24, inner, 18);

        const int modeWidth = 92;
        const int modeHeight = 38;
        var modeTop = h - 62;
        _weekButton.SetBounds(w - margin - modeWidth * 2 - 4, modeTop, modeWidth, modeHeight);
        _monthButton.SetBounds(w - margin - modeWidth, modeTop, modeWidth, modeHeight);
    }
}
