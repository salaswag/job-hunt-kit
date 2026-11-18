# Setup (Claude runs this on the first chat)

For Claude: the user just opened this folder and said "set me up" (or anything). Walk them through the steps below, in order, one step at a time. Plain words, short messages, no jargon. Ask up to 5 questions at a time, wait for the answers, then act. Do every install and file edit yourself; the user only clicks Yes, signs in to sites, and types secrets into Notepad. Never ask them to paste a password or token into the chat. Tick each step off in your reply as you finish it.

Before step 1, tell them: this takes about an hour, it should run on Opus with medium effort (model picker in the app, or `/model`), and after setup everything switches to cheaper models by itself.

## 1. Tools on this PC
Check, then install what is missing (Windows 11; use `winget` with `--accept-package-agreements --accept-source-agreements`):
- Python 3.12 (`Python.Python.3.12`), Node.js LTS (`OpenJS.NodeJS.LTS`), Git (`Git.Git`), Google Chrome (`Google.Chrome`).
- Python packages: `python -m pip install requests beautifulsoup4 pypdf pymupdf patchright scrapling`, then `scrapling install` (the headless browser the board sweep falls back to).
- Tectonic (builds the resume PDFs): download the Windows x86_64 zip from the latest release at https://github.com/tectonic-typesetting/tectonic/releases and put `tectonic.exe` in `%LOCALAPPDATA%\Programs\tectonic\`. Test: build `TEMPLATES/resume.tex` once.
- The Claude Code command line (the scheduled runs need it, even if they chat in the desktop app): `irm https://claude.ai/install.ps1 | iex` in PowerShell. Then ask the user to open PowerShell, run `claude` once, sign in with the same Claude account, and type `/exit`.
- Optional, more job sources: career-ops (MIT, https://github.com/career-ops-hq/career-ops; the kit was tested with v1.38.0). Only if the user wants it: `git clone --branch v1.38.0 --depth 1` it to `%USERPROFILE%\.job_hunt\career-ops` (if that tag is missing, clone and check out the v1.38.0 commit), `npm install`, and write its `portals.yml` from step 3's answers. Set config/kit.json `schedule.career_ops_time` (for example "07:30").
Verify: `python --version`, `node --version`, `git --version`, tectonic builds the template.

## 2. The job Chrome
The runs use a separate Chrome profile, so they never touch the user's own browsing.
1. Ask them to open Chrome, click the profile icon at the top right, Add, and name the profile "Job Hunt".
2. In that profile: sign in to the email they will use for job hunting (a new Gmail just for this is cleaner, but it is their choice) and, if they want LinkedIn outreach, to LinkedIn.
3. In that profile: install the "Claude" extension from the Chrome Web Store and sign in with the same Claude account.
4. Find the profile's folder name: read `%LOCALAPPDATA%\Google\Chrome\User Data\Local State` (JSON, `profile.info_cache`, the entry whose `name` is "Job Hunt"; the key is something like "Profile 2"). It goes in config/kit.json `chrome_profile`.
5. Connect Claude in Chrome to Claude Code: in the terminal version it is the `/chrome` command. In the desktop app, look for the Chrome setting; if the app has none, that is fine, the scheduled runs start the terminal version with `--chrome`. Test with one tool call that lists the tabs.

## 3. About them (the interview)
Ask, in rounds of up to 5:
- Their resume: a PDF path or pasted text. Their LinkedIn "About" and "Experience" (pasted) if they have it. Build `EXPERIENCE_BANK.md` from `EXPERIENCE_BANK.example.md`: every job, project, skill and number, their words kept.
- The facts for `APPLICANT_PROFILE.md` (start from `APPLICANT_PROFILE.example.md`): full name, city, phone, the job email, LinkedIn URL, work status in Canada and the US, visa sponsorship, availability (days, hours, overnight shifts), start date, salary floor, willing to relocate, school, degree, criminal record needing disclosure, SIN (yes or no only, never the number), languages they speak (config/kit.json `languages`).
- What jobs they want: titles, level, places (home area, remote, relocation), and whether they also want nearby no-degree jobs. Turn the answer into tracks and write `TOOLS/search_config.py` (keep its structure; replace the EXAMPLE values), then run `python TOOLS/scan.py --test`. Rewrite the search words in `TOOLS/BOARDS.json` URLs for their field and drop boards that do not fit.
- How many applications a day per track, how often to run (times of day), follow-up days per track, LinkedIn outreach on or off, words that must never appear on their resume, and games to skip runs for (process names).
Then write `config/kit.json` from `config/kit.example.json`, and fill every `{{placeholder}}` in `TOOLS/ANSWER_BANK.json` from the profile (search the file for `{{`; none may be left). Also set the city and province words in the "reside in" row's lookahead.

## 4. Credentials (they type, you never see them)
Create `%USERPROFILE%\.job_hunt\credentials.env` with these three lines, empty after the `=`:
```
NOTION_TOKEN=
JOB_EMAIL=
SITE_PASSWORD=
```
Open it for them with `notepad "$env:USERPROFILE\.job_hunt\credentials.env"`. JOB_EMAIL = the job email. SITE_PASSWORD = one strong password they make up for every job site account the script creates (they can reset any of them later). NOTION_TOKEN comes in step 5. Ask them to save and close Notepad.

## 5. Notion
1. A free account at https://www.notion.so if they have none.
2. https://www.notion.so/profile/integrations > New integration > name "Job Hunt", type Internal, their workspace > Save. Under Capabilities, tick Read content, Update content, Insert content, Insert comments, and Read user information without email. Copy the Internal Integration Secret into credentials.env as NOTION_TOKEN.
3. In Notion: make an empty page called "Job Hunt home". On that page: the ... menu > Connections > add "Job Hunt". Copy the page link (Share > Copy link) and paste it in the chat.
4. Run `node TOOLS/setup_notion.mjs <link>`. It builds the Job Hunt page (Needs you box, Applications, Judgment calls) and writes the IDs into config/kit.json.
5. Test the phone ping: `node TOOLS/needs_you.mjs add "Test: delete me" --ping`. Ask them to check the Notion phone app for the mention (they need the app installed with notifications on), then `node TOOLS/needs_you.mjs done "Test"`.

## 6. The master resume
Write their body into `TEMPLATES/resume.tex` from the bank (one page, filled to the bottom, XYZ bullets). Build it: copy the body into a scratch job folder as RESUME_BODY.tex, run `python TOOLS/build_doc.py <folder> resume Master`, then save the PDF in this folder as `<file_prefix>_Resume.pdf`. Show it to them and fix what they say until they are happy.

## 7. First scan
`python -u TOOLS/scan.py --hours 72`. Show the top 10 in a short list. Ask if these are the right kind of jobs; tune `search_config.py` until they say yes.

## 8. Two or three supervised applications
Pick the best 2 or 3 from the scan and apply following `TOOLS/RUN_PROMPT.md` step 5 while they watch: tailored resume, the form, the Notion row. Ask them to check one Notion row and one resume. Fold every note into CLAUDE.md "Your tailoring notes".

## 9. Turn on the schedule
1. `powershell -ExecutionPolicy Bypass -File TOOLS\install_tasks.ps1` (registers the runs at the times in config/kit.json).
2. Switch this folder to the cheaper model: in `.claude/settings.json` set `"model": "sonnet"` (keep `"effortLevel": "medium"`).
3. Set `"setup_done": true` in config/kit.json.
4. Tell them, in five lines: when the runs happen, where to look (the Notion Job Hunt page, Needs you box at the top), how to give feedback ("Your feedback" and "Your take" columns, or just tell Claude here), how to pause (`powershell -File TOOLS\install_tasks.ps1 -Remove`), and to read GUIDE.md once.
