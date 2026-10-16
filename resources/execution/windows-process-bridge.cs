using System;
using System.Diagnostics;
using System.ComponentModel;
using System.IO;
using System.Text;
using System.Threading;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

public static class ArksProcessBridge {
    // 节点桥被SSH/控制端中断时，内核关闭Job句柄并回收本机docker.exe。
    // 业务进程仍由容器PID1独立TTL及宿主stop容器保证回收。
    private sealed class ProcessJob : SafeHandleZeroOrMinusOneIsInvalid {
        [StructLayout(LayoutKind.Sequential)] private struct BasicLimits {
            public long ProcessTime, JobTime;
            public uint Flags;
            public UIntPtr MinWorkingSet, MaxWorkingSet;
            public uint ActiveProcesses;
            public UIntPtr Affinity;
            public uint PriorityClass, SchedulingClass;
        }
        [StructLayout(LayoutKind.Sequential)] private struct IoCounters {
            public ulong ReadOps, WriteOps, OtherOps, ReadBytes, WriteBytes, OtherBytes;
        }
        [StructLayout(LayoutKind.Sequential)] private struct ExtendedLimits {
            public BasicLimits Basic;
            public IoCounters Io;
            public UIntPtr ProcessMemory, JobMemory, PeakProcessMemory, PeakJobMemory;
        }
        [DllImport("kernel32.dll", SetLastError=true)]
        private static extern IntPtr CreateJobObject(IntPtr attributes, string name);
        [DllImport("kernel32.dll", SetLastError=true)]
        private static extern bool SetInformationJobObject(IntPtr job, int type, IntPtr data, uint size);
        [DllImport("kernel32.dll", SetLastError=true)]
        private static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
        [DllImport("kernel32.dll")] private static extern bool CloseHandle(IntPtr handle);
        public ProcessJob(Process process) : base(true) {
            SetHandle(CreateJobObject(IntPtr.Zero, null));
            if (IsInvalid) {
                try { process.Kill(); } catch { }
                throw new Win32Exception();
            }
            var limits = new ExtendedLimits();
            limits.Basic.Flags = 0x2000; // JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            int size = Marshal.SizeOf(limits);
            IntPtr memory = Marshal.AllocHGlobal(size);
            try {
                Marshal.StructureToPtr(limits, memory, false);
                if (!SetInformationJobObject(handle, 9, memory, (uint)size) ||
                    !AssignProcessToJobObject(handle, process.Handle)) {
                    try { process.Kill(); } catch { }
                    Dispose();
                    throw new Win32Exception();
                }
            } finally { Marshal.FreeHGlobal(memory); }
        }
        protected override bool ReleaseHandle() { return CloseHandle(handle); }
    }

    public static string Quote(string value) {
        var result = new StringBuilder("\"");
        int slashes = 0;
        foreach (char character in value) {
            if (character == '\\') { slashes++; continue; }
            if (character == '"') {
                result.Append('\\', slashes * 2 + 1).Append('"');
            } else { result.Append('\\', slashes).Append(character); }
            slashes = 0;
        }
        return result.Append('\\', slashes * 2).Append('"').ToString();
    }

    private sealed class OutputState {
        public readonly object Sync = new object();
        public long Maximum, Used;
        public bool Overflow, Broken;
        public Process Process;
        public MemoryStream Capture;
        public void Pump(Stream source) {
            try {
                byte[] buffer = new byte[16384];
                int count;
                while ((count = source.Read(buffer, 0, buffer.Length)) != 0) {
                    lock (Sync) {
                        if (Overflow || Broken) { return; }
                        int allowed = (int)Math.Min(count, Maximum - Used);
                        if (allowed > 0) {
                            if (Capture != null) { Capture.Write(buffer, 0, allowed); }
                            else {
                                Console.Out.WriteLine("{\"type\":\"output\",\"data\":\"" +
                                    Convert.ToBase64String(buffer, 0, allowed) + "\"}");
                                Console.Out.Flush();
                            }
                        }
                        Used += allowed;
                        if (allowed != count) {
                            Overflow = true;
                            if (Capture == null) {
                                Console.Out.WriteLine("{\"type\":\"overflow\"}");
                                Console.Out.Flush();
                            }
                            try { Process.Kill(); } catch (InvalidOperationException) { }
                            return;
                        }
                    }
                }
            } catch {
                lock (Sync) { Broken = true; }
                try { Process.Kill(); } catch { }
            }
        }
    }

    public static void VerifyEngine(string executable, string pipe, string expected) {
        var info = new ProcessStartInfo(executable, "--host " + Quote(pipe) + " info --format \"{{.ID}}\"");
        info.UseShellExecute = false; info.CreateNoWindow = true;
        info.RedirectStandardOutput = info.RedirectStandardError = true;
        using (var process = Process.Start(info)) {
            using (var job = new ProcessJob(process)) {
            var state = new OutputState { Maximum = 8192, Process = process, Capture = new MemoryStream() };
            var output = new Thread(() => state.Pump(process.StandardOutput.BaseStream));
            var error = new Thread(() => state.Pump(process.StandardError.BaseStream));
            output.IsBackground = error.IsBackground = true;
            output.Start(); error.Start();
            if (!process.WaitForExit(10000)) { process.Kill(); }
            if (!process.WaitForExit(5000) || !output.Join(5000) || !error.Join(5000) ||
                state.Broken || state.Overflow || process.ExitCode != 0 ||
                Encoding.UTF8.GetString(state.Capture.ToArray()).Trim() != expected) {
                throw new IOException("Engine identity unavailable or changed");
            }
            }
        }
    }

    public static void Run(string executable, string[] arguments, long maximum, int timeout) {
        var joined = new StringBuilder();
        foreach (string value in arguments) { joined.Append(Quote(value)).Append(' '); }
        var info = new ProcessStartInfo(executable, joined.ToString());
        info.UseShellExecute = false;
        info.CreateNoWindow = true;
        info.RedirectStandardInput = true;
        info.RedirectStandardOutput = true;
        info.RedirectStandardError = true;
        using (var process = new Process()) {
            process.StartInfo = info;
            process.Start();
            using (var job = new ProcessJob(process)) {
            process.StandardInput.Close();
            var state = new OutputState { Maximum = maximum, Process = process };
            var output = new Thread(() => state.Pump(process.StandardOutput.BaseStream));
            var error = new Thread(() => state.Pump(process.StandardError.BaseStream));
            output.IsBackground = error.IsBackground = true;
            output.Start(); error.Start();
            bool exited = process.WaitForExit(timeout * 1000);
            if (!exited) { try { process.Kill(); } catch (InvalidOperationException) { } }
            if (!process.WaitForExit(5000) || !output.Join(5000) || !error.Join(5000) || state.Broken) {
                throw new IOException("Bridge streams did not finish");
            }
            if (!exited) { Console.Out.WriteLine("{\"type\":\"timed_out\"}"); }
            else if (!state.Overflow) {
                // Windows Int32退出码直接进JSON，不经过Linux/SSH进程状态的低8位。
                Console.Out.WriteLine("{\"type\":\"result\",\"raw_exit_code\":" +
                    process.ExitCode.ToString(System.Globalization.CultureInfo.InvariantCulture) + "}");
            }
            Console.Out.Flush();
            }
        }
    }
}
