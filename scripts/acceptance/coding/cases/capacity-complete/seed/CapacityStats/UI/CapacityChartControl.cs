using System.Drawing.Drawing2D;

namespace CapacityStats;

/// <summary>
/// 产能柱状图：左侧 K 轴刻度 + 横向网格线，底部日期标签，柱顶竖排数值。
/// </summary>
public sealed class CapacityChartControl : Control
{
    private CapacityChart? _chart;

    private static readonly Color AxisColor = Color.FromArgb(60, 60, 60);
    private static readonly Color GridColor = Color.FromArgb(90, 90, 90);
    private static readonly Color BarColor = Color.FromArgb(120, 168, 224);
    private static readonly Color BarEdge = Color.FromArgb(90, 140, 200);
    private static readonly Color LabelColor = Color.FromArgb(40, 40, 40);

    public CapacityChartControl()
    {
        SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint | ControlStyles.ResizeRedraw, true);
        BackColor = Color.White;
        Name = "capacityChart";
    }

    public CapacityChart? Chart
    {
        get => _chart;
        set
        {
            _chart = value;
            Invalidate();
        }
    }

    /// <summary>当前图表的最大值（供自测/日志使用）。</summary>
    public long MaxValue => _chart is null ? 0 : CapacityAggregator.Max(_chart.Bars);

    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e);
        var g = e.Graphics;
        g.SmoothingMode = SmoothingMode.AntiAlias;
        g.Clear(BackColor);

        var chart = _chart;
        if (chart is null || chart.Bars.Count == 0)
        {
            using var emptyFont = new Font("Microsoft YaHei UI", 10f);
            using var emptyBrush = new SolidBrush(Color.Gray);
            g.DrawString("暂无数据", emptyFont, emptyBrush, new PointF(12, 12));
            return;
        }

        const int axisLeft = 62;
        const int axisRight = 10;
        const int axisTop = 8;
        const int axisBottom = 34;
        const int tickCount = 5;

        var plot = new Rectangle(
            axisLeft,
            axisTop,
            Math.Max(10, Width - axisLeft - axisRight),
            Math.Max(10, Height - axisTop - axisBottom));

        var max = CapacityAggregator.AxisMax(CapacityAggregator.Max(chart.Bars));

        using var axisPen = new Pen(AxisColor, 1f);
        using var gridPen = new Pen(GridColor, 1f);
        using var axisFont = new Font("Microsoft YaHei UI", 9f);
        using var labelFont = new Font("Microsoft YaHei UI", 8f);
        using var valueFont = new Font("Microsoft YaHei UI", 7.5f);
        using var axisBrush = new SolidBrush(LabelColor);
        using var barBrush = new SolidBrush(BarColor);
        using var barPen = new Pen(BarEdge, 1f);

        for (var i = 0; i <= tickCount; i++)
        {
            var value = max * i / tickCount;
            var y = plot.Bottom - (int)Math.Round(plot.Height * (i / (double)tickCount));
            g.DrawLine(i == 0 ? axisPen : gridPen, plot.Left, y, plot.Right, y);

            var text = CapacityAggregator.FormatShort(value);
            var size = g.MeasureString(text, axisFont);
            g.DrawString(text, axisFont, axisBrush, plot.Left - 8 - size.Width, y - size.Height / 2f);
        }

        g.DrawLine(axisPen, plot.Left, plot.Top, plot.Left, plot.Bottom);

        var slot = plot.Width / (float)chart.Bars.Count;
        var barWidth = Math.Max(6f, Math.Min(34f, slot * 0.42f));

        for (var i = 0; i < chart.Bars.Count; i++)
        {
            var bar = chart.Bars[i];
            var center = plot.Left + slot * (i + 0.5f);
            var height = max <= 0 ? 0f : (float)(plot.Height * (bar.Value / (double)max));
            var rect = new RectangleF(center - barWidth / 2f, plot.Bottom - height, barWidth, height);

            if (height > 0.5f)
            {
                g.FillRectangle(barBrush, rect);
                g.DrawRectangle(barPen, rect.X, rect.Y, rect.Width, rect.Height);
            }

            // 柱顶竖排数值
            var valueText = bar.Value.ToString();
            var state = g.Save();
            g.TranslateTransform(center, plot.Bottom - height - 6f);
            g.RotateTransform(-90f);
            var vs = g.MeasureString(valueText, valueFont);
            g.DrawString(valueText, valueFont, axisBrush, -vs.Width, -vs.Height);
            g.Restore(state);

            // 底部日期标签
            var labelSize = g.MeasureString(bar.Label, labelFont);
            var lx = center - labelSize.Width / 2f;
            if (lx < plot.Left - 12)
            {
                lx = plot.Left - 12;
            }

            if (lx + labelSize.Width > plot.Right + 12)
            {
                lx = plot.Right + 12 - labelSize.Width;
            }

            g.DrawString(bar.Label, labelFont, axisBrush, lx, plot.Bottom + 8);
        }
    }
}
