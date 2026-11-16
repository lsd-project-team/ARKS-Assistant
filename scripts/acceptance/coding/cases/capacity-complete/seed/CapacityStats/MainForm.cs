using System.Drawing;
using System.Windows.Forms;

namespace CapacityStats;

/// <summary>
/// 主窗体：左侧导航 + 右侧内容区（标题、日期切换、柱状图、周/月统计切换）。
/// 内容区使用自绘面板，保证截图与布局在任意 DPI 下稳定。
/// </summary>
public sealed class MainForm : Form
{
    private static readonly Color PageBack = Color.FromArgb(243, 243, 243);
    private static readonly Color NavBack = Color.FromArgb(205, 225, 245);
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
            Text = UiText.NavItems[0],
            Font = new Font("Microsoft YaHei UI", 26f, FontStyle.Regular),
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

        _selectedDate = _repository.LatestCapacityDate() ?? DateTime.Today;
        _statusLabel.Text = $"数据源：{Path.GetFileName(_repository.CapacityDbPath)} / {Path.GetFileName(_repository.ClassificationDbPath)}　共 {_daily.Count} 天记录";

        _content.Resize += (_, _) => LayoutContent();
        LayoutContent();
        RefreshChart();
    }

    /// <summary>截图工具使用：切换导航页。</summary>
    public void SelectTab(int index)
    {
        SelectNav(index);
    }

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
        _titleLabel.Text = UiText.NavItems[index];
        RefreshChart();
    }

    private void ShiftPeriod(int direction)
    {
        _selectedDate = CapacityAggregator.Shift(_selectedDate, _mode, direction);
        RefreshChart();
    }

    private void SetMode(string mode)
    {
        _mode = mode;
        RefreshChart();
    }

    private void RefreshChart()
    {
        var chart = CapacityAggregator.Build(_daily, _selectedDate, _mode);
        _chart.Chart = chart;
        _dateLabel.Text = UiText.PeriodText(_selectedDate, _mode);
        _summaryLabel.Text = UiText.SummaryLine(chart);

        _weekButton.BackColor = _mode == CapacityAggregator.WeekMode ? ModeBack : PageBack;
        _monthButton.BackColor = _mode == CapacityAggregator.MonthMode ? ModeBack : PageBack;

        // 非“产能统计”页展示对应数据摘要，标题与日期切换保持一致。
        if (_selectedNav != 0)
        {
            _summaryLabel.Text = BuildPageSummary(_selectedNav);
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
                    var states = _repository.LoadStateStatistics();
                    var total = states.Sum(s => s.Count);
                    var parts = states.Select(s => $"{UiText.StateName(s.State)} {UiText.Count(s.Count)}");
                    return $"工况统计：共 {UiText.Count(total)} 条状态记录（{string.Join("，", parts)}）";
                }

                case 2:
                {
                    var details = _repository.LoadFaultDetails(1);
                    var categories = _repository.LoadFaultCategories();
                    var total = categories.Sum(c => c.Count);
                    var latest = details.Count > 0 ? UiText.DateText(details[0].Date) + " " + details[0].Time : "-";
                    return $"故障统计：共 {UiText.Count(total)} 条故障记录，最近一条 {latest}";
                }

                case 3:
                {
                    var categories = _repository.LoadFaultCategories();
                    var parts = categories.Where(c => c.Count > 0).Select(c => $"{c.CategoryDesc} {UiText.Count(c.Count)}");
                    return $"故障分类及趋势：{string.Join("，", parts)}";
                }

                case 4:
                {
                    var details = _repository.LoadFaultDetails(1);
                    if (details.Count == 0)
                    {
                        return "故障分析：暂无故障记录";
                    }

                    var row = details[0];
                    return $"故障分析：最近故障 {row.Code} {row.Name}（{row.CategoryName}）";
                }

                case 5:
                {
                    var shift = _repository.LoadShiftConfig();
                    var flat = shift.Replace("\r", " ").Replace("\n", " ").Replace("\t", " ").Trim();
                    while (flat.Contains("  ", StringComparison.Ordinal))
                    {
                        flat = flat.Replace("  ", " ", StringComparison.Ordinal);
                    }

                    return "设置：班次配置 " + (string.IsNullOrEmpty(flat) ? "（未配置）" : flat);
                }

                case 6:
                    return $"信息导出：数据目录 {Path.GetDirectoryName(_repository.CapacityDbPath)}";

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

        var chartTop = 128;
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
