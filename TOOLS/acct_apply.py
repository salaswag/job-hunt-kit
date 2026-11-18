"""Apply on account-gated ATS sites with a fixed script (Workday, iCIMS, GuruLink and more).
No AI reads the page: the script fills fields from TOOLS/ANSWER_BANK.json and the job's ANSWERS.json, nothing else.

    python TOOLS/acct_apply.py <job_url> <job_folder> [submit]

Runs headless in its own profile (%USERPROFILE%\\.job_hunt\\chrome_acct), so no window ever covers your
screen. HEADED=1 shows the window for debugging, CDP=http://127.0.0.1:9333 attaches to a running Chrome.
Without "submit" it stops on the Review page (screenshot REVIEW.png). Exit codes:
  0 submitted (CONFIRMATION.png) or stopped at Review     2 unknown required questions: <folder>/QUESTIONS.json
  3 email verification needed: <folder>/VERIFY.json      4 blocked: reason in <folder>/ACCT_STATE.json + BLOCKED.png
  5 posting closed
On 2 the run writes <folder>/ANSWERS.json ({"<label>": "<answer>"}, answers from APPLICANT_PROFILE.md only) and
re-runs. On 3 the run reads the job inbox and re-runs with VERIFY_LINK=<url> (or VERIFY_CODE=<code>).
Workday keeps the draft between runs, so a re-run continues where it stopped.
"""
import sys, os, re, json, time, glob, random, datetime
from patchright.sync_api import sync_playwright

HOME = os.path.expandvars(r"%USERPROFILE%\.job_hunt")
TOOLS = os.path.dirname(os.path.abspath(__file__))
BANK = json.load(open(os.path.join(TOOLS, "ANSWER_BANK.json"), encoding="utf-8"))
sys.path.insert(0, TOOLS)
import kit
CRED, CFG = kit.cred(), kit.cfg()
LANGS = [l.lower() for l in CFG.get("languages", ["English"])]  # languages you speak (config/kit.json)
if any("{{" in json.dumps(r["a"]) for r in BANK):
    sys.exit("TOOLS/ANSWER_BANK.json still has {{placeholders}}: finish the setup (START_HERE.md) first")


class Stop(Exception):
    def __init__(self, code, reason):
        super().__init__(reason); self.code = code


def nap(a=0.6, b=1.4): time.sleep(random.uniform(a, b))


def norm(s): return re.sub(r"\s+", " ", (s or "").replace("*", "")).strip()


def pick(options, wanted):
    """Best option for an answer (or list of answers in preference order): exact, then starts-with, then contains."""
    for w in ([wanted] if isinstance(wanted, str) else wanted):
        w = w.lower()
        for test in (lambda o: o.lower() == w, lambda o: o.lower().startswith(w), lambda o: w in o.lower()):
            hit = [o for o in options if test(o)]
            if hit: return hit[0]
    return None


BS = chr(92)  # a backslash, spelled out so editors and shells never mangle it

def tex_clean(t):
    t = re.sub(r"\\textbf\{(.*?)\}|\\textit\{(.*?)\}|\\emph\{(.*?)\}", lambda m: next(g for g in m.groups() if g is not None), t)
    t = re.sub(r"\\href\{.*?\}\{(.*?)\}", r"\1", t)
    return norm(t.replace(BS + "%", "%").replace(BS + "&", "&").replace(BS + "$", "$").replace(BS + "_", "_").replace("~", " ").replace("--", "-").replace(BS, ""))


MONTHS = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}


def work_history(folder):
    """Work entries from the job's RESUME_BODY.tex: title, company, location, start/end (month, year), bullets."""
    src = os.path.join(folder, "RESUME_BODY.tex")
    if not os.path.exists(src): src = os.path.join(os.path.dirname(TOOLS), "APPLICATIONS", "_LOCAL_BASE", "RESUME_BODY.tex")
    tex = open(src, encoding="utf-8").read()
    out = []
    for sec in re.split(r"\\section\{", tex)[1:]:
        if not re.match(r"[^}]*experience", sec, re.I): continue
        for m in re.finditer(r"\\resumeSubheading\{(.*?)\}\{(.*?)\}\{(.*?)\}\{(.*?)\}(.*?)(?=\\resumeSubheading|\Z)", sec, re.S):
            title, dates, company, loc, rest = m.groups()
            d = re.findall(r"([A-Za-z]{3})[a-z]* (\d{4})", dates)
            if not d: continue
            out.append({"title": tex_clean(title), "company": tex_clean(company), "location": tex_clean(loc),
                        "start": (MONTHS[d[0][0].lower()], d[0][1]), "end": None if re.search(r"present", dates, re.I) or len(d) < 2 else (MONTHS[d[1][0].lower()], d[1][1]),
                        "bullets": [tex_clean(b) for b in re.findall(r"\\resumeItem\{(.*?)\}\s*(?=\\resumeItem|\\resumeItemListEnd)", rest, re.S)]})
    return out


class Job:
    def __init__(self, url, folder):
        self.url, self.folder = url, folder
        self.answers = {}
        p = os.path.join(folder, "ANSWERS.json")
        if os.path.exists(p): self.answers = {norm(k).lower(): v for k, v in json.load(open(p, encoding="utf-8")).items()}
        newest = lambda pat: sorted(glob.glob(os.path.join(folder, pat)), key=os.path.getmtime, reverse=True)  # a rebuilt PDF wins
        pdfs = newest("*Resume*.pdf")
        self.resume = pdfs[0] if pdfs else kit.master_resume()
        cl = newest("*Cover_Letter*.pdf")
        self.cover = cl[0] if cl else None
        self.today = datetime.date.today()

    def answer(self, label):
        """Job answers by exact label first, then the bank by regex. None = unknown."""
        l = norm(label).lower()
        if l in self.answers: return self.answers[l], True, False
        # Current / most recent employer and title come from this job's resume (top entry), so forms match it (2026-11-13).
        if "contact" not in l and re.search(r"(current|most recent).{0,30}(job )?title|most recent position|(current or most recent|current|most recent) employer|name of your (current|most recent)", l):
            wh = work_history(self.folder)
            if wh: return (wh[0]["title"] if re.search(r"title|position", l) else wh[0]["company"]), True, False
        for row in BANK:
            if re.search(row["q"], l, re.I): return row["a"], row.get("force", False), row.get("req_only", False)
        return None, False, False

    def save(self, name, data):
        json.dump(data, open(os.path.join(self.folder, name), "w", encoding="utf-8"), indent=1, ensure_ascii=False)


# ---------------------------------------------------------------- Workday
WD_FIELDS = r"""() => {
 const vis = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
 const out = []; let n = 0;
 for (const c of document.querySelectorAll('[data-automation-id^="formField-"]')) {
   if (!vis(c) || c.parentElement.closest('[data-automation-id^="formField-"]') || c.closest('[aria-labelledby^="Work-Experience-"]')) continue;
   const lab = c.querySelector('label, legend'); const label = (lab ? lab.innerText : c.innerText.split('\n')[0]) || '';
   const id = 'f' + (n++); c.setAttribute('data-cl', id);
   const f = { id, key: c.getAttribute('data-automation-id').slice(10), label: label.trim(),
               required: /\*/.test(label) || !!c.querySelector('[aria-required=true]'), kind: '', value: '', options: [] };
   const radios = [...c.querySelectorAll('input[type=radio]')], checks = [...c.querySelectorAll('input[type=checkbox]')];
   const lb = i => { const l = document.querySelector('label[for="' + i.id + '"]'); return (l ? l.innerText : i.getAttribute('aria-label') || '').trim(); };
   if (c.querySelector('[data-automation-id^=dateSection]')) { f.kind = 'date'; f.value = [...c.querySelectorAll('input')].map(i => i.value).filter(Boolean).join('/'); }
   else if (radios.length) { f.kind = 'radio'; f.options = radios.map(lb); f.value = (radios.find(r => r.checked) && lb(radios.find(r => r.checked))) || ''; }
   else if (c.querySelector('[data-uxi-widget-type=selectinput], [data-automation-id=searchBox]')) {
     f.kind = 'prompt'; f.value = [...c.querySelectorAll('[data-automation-id=selectedItem], [data-automation-id=menuItem] [data-automation-id=promptOption]')].map(e => e.innerText.trim()).join(', '); }
   else if (c.querySelector('button[aria-haspopup=listbox]')) { f.kind = 'select'; const v = c.querySelector('button[aria-haspopup=listbox]').innerText.trim(); f.value = /^select one$/i.test(v) ? '' : v; }
   else if (c.querySelector('textarea')) { f.kind = 'text'; f.value = c.querySelector('textarea').value; }
   else if (checks.length) { f.kind = 'check'; f.options = checks.map(lb); f.value = checks.filter(x => x.checked).map(lb).join(', '); }
   else if (c.querySelector('input[type=file]')) { f.kind = 'file'; f.value = c.innerText.includes('Successfully Uploaded') || !!c.querySelector('[data-automation-id=file-upload-item]') ? 'yes' : ''; }
   else if (c.querySelector('input')) { f.kind = 'text'; f.value = c.querySelector('input').value; }
   else continue;
   out.push(f);
 } return out; }"""


