# How this works (read once, about 5 minutes)

## How Claude Code remembers things
Every chat starts fresh. Claude does not remember yesterday's conversation. What it does remember is whatever is written in files, because it reads them at the start of every chat:

- **Your global CLAUDE.md** (`C:\Users\<you>\.claude\CLAUDE.md`): rules for every project on your PC, for example "never use em dashes" or "always ask before deleting files". Optional. This kit does not need one.
- **The project CLAUDE.md** (the one in this folder): the rules for this folder only. This is where the job hunt rules live. When you say "remember this" or "from now on...", Claude should write it here. If it does not, say "add that to CLAUDE.md".
- **Skills** (`.claude/skills/` here, or `C:\Users\<you>\.claude\skills\` for every project): playbooks Claude loads when a task needs them. This kit ships one: `write-like-me`, which keeps every message and letter sounding like a person. Add your own writing samples to it ("add this to write-like-me") and it learns your voice.
- **Settings** (`.claude/settings.json` here): which model this folder uses, and which commands run without asking.
- **Other files Claude reads**: your profile and experience bank, `config/kit.json`, the search settings, and the playbook. The runs also write what they learn into `APPLY_PLAYBOOK.md`, so the next run does not repeat a mistake.

So the rule is simple: anything that should stick goes in a file. A chat is not memory.

## What runs on its own
Windows Task Scheduler starts these at the times you picked (change them by telling Claude):
- **Board sweep** (once a day, Haiku): reads about 50 job boards and keeps the postings that fit.
- **Job hunt run** (your run times, Sonnet medium): checks your job inbox, scans for new jobs, applies within your daily caps, updates Notion.
- **Follow-ups** (weekday mornings, Sonnet low): one or two short follow-ups per application to a named recruiter, then it stops.

Each run writes a log to `%USERPROFILE%\.job_hunt\work\runs\` and one line to `%USERPROFILE%\.job_hunt\work\RUN_LOG.md`.

## Talking back to it
- **Notion, Needs you box** (top of the Job Hunt page): things only you can do. Do them, then delete the line (or the next run removes it).
- **Notion, "Your feedback" column** on any application: notes on that resume or letter. The next run folds them into the rules.
- **Notion, Judgment calls table**: calls Claude made when a form question was unclear. Write in "Your take" if you disagree.
- **Or just open this folder in Claude Code** and say what you want changed.

## Saving usage
- One chat per task. Type `/clear` before a new task: a long chat re-reads everything each turn and costs more.
- Stay on Sonnet for normal work. Switch to Opus (`/model`) only for something hard, then switch back.
- Do not paste whole web pages or long files into the chat. Give the link or the file name and let Claude read what it needs.

## If something goes wrong
- **Nothing is happening:** open Task Scheduler and look for the "JobHunt" tasks, or ask Claude "check the last run log".
- **"Not logged in" in a run log:** open PowerShell, run `claude`, sign in again, `/exit`.
- **The Chrome part did nothing:** open Chrome with the Job Hunt profile and check the Claude extension is signed in.
- **Pause everything:** `powershell -File TOOLS\install_tasks.ps1 -Remove`. Turn it back on: run `install_tasks.ps1` again.
