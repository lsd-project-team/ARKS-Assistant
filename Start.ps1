param([int]$Port = 8765, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'scripts/dev/Start.ps1') @PSBoundParameters
