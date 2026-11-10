// 在独立子进程实例化原主窗体，以原按钮事件驱动流程；截图仅作证据，状态与产量另行断言。
using System;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;
using System.Linq;
using AKRS.Galaxy2.LogicHardware.Hardwares.MotionControllers;
using AKRS.Galaxy2.LogicHardware.Repository;

namespace CodeWork
{
    internal static class DesktopFlow
    {
        private static Form Form;
        private static object Control;
        private static object Machine;
        private static int ScreenshotIndex;
        private sealed class TestForm : AKRS.ZX2200.Main.Controls.MainForm
        {
            protected override bool ShowWithoutActivation { get { return true; } }
        }
        [DllImport("user32.dll")]
        private static extern bool PrintWindow(IntPtr window, IntPtr dc, uint flags);

        private static bool HasContent(Bitmap image)
        {
            var colors = new System.Collections.Generic.HashSet<int>();
            for (int y = 50; y < image.Height - 20; y += 8)
                for (int x = 20; x < image.Width - 20; x += 8)
                {
                    colors.Add(image.GetPixel(x, y).ToArgb());
                    if (colors.Count > 32) return true;
                }
            return false;
        }

        private static void Wait(Func<bool> condition, int seconds)
        {
            var clock = Stopwatch.StartNew();
            while (!condition())
            {
                if (Harness.UiError != null) throw new InvalidOperationException("原界面UI线程异常", Harness.UiError);
                if (clock.Elapsed.TotalSeconds > seconds) throw new TimeoutException("原界面操作未在时限内达到预期状态");
                Application.DoEvents();
                Thread.Sleep(20);
            }
            Application.DoEvents();
        }

        private static object Property(object instance, string name)
        {
            return instance.GetType().GetProperty(name).GetValue(instance);
        }

