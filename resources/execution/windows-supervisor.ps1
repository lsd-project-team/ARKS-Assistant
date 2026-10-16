$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
# 此入口只做固定ACL准备和TTL，绝不加载或执行项目脚本。
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
if ($identity.Name -notmatch '\\ContainerAdministrator$') { throw 'Wrong supervisor identity' }
$ttl = [int]$env:ARKS_TTL_SECONDS
if ($ttl -lt 1 -or $ttl -gt 86600) { throw 'Invalid supervisor TTL' }
$clock = [Diagnostics.Stopwatch]::StartNew()
$icacls = 'C:\Windows\System32\icacls.exe'
foreach ($directory in @('C:\work','C:\arks-temp')) {
    & $icacls $directory '/inheritance:r' '/grant:r' '*S-1-5-32-544:(OI)(CI)F' `
      '*S-1-5-18:(OI)(CI)F' 'ContainerUser:(OI)(CI)M' '/Q' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Work ACL failed' }
    if (Get-ChildItem -LiteralPath $directory -Force | Select-Object -First 1) {
        & $icacls ($directory + '\*') '/reset' '/T' '/Q' | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Source ACL failed' }
    }
}
$drive = New-Object System.IO.DriveInfo('C')
@{protocol=3;phase='prepared';capacity_bytes=$drive.TotalSize;
  available_bytes=$drive.AvailableFreeSpace;supervisor='ContainerAdministrator'} | ConvertTo-Json -Compress
while ($clock.Elapsed.TotalSeconds -lt $ttl) { [Threading.Thread]::Sleep(250) }
# 即使控制端断线，主进程退出仍终结容器内的所有工作。
[Environment]::Exit(124)
