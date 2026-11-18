# Job Hunt Kit

Claude Code finds jobs for you, writes a tailored resume and cover letter for each one, applies, follows up with recruiters, and keeps everything in a Notion page. You handle the few things only a person can do (CAPTCHA ticks, assessments, interviews).

## What you need
- A Windows 11 PC that can stay on (or wake up) at the times you pick.
- Claude Code (the desktop app is fine) on a paid Claude plan.
- Google Chrome, and a free Notion account.
- About an hour for the setup.

## Set it up
1. Download this repo: the green **Code** button > **Download ZIP**. Unzip it somewhere simple, for example `C:\JobHunt`.
2. Open Claude Code, and open that folder as the project.
3. For this first chat only, pick **Opus** with **medium** effort.
4. Type: **set me up**

Claude takes it from there. It installs what is missing, asks about you and the jobs you want, builds your resume, sets up Notion, and does two or three applications with you watching before anything runs on its own.

## What you do by hand (once)
- Click **Yes** when Claude asks to install or run something.
- Make a "Job Hunt" profile in Chrome, sign in there to your job email (and LinkedIn if you want recruiter messages), and add the Claude extension.
- Make a Notion integration and paste its key into a file Claude opens for you in Notepad. Passwords and keys never go in the chat.
- Read your first resume and tell Claude what to change.

After that, check the **Needs you** box at the top of your Notion Job Hunt page now and then. That is the only list you need to watch.

## Keep the usage light
Claude usage is limited, so the kit is built to be cheap. The setup runs on Opus once. After that, the folder switches to Sonnet, and the scheduled runs use Sonnet (medium effort to apply, low to follow up) and Haiku for the daily job board sweep. Please keep it that way, use one chat per task, and type `/clear` before starting something new.

## More
- `GUIDE.md`: how Claude Code remembers things (the CLAUDE.md files, skills, settings) and how to change how the kit works.
- `CLAUDE.md`: the rules Claude follows in this folder.
