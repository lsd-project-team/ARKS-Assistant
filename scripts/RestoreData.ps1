param([string]$Backup, [string]$DataDirectory, [switch]$Apply, [switch]$Rollback)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'maintenance/RestoreData.ps1') @PSBoundParameters
