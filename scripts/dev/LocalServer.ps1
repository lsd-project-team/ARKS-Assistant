# 启动器与实际 Python 服务可能是两个进程，使用健康接口报告的 PID 记录实际服务。
function Get-ServerDataDirectory([string]$ProjectDirectory) {
    $directory = if ($env:TRUNK_AGENT_DATA_DIR) { $env:TRUNK_AGENT_DATA_DIR } else { Join-Path $ProjectDirectory 'data' }
    return [IO.Path]::GetFullPath($directory)
}

function Test-ServerCommand([string]$CommandLine) {
    return $CommandLine -match '\s-m\s+uvicorn\s+app\.main:app\b' -and $CommandLine -match '--host\s+127\.0\.0\.1\b'
}

function Get-LocalServerHealth([string]$Address, [int]$TimeoutSeconds = 2) {
    # 本地健康检查绕过系统代理，不能把已就绪的本机服务误判为未启动。
    $request = [Net.WebRequest]::CreateHttp("$Address/api/health")
    $request.Proxy = $null
    $request.Timeout = $TimeoutSeconds * 1000
    $request.ReadWriteTimeout = $TimeoutSeconds * 1000
    $response = $request.GetResponse()
    $reader = [IO.StreamReader]::new($response.GetResponseStream())
    try { return ($reader.ReadToEnd() | ConvertFrom-Json) }
    finally { $reader.Dispose(); $response.Dispose() }
}

function Save-ServerProcess($Health, [string]$ProjectDirectory, [string]$DataDirectory, [int]$Port) {
    if (-not $Health.project_directory -or -not $Health.data_directory -or -not $Health.process_id) {
        throw '运行的是旧版服务，请先运行 Stop.ps1，再重新启动。'
    }
    if ($Health.project_directory -ne $ProjectDirectory -or $Health.data_directory -ne $DataDirectory) {
        throw '端口上的服务属于其他项目或数据目录，未接管该服务。'
    }
    $actualProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($Health.process_id)"
    if (-not $actualProcess -or -not (Test-ServerCommand $actualProcess.CommandLine)) {
        throw '无法核对实际服务进程，请检查服务日志。'
    }
    $listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    if ($actualProcess.ProcessId -notin $listeners.OwningProcess) { throw '健康接口与端口监听进程不一致。' }
    $record = @{
        process_id = $actualProcess.ProcessId
        executable = $actualProcess.ExecutablePath
        created_ticks = $actualProcess.CreationDate.ToUniversalTime().Ticks.ToString()
        project_directory = $ProjectDirectory
        data_directory = $DataDirectory
        port = $Port
    }
    $temporary = Join-Path $DataDirectory 'server.process.tmp'
    $record | ConvertTo-Json | Set-Content -LiteralPath $temporary -Encoding UTF8
    Move-Item -LiteralPath $temporary -Destination (Join-Path $DataDirectory 'server.process.json') -Force
    $actualProcess.ProcessId | Set-Content -LiteralPath (Join-Path $DataDirectory 'server.pid') -Encoding ascii
}

function Get-RecordedServerProcesses([string]$ProjectDirectory, [string]$DataDirectory) {
    $recordFile = Join-Path $DataDirectory 'server.process.json'
    if (Test-Path -LiteralPath $recordFile) {
        $record = Get-Content -LiteralPath $recordFile -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($record.project_directory -ne $ProjectDirectory -or $record.data_directory -ne $DataDirectory) {
            throw '服务记录不属于当前项目或数据目录，未执行关闭。'
        }
        $actualProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$record.process_id)"
        if (-not $actualProcess) { return }
        # PID 会复用，必须同时核对创建时间、可执行文件及服务命令。
        if ($actualProcess.CreationDate.ToUniversalTime().Ticks.ToString() -ne $record.created_ticks -or
            $actualProcess.ExecutablePath -ne $record.executable -or
            -not (Test-ServerCommand $actualProcess.CommandLine) -or
            $actualProcess.CommandLine -notmatch "--port\s+$($record.port)\b") {
            throw '服务记录对应的进程身份已变化，未执行关闭。'
        }
        return $actualProcess
    }
    $pidFile = Join-Path $DataDirectory 'server.pid'
    if (-not (Test-Path -LiteralPath $pidFile)) { return }
    $launcher = Get-CimInstance Win32_Process -Filter "ProcessId=$([int](Get-Content -LiteralPath $pidFile))"
    if (-not $launcher) { return }
    $expectedExecutable = Join-Path $ProjectDirectory 'backend\.venv\Scripts\python.exe'
    if ($launcher.ExecutablePath -ne $expectedExecutable -or -not (Test-ServerCommand $launcher.CommandLine)) {
        throw '旧 PID 记录对应的进程身份已变化，未执行关闭。'
    }
    # 兼容旧记录：只接纳已核实启动器的直接 Python 子进程，先停子进程再停启动器。
    Get-CimInstance Win32_Process -Filter "ParentProcessId=$($launcher.ProcessId)" |
        Where-Object { (Test-ServerCommand $_.CommandLine) -and $_.ExecutablePath -match '\\python\.exe$' }
    return $launcher
}
