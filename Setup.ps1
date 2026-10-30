param([switch]$SkipFrontend, [switch]$SkipSemanticModels)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'scripts/dev/Setup.ps1') @PSBoundParameters
