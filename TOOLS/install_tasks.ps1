# Registers the scheduled runs in Windows Task Scheduler from config/kit.json:
#   "JobHunt run"         every day at each time in "run_times"          (TOOLS/RUN_PROMPT.md)
#   "JobHunt follow-ups"  Monday to Friday at "followup_time"            (TOOLS/FOLLOWUP_PROMPT.md)
#   "JobHunt board sweep" every day at "sweep_time", before the first run (TOOLS/BOARD_SWEEP_PROMPT.md)
#   "JobHunt career-ops"  every day at "career_ops_time", only when career-ops is installed
# Run again after changing the times. Remove everything: powershell -File TOOLS\install_tasks.ps1 -Remove
param([switch]$Remove)
$root = Split-Path -Parent $PSScriptRoot
$names = "JobHunt run", "JobHunt follow-ups", "JobHunt board sweep", "JobHunt career-ops"
foreach ($n in $names) { Unregister-ScheduledTask -TaskName $n -Confirm:$false -ErrorAction SilentlyContinue }
if ($Remove) { "removed"; exit 0 }

$cfg = Get-Content "$root\config\kit.json" -Raw | ConvertFrom-Json
$s = $cfg.schedule
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -ExecutionTimeLimit (New-TimeSpan -Hours 4) -MultipleInstances IgnoreNew
function Add-Run($name, $prompt, $triggers) {
    $ps = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$root\TOOLS\RUN_JOB_HUNT.ps1`" -Prompt $prompt"
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $ps -WorkingDirectory $root
    Register-ScheduledTask -TaskName $name -Action $action -Trigger $triggers -Settings $settings | Out-Null
    "registered: $name"
}
Add-Run "JobHunt run" "TOOLS/RUN_PROMPT.md" @($s.run_times | ForEach-Object { New-ScheduledTaskTrigger -Daily -At $_ })
if ($s.followup_time) {
    Add-Run "JobHunt follow-ups" "TOOLS/FOLLOWUP_PROMPT.md" (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At $s.followup_time)
}
if ($s.sweep_time) { Add-Run "JobHunt board sweep" "TOOLS/BOARD_SWEEP_PROMPT.md" (New-ScheduledTaskTrigger -Daily -At $s.sweep_time) }
$co = "$env:USERPROFILE\.job_hunt\career-ops"
if ($s.career_ops_time -and (Test-Path "$co\scan-ats-full.mjs")) {
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$root\TOOLS\CAREER_OPS_SWEEP.ps1`""
    Register-ScheduledTask -TaskName "JobHunt career-ops" -Action $action -Trigger (New-ScheduledTaskTrigger -Daily -At $s.career_ops_time) -Settings $settings | Out-Null
    "registered: JobHunt career-ops"
}
