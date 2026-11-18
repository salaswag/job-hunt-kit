# Scheduled job hunt run. TOOLS/install_tasks.ps1 registers it in Windows Task Scheduler.
#   -Prompt TOOLS/RUN_PROMPT.md          the main run: replies, scan, apply   (config/kit.json models.run)
#   -Prompt TOOLS/FOLLOWUP_PROMPT.md     weekday follow-ups                   (models.followup)
#   -Prompt TOOLS/BOARD_SWEEP_PROMPT.md  daily job board sweep, no browser    (models.sweep)
# It skips while a game from config/kit.json "games" runs, keeps one run at a time, starts the job Chrome profile,
# and at the end closes Chrome only if this run opened it. Logs: %USERPROFILE%\.job_hunt\work\runs\
param([string]$Prompt = "TOOLS/RUN_PROMPT.md")
$root = Split-Path -Parent $PSScriptRoot
$work = "$env:USERPROFILE\.job_hunt\work"
New-Item -ItemType Directory -Force "$work\runs" | Out-Null
$cfg = Get-Content "$root\config\kit.json" -Raw | ConvertFrom-Json
$tag = if ($Prompt -like "*FOLLOWUP*") { "followup" } elseif ($Prompt -like "*BOARD_SWEEP*") { "sweep" } else { "run" }
$log = "$work\runs\$($tag)_$(Get-Date -Format yyyy-MM-dd_HHmm).log"
$start = Get-Date
$claude = (Get-Command claude -ErrorAction SilentlyContinue).Source
if (-not $claude) { $claude = "$env:USERPROFILE\.local\bin\claude.exe" }

# Model and effort per kind of run (cheap by default: Sonnet medium to apply, Sonnet low to follow up, Haiku to sweep)
$model = @{ run = @("sonnet", "medium"); followup = @("sonnet", "low"); sweep = @("haiku", "") }[$tag]
if ($cfg.models -and $cfg.models.$tag) { $model = @($cfg.models.$tag) }
$flags = @("--model", $model[0]); if ($model.Count -gt 1 -and $model[1]) { $flags += @("--effort", $model[1]) }

if ($cfg.games -and (Get-Process -Name $cfg.games -ErrorAction SilentlyContinue)) { "skipped: game running" | Out-File $log; exit 0 }

function Stop-Leftovers {
    # Processes this run started that are still alive (its own children, and anything pointing at the kit's folders or
    # headless profiles). Never your own Chrome, Claude or terminal windows.
    $all = Get-CimInstance Win32_Process
    $mine = @{}; $mine[$PID] = $true
    do { $grew = $false; foreach ($p in $all) { if ($mine[[int]$p.ParentProcessId] -and -not $mine[[int]$p.ProcessId]) { $mine[[int]$p.ProcessId] = $true; $grew = $true } } } while ($grew)
    $marks = '\\\.job_hunt\\|chrome_job|chrome_acct|' + [regex]::Escape("$root\TOOLS")
    $left = $all | Where-Object {
        $_.ProcessId -ne $PID -and $_.CreationDate -gt $start -and $_.Name -notin 'conhost.exe', 'claude.exe', 'WindowsTerminal.exe' -and
        $_.ExecutablePath -ne 'C:\Program Files\Google\Chrome\Application\chrome.exe' -and ($mine[[int]$_.ProcessId] -or ($_.CommandLine -match $marks)) }
    foreach ($p in $left) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
    "cleanup: stopped $(@($left).Count) leftover process(es)" | Out-File $log -Append
}

Set-Location $root
if ($tag -eq "sweep") {
    try { & $claude -p "Run the daily job board sweep: read $Prompt and follow it exactly." @flags --dangerously-skip-permissions *>> $log }
    finally { Stop-Leftovers }
    exit 0
}

# One run at a time (a lock older than 4 h is stale). Follow-ups wait up to 3 h for a run that is still going.
$lock = "$work\run.lock"
if ($tag -eq "followup") { $waited = 0; while ((Test-Path $lock) -and ((Get-Date) - (Get-Item $lock).LastWriteTime).TotalHours -lt 4 -and $waited -lt 180) { Start-Sleep 300; $waited += 5 } }
if ((Test-Path $lock) -and ((Get-Date) - (Get-Item $lock).LastWriteTime).TotalHours -lt 4) { "skipped: a run is still going" | Out-File $log; exit 0 }
New-Item -ItemType File -Force $lock | Out-Null
# Hold the PC awake until this script ends (Windows clears it then).
Add-Type -Namespace Win32 -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);'
[Win32.Power]::SetThreadExecutionState([uint32]"0x80000001") | Out-Null
$chromeWasOpen = [bool](Get-Process chrome -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq 'C:\Program Files\Google\Chrome\Application\chrome.exe' })
try {
    python "$root\TOOLS\preflight.py" fix *>> $log   # start the job Chrome profile, or restart it if the extension is offline
    & $claude -p "Run the scheduled job hunt: read $Prompt and follow it exactly." @flags --chrome --dangerously-skip-permissions *>> $log
} finally {
    if (-not $chromeWasOpen) { python "$root\TOOLS\preflight.py" close *>> $log }
    Remove-Item $lock -Force -ErrorAction SilentlyContinue
    Stop-Leftovers
}
