// 固定验证入口：只加载本次Simulation输出，运行原业务和用户可审阅的断言。
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Windows.Forms;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using HarmonyLib;

namespace CodeWork
{
    public static class Harness
    {
        internal static readonly Assembly App = Assembly.LoadFrom(Path.Combine(Application.StartupPath, "AKRS.ZX2200.exe"));
        internal static readonly List<object> Results = new List<object>();
        internal static int Assertions;
        internal static Exception UiError;
        private static readonly Dictionary<MethodBase, int> Calls = new Dictionary<MethodBase, int>();

        public static int CountCalls(MethodBase method, Action action)
        {
            var patch = new Harmony("CodeWork.Requirement.Count." + Guid.NewGuid().ToString("N"));
            var prefix = typeof(Harness).GetMethod("Count", BindingFlags.NonPublic | BindingFlags.Static);
            Calls[method] = 0;
            patch.Patch(method, new HarmonyMethod(prefix));
            try { action(); return Calls[method]; }
            finally { patch.Unpatch(method, HarmonyPatchType.Prefix, patch.Id); Calls.Remove(method); }
        }

        private static void Count(MethodBase __originalMethod)
        {
            if (Calls.ContainsKey(__originalMethod)) Calls[__originalMethod]++;
        }

        public static void Check(bool condition, string description)
        {
            Assertions++;
            Console.WriteLine((condition ? "PASS: " : "FAIL: ") + description);
            if (!condition) throw new InvalidOperationException(description);
        }

        public static object Invoke(object value, string method, params object[] args)
        {
            var type = value as Type ?? value.GetType();
            var flags = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.FlattenHierarchy | (value is Type ? BindingFlags.Static : BindingFlags.Instance);
            var methods = type.GetMethods(flags).Where(m => m.Name == method && m.GetParameters().Length == args.Length).ToArray();
            if (methods.Length != 1) throw new MissingMethodException(type.FullName, method + "（参数数=" + args.Length + "，匹配数=" + methods.Length + "）");
            var target = methods[0];
            try { return target.Invoke(value is Type ? null : value, args); }
            catch (TargetInvocationException error) { throw error.InnerException ?? error; }
        }

        internal static object Singleton(string name)
        {
            var type = App.GetType(name) ?? AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType(name)).FirstOrDefault(t => t != null);
            if (type == null)
                foreach (var file in Directory.GetFiles(Application.StartupPath, "AKRS.*.dll"))
                {
                    type = Assembly.LoadFrom(file).GetType(name);
                    if (type != null) break;
                }
            if (type == null) throw new TypeLoadException("找不到原工程类型：" + name);
            return Invoke(type, "GetInstance");
        }

        internal static Type Simulation(string name)
        {
            return App.GetType("AKRS.ZX2200.Infrastructure.Simulation." + name, true);
        }

        internal static void Initialize(bool desktop)
        {
            if (!string.Equals(new DirectoryInfo(Application.StartupPath).Name, "Simulation", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("必须在独立Simulation目录执行");
            var enabled = Simulation("OriginalSimulation").GetProperty("IsEnabled", BindingFlags.NonPublic | BindingFlags.Static);
            if (!(bool)enabled.GetValue(null)) throw new InvalidOperationException("拒绝对非Simulation程序运行验证");
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            DevExpress.Utils.AppearanceObject.DefaultFont = new System.Drawing.Font("Tahoma", 9);
            DevExpress.XtraEditors.WindowsFormsSettings.DefaultFont = new System.Drawing.Font("Tahoma", 9, System.Drawing.FontStyle.Bold);
            DevExpress.XtraEditors.WindowsFormsSettings.DefaultMenuFont = new System.Drawing.Font("Tahoma", 9, System.Drawing.FontStyle.Bold);
            DevExpress.UserSkins.BonusSkins.Register();
            DevExpress.Skins.SkinManager.EnableFormSkins();
            DevExpress.LookAndFeel.UserLookAndFeel.Default.SetSkinStyle("Office 2010 Blue");
            Application.SetUnhandledExceptionMode(UnhandledExceptionMode.CatchException);
            Application.ThreadException += (sender, args) => { UiError = args.Exception; };
            Invoke(Simulation("OriginalSimulationChecks"), "InstallDialogCapture");
            Invoke(Simulation("OriginalSimulation"), "Initialize");
            if (!desktop)
            {
                Invoke(Singleton("AKRS.ZX2200.Main.Machine.MachineSupport.Machine"), "DataLoad");
                Invoke(Singleton("AKRS.ZX2200.SupportFeature.Consumables.ConsumablesProgram"), "ScanConsumables");
            }
        }

        internal static void Save(string kind)
        {
            File.WriteAllText(Path.Combine(Application.StartupPath, "code-work-" + kind + ".json"), JsonConvert.SerializeObject(new { kind, results = Results }, Formatting.Indented));
        }

        private static int Requirements()
        {
            var cases = JArray.Parse(File.ReadAllText(Path.Combine(Application.StartupPath, "code-work-cases.json")));
            bool failed = false;
            foreach (JObject test in cases)
            {
                var id = (string)test["id"];
                Assertions = 0;
                string error = null;
                try
                {
                    RequirementCases.All[id]();
                    if (Assertions == 0) throw new InvalidOperationException("测试没有执行Check断言，不能视为通过");
                }
                catch (Exception exception) { error = exception.ToString(); failed = true; Console.WriteLine(error); }
                Results.Add(new { id, name = (string)test["name"], expectation = (string)test["expectation"], assertions = Assertions, status = error == null ? "passed" : "failed", error });
            }
            Save("requirements");
            return failed ? 1 : 0;
        }

        [STAThread]
        public static int Main(string[] args)
        {
            string kind = args.Length == 1 && args[0] == "desktop" ? "desktop" : "requirements";
            int code = 1;
            try { Initialize(kind == "desktop"); code = kind == "desktop" ? DesktopFlow.Run() : Requirements(); }
            catch (Exception error)
            {
                Console.WriteLine(error);
                Results.Add(new { id = "startup", status = "failed", assertions = 0, error = error.ToString() });
                Save(kind);
            }
            finally
            {
                try { Invoke(Singleton("AKRS.ZX2200.Main.Machine.MachineSupport.Machine"), "Stop"); } catch { }
            }
            Console.WriteLine(code == 0 ? "PASS: code-work " + kind : "FAIL: code-work " + kind);
            Environment.Exit(code); // 结束本次独立进程及其后台线程，不操作其他仿真实例。
            return code;
        }
    }
}
