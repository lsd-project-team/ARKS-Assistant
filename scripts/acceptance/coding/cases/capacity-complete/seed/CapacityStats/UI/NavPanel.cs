using System.Drawing.Drawing2D;

namespace CapacityStats;

/// <summary>
/// 左侧导航栏：顶部返回箭头 + 导航项（选中项高亮），底部“设置 / 信息导出”。
/// </summary>
public sealed class NavPanel : Control
{
    private static readonly Color NavBack = Color.FromArgb(205, 225, 245);
    private static readonly Color SelectedBack = Color.FromArgb(150, 190, 230);
    private static readonly Color ArrowBack = Color.FromArgb(185, 215, 245);
    private static readonly Color TextColor = Color.FromArgb(20, 20, 20);

    private readonly List<Rectangle> _itemBounds = new();
    private readonly List<Rectangle> _bottomBounds = new();
    private int _selectedIndex;
    private int _hoverIndex = -1;

    public NavPanel()
    {
        SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint | ControlStyles.ResizeRedraw, true);
        BackColor = NavBack;
        Name = "navPanel";
        Cursor = Cursors.Hand;
    }

    /// <summary>顶部导航项（不含底部两项）。</summary>
    public string[] TopItems { get; set; } = Array.Empty<string>();

    /// <summary>底部导航项。</summary>
    public string[] BottomItems { get; set; } = Array.Empty<string>();

    public int SelectedIndex
    {
        get => _selectedIndex;
        set
        {
            if (_selectedIndex == value)
            {
                return;
            }

            _selectedIndex = value;
            Invalidate();
        }
    }

    public event EventHandler? BackClicked;

    public event EventHandler<int>? ItemClicked;

    private Rectangle ArrowBounds => new(8, 8, Math.Max(10, Width - 16), 56);

    protected override void OnMouseMove(MouseEventArgs e)
    {
        base.OnMouseMove(e);
        var index = HitTest(e.Location);
        if (index != _hoverIndex)
        {
            _hoverIndex = index;
            Invalidate();
        }
    }

    protected override void OnMouseLeave(EventArgs e)
    {
        base.OnMouseLeave(e);
        _hoverIndex = -1;
        Invalidate();
    }

    protected override void OnMouseClick(MouseEventArgs e)
    {
        base.OnMouseClick(e);
        if (ArrowBounds.Contains(e.Location))
        {
            BackClicked?.Invoke(this, EventArgs.Empty);
            return;
        }

        var index = HitTest(e.Location);
        if (index >= 0)
        {
            SelectedIndex = index;
            ItemClicked?.Invoke(this, index);
        }
    }

    private int HitTest(Point point)
    {
        for (var i = 0; i < _itemBounds.Count; i++)
        {
            if (_itemBounds[i].Contains(point))
            {
                return i;
            }
        }

        for (var i = 0; i < _bottomBounds.Count; i++)
        {
            if (_bottomBounds[i].Contains(point))
            {
                return _itemBounds.Count + i;
            }
        }

        return -1;
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e);
        var g = e.Graphics;
        g.SmoothingMode = SmoothingMode.AntiAlias;
        g.Clear(BackColor);

        // 返回箭头
        var arrow = ArrowBounds;
        using (var arrowBrush = new SolidBrush(ArrowBack))
        {
            g.FillRectangle(arrowBrush, arrow);
        }

        using (var arrowPen = new Pen(Color.White, 9f))
        {
            arrowPen.StartCap = LineCap.Round;
            arrowPen.EndCap = LineCap.Round;
            var cx = arrow.Left + arrow.Width / 2f;
            var cy = arrow.Top + arrow.Height / 2f;
            g.DrawLine(arrowPen, cx + 16, cy - 16, cx - 16, cy);
            g.DrawLine(arrowPen, cx - 16, cy, cx + 16, cy + 16);
        }

        _itemBounds.Clear();
        _bottomBounds.Clear();

        using var font = new Font("Microsoft YaHei UI", 10.5f, FontStyle.Bold);
        using var textBrush = new SolidBrush(TextColor);
        using var selectedBrush = new SolidBrush(SelectedBack);
        using var hoverBrush = new SolidBrush(Color.FromArgb(190, 215, 240));

        var y = arrow.Bottom + 8;
        const int itemHeight = 46;
        for (var i = 0; i < TopItems.Length; i++)
        {
            var rect = new Rectangle(0, y, Width, itemHeight);
            _itemBounds.Add(rect);
            if (i == SelectedIndex)
            {
                g.FillRectangle(selectedBrush, rect);
            }
            else if (i == _hoverIndex)
            {
                g.FillRectangle(hoverBrush, rect);
            }

            DrawCentered(g, TopItems[i], font, textBrush, rect);
            y += itemHeight;
        }

        var by = Height - 8 - itemHeight * BottomItems.Length;
        for (var i = 0; i < BottomItems.Length; i++)
        {
            var rect = new Rectangle(0, by, Width, itemHeight);
            _bottomBounds.Add(rect);
            var index = TopItems.Length + i;
            if (index == SelectedIndex)
            {
                g.FillRectangle(selectedBrush, rect);
            }
            else if (index == _hoverIndex)
            {
                g.FillRectangle(hoverBrush, rect);
            }

            DrawCentered(g, BottomItems[i], font, textBrush, rect);
            by += itemHeight;
        }
    }

    private static void DrawCentered(Graphics g, string text, Font font, Brush brush, Rectangle rect)
    {
        var size = g.MeasureString(text, font);
        g.DrawString(text, font, brush, rect.Left + (rect.Width - size.Width) / 2f, rect.Top + (rect.Height - size.Height) / 2f);
    }
}
