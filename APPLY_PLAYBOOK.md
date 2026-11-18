# Apply playbook: what worked on each job site, and why

Every run adds to this file when something took more than one try (newest section at the bottom). These first lessons come from a few hundred real applications made with this kit in November 2026.

## Where to apply
- **Company sites beat job boards.** In 2026 user data, employer-site applications got about 6% interviews against about 3.4% from boards, and a tailored resume about 5.7% against 3.1%. Apply on the company's own form whenever there is one, and always tailor.
- **The easy lanes (no account):** Greenhouse, Lever, Ashby, SmartRecruiters, BambooHR, JazzHR, Fitzii. Find the job on the public feed, fill, upload, submit, read the thank-you page.
- **Account lanes:** Workday, iCIMS, GuruLink go through `TOOLS/acct_apply.py`. CareerBeacon's Apply just forwards to the employer's own ATS: use that URL. Not scripted yet: SuccessFactors, Taleo, Oracle Cloud, Avature, Paradox chat ("Olivia"): Needs you with the URL and a ready resume.
- **Indeed** shows a reCAPTCHA puzzle at sign-in and its Canadian terms ban AI use of Indeed Apply: leave Indeed jobs to the user, or find the same job on the company site.
- **LinkedIn** is for applicant counts and recruiters. Easy Apply only for a super match with no company-site route.
- **Ghost postings:** "talent pool", "future opportunities", reposted again and again, or 30+ days old: lower priority. Ontario employers with 25+ staff must say whether a vacancy really exists (since 2026-01-01).

## Discovery
- `TOOLS/scan.py`: LinkedIn guest endpoints give the post age and the exact applicant count with no login; Greenhouse (`first_published`, not `updated_at`), Lever (`createdAt`) and Ashby (`publishedAt`) feeds cover company sites directly.
- Required questions for one Greenhouse posting: `https://boards-api.greenhouse.io/v1/boards/<token>/jobs/<id>?questions=true`.
- A LinkedIn-only Workday job can often be found through Workday's public search: POST `https://<host>/wday/cxs/<tenant>/<site>/jobs` with `{"searchText": "<title>"}`.
- D2L-style embedded Greenhouse forms: `job-boards.greenhouse.io/embed/job_app?for=<board>&token=<id>`.

## Forms in Chrome (Claude in Chrome tools)
- Upload the resume with the `file_upload` tool (load it with ToolSearch). Fallback: a JS DataTransfer File built from base64 (small PDFs only).
- Greenhouse selects are react-select: click the label, then the option by name. Country and "Location (City)" are separate fields; the city is an autocomplete (type it, take the first option).
- Cookie banners and popups: dismiss and carry on.
- Ashby can take 10 to 45 seconds to show the thank-you page. Do not resubmit; confirm from the inbox if it never shows.
- Anti-fraud: Lever flags bot-like speed and virtual numbers, Ashby flags VPNs, Greenhouse sometimes adds an email code. Use a real phone number, no VPN, human pacing, and never more than a few applications to one company.

## Forms without the Chrome tools (`TOOLS/gh_apply.py`)
- Always `fill` first and look at `%USERPROFILE%\.job_hunt\work\filled.png`, then `submit`. Example answers file: `TOOLS/EXAMPLE_ANSWERS_AFFIRM.json`.
- The browser window is parked off-screen, never over your work.

## Account sites (`TOOLS/acct_apply.py`)
- Headless Chrome with a normal user agent works on Workday and iCIMS. iCIMS has an invisible hCaptcha that passed every time.
- **Workday:** most tenants need no email verification (some do: then exit 3, read the inbox, re-run with VERIFY_LINK). A saved draft shows "Continue Application" instead of "Apply". The resume parser scrambles work history, so the script deletes extra panels and types each entry from RESUME_BODY.tex. Date boxes: focus the month box and type MMYYYY in one go. "How did you hear" and "School" are nested lists or search boxes. Some tenants ask "Sign in with Google or with email": pick email. After a session expires, sign in on `<site>/login`, then open the job page (not its `/apply` link).
- **iCIMS:** the form lives in an `in_iframe=1` frame that can take 15 to 20 seconds to appear. Uploading the resume reloads the page. The address check can fail for a valid address: tick "Use this address anyway". The last "Step N of M" is where Submit sends it.
- **Answer bank order matters:** long acknowledgments first (a certification that mentions "related to my employment" once matched the relatives row and got "No"). Yes/No answers never go into optional "If yes, specify" boxes. Write regex backslashes with the Write or Edit tool, never through a Git Bash heredoc (it turned `\b` into a backspace once).
- **Dev loop for a broken site:** start Chrome with `--remote-debugging-port=9333 --user-data-dir=%USERPROFILE%\.job_hunt\chrome_acct --headless=new` and run the script with `CDP=http://127.0.0.1:9333`, so each fix is retried without a new login. Stop that Chrome before a normal run.

## CAPTCHAs
- Never clicked, never solved, not even a checkbox. Fill everything else, leave it unsent, Needs you with the URL.
- Greenhouse and Ashby use invisible reCAPTCHA that passes at human pace. Lever may show hCaptcha at submit, Workable Turnstile, SmartRecruiters DataDome: expect some of those to land in Needs you.

## Email
- Every email: greeting, blank line, short paragraphs with blank lines between, sign-off. In Gmail compose, type one paragraph at a time and press Enter twice between them (a typed "\n" can vanish and send one block). Read it back before Send, check the Sent copy after.

## Run notes
(Each run adds dated lessons below.)
