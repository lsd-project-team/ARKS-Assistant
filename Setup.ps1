param([switch]$SkipFrontend, [switch]$SkipSemanticModels)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$projectDirectory = $PSScriptRoot

# 每个子目录使用自己的锁文件，避免升级后改变已验收的框架 API。
Push-Location (Join-Path $projectDirectory 'backend')
try {
    uv sync --frozen
    if ($LASTEXITCODE -ne 0) { throw 'Python 依赖安装失败' }
    if (-not $SkipSemanticModels) {
        uv run python -m app.retrieval_setup
        if ($LASTEXITCODE -ne 0) { throw '本地检索模型准备失败，可离线使用 -SkipSemanticModels' }
        uv run python -m app.analysis_setup
        if ($LASTEXITCODE -ne 0) { throw 'Roslyn 分析器准备失败，可离线使用 -SkipSemanticModels' }
    }
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
