$ErrorActionPreference = 'Stop'
$sourceRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../../trunk/AKRS.ZX2200')).Path
$calculatorPath = Join-Path $sourceRoot 'SupportFeature/Compensate/MotionAreaCompensate/CompensateCalculator.cs'
if (-not ([IO.Path]::GetFullPath($calculatorPath).StartsWith($sourceRoot + [IO.Path]::DirectorySeparatorChar))) {throw 'Source scope violation'}
# Compile the pure numerical class only. No machine, UI or business process is loaded.
Add-Type -Path $calculatorPath
$calculatorType = [AKRS.ZX2200.SupportFeature.Compensate.MotionAreaCompensate.CompensateCalculator]
$checks = [Collections.Generic.List[object]]::new()
function Check-Near($name, $actual, $expected, $tolerance=1e-10) {
    if ([Math]::Abs($actual-$expected) -gt $tolerance) {throw "$name : $actual != $expected"}
    $checks.Add(@{name=$name; actual=$actual; expected=$expected; tolerance=$tolerance; passed=$true})
}
Check-Near 'empty Huber' ($calculatorType::HuberEstimate([double[]]@())) 0
Check-Near 'single Huber' ($calculatorType::HuberEstimate([double[]]@(0.015))) 0.015
Check-Near 'zero MAD returns median' ($calculatorType::HuberEstimate([double[]]@(1,1,100))) 1
Check-Near 'even median' ($calculatorType::Median([double[]]@(1,2,10,20))) 6
$sample=[double[]]@(0.01,0.011,0.012,0.4)
$center=$calculatorType::HuberEstimate($sample)
$referencePath=Join-Path $PSScriptRoot '../../../../output/correction-v3.2/calculator-reference.json'
$reference=Get-Content -LiteralPath $referencePath -Raw | ConvertFrom-Json
Check-Near 'Huber weighted center agrees with independent Python' $center $reference.center
$residual=[double[]]($sample | ForEach-Object {$_-$center})
Check-Near 'residual Huber is zero within floating precision' ($calculatorType::HuberEstimate($residual)) 0
$matrix=[double[,]]::new(5,3)
$row=[double[]]@(0,1,100,3,4)
for($i=0;$i -lt 5;$i++){for($j=0;$j -lt 3;$j++){$matrix[$i,$j]=$row[$i]}}
$result=$calculatorType::Calculate($matrix,1,5,0.85,5)
$expected=[double[]]@(1,2,3,3.5,4)
for($i=0;$i -lt 5;$i++){Check-Near "row median boundary $i" $result[0,$i] $expected[$i]}
$twoRows=[double[,]]::new(6,1)
$layoutValues=[double[]]@(1,2,3,100,200,300)
for($i=0;$i -lt 6;$i++){$twoRows[$i,0]=$layoutValues[$i]}
$result2=$calculatorType::Calculate($twoRows,2,3)
for($i=0;$i -lt 3;$i++){
    Check-Near "row zero layout $i" $result2[0,$i] 2
    Check-Near "row one does not mix $i" $result2[1,$i] 200
}
$mismatchThrown=$false
try {$calculatorType::Calculate($matrix,2,3) | Out-Null} catch {$mismatchThrown=$true}
if (-not $mismatchThrown){throw 'Point count mismatch did not throw'}
$checks.Add(@{name='shape mismatch throws'; passed=$true})
$outPath=Join-Path $PSScriptRoot '../../../../output/correction-v3.2/calculator-csharp.json'
@{scope='pure CompensateCalculator class only'; source_sha256=(Get-FileHash -LiteralPath $calculatorPath -Algorithm SHA256).Hash.ToLower(); checks=$checks} |
    ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outPath -Encoding utf8
Write-Output "Pure C# numerical checks passed: $($checks.Count)"