class Workday:
    FIELDS = WD_FIELDS

    def __init__(self, pg, job):
        self.pg, self.root, self.job = pg, pg, job  # root = the page, or the frame holding the form
        if type(self) is Workday:  # the job page, not its /apply link, so a saved draft shows "Continue Application"
            job.url = re.sub(r"/apply(/[a-zA-Z]+)?/?(\?.*)?$", "", job.url)

    def q(self, sel): return self.pg.locator(sel)

    def shown(self, sel, t=0):
        """Visible now (t=0, no wait: a 0 timeout in Playwright means wait forever) or within t seconds."""
        if not t: return self.q(sel).first.is_visible()
        try: self.q(sel).first.wait_for(state="visible", timeout=t * 1000); return True
        except Exception: return False

    def step(self):
        s = self.q("[data-automation-id=progressBarActiveStep]")
        return norm(s.first.inner_text()) if s.count() else ""

    def run(self, submit):
        pg = self.pg
        if os.environ.get("VERIFY_LINK"):  # open it first, then sign in as usual (verifying mid-sign-in left a broken Create Account form on Nelnet)
            pg.goto(os.environ.pop("VERIFY_LINK"), wait_until="domcontentloaded", timeout=60000); time.sleep(6)
        pg.goto(self.job.url, wait_until="domcontentloaded", timeout=60000); time.sleep(5)
        if self.shown("[data-automation-id=legalNoticeAcceptButton]"): pg.click("[data-automation-id=legalNoticeAcceptButton]"); nap()
        if self.shown("[data-automation-id=errorMessage]") or "doesn't exist" in pg.inner_text("body")[:3000]:
            raise Stop(5, "posting closed or moved")
        if self.shown("[data-automation-id=continueButton]", 3):  # a saved draft from an earlier run
            pg.click("[data-automation-id=continueButton]"); time.sleep(5)
        elif self.shown("[data-automation-id=adventureButton]", 5):
            pg.click("[data-automation-id=adventureButton]"); time.sleep(3)
        for b in ("autofillWithResume", "applyManually"):  # the chooser also shows straight away on an /apply link
            if self.shown(f"[data-automation-id={b}]", 3): pg.click(f"[data-automation-id={b}]"); time.sleep(4); break
        self.sign_in()
        if not self.step():  # signed in on a bare Sign In page: open the job again
            pg.goto(self.job.url, wait_until="domcontentloaded", timeout=60000); time.sleep(5); self.enter(); self.sign_in()
        if not self.step():  # last resort, proven on Skechers and PVH: the site's own /login page, then the job again
            pg.goto(self.job.url.split("/job/")[0] + "/login", wait_until="domcontentloaded", timeout=60000); time.sleep(6)
            self.sign_in()
            pg.goto(self.job.url, wait_until="domcontentloaded", timeout=60000); time.sleep(6); self.enter()
        redo = os.environ.get("REDO")  # e.g. REDO="My Experience": go back to that step and fill it again
        for _ in range(6):
            if not redo or redo in self.step() or not self.shown("[data-automation-id=pageFooterBackButton]", 3): break
            self.pg.click("[data-automation-id=pageFooterBackButton]"); time.sleep(3)
        last, same = None, 0
        for _ in range(20):
            time.sleep(2.5)
            st = self.step()
            if not st:
                if re.search(r"you applied for this job on", pg.inner_text("body"), re.I):  # Cineplex 2026-11-13: Submit led to a landing page
                    pg.screenshot(path=os.path.join(self.job.folder, "CONFIRMATION.png"), full_page=True); return "submitted (job page says: you applied for this job)"
                if last and re.search(r"application submitted|thank you for applying", pg.inner_text("body"), re.I):  # DXC: no Review step, Next on the last page submits
                    pg.screenshot(path=os.path.join(self.job.folder, "CONFIRMATION.png"), full_page=True); return "submitted (site had no Review step)"
                raise Stop(4, "no application step found after sign-in")
            same = same + 1 if st == last else 0; last = st
            print("step:", st, flush=True)
            if same >= 2: raise Stop(4, f"stuck on {st}: " + "; ".join(self.errors()))
            if "Review" in st:
                pg.screenshot(path=os.path.join(self.job.folder, "REVIEW.png"), full_page=True)
                # Workday's parser can read a language word in an employer's name as a spoken language; never submit with it
                bad = [m for m in re.findall(r"Language\s*\n+\s*(Chinese|Mandarin|Cantonese)", pg.inner_text("body")) if m.lower() not in LANGS]
                if bad:
                    raise Stop(4, f"Review lists {bad[0]} as a language (not in config/kit.json languages): re-run with REDO=\"My Experience\"")
                if not submit: return "stopped at Review"
                self.next(); time.sleep(6)
                body = pg.inner_text("body")
                pg.screenshot(path=os.path.join(self.job.folder, "CONFIRMATION.png"), full_page=True)
                if re.search(r"submitted|thank you|received your application|application has been", body, re.I): return "submitted"
                raise Stop(4, "clicked Submit but saw no confirmation: " + "; ".join(self.errors()))
            if "Autofill with Resume" in st:
                if not self.q("[data-automation-id=file-upload-item]").count():
                    pg.set_input_files("[data-automation-id=file-upload-input-ref]", self.job.resume); time.sleep(6)
            else:
                if "My Experience" in st: self.fill_experience(); self.drop_false_languages()
                self.fill_page()
            self.next()
            if os.environ.get("DEBUG_WX") and "My Experience" in st:
                time.sleep(2); print("after Next:", self.step(), "| errors:", self.errors(), flush=True)
                pg.screenshot(path=os.path.join(self.job.folder, "MX_AFTER_NEXT.png"), full_page=True)

    def errors(self):
        return [norm(e) for e in self.pg.locator("[data-automation-id=errorHeading], [data-automation-id=errorMessage], [data-automation-id=inputError], [role=alert]").all_inner_texts() if norm(e)][:8]

    def next(self):
        self.pg.click("[data-automation-id=pageFooterNextButton]"); nap(1.5, 2.5)

    EMAIL = "[data-automation-id=email]:visible, input[type=email]:visible"
    PW = "[data-automation-id=password]:visible, input[type=password]:visible"

    def sign_in(self):
        """Create the account, or sign in (a draft can also open on a bare Sign In page once the session expired)."""
        pg = self.pg
        by_email = pg.get_by_role("button", name=re.compile(r"sign in with email|continue with email", re.I))
        if by_email.count() and by_email.first.is_visible(): by_email.first.click(); time.sleep(4)  # GoodLife: Google or email
        if not self.shown(self.PW, 6):
            return  # already signed in
        email, pw = CRED["JOB_EMAIL"], CRED["SITE_PASSWORD"]
        if self.shown("[data-automation-id=verifyPassword]"):
            pg.fill("[data-automation-id=email]", email); nap()
            pg.fill("[data-automation-id=password]", pw); nap()
            pg.fill("[data-automation-id=verifyPassword]", pw); nap()
            if self.q("[data-automation-id=createAccountCheckbox]").count(): pg.check("[data-automation-id=createAccountCheckbox]"); nap()
            cf = pg.locator("[data-automation-id=click_filter][aria-label*='Create Account' i]")
            if cf.count() and cf.first.is_visible(): cf.first.click()
            else: pg.locator("[data-automation-id=createAccountSubmitButton]").first.click(force=True)
            time.sleep(6)
            body = pg.inner_text("body")
            if re.search(r"verify your (email|account)|verification email|check your email", body, re.I):
                if not self.verify(): raise Stop(3, "Workday sent a verification email")
                return self.sign_in()
            if not self.shown(self.PW): return  # created, the application moved on
            # still on the form: this email already has an account here (the wording varies), so sign in instead
            if self.shown("[data-automation-id=signInLink]"): pg.click("[data-automation-id=signInLink]"); time.sleep(3)
        if self.shown(self.PW):
            pg.locator(self.EMAIL).first.fill(email); nap()
            pg.locator(self.PW).first.fill(pw); nap()
            cf = pg.locator("[data-automation-id=click_filter][aria-label*='Sign In' i]")
            if cf.count() and cf.first.is_visible(): cf.first.click()
            elif self.q("[data-automation-id=signInSubmitButton]").count():
                pg.locator("[data-automation-id=signInSubmitButton]").first.click(force=True)  # can be aria-hidden under an overlay
            else:
                pg.get_by_role("button", name=re.compile(r"^sign in$", re.I)).last.click()
            time.sleep(7)
            body = pg.inner_text("body")
            if re.search(r"verify your (email|account)|not been verified|verification email", body, re.I):
                if not self.verify(): raise Stop(3, "account not verified yet")
                return self.sign_in()
            if self.shown(self.PW) and re.search(r"wrong email|incorrect|invalid|locked|try again", body, re.I):
                if not getattr(self, "tried_create", False) and self.shown("[data-automation-id=createAccountLink]"):
                    self.tried_create = True  # no account on this site yet: make one
                    pg.click("[data-automation-id=createAccountLink]"); time.sleep(4)
                    return self.sign_in()
                raise Stop(4, "sign-in refused: " + "; ".join(self.errors()) + " (try Forgot your password with the inbox)")

    def enter(self):
        """From the job page into the application: draft (Continue Application), Apply, then Autofill or Manual."""
        pg = self.pg
        if self.shown("[data-automation-id=continueButton]", 3):
            pg.click("[data-automation-id=continueButton]"); time.sleep(5)
        elif self.shown("[data-automation-id=adventureButton]", 5):
            pg.click("[data-automation-id=adventureButton]"); time.sleep(3)
        for b in ("autofillWithResume", "applyManually"):
            if self.shown(f"[data-automation-id={b}]", 3): pg.click(f"[data-automation-id={b}]"); time.sleep(4); break

    def verify(self):
        link = os.environ.get("VERIFY_LINK")
        if not link:
            self.job.save("VERIFY.json", {"site": self.job.url, "look_for": "Workday verification email to the job inbox, newest",
                                          "then": "re-run with VERIFY_LINK=<the link in it>"})
            return False
        self.pg.goto(link, wait_until="domcontentloaded"); time.sleep(5)
        os.environ.pop("VERIFY_LINK")
        self.pg.goto(self.job.url, wait_until="domcontentloaded"); time.sleep(4)
        if self.shown("[data-automation-id=adventureButton]", 5):
            self.pg.click("[data-automation-id=adventureButton]"); time.sleep(3)
            for b in ("autofillWithResume", "applyManually"):
                if self.shown(f"[data-automation-id={b}]", 3): self.pg.click(f"[data-automation-id={b}]"); break
            time.sleep(4)
        return True

    # ---- fields
    def fill_page(self, rescans=0):
        unknown = []
        fields = self.root.evaluate(self.FIELDS)
        for _ in range(4):  # JCI 2026-11-13: the step label changed before the questions rendered, so 0 fields were seen
            if fields: break
            time.sleep(2.5); fields = self.root.evaluate(self.FIELDS)
        for f in fields:
            box = f'[data-cl="{f["id"]}"]'
            if f["kind"] == "file":
                if self.upload(box, f): return self.fill_page(rescans)  # an upload can reload the page: start over
                continue
            ans, force, req_only = self.job.answer(f["label"])
            if os.environ.get("DEBUG_FIELDS"): print("FIELD", f["kind"], "|", f["label"][:90], "| value:", str(f["value"])[:40], "| ans:", ans, "| force:", force, flush=True)
            if req_only and not f["required"]: continue  # street address and postal code only where a form demands them
            if ans == "today" or (f["kind"] == "date" and ans is not None and not re.match(r"\d", str(ans[0] if isinstance(ans, list) else ans))):
                ans = self.job.today.strftime("%m/%d/%Y")  # "start date: Immediately" on a date picker = today
            if f["value"] and not force and f["kind"] != "check": continue  # check groups are always reconciled
            first = ans[0] if isinstance(ans, list) and ans else ans
            if f["kind"] == "text" and str(first).lower() in ("yes", "no") and not f["required"]: continue  # an "If yes, name them" box stays empty
            if norm(str(f["value"])) == norm(str(ans)): continue
            if ans is None or (ans == "" and not force):
                if f["required"] and not f["value"]:
                    unknown.append({k: f[k] for k in ("label", "kind", "options")} | ({"options": self.options(box)} if f["kind"] in ("select", "prompt", "icdd") else {}))
                continue
            if not self.root.locator(box).count():  # a field change re-rendered the page: scan it again
                if rescans < 4: time.sleep(2); return self.fill_page(rescans + 1)
                unknown.append({"label": f["label"], "kind": f["kind"], "options": f["options"], "error": "page keeps re-rendering"}); continue
            try:
                getattr(self, "set_" + f["kind"])(box, f, ans)
            except Exception as e:
                self.pg.keyboard.press("Escape")
                if not self.root.locator(box).count() and rescans < 4: time.sleep(2); return self.fill_page(rescans + 1)
                if f["required"]: unknown.append({"label": f["label"], "kind": f["kind"], "options": f["options"], "error": str(e)[:300]})
            nap(0.3, 0.8)
        if unknown:
            self.job.save("QUESTIONS.json", {"step": self.step(), "unknown": unknown})
            raise Stop(2, f"{len(unknown)} unknown required field(s) on {self.step()}")

    def drop_false_languages(self):
        """Workday's resume parser can read a language word in an employer's name as a spoken language. Delete any Languages panel
        that is not one of config/kit.json "languages"."""
        pg = self.pg
        groups = pg.locator('[role=group][aria-labelledby^="Languages-"][aria-labelledby$="-panel"]')
        print("language panels:", groups.count(), [norm(x)[:40] for x in groups.all_inner_texts()], flush=True)
        for _ in range(4):
            hit = False
            for g in groups.all():
                v = g.locator('[data-automation-id^="formField-language"] button, [data-automation-id^="formField-language"] input').first
                t = (v.inner_text() if v.count() and v.evaluate("e => e.tagName") == "BUTTON" else (v.input_value() if v.count() else "")) or g.inner_text()
                if any(l in t.lower() for l in LANGS): continue
                d = g.locator("button:has-text('Delete'), button[aria-label*='Delete' i], [data-automation-id=panel-set-delete-button]").first
                if d.count():
                    try: d.click(timeout=5000)
                    except Exception: d.dispatch_event("click")
                    time.sleep(1.5); hit = True; break
                # the only panel (no Delete button) holds a false language: switch it to English instead
                b = g.locator('[data-automation-id^="formField-language"] button[aria-haspopup=listbox]').first
                if b.count():
                    opts = pg.locator("[role=listbox] [role=option]:not([data-automation-id=selectedItem]):visible")
                    b.click(); time.sleep(1.2)
                    for key in ("Enter", "ArrowDown"):
                        if opts.count(): break
                        b.press(key); time.sleep(1.2)
                    names = [norm(x) for x in opts.all_inner_texts()]
                    if "English" in names:
                        opts.nth(names.index("English")).click(); time.sleep(1.2); hit = True; break
                    pg.keyboard.press("Escape")
            if not hit: return

    def fill_experience(self):
        """Work Experience = the tailored resume's entries, typed in (Workday's resume parser mixes up titles and companies)."""
        pg, hist = self.pg, work_history(self.job.folder)
        if not hist or not pg.locator('[aria-labelledby="Work-Experience-section"]').count(): return
        while True:  # delete only the panels beyond the resume's entries (last first); the rest get overwritten in place
            panels = pg.locator('[role=group][aria-labelledby^="Work-Experience-"][aria-labelledby$="-panel"]')
            n = panels.count()
            if n <= max(1, len(hist)): break  # JCI 2026-11-13: delete-then-re-add in one save lost 1 to 3 entries
            d = panels.nth(n - 1).locator("button:has-text('Delete'), button[aria-label*='Delete' i], [data-automation-id=panel-set-delete-button]").first
            if not d.count(): break
            try: d.click(timeout=5000)
            except Exception:
                try: d.dispatch_event("click", timeout=5000)  # an overlay can sit on the button
                except Exception: break
            time.sleep(1.5)
            if panels.count() == n: break  # could not delete: the extra panel stays and gets overwritten below
        pids = lambda: pg.eval_on_selector_all('[role=group][aria-labelledby^="Work-Experience-"][aria-labelledby$="-panel"]', "els => els.map(e => e.getAttribute('aria-labelledby'))")
        for i, e in enumerate(hist, 1):
            ids = pids()  # a saved draft can keep panel ids that are not 1..n (2026-11-13 PwC): use the panels that exist
            if len(ids) < i:
                try: pg.locator('[aria-labelledby="Work-Experience-section"] [data-automation-id=add-button]').first.click(timeout=6000); time.sleep(1.5)
                except Exception:
                    # JCI 2026-11-13: the "Add Another" button sits outside the section group. Take the first Add button
                    # between the Work Experience heading and the next section heading.
                    ok = pg.evaluate("""() => { const h = document.getElementById('Work-Experience-section'); if (!h) return false;
                      const after = (a, b) => !!(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
                      const nxt = [...document.querySelectorAll('[id$="-section"]')].find(x => x !== h && after(h, x));
                      const b = [...document.querySelectorAll('button')].find(b => /^add( another)?$/i.test(b.innerText.trim()) && after(h, b) && (!nxt || after(b, nxt)));
                      if (!b) return false; b.click(); return true; }""")
                    time.sleep(1.5)
                    if not ok: print("no Work Experience add button: keeping the", len(ids), "panels that exist", flush=True)
                ids = pids()
                if os.environ.get("DEBUG_WX"):
                    print("WX debug i", i, "panels", len(ids), "add buttons:", pg.evaluate("""() => [...document.querySelectorAll('button')]
                      .filter(b => /add/i.test(b.innerText)).map(b => (b.getAttribute('data-automation-id') || '') + '|' + b.innerText.trim() + '|' + (b.closest('[aria-labelledby]') || {getAttribute: () => ''}).getAttribute('aria-labelledby'))"""), flush=True)
                if len(ids) < i: break  # the saved draft already holds the entries
            g = f'[aria-labelledby="{ids[min(i, len(ids)) - 1]}"] '
            try: pg.locator(g + 'input[id$="--jobTitle"]').first.wait_for(timeout=6000)  # JCI 2026-11-13: panel 6 was filled before it rendered
            except Exception: pass
            for key, val in (("jobTitle", e["title"]), ("companyName", e["company"]), ("location", e["location"])):
                el = pg.locator(g + f'input[id$="--{key}"]')
                if el.count(): el.first.fill(val); nap(0.2, 0.5)
            cb = pg.locator(g + 'input[id$="--currentlyWorkHere"]')
            if cb.count() and cb.first.is_checked() != (e["end"] is None): cb.first.click(force=True); time.sleep(0.8)
            for which, md in (("startDate", e["start"]), ("endDate", e["end"])):
                el = pg.locator(g + f'input[id$="--{which}-dateSectionMonth-input"]')
                if md and el.count():  # MMYYYY into the month box: the widget moves on to the year by itself after 2 digits
                    el.first.focus(); el.first.press("Control+a"); el.first.press("Backspace")
                    el.first.type(f"{md[0]:02d}{md[1]}", delay=70); nap(0.3, 0.6)
            ta = pg.locator(g + 'textarea[id$="--roleDescription"]')
            if ta.count(): ta.first.fill("\n".join("- " + b for b in e["bullets"])); ta.first.press("Tab")  # blur so Workday commits it
            nap()
        time.sleep(3)  # JCI 2026-11-13: the last panels were lost when Next came right after typing
        got = []  # check every panel before Next: refill a title or company that did not stick
        for idx, pid in enumerate(pids()[:len(hist)]):
            g = f'[aria-labelledby="{pid}"] '
            for key, val in (("jobTitle", hist[idx]["title"]), ("companyName", hist[idx]["company"])):
                el = pg.locator(g + f'input[id$="--{key}"]')
                if el.count() and not el.first.input_value().strip(): el.first.fill(val); el.first.press("Tab"); nap(0.3, 0.6)
            el = pg.locator(g + 'input[id$="--companyName"]')
            got.append(el.first.input_value() if el.count() else "?")
        print("work experience panels:", len(got), "of", len(hist), got, flush=True)

    def upload(self, box, f=None):
        """The job's resume plus its cover letter . A file from an earlier
        run is swapped out when its name differs or the PDF was rebuilt since (ACCT_UPLOADS.json keeps the mtimes)."""
        want = [self.job.resume] + ([self.job.cover] if self.job.cover else [])
        mark = os.path.join(self.job.folder, "ACCT_UPLOADS.json")
        stamp = {os.path.basename(x): os.path.getmtime(x) for x in want}
        old = json.load(open(mark)) if os.path.exists(mark) else {}
        txt = self.root.locator(box).inner_text()
        if all(os.path.basename(x) in txt for x in want) and old == stamp: return False
        dels = self.root.locator(box + " [data-automation-id=delete-file]")
        for _ in range(6):  # delete one at a time: .all() indexes go stale after the first delete (Intact 2026-11-13)
            if not dels.count(): break
            dels.first.click(); time.sleep(1.5)
        self.root.set_input_files(box + " input[type=file]", want); time.sleep(6)
        json.dump(stamp, open(mark, "w"))
        return False

    def options(self, box):
        try:
            self.pg.click(box + " button[aria-haspopup=listbox], " + box + " input"); time.sleep(1.2)
            o = [norm(x) for x in self.pg.locator("[role=listbox] [role=option]:visible").all_inner_texts() + self.pg.locator(self.PROMPT_OPTS).all_inner_texts()]
            self.pg.keyboard.press("Escape"); time.sleep(0.5)
            return [x for x in o if x and x.lower() != "select one"][:80]
        except Exception: return []

    def set_text(self, box, f, ans):
        el = self.root.locator(box + " textarea, " + box + " input:not([type=hidden])").first
        el.click(force=True); el.fill(ans[0] if isinstance(ans, list) else str(ans))
        el.press("Tab")

    def set_select(self, box, f, ans):
        self.pg.keyboard.press("Escape"); time.sleep(0.3)  # close a popup left open by the previous field
        btn = self.pg.locator(box + " button[aria-haspopup=listbox]").first
        # Intact 2026-11-13: the click did not open the list, and the Ethnicity pill (role=option, selectedItem) was
        # read as this field's options. Skip pills; if nothing opened, try Enter, ArrowDown, then a second click.
        opts = self.pg.locator("[role=listbox] [role=option]:not([data-automation-id=selectedItem]):visible")
        btn.click(); time.sleep(1.2)
        for key in ("Enter", "ArrowDown", None):
            if opts.count(): break
            (btn.press(key) if key else btn.click(force=True)); time.sleep(1.2)
        ctl = btn.get_attribute("aria-controls")
        names = [norm(x) for x in opts.all_inner_texts()]
        hit = pick(names, ans)
        if not hit:
            try:  # evidence for the next fix: what the page showed when no option matched
                self.pg.screenshot(path=os.path.join(self.job.folder, "SELECT_FAIL.png"))
                open(os.path.join(self.job.folder, "SELECT_FAIL.html"), "w", encoding="utf-8").write(
                    f"ctl={ctl}\n" + self.pg.locator(box).inner_html() + "\n\n<!-- listboxes -->\n" +
                    "\n".join(x.inner_html()[:3000] for x in self.pg.locator("[role=listbox]").all()))
            except Exception: pass
            self.pg.keyboard.press("Escape"); raise ValueError(f"no option for {ans!r} in {names[:15]}")
        opts.nth(names.index(hit)).click(); time.sleep(0.8)

    PROMPT_OPTS ="xpath=//*[@data-automation-id='promptOption' and not(ancestor::*[@data-automation-id='selectedItemList'])] >> visible=true"

    def prompt_selected(self, box):
        t = " ".join(self.pg.locator(box + " [data-automation-id=promptAriaInstruction]").all_inner_texts())
        m = re.search(r"(\d+) items? selected", t)
        return bool(m and int(m.group(1)) > 0) or self.pg.locator(box + " [data-automation-id=selectedItem]").count() > 0

    def set_prompt(self, box, f, ans):
        """Workday prompt: a list to browse (often nested: Social Network > LinkedIn) or a search box (schools,
        fields of study). Browse first; if nothing matches, search each wanted value (Enter auto-picks a single hit).
        Past the first level, or after a search, any listed option is acceptable (Other first)."""
        wants = [ans] if isinstance(ans, str) else list(ans)
        inp = self.pg.locator(box + " input").first
        inp.click(force=True); time.sleep(1.5)
        if self.prompt_selected(box):  # a forced answer replaces an earlier pick (Backspace removes the last chip)
            for _ in range(3): inp.press("Backspace"); time.sleep(0.5)
        opts = self.pg.locator(self.PROMPT_OPTS)
        live = lambda: [n for n in (norm(x) for x in opts.all_inner_texts()) if n and n != "No Items."]
        searched = False
        if not pick(live(), wants):
            for w in wants:
                inp.fill(""); inp.type(w[:40], delay=40); inp.press("Enter"); time.sleep(3); searched = True
                if self.prompt_selected(box) or live(): break
        for level in range(3):
            if self.prompt_selected(box): break
            names = live()
            safe = [n for n in names if not re.search(r"referr|employee|recruit|agency|friend|family|event|fair", n, re.I)]  # no follow-up questions
            hit = pick(names, wants) or ((pick(safe, ["LinkedIn", "Other", "Job Board", "Website", "Internet", "Social"]) or (safe or names)[0])
                                         if names and (level > 0 or searched) else None)
            if not hit: raise ValueError(f"no prompt option for {ans!r} in {names[:15]}")
            opts.nth(names.index(hit)).click(); time.sleep(1.5)
        self.pg.keyboard.press("Escape"); time.sleep(0.5)
        if not self.prompt_selected(box): raise ValueError(f"prompt still empty after choosing for {ans!r}")

    def set_radio(self, box, f, ans):
        hit = pick(f["options"], ans)
        if not hit: raise ValueError(f"no radio for {ans!r} in {f['options']}")
        self.root.locator(box + " input[type=radio]").nth(f["options"].index(hit)).check(force=True)

    def set_check(self, box, f, ans):
        """One checkbox (an agreement, "I am fluent"): ticked unless the answer is No. A group: exactly the matching
        option ticked and every other one cleared (a group is never "tick all")."""
        boxes = self.root.locator(box + " input[type=checkbox]")
        n = boxes.count()
        first = ans[0] if isinstance(ans, list) and ans else ans
        if n == 1:
            want = str(first).lower() not in ("no", "false", "")
            for how in ("click", "dispatch", "label"):  # DXC's terms box ignored a forced click
                if boxes.first.is_checked() == want: return
                if how == "click": boxes.first.click(force=True)
                elif how == "dispatch": boxes.first.dispatch_event("click")
                else: self.root.locator(box + " label").first.click(force=True)
                time.sleep(0.8)
            return
        if first == "ALL":  # "which days / shifts are you available": every box, re-checked (fast clicks can drop one)
            opts = f.get("options") or []
            night = [k for k in range(n) if k < len(opts) and re.search(r"overnight|graveyard|night shift", opts[k], re.I)]
            if not CFG.get("no_overnight_shifts"): night = []  # config/kit.json: true = never tick overnight shifts
            for k in night:
                if boxes.nth(k).is_checked(): boxes.nth(k).dispatch_event("click"); time.sleep(0.6)
            for _ in range(3):
                for k in range(n):
                    if k in night: continue
                    if not boxes.nth(k).is_checked():
                        try: boxes.nth(k).check(force=True, timeout=4000)
                        except Exception: boxes.nth(k).dispatch_event("click")  # Dollar Tree 2026-11-13: check() "did not change its state"
                        time.sleep(0.6)
                time.sleep(0.8)
                if all(boxes.nth(k).is_checked() for k in range(n) if k not in night): return
            raise ValueError("could not tick every box")
        if isinstance(first, str) and first.startswith("MANY:"):  # Walmart 2026-11-17: tick several (Morning, Afternoon, Evening), clear the rest
            want = {pick(f["options"], w.strip()) for w in first[5:].split(",")} - {None}
            for k in range(n):
                if boxes.nth(k).is_checked() != (f["options"][k] in want): boxes.nth(k).click(force=True); time.sleep(0.5)
            return
        hit = pick(f["options"], ans)
        if not hit: raise ValueError(f"no checkbox for {ans!r} in {f['options']}")
        for k in range(n):
            if boxes.nth(k).is_checked() != (f["options"][k] == hit): boxes.nth(k).click(force=True); time.sleep(0.5)

    def set_date(self, box, f, ans):
        """MM/DD/YYYY or MM/YYYY or YYYY typed as one run of digits into the first box (the widget advances itself)."""
        digits = "".join(x.zfill(2) if len(x) < 3 else x for x in ans.split("/"))
        el = self.pg.locator(f"{box} input[data-automation-id^=dateSection]")
        if el.count(): el.first.focus(); el.first.press("Control+a"); el.first.press("Backspace"); el.first.type(digits, delay=80)


