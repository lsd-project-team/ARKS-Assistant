using System.Globalization;
using System.Text;

namespace CapacityStats;

internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        ApplicationConfiguration.Initialize();

        // 截图契约: --screenshot <png路径> <标签页索引>
        if (args.Length >= 2 && string.Equals(args[0], "--screenshot", StringComparison.OrdinalIgnoreCase))
        {
            return ScreenshotTool.Run(args[1], args.Length > 2 ? args[2] : "0");
        }

        Application.Run(new MainForm());
        return 0;
    }
}

/// <summary>
/// 离屏渲染主窗体并保存 PNG，同时把全部控件的 bounds 递归打印到标准输出。
/// </summary>
internal static class ScreenshotTool
{
    public static int Run(string pngPath, string tabIndexText)
    {
        int tabIndex = int.TryParse(tabIndexText, NumberStyles.Integer, CultureInfo.InvariantCulture, out var parsed)
            ? parsed
            : 0;

        using var form = new MainForm();
        form.SelectTab(tabIndex);
        form.Show();
        Application.DoEvents();
        form.Refresh();
        Application.DoEvents();

        var full = Path.GetFullPath(pngPath);
        var dir = Path.GetDirectoryName(full);
        if (!string.IsNullOrEmpty(dir))
        {
            Directory.CreateDirectory(dir);
        }

        using (var bmp = new Bitmap(form.Width, form.Height))
        {
            form.DrawToBitmap(bmp, new Rectangle(0, 0, form.Width, form.Height));
            bmp.Save(full, System.Drawing.Imaging.ImageFormat.Png);
        }

        var sb = new StringBuilder();
        sb.AppendLine($"SCREENSHOT {full}");
        sb.AppendLine($"FORM {form.Width}x{form.Height} title=\"{form.Text}\"");
        DumpControls(form, sb, 0);
        Console.Out.Write(sb.ToString());
        Console.Out.Flush();

        form.Close();
        return 0;
    }

    private static void DumpControls(Control parent, StringBuilder sb, int depth)
    {
        foreach (Control child in parent.Controls)
        {
            var b = child.Bounds;
            var text = (child.Text ?? string.Empty).Replace("\r", " ").Replace("\n", " ");
            if (text.Length > 40)
            {
                text = text[..40] + "…";
            }

            sb.AppendLine(
                $"{new string(' ', depth * 2)}[{child.GetType().Name}] name={child.Name} " +
                $"bounds={b.X},{b.Y},{b.Width},{b.Height} visible={child.Visible} text=\"{text}\"");
            DumpControls(child, sb, depth + 1);
        }
    }
}
