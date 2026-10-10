param([int]$Port = 8765, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$projectDirectory = $PSScriptRoot
. (Join-Path $projectDirectory 'scripts\LocalServer.ps1')
$dataDirectory = Get-ServerDataDirectory $projectDirectory
$env:TRUNK_AGENT_DATA_DIR = $dataDirectory
$pythonExecutable = Join-Path $projectDirectory 'backend\.venv\Scripts\python.exe'
$frontendIndex = Join-Path $projectDirectory 'frontend\dist\index.html'
if (-not (Test-Path -LiteralPath $pythonExecutable) -or -not (Test-Path -LiteralPath $frontendIndex)) {
    throw '请先运行 Setup.ps1 安装依赖并构建前端。'
}
$address = "http://127.0.0.1:$Port"
$health = $null
try {
    $health = Invoke-RestMethod -Uri "$address/api/health" -TimeoutSec 2
} catch { }
if ($health.ok) {
    Save-ServerProcess $health $projectDirectory $dataDirectory $Port
    if (-not $NoBrowser) { Start-Process $address }
    Write-Host "工作区已运行：$address"
    return
}

# 后台服务不弹出终端窗口；PID 与日志保留在本地，供 Stop.ps1 精确关闭。
New-Item -ItemType Directory -Path $dataDirectory -Force | Out-Null
$process = Start-Process -FilePath $pythonExecutable -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$Port") -WorkingDirectory (Join-Path $projectDirectory 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $dataDirectory 'server.stdout.log') -RedirectStandardError (Join-Path $dataDirectory 'server.stderr.log')
for ($attempt = 0; $attempt -lt 40; $attempt++) {
    if ($process.HasExited) { throw '服务启动失败，请查看 data/server.stderr.log。' }
    $health = $null
    try {
        $health = Invoke-RestMethod -Uri "$address/api/health" -TimeoutSec 1
    } catch { }
    if ($health.ok) {
        Save-ServerProcess $health $projectDirectory $dataDirectory $Port
        if (-not $NoBrowser) { Start-Process $address }
        Write-Host "工作区已启动：$address"
        return
    }
    Start-Sleep -Milliseconds 500
}
throw '服务尚未就绪，请查看 data/server.stderr.log。'