# ---------------------------------------------------------------- iCIMS
IC_FIELDS = r"""() => {
 const vis = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
 const out = []; let n = 0;
 for (const c of document.querySelectorAll('.iCIMS_FieldRow, .iCIMS_TableRow')) {
   if (!vis(c) || c.querySelector('.iCIMS_FieldRow, .iCIMS_TableRow')) continue;
   const lab = c.querySelector('label, legend'); if (!lab) continue;
   const id = 'f' + (n++); c.setAttribute('data-cl', id);
   const f = { id, key: '', label: lab.innerText.trim(), required: !!c.querySelector('.Field_RequiredStar, [i_required=true], [aria-required=true]'), kind: '', value: '', options: [] };
   const radios = [...c.querySelectorAll('input[type=radio]')], checks = [...c.querySelectorAll('input[type=checkbox]')];
   const lb = i => { const l = document.querySelector('label[for="' + i.id + '"]'); return (l ? l.innerText : i.getAttribute('aria-label') || i.value || '').trim(); };
   const dd = c.querySelector('a.dropdown-select'), sel = c.querySelector('select');
   const txt = c.querySelector('textarea, input:not([type=hidden]):not([type=password]):not([type=radio]):not([type=checkbox]):not([type=file]):not(.dropdown-search)');
   if (dd) { f.kind = 'icdd'; const t = (c.querySelector('.dropdown-text') || dd).innerText.trim(); f.value = /make a selection/i.test(t) ? '' : t; }
   else if (sel && vis(sel)) { f.kind = 'native'; f.options = [...sel.options].map(o => o.text.trim()).filter(t => t && !/make a selection/i.test(t));
     const o = sel.options[sel.selectedIndex]; f.value = o && o.value && !/make a selection/i.test(o.text) ? o.text.trim() : ''; }
   else if (radios.length) { f.kind = 'radio'; f.options = radios.map(lb); const r = radios.find(r => r.checked); f.value = r ? lb(r) : ''; }
   else if (checks.length) { f.kind = 'check'; f.options = checks.map(lb); f.value = checks.filter(x => x.checked).map(lb).join(', '); }
   else if (c.querySelector('input[type=file]')) { f.kind = 'file'; f.value = /replace/i.test(c.innerText) ? 'kept' : ''; }
   else if (txt) { f.kind = 'text'; f.value = txt.value; }
   else continue;
   out.push(f);
 } return out; }"""


