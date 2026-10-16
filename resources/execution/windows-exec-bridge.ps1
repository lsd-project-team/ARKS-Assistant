$ErrorActionPreference='Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$payload=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('PAYLOAD_BASE64')) | ConvertFrom-Json
if ($payload.container -notmatch '^[a-f0-9]{64}$') { throw 'Invalid container identity' }
if ($payload.pipe -notin @('docker_engine','dockerDesktopWindowsEngine')) { throw 'Invalid engine pipe' }
Add-Type -TypeDefinition @'
CSHARP_SOURCE
'@
$docker=(Get-Command docker.exe -CommandType Application -ErrorAction Stop).Source
# 结构化参数只传给固定docker.exe；不在宿主shell中执行任何目标命令。
$pipe='npipe:////./pipe/' + $payload.pipe
[ArksProcessBridge]::VerifyEngine($docker,$pipe,[string]$payload.daemon_id)
$arguments=@('--host',$pipe,'exec','--user','ContainerUser','--workdir','C:\work',
             '--env','TEMP=C:\arks-temp','--env','TMP=C:\arks-temp',$payload.container)
$arguments += [string[]]$payload.argv
[ArksProcessBridge]::Run($docker,[string[]]$arguments,[long]$payload.maximum,[int]$payload.timeout)
