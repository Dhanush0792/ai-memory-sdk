# TruthKeeper Automated Backup Task
# Run this script to set up daily backups on Windows

# Configuration
$TaskName = "TruthKeeper-DailyBackup"
$ScriptPath = "C:\Users\Desktop\Projects\memory\scripts\run_backup.py"
$PythonPath = "python"  # or full path to python.exe
$WorkingDir = "C:\Users\Desktop\Projects\memory"
$LogFile = "C:\Users\Desktop\Projects\memory\backups\backup.log"

# Create task to run daily at 2 AM
$Action = New-ScheduledTaskAction -Execute $PythonPath `
    -Argument "$ScriptPath >> $LogFile 2>&1" `
    -WorkingDirectory $WorkingDir

$Trigger = New-ScheduledTaskTrigger -Daily -At 2am

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

# Register the task
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Daily automated backup of TruthKeeper database" `
    -Force

Write-Host "✅ Scheduled task created: $TaskName"
Write-Host "   Runs daily at 2:00 AM"
Write-Host "   Logs to: $LogFile"
Write-Host ""
Write-Host "To test the task:"
Write-Host "   Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "To view task:"
Write-Host "   Get-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "To remove task:"
Write-Host "   Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
