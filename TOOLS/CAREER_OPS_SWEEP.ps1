# Daily career-ops sweep (optional; TOOLS/install_tasks.ps1 registers it when career-ops is installed).
# No AI tokens, no login: public job boards only. Writes %USERPROFILE%\.job_hunt\work\co_sweep.log, which
# TOOLS\career_ops_feed.py reads on the next run.
$work = "$env:USERPROFILE\.job_hunt\work"
New-Item -ItemType Directory -Force $work | Out-Null
Set-Location "$env:USERPROFILE\.job_hunt\career-ops"
# Start-Process keeps stderr raw (PowerShell 5.1's 2> would wrap each line as an error record and break the JSON lines)
Start-Process node -ArgumentList "scan-ats-full.mjs", "--since", "2", "--json" -NoNewWindow -Wait `
    -RedirectStandardError "$work\co_sweep.tmp" -RedirectStandardOutput "$work\co_sweep.out"
Move-Item -Force "$work\co_sweep.tmp" "$work\co_sweep.log"
