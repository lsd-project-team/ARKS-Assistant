param([switch]$SkipFrontend)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$projectDirectory = $PSScriptRoot

# 每个子目录使用自己的锁文件，避免升级后改变已验收的框架 API。
Push-Location (Join-Path $projectDirectory 'backend')
try {
    uv sync --frozen
    if ($LASTEXITCODE -ne 0) { throw 'Python 依赖安装失败' }
} finally { Pop-Location }

if (-not $SkipFrontend) {
    Push-Location (Join-Path $projectDirectory 'frontend')
    try {
        npm ci
        if ($LASTEXITCODE -ne 0) { throw '前端依赖安装失败' }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw '前端构建失败' }
    } finally { Pop-Location }
}
Write-Host '环境准备完成。运行 Start.ps1 打开工作区。'
