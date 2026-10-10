param(
    [string]$Backup,
    [string]$DataDirectory,
    [switch]$Apply,
    [switch]$Rollback
)

$ErrorActionPreference = 'Stop'
$restoreProject = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'LocalServer.ps1')
if (-not $DataDirectory) { $DataDirectory = Get-ServerDataDirectory $restoreProject }
$restoreData = [System.IO.Path]::GetFullPath($DataDirectory)
$restorePython = Join-Path $restoreProject 'backend\.venv\Scripts\python.exe'
$restoreArguments = @('-m', 'app.backup_restore', '--data-dir', $restoreData)
if ($Backup) { $restoreArguments += (Resolve-Path -LiteralPath $Backup).Path }
if ($Apply) { $restoreArguments += '--apply' }
if ($Rollback) { $restoreArguments += '--rollback' }
Push-Location (Join-Path $restoreProject 'backend')
try {
    & $restorePython @restoreArguments
    if ($LASTEXITCODE -ne 0) { throw '备份校验或恢复未完成，请查看上方提示。' }
} finally {
    Pop-Location
}
