param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $ArgsForProgram
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$unifiedRun = Join-Path $root "stock_rtx4060_unified\run.ps1"

if (-not (Test-Path -LiteralPath $unifiedRun)) {
    Write-Error "Unified runner not found: $unifiedRun"
    exit 1
}

& $unifiedRun @ArgsForProgram
exit $LASTEXITCODE
