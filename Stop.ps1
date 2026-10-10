$ErrorActionPreference = 'Stop'
$pidFile = Join-Path $PSScriptRoot 'data\server.pid'
if (-not (Test-Path -LiteralPath $pidFile)) { Write-Host '没有由 Start.ps1 启动的服务。'; return }
$serverProcessId = [int](Get-Content -LiteralPath $pidFile)
$serverProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$serverProcessId"
if (-not $serverProcess) { Remove-Item -LiteralPath $pidFile; return }
$expectedExecutable = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'backend\.venv\Scripts\python.exe'))
if ($serverProcess.ExecutablePath -ne $expectedExecutable -or $serverProcess.CommandLine -notlike '*uvicorn*app.main:app*') {
    throw 'PID 已被其他进程使用，未执行关闭。'
}
Stop-Process -Id $serverProcessId
Remove-Item -LiteralPath $pidFile
Write-Host '服务已停止。正在运行的对话将在下次启动时标记为可恢复。'
