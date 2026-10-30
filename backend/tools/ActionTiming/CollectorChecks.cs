// 仅验证采集器；这里的委托和可控时钟不是设备模拟，也不是现场耗时数据。
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using Arks.ActionTiming;

internal static class CollectorChecks
{
    private static int checks;
    private static readonly JavaScriptSerializer json = new JavaScriptSerializer { MaxJsonLength = 16777216 };
    private static readonly string[] codes = { "s1.bond_position_vision", "s1.dispense", "s2.pick", "s2.uplook", "s2.bond" };
    private static Dictionary<string, string> Context() { return new Dictionary<string, string> { { "bond_position", "测试焊点" }, { "process_step", "采集器验证" } }; }
    private static RunManifest Manifest() { return new RunManifest { source_kind = "collector_test", source_revision = "collector-checks-v1", recipe_name = "采集器协议验证", entry_point = "CollectorChecks" }; }
    private static void Check(bool success, string message) { if (!success) throw new Exception(message); checks++; }
    private static Dictionary<string, object>[] Read(Collector run)
    {
        return File.ReadAllLines(Path.Combine(run.DirectoryPath, "events.jsonl")).Select(line => json.Deserialize<Dictionary<string, object>>(line)).ToArray();
    }

    private static void Deterministic(string output)
    {
        long tick = 0;
        var collector = new Collector(output, Manifest(), value => json.Serialize(value), () => Interlocked.Read(ref tick), 1000);
        int invoked = 0;
        string result = collector.Invoke("s1.dispense", "S1", "same-logical", Context(), () =>
        {
            collector.Stage("等料", "wait", () => { tick += 7; });
            collector.Stage("轨迹", "work", () => { tick += 13; invoked++; });
            return "Success";
        });
        collector.Invoke("s1.dispense", "S1", "same-logical", Context(), () => "Success");
        collector.Skip("s2.bond", "S2", "skip", Context());
        string mismatched = collector.Invoke("s1.bond_position_vision", "S1", "mismatch", Context(), () =>
        {
            collector.Stage("视觉返回失败", "work", () => false);
            return "Success";
        });
        collector.Invoke("s2.pick", "S2", "retry", Context(), () =>
        {
            collector.Stage("取片", "work", () => { tick += 3; });
            return "Retry";
        });
        var expected = new InvalidOperationException("original-error");
        bool propagated = false;
        try
        {
            collector.Invoke<string>("s2.bond", "S2", "failure", Context(), () =>
            {
                collector.Stage("异常", "work", (Action)(() => { throw expected; }));
                return "Success";
            });
        }
        catch (InvalidOperationException error) { propagated = object.ReferenceEquals(error, expected); }
        Check(propagated, "原异常必须原样传播");
        collector.StopAsync("completed").GetAwaiter().GetResult();
        var rows = Read(collector);
        var roots = rows.Where(row => (string)row["kind"] == "action").ToArray();
        Check(result == "Success" && invoked == 1, "委托不能重放或改变结果");
        var first = roots.Single(row => (string)row["logical_id"] == "same-logical" && Convert.ToInt32(row["attempt"]) == 1);
        Check(Convert.ToDouble(first["end_ms"]) - Convert.ToDouble(first["start_ms"]) == 20, "独立单调计时和等待");
        Check(roots.Any(row => (string)row["status"] == "noop" && Convert.ToInt32(row["attempt"]) == 2), "无操作不算成功样本");
        Check(roots.Any(row => (string)row["status"] == "skipped"), "调度跳过");
        Check(roots.Any(row => (string)row["status"] == "retry"), "重试结果");
        Check(roots.Any(row => (string)row["status"] == "failed"), "异常结果");
        Check(mismatched == "Success" && roots.Any(row => (string)row["logical_id"] == "mismatch"
            && (string)row["status"] == "failed" && (string)row["raw_result"] == "Success"), "原返回值与内部阶段失败分别保存");
        Check(collector.Manifest.event_count == rows.Length && collector.LastError == null, "持久化条数与错误状态");
        Console.WriteLine("PACKAGE=" + collector.DirectoryPath);
    }

    private static void ConcurrentAndLimit(string output)
    {
        var concurrent = new Collector(output, Manifest(), value => new JavaScriptSerializer().Serialize(value));
        Parallel.For(0, 40, i => concurrent.Invoke("s2.pick", "S2", "parallel-" + i, Context(), () =>
        {
            concurrent.Stage("移动", "work", () => Thread.SpinWait(100));
            return "Success";
        }));
        concurrent.StopAsync().GetAwaiter().GetResult();
        var rows = Read(concurrent);
        Check(rows.Count(row => (string)row["kind"] == "action") == 40, "并发父记录不丢失");
        Check(rows.Count(row => (string)row["kind"] == "stage") == 40, "并发子记录不串行归属");
        var limited = new Collector(output, Manifest(), value => json.Serialize(value), maxEvents: 1);
        int calls = 0;
        limited.Invoke("s2.bond", "S2", "limit", Context(), () =>
        {
            limited.Stage("超出上限", "work", () => calls++);
            return "Success";
        });
        limited.StopAsync().GetAwaiter().GetResult();
        Check(calls == 1 && limited.Manifest.dropped_events == 1, "达到上限仍执行原动作并记丢失");
        Check(Read(limited).Length == 1 && limited.Manifest.state == "incomplete", "上限保留父记录，批次标不完整");
    }

    private static void StopDuringAction(string output)
    {
        var serializing = new ManualResetEventSlim();
        var releaseWriter = new ManualResetEventSlim();
        var collector = new Collector(output, Manifest(), value =>
        {
            if (value is TimingEvent) { serializing.Set(); releaseWriter.Wait(); }
            return new JavaScriptSerializer().Serialize(value);
        });
        var started = new ManualResetEventSlim();
        var release = new ManualResetEventSlim();
        Task task = Task.Run(() => collector.Invoke("s2.bond", "S2", "unfinished", Context(), () =>
        {
            started.Set(); release.Wait(); return "Success";
        }));
        started.Wait();
        Task stopped = collector.StopAsync(timeoutMs: 0);
        serializing.Wait();
        release.Set(); task.GetAwaiter().GetResult();
        releaseWriter.Set(); stopped.GetAwaiter().GetResult();
        var rows = Read(collector);
        Check(rows.Length == 1 && (string)rows[0]["status"] == "incomplete" && rows[0]["end_ms"] == null, "停止中断保留未完成记录");
        Check(collector.Manifest.state == "incomplete", "未完成不能报告已结束");
    }

    private static void Smoke(string output)
    {
        var run = new Collector(output, Manifest(), value => json.Serialize(value));
        foreach (string code in codes)
        {
            for (int i = 0; i < 100; i++)
            {
                string copy = code;
                run.Invoke(code, code.StartsWith("s1") ? "S1" : "S2", code.Replace('.', '-') + "-" + i, Context(), () =>
                {
                    run.Branch("drycycle.collector_test");
                    run.Stage("采集器调用验证", "work", () => Thread.SpinWait(copy.Length * 10));
                    return "Success";
                });
            }
        }
        run.StopAsync("completed").GetAwaiter().GetResult();
        Check(run.Manifest.event_count == 1000 && run.Manifest.dropped_events == 0, "五项各100次测试调用及阶段");
        Console.WriteLine("SMOKE=" + run.DirectoryPath);
    }

    private static int Main(string[] args)
    {
        try
        {
            Deterministic(args[0]); ConcurrentAndLimit(args[0]); StopDuringAction(args[0]); Smoke(args[0]);
            Console.WriteLine("CHECKS_PASSED=" + checks);
            return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
