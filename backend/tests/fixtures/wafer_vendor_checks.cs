// 独立验收程序：不使用模型编写的断言，仅读取新生成的 Simulation 程序。
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using System.Text;
using System.Runtime.Serialization;
using HarmonyLib;

class WaferVendorChecks
{
    const string AdapterName = "AKRS.ZX2200.WaferSubSystem.Services.SimWaferBMapAdapter";
    const string BlockName = "AKRS.ZX2200.WaferSubSystem.Models.Entities.SearchChip.Block";
    static MethodInfo normalize, prepare;
    static int assertions;
    static bool failed;
    static string work;
    static string opened;

    static bool CaptureOpen(object[] __args) { opened = (string)__args[0]; return false; }

    // 仅替换最后的 UI 打开动作，真实执行 Block.LoadMap 的查找、复制和适配逻辑。
    static void ImportEntry(Assembly app, string sample)
    {
        const BindingFlags instance = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
        var blockType = app.GetType(BlockName, true);
        var block = FormatterServices.GetUninitializedObject(blockType);
        var carrierType = app.GetType("AKRS.ZX2200.WaferSubSystem.Models.Repositories.CarrierWithWafer.CarrierWithWaferConfig", true);
        var carrier = Activator.CreateInstance(carrierType);
        carrierType.GetProperty("Name").SetValue(carrier, "legacy-entry");
        blockType.GetField("currentCarrierConfig", instance).SetValue(block, carrier);
        var mapProperty = blockType.GetProperty("WaferMapII", instance);
        mapProperty.SetValue(block, FormatterServices.GetUninitializedObject(mapProperty.PropertyType));
        var parameterType = app.GetType("AKRS.ZX2200.WaferSubSystem.Models.DeviceParams.WaferSubDevicePara", true);
        var parameters = FormatterServices.GetUninitializedObject(parameterType);
        var tableProperty = parameterType.GetProperty("WaferTableDevicePara");
        var table = FormatterServices.GetUninitializedObject(tableProperty.PropertyType);
        tableProperty.SetValue(parameters, table);
        parameterType.BaseType.GetField("instance", BindingFlags.Static | BindingFlags.NonPublic).SetValue(null, parameters);
        string destination = Path.Combine(work, "entry-cache");
        Directory.CreateDirectory(destination);
        table.GetType().GetProperty("WaferMapFilePath").SetValue(table, destination);
        var ui = app.GetType("AKRS.ZX2200.Main.Controls.MainForm", true).GetField("SendUiAction");
        ui.SetValue(null, new Action<Action>(action => action()));
        var patch = new Harmony("WaferVendorChecks.UILeaf");
        var open = mapProperty.PropertyType.GetMethod("OpenFile", new[] { typeof(string) });
        patch.Patch(open, new HarmonyMethod(typeof(WaferVendorChecks).GetMethod("CaptureOpen", BindingFlags.Static | BindingFlags.NonPublic)));
        string repository = Path.Combine(Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location), "Config1");
        Directory.CreateDirectory(repository);
        string oldSource = Path.Combine(repository, "legacy-entry");
        File.WriteAllText(oldSource, "old map sentinel");
        try
        {
            opened = null;
            blockType.GetMethod("LoadMap").Invoke(block, new object[] { "legacy-entry", false });
            Check(opened != null && File.ReadAllText(opened) == "old map sentinel", "真实 LoadMap 旧格式查找与复制仍成功");
            Check(File.ReadAllText(oldSource) == "old map sentinel", "真实导入未改旧原件");
            carrierType.GetProperty("Name").SetValue(carrier, "vendor-entry");
            string newSource = Path.Combine(repository, "vendor-entry.svb.csv");
            File.WriteAllText(newSource, sample);
            opened = null;
            blockType.GetMethod("LoadMap").Invoke(block, new object[] { "vendor-entry", true });
            Check(opened != null && Path.GetExtension(opened).Equals(".AKRS", StringComparison.OrdinalIgnoreCase), "真实 LoadMap 按载具名定位复合后缀并打开转换结果");
            Matrix(File.ReadAllText(opened), "...2", "..1.", "1...");
            Check(File.ReadAllText(newSource) == sample, "真实导入未改新厂商原件");
        }
        finally { patch.UnpatchAll(patch.Id); }
    }

    static void Check(bool value, string message)
    {
        Console.WriteLine((value ? "PASS: " : "FAIL: ") + message);
        assertions++;
        if (!value) throw new Exception(message);
    }

    static object Call(MethodInfo method, params object[] args)
    {
        try { return method.Invoke(null, args); }
        catch (TargetInvocationException error) { throw error.InnerException ?? error; }
    }

    static string Csv(int rows, int columns, string records, string id = "SIM-B-001")
    {
        return "#SIM_WAFER_B,1\nWAFER_ID," + id + "\nROWS," + rows + "\nCOLS," + columns + "\nNOTCH,DOWN\nX,Y,BIN\n" + records;
    }

    static string Normalize(string text) { return (string)Call(normalize, text); }
    static string Prepare(string file, string cache) { return (string)Call(prepare, file, cache); }

    static void Matrix(string result, params string[] expected)
    {
        string[] lines = result.Replace("\r\n", "\n").TrimEnd('\n').Split('\n');
        Check(lines[0] == "Wafer_ID : SIM-B-001", "标准头保留晶圆 ID");
        Check(lines[1] == "Flat_Notch : Bottom" && lines[2] == "Bin Type : Char", "标准头使用真实库支持的 Bottom 方向及字符 BIN");
        Check(lines[3] == "Null Bin : ." && lines[4].StartsWith("Void Bin : "), "标准空位头字段");
        Check(lines[5] == "" && lines.Skip(6).SequenceEqual(expected), "非对称网格的方向、BIN 与行列严格符合预期");
    }

    static void Reject(Action action, string reason)
    {
        Exception failure = null;
        try { action(); } catch (Exception error) { failure = error; }
        Check(failure != null && !string.IsNullOrWhiteSpace(failure.Message), "拒绝非法输入并说明原因：" + reason);
    }

    static void Case(string name, Action action)
    {
        try { action(); }
        catch (Exception error) { failed = true; Console.WriteLine("FAIL CASE: " + name + "\n" + error); }
    }

    // 遍历真实编译 IL 及 Block 的闭包/辅助方法，确认适配器接入 LoadMap。
    static bool Connected(Assembly app)
    {
        var opcodes = typeof(OpCodes).GetFields().Where(f => f.FieldType == typeof(OpCode))
            .Select(f => (OpCode)f.GetValue(null)).ToDictionary(op => unchecked((ushort)op.Value));
        var pending = new Queue<MethodBase>();
        var visited = new HashSet<MethodBase>();
        pending.Enqueue(app.GetType(BlockName, true).GetMethod("LoadMap"));
        while (pending.Count > 0 && visited.Count < 300)
        {
            var method = pending.Dequeue();
            if (!visited.Add(method)) continue;
            var body = method.GetMethodBody();
            if (body == null) continue;
            byte[] il = body.GetILAsByteArray();
            for (int p = 0; p < il.Length;)
            {
                ushort value = il[p++];
                if (value == 0xfe) value = (ushort)(0xfe00 | il[p++]);
                var op = opcodes[value];
                if (op.OperandType == OperandType.InlineMethod || op.OperandType == OperandType.InlineTok)
                {
                    MethodBase target = null;
                    try { target = method.Module.ResolveMember(BitConverter.ToInt32(il, p)) as MethodBase; }
                    catch (ArgumentException) { }
                    if (target != null)
                    {
                        if (target.DeclaringType.FullName == AdapterName && target.Name == "PrepareForLoad") return true;
                        if (target.DeclaringType.FullName == BlockName || target.DeclaringType.FullName.StartsWith(BlockName + "+")) pending.Enqueue(target);
                    }
                }
                switch (op.OperandType)
                {
                    case OperandType.InlineNone: break;
                    case OperandType.ShortInlineBrTarget:
                    case OperandType.ShortInlineI:
                    case OperandType.ShortInlineVar: p += 1; break;
                    case OperandType.InlineVar: p += 2; break;
                    case OperandType.InlineI8:
                    case OperandType.InlineR: p += 8; break;
                    case OperandType.InlineSwitch: p += 4 + 4 * BitConverter.ToInt32(il, p); break;
                    default: p += 4; break;
                }
            }
        }
        return false;
    }

    [STAThread]
    static int Main(string[] args)
    {
        try
        {
            string bin = Path.GetDirectoryName(Path.GetFullPath(args[0]));
            AppDomain.CurrentDomain.AssemblyResolve += (sender, request) => {
                string file = Path.Combine(bin, new AssemblyName(request.Name).Name + ".dll");
                return File.Exists(file) ? Assembly.LoadFrom(file) : null;
            };
            Assembly app = Assembly.LoadFrom(args[0]);
            var adapter = app.GetType(AdapterName, true);
            normalize = adapter.GetMethod("NormalizeContent", BindingFlags.Public | BindingFlags.Static);
            prepare = adapter.GetMethod("PrepareForLoad", BindingFlags.Public | BindingFlags.Static);
            Check(normalize != null && prepare != null, "公开模拟适配接口存在");
            Check(Connected(app), "真实 LoadMap 编译调用路径已经接入 PrepareForLoad");
            work = Path.GetFullPath(args[1]);
            Directory.CreateDirectory(work);
            string sample = Csv(3, 4, "1,1,0\n4,3,9\n2,2,255\n3,2,0\n");
            Matrix(Normalize(sample), "...2", "..1.", "1...");
            Case("BOM/CRLF/合法字段空白", () => Matrix(Normalize("\ufeff" + sample.Replace("\n", "\r\n").Replace("1,1,0", " 1 , 1 , 0 ")), "...2", "..1.", "1..."));
            Matrix(Normalize(Csv(1, 1, "1,1,255")), ".");
            Matrix(Normalize(Csv(1, 4, "4,1,0\n1,1,9\n3,1,255")), "2..1");
            Matrix(Normalize(Csv(4, 1, "1,4,9\n1,1,0\n1,2,255")), "2", ".", ".", "1");
            foreach (var test in new Dictionary<string, string> {
                {"空内容", ""}, {"null", null}, {"无数据", Csv(1,1,"")},
                {"零尺寸", Csv(0,1,"1,1,0")}, {"负尺寸", Csv(1,-1,"1,1,0")},
                {"超尺寸", Csv(1001,1,"1,1,0")}, {"尺寸溢出", sample.Replace("ROWS,3","ROWS,999999999999999999")},
                {"尺寸非整数", sample.Replace("ROWS,3","ROWS,3.5")},
                {"坐标为零", Csv(3,4,"0,1,0")}, {"坐标越界", Csv(3,4,"1,4,0")},
                {"坐标负值", Csv(3,4,"-1,1,0")}, {"坐标小数", Csv(3,4,"1.5,1,0")},
                {"未知 BIN", Csv(3,4,"1,1,10")}, {"空 BIN 重复坐标", Csv(3,4,"1,1,255\n1,1,255")},
                {"缺失表头", sample.Replace("X,Y,BIN\n", "")},
                {"元数据乱序", sample.Replace("ROWS,3\nCOLS,4", "COLS,4\nROWS,3")},
                {"额外字段", sample.Replace("1,1,0", "1,1,0,EXTRA")},
                {"错误版本", sample.Replace("#SIM_WAFER_B,1", "#SIM_WAFER_B,2")},
                {"不支持方向", sample.Replace("NOTCH,DOWN", "NOTCH,UP")},
                {"非法 ID", sample.Replace("SIM-B-001", "../../escape")},
                {"引号字段", sample.Replace("1,1,0", "\"1\",1,0")},
            }) Reject(() => Normalize(test.Value), test.Key);
            string legacy = Path.Combine(work, "legacy.AKRS"), cache = Path.Combine(work, "cache");
            File.WriteAllBytes(legacy, new byte[] { 0, 1, 2, 3 });
            Check(Prepare(legacy, cache) == legacy && File.ReadAllBytes(legacy).SequenceEqual(new byte[] {0,1,2,3}), "旧格式路径和原件字节不变");
            string otherCsv = Path.Combine(work, "ordinary.csv");
            File.WriteAllText(otherCsv, sample);
            Check(Prepare(otherCsv, cache) == otherCsv, "不能把所有 CSV 误当作新厂商");
            string source = Path.Combine(work, "SIM-B-001.svb.csv");
            File.WriteAllText(source, sample, new UTF8Encoding(true));
            byte[] raw = File.ReadAllBytes(source);
            string converted = Prepare(source, cache);
            Check(Path.GetFullPath(converted).StartsWith(Path.GetFullPath(cache) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) && Path.GetExtension(converted).Equals(".AKRS", StringComparison.OrdinalIgnoreCase), "新结果仅写指定缓存目录的 AKRS 文件");
            Matrix(File.ReadAllText(converted), "...2", "..1.", "1...");
            Case("实际导入入口的旧格式与新后缀", () => ImportEntry(app, sample));
            Case("真实 WaferMap 库读取", () => {
            var wm = Assembly.LoadFrom(Path.Combine(bin, "AKRS.WM.WaferMap.dll"));
            var mapType = wm.GetType("AKRS.WM.WaferMap", true);
            Console.WriteLine("INFO: FlatNotch values=" + string.Join(",", Enum.GetNames(wm.GetType("AKRS.WM.FlatNotch", true))));
            var load = mapType.GetMethod("LoadFile", BindingFlags.Public | BindingFlags.Static, null, new[] { typeof(string) }, null);
            Check(load != null, "现有 WaferMap 读取 API 可用");
            var oldMap = Call(load, args[2]);
            Check((int)mapType.GetProperty("RowCount").GetValue(oldMap) > 0, "原 AKRS 样例可由既有库读取");
            var newMap = Call(load, converted);
            Check((int)mapType.GetProperty("RowCount").GetValue(newMap) == 3 && (int)mapType.GetProperty("ColumnCount").GetValue(newMap) == 4, "转换结果由真实 WaferMap 库读取为 3×4");
            Check((string)mapType.GetProperty("WaferID").GetValue(newMap) == "SIM-B-001", "真实 WaferMap 库保留新厂商 ID");
            });
            Check(File.ReadAllBytes(source).SequenceEqual(raw), "新厂商原件字节保留");
            File.WriteAllText(source, sample.Replace("1,1,0", "1,1,9"));
            converted = Prepare(source, cache);
            Matrix(File.ReadAllText(converted), "...2", "..1.", "2...");
            string valid = File.ReadAllText(converted);
            File.WriteAllText(source, Csv(3,4,"1,1,255\n1,1,255"));
            Reject(() => Prepare(source, cache), "非法新文件导入");
            Check(File.ReadAllText(converted) == valid, "失败导入不覆盖有效缓存");
            Console.WriteLine("RESULT: assertions=" + assertions + "; passed=" + (!failed).ToString().ToLowerInvariant());
            return failed ? 1 : 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error); Console.WriteLine("RESULT: assertions=" + assertions + "; passed=false"); return 1; }
    }
}
