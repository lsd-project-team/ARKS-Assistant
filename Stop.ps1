$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'scripts\LocalServer.ps1')
$dataDirectory = Get-ServerDataDirectory $PSScriptRoot
$serverProcesses = @(Get-RecordedServerProcesses $PSScriptRoot $dataDirectory)
foreach ($serverProcess in $serverProcesses) {
    $currentProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($serverProcess.ProcessId)"
    if (-not $currentProcess) { continue }
    if ($currentProcess.CreationDate -ne $serverProcess.CreationDate) { throw '进程身份已变化，未执行关闭。' }
    Stop-Process -Id $serverProcess.ProcessId
    Wait-Process -Id $serverProcess.ProcessId -Timeout 10 -ErrorAction SilentlyContinue
}
foreach ($name in @('server.pid', 'server.process.json')) {
    $recordPath = Join-Path $dataDirectory $name
    if (Test-Path -LiteralPath $recordPath) { Remove-Item -LiteralPath $recordPath }
}
if ($serverProcesses.Count) { Write-Host '服务已停止。正在运行的对话将在下次启动时标记为可恢复。' }
else { Write-Host '当前没有已记录的服务进程。' }
