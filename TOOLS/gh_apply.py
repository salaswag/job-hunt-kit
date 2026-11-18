"""Fill (and optionally submit) a public job form in the private job Chrome profile.
    python TOOLS/gh_apply.py <url> <answers.json> fill|submit
Answers keys (all optional): text {label: value}, select {label: option} (react-select), check [label],
country, city (Greenhouse), resume / cover (file paths), resume_input / cover_input (CSS, default Greenhouse ids),
css {selector: value}, css_select {selector: option label} (native <select>), submit_button (button name) or submit_css,
dismiss [button names] (cookie banners), recaptcha true (a visible CAPTCHA: exits 2 unsent, you tick it).
Always run fill first and look at %USERPROFILE%\\.job_hunt\\work\\filled.png before submit."""
import sys, os, time, json
from patchright.sync_api import sync_playwright
HOME = os.path.expandvars(r"%USERPROFILE%\.job_hunt")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
DEFAULT_RESUME = kit.master_resume()
url, answers_path, submit = sys.argv[1], sys.argv[2], sys.argv[3] == "submit"
A = json.load(open(answers_path, encoding="utf-8"))
shot = lambda pg, n: pg.screenshot(path=os.path.join(HOME, "work", n + ".png"), full_page=True)
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(HOME + r"\chrome_job", channel="chrome", headless=False, no_viewport=True,
                                             args=["--window-position=-2400,-2400"])  # parked off-screen: never over your screen
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto(url, wait_until="domcontentloaded", timeout=45000); time.sleep(4)
    def txt(label, val):
        loc = pg.get_by_label(label, exact=False).first
        loc.click(); loc.fill(val); time.sleep(0.4)
    for lab, val in A.get("text", {}).items(): txt(lab, val)
    pg.set_input_files(A.get("resume_input", "input#resume"), A.get("resume", DEFAULT_RESUME)); time.sleep(3)
    if A.get("cover"):
        pg.set_input_files(A.get("cover_input", "input#cover_letter"), A["cover"]); time.sleep(3)
    for sel, val in A.get("css", {}).items():
        pg.click(sel); pg.fill(sel, val); time.sleep(0.4)
    for sel, opt in A.get("css_select", {}).items():
        pg.select_option(sel, label=opt); time.sleep(0.4)
    for lab, opt in A.get("select", {}).items():
        loc = pg.get_by_label(lab, exact=False).first
        loc.click(); time.sleep(0.5)
        pg.get_by_role("option", name=opt).first.click(); time.sleep(0.5)
    if A.get("country"):
        pg.get_by_label("Country", exact=False).first.click(); time.sleep(0.5)
        pg.get_by_role("option", name=A["country"]).first.click(); time.sleep(0.5)
    if A.get("city"):
        c = pg.get_by_label(A.get("city_label", "Location (City)"), exact=False).first
        c.click(); c.type(A["city"], delay=90); time.sleep(2.5)
        pg.get_by_role("option").first.click(); time.sleep(0.5)
    for sel in A.get("check_css", []):  # radios and checkboxes by selector (Lever cards)
        pg.check(sel); time.sleep(0.4)
    for sel, val, opt in A.get("type_pick", []):  # autocomplete: type, then click the first suggestion
        pg.click(sel); pg.type(sel, val, delay=90); time.sleep(2.5)
        if pg.locator(opt).count(): pg.locator(opt).first.click(); time.sleep(0.5)
    for lab in A.get("check", []):
        pg.get_by_label(lab, exact=True).first.check(); time.sleep(0.3)
    for name in A.get("dismiss", []):  # cookie banners: dismiss and carry on
        b = pg.get_by_role("button", name=name)
        if b.count(): b.first.click(); time.sleep(0.5)
    if A.get("recaptcha"):  # a visible CAPTCHA is your tick (Claude never clicks it): stop unsent
        shot(pg, "filled"); print("CAPTCHA: needs your tick, not submitted"); ctx.close(); sys.exit(2)
    shot(pg, "filled")
    if submit:
        if A.get("submit_css"): pg.click(A["submit_css"])  # JazzHR's submit is a link, not a button
        else: pg.get_by_role("button", name=A.get("submit_button", "Submit application")).first.click()
        before = pg.url  # wait for a real confirmation (Ashby takes 10 s or more), not a fixed sleep
        for _ in range(45):
            time.sleep(1)
            body = pg.inner_text("body").lower()
            if pg.url != before or any(w in body for w in ("thank you", "thanks for applying", "application submitted", "has been received", "successfully")):
                break
        time.sleep(2); shot(pg, "after_submit")
        print("URL after:", pg.url); print(pg.inner_text("body")[:800])
    ctx.close()
