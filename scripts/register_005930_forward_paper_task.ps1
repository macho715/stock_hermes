##############################################################################
# register_005930_forward_paper_task.ps1
# Register Windows Task Scheduler task for daily forward paper recorder
#
# Adjust $TriggerTime based on your PC timezone:
#   Korea timezone (KST=UTC+9)  → run at 16:10 KST
#   UAE timezone (GST=UTC+4)    → run at 11:10 GST
#   UTC                         → run at 07:10 UTC
#
# Run as Administrator to register the task.
##############################################################################

$TaskName   = "STOCKPRED_005930_FORWARD_PAPER_EOD"
$ScriptPath = "C:\Users\jichu\Downloads\주식\stock_1901\scripts\run_005930_forward_paper_daily.ps1"

# Adjust trigger time for your local timezone (default: 16:10 for KST)
$TriggerTime = "16:10"

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""

$Trigger = New-ScheduledTaskTrigger -Daily -At $TriggerTime

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

# Remove existing task if present
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed existing task: $TaskName"
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "STOCK·PRED 005930.KS forward paper trading recorder (report-only, no broker orders)"

Write-Host ""
Write-Host "Task registered: $TaskName"
Write-Host "Trigger: daily at $TriggerTime (local time)"
Write-Host "Script:  $ScriptPath"
Write-Host ""
Write-Host "SAFETY NOTE: This task only records paper trading evidence."
Write-Host "No broker orders will be executed. Manual approval required before any real investment."