        private static void Click(string name)
        {
            var field = Control.GetType().GetField(name, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            if (field == null) throw new MissingFieldException("找不到原界面按钮：" + name);
            var button = field.GetValue(Control);
            Wait(() => button != null && (bool)Property(button, "Enabled"), 10);
            Harness.Check(button != null && (bool)Property(button, "Enabled"), "原按钮可用：" + name);
            Harness.Invoke(button, "PerformClick");
        }

        private static void Step(string id, string name, Action action)
        {
            Harness.Assertions = 0;
            string error = null;
            try { action(); }
            catch (Exception exception) { error = exception.ToString(); }
            string screenshot = "code-work-ui-" + (ScreenshotIndex++).ToString("00") + ".png";
            try
            {
                using (var image = new Bitmap(Form.Width, Form.Height))
                {
                    Form.Refresh();
                    Application.DoEvents();
                    Form.DrawToBitmap(image, new Rectangle(Point.Empty, Form.Size));
                    if (!HasContent(image))
                        using (var graphics = Graphics.FromImage(image))
                        {
                            var dc = graphics.GetHdc();
                            try { PrintWindow(Form.Handle, dc, 0); }
                            finally { graphics.ReleaseHdc(dc); }
                        }
                    if (!HasContent(image)) throw new InvalidOperationException("截图缺少原界面内容，不能作为流程通过证据");
                    image.Save(Path.Combine(Application.StartupPath, screenshot), ImageFormat.Png);
                }
            }
            catch (Exception exception) { error = (error ?? "") + "\n截图失败：" + exception; }
            Harness.Results.Add(new { id, name, status = error == null ? "passed" : "failed", assertions = Harness.Assertions, screenshot, error });
            Harness.Save("desktop");
            if (error != null) throw new InvalidOperationException(name + "未通过：" + error);
        }

        internal static int Run()
        {
            Machine = Harness.Singleton("AKRS.ZX2200.Main.Machine.MachineSupport.Machine");
            Form = new TestForm();
            var formType = Harness.App.GetType("AKRS.ZX2200.Main.Controls.MainForm", true);
            var callback = Delegate.CreateDelegate(typeof(Action<Action>), Form, formType.GetMethod("PostAction", BindingFlags.NonPublic | BindingFlags.Instance));
            formType.GetField("SendUiAction", BindingFlags.Public | BindingFlags.Static).SetValue(null, callback);
            // 独立窗体在屏幕外渲染，不向用户正在运行的程序发送键鼠事件。
            Form.StartPosition = FormStartPosition.Manual;
            Form.WindowState = FormWindowState.Normal;
            Form.Location = new Point(-20000, -20000);
            Form.Size = new Size(1600, 900);
            Form.ShowInTaskbar = false;
            Form.Show();
            Step("loaded", "原主界面加载", () =>
            {
                Wait(() => { Control = Property(Form, "UcMainSystem"); return Control is System.Windows.Forms.Control && ((System.Windows.Forms.Control)Control).Visible; }, 30);
                Console.WriteLine("UI frame=" + Form.Bounds + ", main=" + ((System.Windows.Forms.Control)Control).Bounds + ", visible=" + ((System.Windows.Forms.Control)Control).Visible);
                Harness.Check(Form.IsHandleCreated && Control is System.Windows.Forms.Control, "原MainForm和主系统控件已创建");
                Harness.Check(Harness.UiError == null, "原界面无UI线程异常");
            });
            var configuration = Harness.Singleton("AKRS.ZX2200.Main.Machine.MachineSupport.MachineSoftwareConfiguration");
            configuration.GetType().GetProperty("RecipeWarningBeforeMachineStart").SetValue(configuration, false);
            var statistics = Harness.Singleton("AKRS.ZX2200.SupportFeature.Statistics.StatisticsDomain");
            int bonded = Convert.ToInt32(Property(statistics, "AllBondedNumber"));
            int dispensed = Convert.ToInt32(Property(statistics, "AllDispensedNumber"));
            Step("reset", "点击原整机复位按钮", () =>
            {
                var stage = Harness.Simulation("OriginalSimulationChecks").GetField("step", BindingFlags.NonPublic | BindingFlags.Static);
                stage.SetValue(null, "原去上视与整机复位");
                try { Click("BtInitialize"); }
                finally { stage.SetValue(null, "桌面按钮流程"); }
                Wait(() => (bool)Property(Machine, "AllAxisReset"), 30);
                Harness.Check((bool)Property(Machine, "AllAxisReset"), "原整机复位已完成");
                Harness.Check(HardwareRepositoryService.GetHardwaresByType<Axis>().All(axis => axis.IsAtHome()), "全部虚拟轴提供回零反馈");
            });
            Step("start", "点击原启动按钮", () => { Click("BtStart"); Wait(() => (bool)Harness.Invoke(Machine, "IsWorking"), 10); Harness.Check((bool)Harness.Invoke(Machine, "IsWorking"), "启动后进入工作状态"); });
            Step("pause", "点击原暂停按钮", () => { Click("BtPause"); Wait(() => Property(Harness.Singleton("AKRS.Galaxy2.Machine.Models.MachineStateModel"), "MachineState").ToString() == "Pause", 10); Harness.Check(Property(Harness.Singleton("AKRS.Galaxy2.Machine.Models.MachineStateModel"), "MachineState").ToString() == "Pause", "暂停后状态为Pause"); });
            Step("continue", "点击原继续按钮", () => { Click("BtContinue"); Wait(() => (bool)Harness.Invoke(Machine, "IsWorking"), 10); Harness.Check((bool)Harness.Invoke(Machine, "IsWorking"), "继续后恢复工作状态"); });
            Step("production", "原界面运行示例生产", () => { Wait(() => Convert.ToInt32(Property(statistics, "AllBondedNumber")) > bonded && Convert.ToInt32(Property(statistics, "AllDispensedNumber")) > dispensed, 100); Harness.Check(Convert.ToInt32(Property(statistics, "AllBondedNumber")) > bonded && Convert.ToInt32(Property(statistics, "AllDispensedNumber")) > dispensed, "原点胶和固晶产量实际增加"); });
            Step("stop", "点击原停止按钮", () => { Click("BtCancel"); Wait(() => (bool)Harness.Invoke(Machine, "IsStop") && (bool)Harness.Invoke(Machine, "IsAllowTaskClosed"), 15); Harness.Check((bool)Harness.Invoke(Machine, "IsStop") && (bool)Harness.Invoke(Machine, "IsAllowTaskClosed"), "停止后原任务退出"); });
            return 0;
        }
    }
}
