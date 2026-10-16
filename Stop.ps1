
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'scripts/dev/Stop.ps1') @PSBoundParameters