class Icims(Workday):
    """iCIMS: the form sits in an iframe (in_iframe=1). Email first; a new email gets a profile (resume, names, login,
    password) behind an invisible hCaptcha; then profile, questions and EEO pages, each with one submit button."""
    FIELDS = IC_FIELDS

    def frame(self):
        """The iframe a careers site wraps iCIMS in, or the page itself when iCIMS is the top page."""
        # employer forms (Porter's Employment Equity page, 2026-11-17) sit one iframe deeper, on icims.com/forms
        f = next((f for f in self.pg.frames if "icims.com/forms" in f.url and "action=showForm" in f.url), None)
        f = f or next((f for f in self.pg.frames if "icims.com" in f.url and "in_iframe=1" in f.url), None)
        return f or self.pg.main_frame

    def body(self):
        try: return self.root.inner_text("body")
        except Exception: return ""

    def run(self, submit):
        pg = self.pg
        pg.goto(self.job.url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(12)  # iCIMS pages bounce to the careers-site wrapper a few seconds in; act only after that
        for _ in range(15):  # careers sites wrap iCIMS in an iframe that can take 15 s to show up
            self.root = self.frame()
            if "in_iframe=1" in self.root.url: break
            try:
                if self.root.locator("a.iCIMS_ApplyOnlineButton, #enterEmailSubmitButton, #cp_form_submit_i").count(): break
            except Exception: pass
            time.sleep(1.5)
        if re.search(r"no longer (available|accepting)|(position|job) (has been |is )?(closed|filled)|job .{0,20}not found", self.body(), re.I):
            raise Stop(5, "posting closed")
        a = self.root.locator("a", has_text=re.compile(r"apply for this job|apply now|^apply$", re.I))
        try: a.first.wait_for(state="visible", timeout=8000); a.first.click(); time.sleep(7)
        except Exception: pass
        email, pw = CRED["JOB_EMAIL"], CRED["SITE_PASSWORD"]
        for _ in range(18):
            try:
                out = self.page_step(submit, email, pw)
            except Stop: raise
            except Exception as e:  # the iframe reloads under us now and then: look again
                if "detached" not in str(e) and "Target closed" not in str(e): raise
                time.sleep(4); continue
            if out: return out
        raise Stop(4, "too many pages")

    def page_step(self, submit, email, pw):
        pg = self.pg
        for t in ("Remind me later", "Not on this device", "Skip for now"):  # Auth0 passkey prompt on iCIMS sign-in
            b = pg.get_by_role("button", name=t)
            if not b.count(): b = pg.get_by_role("link", name=t)
            if b.count() and b.first.is_visible(): b.first.click(); time.sleep(6); return None
        for _ in range(12):  # a careers-site wrapper whose iCIMS iframe has not loaded yet
            if not pg.locator("iframe#icims_content_iframe").count() or any("in_iframe=1" in f.url for f in pg.frames): break
            time.sleep(2)
        self.root = self.frame(); r = self.root
        if r.locator("#enterEmailSubmitButton:visible").count():
            r.fill("#email", email); nap()
            if r.locator("#gdpr_consent_type").count():  # privacy consent gates the Next button
                r.locator("#gdpr_consent_type").select_option(index=1); nap()
            if r.locator("#accept_gdpr").count(): r.locator("#accept_gdpr").check(force=True); nap()
            for _ in range(10):
                try:
                    if not r.locator("#enterEmailSubmitButton").count(): break  # the page moved on by itself
                    if not r.locator("#enterEmailSubmitButton").is_disabled(timeout=2000):
                        r.click("#enterEmailSubmitButton", timeout=5000); break
                except Exception: pass
                time.sleep(1)
            else:
                raise Stop(4, "email page Next stays disabled (a consent box the script does not know)")
            time.sleep(8); return None
        if r.locator("[id='PersonProfileFields.Password_Confirm']:visible").count():  # new profile
            if r.locator("[id='PortalProfileFields.Resume_File']").count() and not r.locator("[id='PortalProfileFields.Resume_Button']").count():
                r.set_input_files("[id='PortalProfileFields.Resume_File']", self.job.resume); time.sleep(12); return None  # the page reloads, parsed
            for sel, val in (("FirstName", CFG["name"]["first"]), ("LastName", CFG["name"]["last"]), ("Login", email), ("Password", pw), ("Password_Confirm", pw)):
                el = r.locator(f"[id='PersonProfileFields.{sel}']")
                if el.count() and el.first.is_editable(): el.first.fill(val); nap(0.3, 0.7)
            self.fill_page()  # some sites put the whole profile (phone, address, questions) on this page
            self.address_anyway()
            btn, _ = self.primary()
            if not btn: raise Stop(4, "no submit button on the profile page")
            url0 = (pg.url, r.url); btn.click()  # a careers-site wrapper keeps its own URL: watch the iCIMS frame too
            for _ in range(15):
                time.sleep(2)
                try: now = (pg.url, self.frame().url)
                except Exception: now = (None, None)
                if now != url0 or not self.frame().locator("[id='PersonProfileFields.Password_Confirm']:visible").count(): break
            else:  # errors on the page (an address check, say) get one more pass with the fixes ticked
                tries = getattr(self, "tries", 0) + 1; self.tries = tries
                if tries >= 3: raise Stop(4, "profile not accepted (hCaptcha puzzle or a page error): " + "; ".join(self.errors()))
            time.sleep(5); return None
        pwd = r.locator("input[type=password]:visible")
        if pwd.count() == 1:  # returning candidate
            pwd.first.fill(pw); nap(); r.locator("input[type=submit]:visible, button[type=submit]:visible").first.click(); time.sleep(8)
            if r.locator("input[type=password]:visible").count(): raise Stop(4, "iCIMS sign-in refused (try Forgot password with the inbox)")
            return None
        body = self.body()
        if re.search(r"thank you for (applying|your (application|interest))|application (has been|was) (submitted|received)|successfully submitted", body, re.I):
            pg.screenshot(path=os.path.join(self.job.folder, "CONFIRMATION.png"), full_page=True)
            return "submitted"
        heading = norm(" ".join(r.locator("h2:visible").all_inner_texts()))[:120]
        print("step:", heading, flush=True)
        self.same = getattr(self, 'same', 0) + 1 if heading == getattr(self, 'last', None) else 0; self.last = heading
        if self.same >= 2: raise Stop(4, f"stuck on {heading}: " + "; ".join(self.errors()))
        self.fill_page(); self.address_anyway(); self.loose_radios()
        btn, label = self.primary()
        if not btn:
            for fr in pg.frames:  # debug aid: where are the buttons?
                try: print("FRAME", fr.url[:110], fr.evaluate("() => [...document.querySelectorAll('input[type=submit],input[type=button],button')].map(b => (b.value || b.innerText || '').trim()).slice(0, 12).join('|')"), flush=True)
                except Exception as e: print("FRAME", fr.url[:110], "err", str(e)[:80], flush=True)
            raise Stop(4, "no submit button on " + heading)
        final = self.last_step()
        if final is None: final = bool(re.search(r"submit application|^apply$|^finish$", label, re.I))
        if final:
            pg.screenshot(path=os.path.join(self.job.folder, "REVIEW.png"), full_page=True)
            if not submit: return "stopped at Review"
        btn.click(); time.sleep(9)

    def step(self):
        return norm(" ".join(self.root.locator("h2:visible").all_inner_texts()))[:120]

    def primary(self):
        """The page's forward button: the first visible submit that is not Finish Later / Save / Back.
        Custom employer forms (Porter's EEO page, 2026-11-17) use a plain input[type=button] "Submit": accept that too."""
        for b in self.root.locator("input[type=submit]:visible, button[type=submit]:visible").all():
            lab = norm(b.get_attribute("value") or b.inner_text())
            if not re.search(r"later|save|back|previous|cancel|search", lab, re.I): return b, lab
        for b in self.root.locator("input[type=button]:visible, button:visible").all():
            lab = norm(b.get_attribute("value") or b.inner_text())
            if re.fullmatch(r"submit|next|continue", lab, re.I): return b, lab
        return None, ""

    LOOSE_RADIOS = r"""() => {
     const out = [], seen = new Set();
     for (const r of document.querySelectorAll('input[type=radio]')) {
       if (seen.has(r.name) || r.closest('.iCIMS_FieldRow, .iCIMS_TableRow')) continue; seen.add(r.name);
       const group = [...document.querySelectorAll('input[type=radio]')].filter(x => x.name === r.name);
       if (group.some(x => x.checked)) continue;
       const rg = document.createRange(); rg.setStart(document.body, 0); rg.setEndBefore(r);
       const q = rg.toString().split(String.fromCharCode(10)).map(t => t.trim()).filter(t => t.includes('?')).pop() || '';
       const lb = x => { const l = x.closest('label') || document.querySelector('label[for="' + x.id + '"]'); return ((l && l.innerText) || (x.nextSibling && x.nextSibling.textContent) || x.value || '').trim(); };
       out.push({ name: r.name, q, options: group.map(lb) });
     } return out; }"""

    def loose_radios(self):
        """Radio groups outside iCIMS field rows (employer EEO questionnaires): answer by question text from the bank."""
        for g in self.root.evaluate(self.LOOSE_RADIOS):
            ans = self.job.answer(g["q"])[0] or ["prefer not", "decline", "do not wish"]
            hit = pick(g["options"], ans)
            if not hit: print("loose radio unanswered:", g["q"][:80], g["options"], flush=True); continue
            self.root.locator(f'input[type=radio][name="{g["name"]}"]').nth(g["options"].index(hit)).check(force=True); nap(0.3, 0.8)

    def last_step(self):
        """iCIMS lists "Step 3 of 5 ... (Current Step)"; the last one is where Submit sends the application."""
        for t in self.root.locator("li[id^=Step_]").all_inner_texts():
            m = re.search(r"(\d+)\D+of\D+(\d+).*current step", t.replace(" ", " "), re.I)
            if m: return m.group(1) == m.group(2)
        return None

    def address_anyway(self):
        """iCIMS cannot verify some valid addresses and asks "Use this address anyway?": yes."""
        for cb in self.root.locator("input[type=checkbox][id^=address_]").all():
            try:
                if cb.is_visible() and not cb.is_checked(): cb.check(force=True); time.sleep(0.5)
            except Exception: pass

    def errors(self):
        try: return [norm(e) for e in self.root.locator(".iCIMS_ErrorMessage:visible, .iCIMS_Error:visible, .Field_Error:visible, [id$=_error]:visible, [role=alert]:visible, li:has-text('could not'):visible, li:has-text('not able to be verified'):visible").all_inner_texts() if norm(e)][:8]
        except Exception: return []

    def options(self, box):
        try:
            if self.root.locator(box + " a.dropdown-select").count():
                self.root.locator(box + " a.dropdown-select").first.click(); time.sleep(1.5)
                o = self.root.locator(box + " .dropdown-container li:visible").all_inner_texts(); self.pg.keyboard.press("Escape")
            else: o = self.root.locator(box + " option").all_inner_texts()
            return [norm(x) for x in o if norm(x) and "make a selection" not in x.lower()][:80]
        except Exception: return []

    def upload(self, box, f=None):
        """Resume rows when empty; the cover letter goes into a cover letter or additional documents row. Once each per run:
        some sites never show a "Replace" button afterwards, and an upload reloads the page."""
        if not f: return False
        if re.search(r"resume|cv", f["label"], re.I) and not re.search(r"additional|cover", f["label"], re.I):
            if f["value"] or getattr(self, "uploaded", False): return False
            self.uploaded = True; self.root.set_input_files(box + " input[type=file]", self.job.resume)
        elif re.search(r"cover|additional doc", f["label"], re.I) and self.job.cover and not getattr(self, "cover_up", False) and not f["value"]:
            self.cover_up = True; self.root.set_input_files(box + " input[type=file]", self.job.cover)
        else:
            return False
        time.sleep(10); self.root = self.frame(); return True

    def set_native(self, box, f, ans):
        # dependent selects (iCIMS "Please specify" after Source) fill their options late: read them live
        live = [t.strip() for t in self.root.locator(box + " select option").all_inner_texts() if t.strip()]
        hit = pick(live or f["options"], ans)
        if not hit: raise ValueError(f"no option for {ans!r} in {f['options'][:15]}")
        self.root.select_option(box + " select", label=hit)

    def set_icdd(self, box, f, ans):
        self.root.locator(box + " a.dropdown-select").first.click(); time.sleep(1.5)
        lis = self.root.locator(box + " .dropdown-container li:visible")
        names = [norm(x) for x in lis.all_inner_texts()]
        hit = pick(names, ans)
        if not hit and self.root.locator(box + " input.dropdown-search:visible").count():
            self.root.locator(box + " input.dropdown-search").first.type((ans if isinstance(ans, str) else ans[0])[:20], delay=60); time.sleep(2)
            names = [norm(x) for x in lis.all_inner_texts()]; hit = pick(names, ans)
        if not hit:
            self.pg.keyboard.press("Escape"); raise ValueError(f"no option for {ans!r} in {names[:15]}")
        lis.nth(names.index(hit)).click(); time.sleep(0.8)


# ---------------------------------------------------------------- plain HTML forms (GuruLink and similar)
GEN_FIELDS = r"""() => {
 const vis = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
 const out = []; let n = 0; const seen = new Set();
 for (const lab of document.querySelectorAll('label')) {
   let el = lab.control || (lab.htmlFor && document.getElementById(lab.htmlFor));
   for (let p = lab.parentElement, i = 0; !el && p && i < 3; p = p.parentElement, i++) {
     const cs = p.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]), select, textarea'); if (cs.length === 1) el = cs[0]; }
   if (!el || seen.has(el) || el.type === 'radio' || !(vis(el) || el.type === 'file')) continue;
   seen.add(el); const id = 'f' + (n++); el.setAttribute('data-cl', id);
   const t = lab.innerText.trim();
   const f = { id, key: el.name || el.id || '', label: t, required: /\*/.test(t) || el.required || el.getAttribute('aria-required') === 'true', kind: '', value: '', options: [] };
   if (el.tagName === 'SELECT') { f.kind = 'gnative'; f.options = [...el.options].map(o => o.text.trim()).filter(x => x && !/^-+$|^select/i.test(x));
     const o = el.options[el.selectedIndex]; f.value = o && o.value && !/^-+$|^select/i.test(o.text) ? o.text.trim() : ''; }
   else if (el.type === 'password') { f.kind = 'gpassword'; f.value = el.value ? 'set' : ''; f.required = true; }
   else if (el.type === 'file') { f.kind = 'file'; }
   else if (el.type === 'checkbox') { f.kind = 'gcheck'; f.value = el.checked ? 'yes' : ''; }
   else { f.kind = 'gtext'; f.value = el.value; }
   out.push(f);
 } return out; }"""


class Generic(Workday):
    """Plain HTML forms: a <label> per field, native controls. Subclasses only drive the pages."""
    FIELDS = GEN_FIELDS

    def step(self): return norm(" ".join(self.root.locator("h1:visible, h2:visible").all_inner_texts()))[:120]

    def errors(self):
        try: return [norm(e) for e in self.root.locator(".error:visible, .alert:visible, [role=alert]:visible, [class*=rror]:visible").all_inner_texts() if norm(e)][:8]
        except Exception: return []

    def upload(self, box, f=None):
        if f and re.search(r"resume|cv", f["label"], re.I) and not getattr(self, "uploaded", False):
            self.uploaded = True; self.root.set_input_files(box, self.job.resume); time.sleep(3)
        return False

    def options(self, box): return []

    def set_gtext(self, box, f, ans): self.root.locator(box).fill(ans[0] if isinstance(ans, list) else str(ans))

    def set_gnative(self, box, f, ans):
        hit = pick(f["options"], ans)
        if not hit: raise ValueError(f"no option for {ans!r} in {f['options'][:15]}")
        self.root.select_option(box, label=hit)

    def set_gpassword(self, box, f, ans): self.root.locator(box).fill(CRED["SITE_PASSWORD"])

    def recaptcha_tick(self):
        """A visible "I'm not a robot" box is your step: the script never clicks a CAPTCHA (2026-11-12). Passive checks
        that pass by themselves (iCIMS hCaptcha, CareerBeacon) need nothing."""
        fr = next((f for f in self.pg.frames if "recaptcha/api2/anchor" in f.url), None)
        if fr and fr.locator("#recaptcha-anchor").get_attribute("aria-checked") != "true":
            raise Stop(4, "visible CAPTCHA checkbox before submit: your step, everything else is filled")

    def set_gcheck(self, box, f, ans):
        want = str(ans[0] if isinstance(ans, list) else ans).lower() not in ("no", "false", "")
        if self.root.locator(box).is_checked() != want: self.root.locator(box).click(force=True)


class GuruLink(Generic):
    """GuruLink (app.gurulink.ca): sign in with the student email, or register (resume, then a one-page profile), then apply.
    Its passwords must be letters and digits only: SITE_PASSWORD minus its symbols."""
    PW = re.sub(r"[^A-Za-z0-9]", "", CRED["SITE_PASSWORD"])
    OFFSCREEN = True  # its reCAPTCHA only renders in a real window: headed, parked off-screen (never over your screen)

    def set_gpassword(self, box, f, ans): self.root.locator(box).fill(self.PW)

    def run(self, submit):
        pg = self.pg
        jid = re.search(r"JobID=(\d+)", self.job.url).group(1)
        pg.goto(f"https://app.gurulink.ca/login.asp?JobID={jid}&ia=Apply", wait_until="domcontentloaded"); time.sleep(5)
        if self.q("#usernamebox").count():
            pg.fill("#usernamebox", CRED["JOB_EMAIL"]); nap(); pg.locator("input[type=password]").first.fill(self.PW); nap()
            pg.locator("input[type=submit][value=Login]").click(); time.sleep(6)
            if self.q("#usernamebox:visible").count():  # no account yet
                pg.goto(f"https://app.gurulink.ca/cregister.asp?JobID={jid}&ia=Apply", wait_until="domcontentloaded"); time.sleep(5)
        last, same = None, 0
        for _ in range(8):
            st = self.step() + " | " + pg.url.split("?")[0] + " | " + pg.evaluate("() => [...document.querySelectorAll('input,select,textarea')].map(e => e.name).join(',')")[:200]
            print("step:", st, flush=True)
            if re.search(r"thank you|application (has been|was) (submitted|received)|successfully applied|you have applied", pg.inner_text("body"), re.I):
                pg.screenshot(path=os.path.join(self.job.folder, "CONFIRMATION.png"), full_page=True); return "submitted"
            same = same + 1 if st == last else 0; last = st
            if same >= 2: raise Stop(4, f"stuck on {st}: " + "; ".join(self.errors()))
            self.fill_page()
            btn = pg.locator("input[type=submit]:visible, button[type=submit]:visible").filter(has_not_text=re.compile(r"talent|employers|about|resources|get started", re.I))
            btns = [b for b in btn.all() if re.search(r"continue|apply|submit|next|send", (b.get_attribute("value") or b.inner_text()), re.I)]
            if not btns: raise Stop(4, "no Continue/Apply button on " + st)
            label = norm(btns[0].get_attribute("value") or btns[0].inner_text())
            only_file = not pg.locator("input:not([type=hidden]):not([type=submit]):not([type=file]):visible, select:visible, textarea:visible").count()
            if re.search(r"apply|submit|send", label, re.I) and not only_file and not submit:
                pg.screenshot(path=os.path.join(self.job.folder, "REVIEW.png"), full_page=True); return "stopped at Review"
            self.recaptcha_tick()
            btns[0].click(); time.sleep(8)
        raise Stop(4, "too many pages")


PLATFORMS = [(re.compile(r"myworkdayjobs\.com|\.myworkday\.com"), Workday), (re.compile(r"icims\.com"), Icims),
             (re.compile(r"gurulink\.ca"), GuruLink)]


def selftest():
    """python TOOLS/acct_apply.py --test : the answer bank, option picking and resume parsing, no browser."""
    j = Job("x", os.path.join(os.path.dirname(TOOLS), "APPLICATIONS", "_LOCAL_BASE"))
    a = lambda label: j.answer(label)[0]
    assert a("Are you legally eligible to work in Canada?") == "Yes" and a("Do you require sponsorship now or in the future?") == "No"
    assert a("Are you legally authorized to work in the United States?") == "No" and a("Province or Territory")[0] == "Ontario"
    assert a("I have a preferred name") is None and a("Were you referred by an employee?") == "No"
    assert a("Are you a Region of Peel employee?") == "No" and a("Overall Result (GPA)") == ""
    assert a("Please note any potential scheduling restrictions (religion, a disability)") == "None"
    assert a("What days of the week are you available?") == "ALL" and j.answer("Address Line 1")[2] is True
    assert pick(["Yes", "No"], "yes") == "Yes" and pick(["1 - 10 HRS", "32 - 40 HRS"], ["32 - 40"]) == "32 - 40 HRS"
    assert not any(chr(8) in r["q"] for r in BANK), "a backspace slipped into a bank regex"
    h = work_history(j.folder)
    assert h and all(e["title"] and e["company"] and e["start"] for e in h), h
    print("acct_apply self-check ok:", len(BANK), "bank rows,", len(h), "local-base jobs")


def main():
    if sys.argv[1:] == ["--test"]: return selftest()
    url, folder = sys.argv[1], os.path.abspath(sys.argv[2])
    submit = len(sys.argv) > 3 and sys.argv[3] == "submit"
    plat = next((cls for rx, cls in PLATFORMS if rx.search(url)), None)
    if not plat: print("no script for this site yet:", url); sys.exit(4)
    job = Job(url, folder)
    ver = max((d for d in os.listdir(r"C:\Program Files\Google\Chrome\Application") if re.match(r"\d+\.", d)), default="157.0.0.0")
    ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver.split('.')[0]}.0.0.0 Safari/537.36"
    with sync_playwright() as p:
        if os.environ.get("CDP"):
            ctx = p.chromium.connect_over_cdp(os.environ["CDP"]).contexts[0]
        else:
            off = getattr(plat, "OFFSCREEN", False) and not os.environ.get("HEADED")
            ctx = p.chromium.launch_persistent_context(HOME + r"\chrome_acct", channel="chrome", headless=not (os.environ.get("HEADED") or off),
                                                       user_agent=ua, viewport={"width": 1280, "height": 900},
                                                       args=["--window-position=-2400,-2400"] if off else [])
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        pg.set_default_timeout(12000)
        code, msg = 0, ""
        try:
            msg = plat(pg, job).run(submit)
        except Stop as s:
            code, msg = s.code, str(s)
        except Exception as e:
            code, msg = 4, f"script error: {type(e).__name__}: {str(e)[:300]}"
        if code == 4:
            try: pg.screenshot(path=os.path.join(folder, "BLOCKED.png"), full_page=True)
            except Exception as e: msg += f" (no screenshot: {type(e).__name__})"
        job.save("ACCT_STATE.json", {"url": url, "code": code, "result": msg, "at": datetime.datetime.now().isoformat(timespec="minutes")})
        print(code, msg)
        if not os.environ.get("CDP"): ctx.close()
    sys.exit(code)


if __name__ == "__main__":
    main()
