using System.Drawing.Drawing2D;

namespace CapacityStats;

/// <summary>
/// 圆形箭头按钮（日期切换）：白底、深色圆环、内部左右箭头。
/// </summary>
public sealed class CircleArrowButton : Control
{
    private bool _hover;
    private bool _pressed;

    public CircleArrowButton()
    {
        SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint | ControlStyles.ResizeRedraw | ControlStyles.SupportsTransparentBackColor, true);
        BackColor = Color.Transparent;
        Cursor = Cursors.Hand;
        Size = new Size(36, 36);
    }

    /// <summary>true 表示指向左（上一周期），false 表示指向右（下一周期）。</summary>
    public bool PointLeft { get; set; }

    protected override void OnMouseEnter(EventArgs e)
    {
        base.OnMouseEnter(e);
        _hover = true;
        Invalidate();
    }

    protected override void OnMouseLeave(EventArgs e)
    {
        base.OnMouseLeave(e);
        _hover = false;
        _pressed = false;
        Invalidate();
    }

    protected override void OnMouseDown(MouseEventArgs e)
    {
        base.OnMouseDown(e);
        _pressed = true;
        Invalidate();
    }

    protected override void OnMouseUp(MouseEventArgs e)
    {
        base.OnMouseUp(e);
        _pressed = false;
        Invalidate();
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e);
        var g = e.Graphics;
        g.SmoothingMode = SmoothingMode.AntiAlias;
        g.Clear(Parent?.BackColor ?? Color.White);

        var d = Math.Min(Width, Height) - 4;
        var rect = new Rectangle((Width - d) / 2, (Height - d) / 2, d, d);
        using var fill = new SolidBrush(_pressed ? Color.FromArgb(225, 235, 245) : _hover ? Color.FromArgb(240, 246, 252) : Color.White);
        using var ring = new Pen(Color.FromArgb(30, 30, 30), 2f);
        g.FillEllipse(fill, rect);
        g.DrawEllipse(ring, rect);

        var cx = rect.Left + rect.Width / 2f;
        var cy = rect.Top + rect.Height / 2f;
        var r = rect.Width * 0.22f;
        using var arrowPen = new Pen(Color.FromArgb(30, 30, 30), 2.4f)
        {
            StartCap = LineCap.Round,
            EndCap = LineCap.Round,
            LineJoin = LineJoin.Round,
        };

        var dir = PointLeft ? -1 : 1;
        g.DrawLines(arrowPen, new[]
        {
            new PointF(cx + dir * r * 0.6f, cy - r),
            new PointF(cx - dir * r * 0.6f, cy),
            new PointF(cx + dir * r * 0.6f, cy + r),
        });
    }
}
