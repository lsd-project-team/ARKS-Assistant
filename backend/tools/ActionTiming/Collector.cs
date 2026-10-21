// 不依赖设备SDK；由ZX2200隔离副本传入原动作委托和JSON序列化器。
using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace Arks.ActionTiming
{
    public sealed class RunManifest
    {
        public int protocol_version { get; set; } = 1;
        public string run_id { get; set; } = Guid.NewGuid().ToString("N");
        public string mode { get; set; } = "DryCycle";
        public string source_kind { get; set; } = "zx2200";
        public string source_revision { get; set; }
        public string recipe_name { get; set; }
        public string recipe_fingerprint { get; set; } = "";
        public string entry_point { get; set; } = "Machine.Start";
        public string started_at { get; set; } = DateTimeOffset.UtcNow.ToString("o");
        public string finished_at { get; set; }
        public string state { get; set; } = "running";
        public string clock { get; set; } = "stopwatch";
        public long clock_frequency { get; set; } = Stopwatch.Frequency;
        public int event_count { get; set; }
        public int dropped_events { get; set; }
        public string boundary { get; set; } = "synchronous_call_including_waits";
    }

    public sealed class TimingEvent
    {
        public string event_id { get; set; } = Guid.NewGuid().ToString("N");
        public string action_code { get; set; }
        public string parent_id { get; set; }
        public string logical_id { get; set; }
        public int attempt { get; set; }
        public string kind { get; set; } = "action";
        public string stage { get; set; } = "";
        public string category { get; set; } = "work";
        public string branch { get; set; }
        public string station { get; set; }
        public double start_ms { get; set; }
        public double? end_ms { get; set; }
        public string status { get; set; } = "incomplete";
        public string raw_result { get; set; } = "";
        public string reason { get; set; } = "";
        public int thread_id { get; set; } = Thread.CurrentThread.ManagedThreadId;
        public Dictionary<string, string> context { get; set; }
    }

    internal sealed class Invocation
    {
        internal TimingEvent Event;
        internal bool Executed;
        internal bool FailedWork;
        internal bool Finished;
        internal int ThreadId;
    }

    public sealed class Collector
    {
        private readonly object gate = new object();
        private readonly BlockingCollection<TimingEvent> queue = new BlockingCollection<TimingEvent>();
        private readonly Dictionary<string, Invocation> active = new Dictionary<string, Invocation>();
        private readonly ConcurrentDictionary<string, int> attempts = new ConcurrentDictionary<string, int>();
        private readonly AsyncLocal<Invocation> current = new AsyncLocal<Invocation>();
        private readonly Func<object, string> serialize;
        private readonly Func<long> timestamp;
        private readonly long origin;
        private readonly long frequency;
        private readonly int capacity;
        private readonly Task writer;
        private bool closing;
        private int reserved;
        private int dropped;
        private Task completion;
        public string DirectoryPath { get; private set; }
        public RunManifest Manifest { get; private set; }
        public Exception LastError { get; private set; }

        public Collector(string output, RunManifest manifest, Func<object, string> serializer,
            Func<long> clock = null, long clockFrequency = 0, int maxEvents = 20000)
        {
            Manifest = manifest;
            serialize = serializer;
            timestamp = clock ?? Stopwatch.GetTimestamp;
            frequency = clockFrequency > 0 ? clockFrequency : Stopwatch.Frequency;
            if (maxEvents < 1) throw new ArgumentOutOfRangeException("maxEvents");
            capacity = maxEvents;
            Manifest.clock_frequency = frequency;
            origin = timestamp();
            DirectoryPath = Path.Combine(Path.GetFullPath(output), manifest.run_id);
            Directory.CreateDirectory(DirectoryPath);
            File.WriteAllText(Path.Combine(DirectoryPath, "manifest.json"), serialize(Manifest), new UTF8Encoding(false));
            writer = Task.Run((Action)WriteEvents);
        }

        private double Now() { return (timestamp() - origin) * 1000.0 / frequency; }

        private bool Reserve()
        {
            if (reserved >= capacity) { dropped++; return false; }
            reserved++;
            return true;
        }

        private Invocation Begin(string code, string station, string logicalId, Dictionary<string, string> context)
        {
            lock (gate)
            {
                // 先预留父记录名额，避免达到上限时只留下无法关联的子记录。
                if (closing || !Reserve()) return null;
                var invocation = new Invocation
                {
                    ThreadId = Thread.CurrentThread.ManagedThreadId,
                    Event = new TimingEvent
                    {
                        action_code = code, station = station, logical_id = logicalId,
                        attempt = attempts.AddOrUpdate(logicalId, 1, (key, old) => old + 1),
                        context = new Dictionary<string, string>(context), branch = "drycycle",
                        start_ms = Now()
                    }
                };
                active.Add(invocation.Event.event_id, invocation);
                return invocation;
            }
        }

        public T Invoke<T>(string code, string station, string logicalId, Dictionary<string, string> context, Func<T> action)
        {
            Invocation invocation = Begin(code, station, logicalId, context);
            if (invocation == null) return action();
            Invocation previous = current.Value;
            current.Value = invocation;
            try
            {
                T result = action();
                string raw = Convert.ToString(result, System.Globalization.CultureInfo.InvariantCulture);
                lock (gate)
                {
                    // 停止超时已经封存的未完成记录不能被迟到返回改写。
                    if (!invocation.Finished)
                    {
                        invocation.Event.raw_result = raw;
                        invocation.Event.status = raw == "Success" || raw == "True"
                            ? (invocation.FailedWork ? "failed" : invocation.Executed ? "success" : "noop")
                            : raw == "Retry" ? "retry" : raw == "Abort" ? "aborted" : "failed";
                        if (invocation.Event.status == "noop") invocation.Event.reason = "动作内部条件未进入已接入的工作阶段";
                        if (invocation.FailedWork && (raw == "Success" || raw == "True"))
                            invocation.Event.reason = "原动作返回成功，但已采集的工作阶段包含失败结果";
                    }
                }
                return result;
            }
            catch (Exception error)
            {
                lock (gate)
                {
                    if (!invocation.Finished)
                    {
                        invocation.Event.status = "failed";
                        invocation.Event.raw_result = error.GetType().Name;
                        invocation.Event.reason = Limit(error.Message);
                    }
                }
                throw;
            }
            finally
            {
                current.Value = previous;
                lock (gate)
                {
                    if (!invocation.Finished)
                    {
                        invocation.Finished = true;
                        invocation.Event.end_ms = Now();
                        queue.Add(invocation.Event);
                        active.Remove(invocation.Event.event_id);
                    }
                }
            }
        }

        public void Skip(string code, string station, string logicalId, Dictionary<string, string> context)
        {
            Invocation invocation = Begin(code, station, logicalId, context);
            if (invocation == null) return;
            lock (gate)
            {
                // Begin与跳过记录入队之间，停止任务可能已经封存了本次调用。
                if (invocation.Finished) return;
                invocation.Event.end_ms = invocation.Event.start_ms;
                invocation.Event.status = "skipped";
                invocation.Event.raw_result = "False";
                invocation.Event.reason = "IsDoWork=false";
                queue.Add(invocation.Event);
                active.Remove(invocation.Event.event_id);
                invocation.Finished = true;
            }
        }

        public void Branch(string branch)
        {
            var invocation = current.Value;
            lock (gate)
                if (invocation != null && !invocation.Finished && invocation.ThreadId == Thread.CurrentThread.ManagedThreadId)
                    invocation.Event.branch = branch;
        }

        public T Stage<T>(string name, string category, Func<T> action)
        {
            Invocation invocation = current.Value;
            // ExecutionContext会流入Task.Run；首期只采同步子阶段，后台不能误归到下一动作。
            if (invocation == null || invocation.ThreadId != Thread.CurrentThread.ManagedThreadId || invocation.Finished)
                return action();
            TimingEvent entry;
            lock (gate)
            {
                if (invocation.Finished || !Reserve()) entry = null;
                else
                {
                    entry = new TimingEvent
                    {
                        action_code = invocation.Event.action_code, station = invocation.Event.station,
                        logical_id = invocation.Event.logical_id, attempt = invocation.Event.attempt,
                        parent_id = invocation.Event.event_id, context = invocation.Event.context,
                        kind = "stage", stage = name, category = category, branch = invocation.Event.branch,
                        start_ms = Now()
                    };
                    if (category == "work" || category == "delay") invocation.Executed = true;
                }
            }
            if (entry == null) return action();
            try
            {
                T result = action();
                entry.raw_result = Convert.ToString(result, System.Globalization.CultureInfo.InvariantCulture);
                entry.status = entry.raw_result == "Abort" ? "aborted"
                    : entry.raw_result == "Retry" ? "retry"
                    : entry.raw_result == "Exception" || entry.raw_result == "Fail" || entry.raw_result == "Alarm" || entry.raw_result == "False"
                        ? "failed" : "success";
                if (category == "work" && entry.status != "success") invocation.FailedWork = true;
                return result;
            }
            catch (Exception error)
            {
                entry.status = "failed";
                entry.raw_result = error.GetType().Name;
                entry.reason = Limit(error.Message);
                if (category == "work") invocation.FailedWork = true;
                throw;
            }
            finally
            {
                lock (gate)
                {
                    if (!invocation.Finished) { entry.end_ms = Now(); queue.Add(entry); }
                    else dropped++;
                }
            }
        }

        public void Stage(string name, string category, Action action)
        {
            Stage(name, category, () => { action(); return "Success"; });
        }

        public Task StopAsync(string state = "stopped", int timeoutMs = 10000)
        {
            lock (gate)
            {
                if (completion != null) return completion;
                closing = true;
                completion = Task.Run(async () =>
                {
                    var deadline = Stopwatch.StartNew();
                    while (true)
                    {
                        lock (gate)
                        {
                            if (active.Count == 0 || deadline.ElapsedMilliseconds >= timeoutMs)
                            {
                                bool unfinished = active.Count != 0;
                                foreach (var invocation in active.Values)
                                {
                                    invocation.Finished = true;
                                    invocation.Event.status = "incomplete";
                                    invocation.Event.reason = "停止采集后同步调用未在期限内结束";
                                    queue.Add(invocation.Event);
                                }
                                active.Clear();
                                Manifest.state = unfinished ? "incomplete" : state;
                                queue.CompleteAdding();
                                break;
                            }
                        }
                        await Task.Delay(10).ConfigureAwait(false);
                    }
                    await writer.ConfigureAwait(false);
                    Manifest.dropped_events = dropped;
                    if (dropped > 0 || LastError != null) Manifest.state = "incomplete";
                    Manifest.finished_at = DateTimeOffset.UtcNow.ToString("o");
                    try
                    {
                        string path = Path.Combine(DirectoryPath, "manifest.json");
                        File.WriteAllText(path + ".tmp", serialize(Manifest), new UTF8Encoding(false));
                        File.Copy(path + ".tmp", path, true);
                        File.Delete(path + ".tmp");
                    }
                    catch (Exception error) { LastError = error; Trace.TraceError(error.ToString()); }
                });
                return completion;
            }
        }

        private void WriteEvents()
        {
            try
            {
                using (var output = new StreamWriter(Path.Combine(DirectoryPath, "events.jsonl"), false, new UTF8Encoding(false)))
                {
                    foreach (TimingEvent entry in queue.GetConsumingEnumerable())
                    {
                        output.WriteLine(serialize(entry));
                        Manifest.event_count++;
                        if (Manifest.event_count % 32 == 0) output.Flush();
                    }
                }
            }
            catch (Exception error)
            {
                LastError = error;
                Trace.TraceError(error.ToString());
                foreach (var ignored in queue.GetConsumingEnumerable()) Interlocked.Increment(ref dropped);
            }
        }

        private static string Limit(string value) { return value.Length > 1000 ? value.Substring(0, 1000) : value; }
    }
}
