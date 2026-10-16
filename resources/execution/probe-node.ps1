$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
# ROOT_BASE64 由控制端只允许本地盘绝对路径后替换，不插入任意 PowerShell 表达式。
$root = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('ROOT_BASE64'))
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class ArksDiskProbe {
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool GetDiskFreeSpaceEx(string path, out ulong available,
        out ulong total, out ulong free);
}
'@
[UInt64]$available = 0
[UInt64]$total = 0
[UInt64]$free = 0
if (-not [ArksDiskProbe]::GetDiskFreeSpaceEx($root, [ref]$available, [ref]$total, [ref]$free)) {
    throw 'Node capacity probe failed'
}
@{probe_version=1;free_bytes=[Math]::Min($available,$free);total_bytes=$total;
  measured_at=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()} | ConvertTo-Json -Compress
