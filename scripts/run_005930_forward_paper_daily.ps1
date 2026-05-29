##############################################################################
# run_005930_forward_paper_daily.ps1
# Daily forward paper trading recorder for 005930.KS
#
# Safety boundaries (never change):
#   --no-auto-promote  : LIVE_REVIEW promotion requires manual user approval
#   No broker orders   : paper trading only
#   No new capital     : new_capital_allowed=false enforced in code
##############################################################################

$ErrorActionPreference = "Stop"

$Repo = "C:\Users\jichu\Downloads\주식\stock_1901"
Set-Location $Repo

# Prefer project venv, fall back to system Python 3.12
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
if (!(Test-Path $Python)) {
    $Python = "py"
    $PythonArgs = @("-3.12")
} else {
    $PythonArgs = @()
}

$LogDir = Join-Path $Repo "reports\live_review\005930\recorder_logs"
if (!(Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$LogFile = Join-Path $LogDir "$(Get-Date -Format 'yyyy-MM-dd').log"

$Args = $PythonArgs + @(
    "-m", "stock_rtx4060.live_review.auto_forward_recorder",
    "--symbol", "005930.KS",
    "--market", "KRX",
    "--benchmark", "069500.KS",
    "--readiness", "PAPER_PASS",
    "--evidence-dir", "reports\live_review\005930",
    "--stop-after-days", "30",
    "--no-auto-promote"
)

Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting forward paper recorder..."

try {
    & $Python @Args 2>&1 | Tee-Object -FilePath $LogFile -Append
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Done."
} catch {
    Write-Error "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] ERROR: $_"
    exit 1
}
