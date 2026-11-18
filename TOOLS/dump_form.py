import sys, os, time, json
from patchright.sync_api import sync_playwright
url = sys.argv[1]
ud = os.path.expandvars(r"%USERPROFILE%\.job_hunt\chrome_job")
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(ud, channel="chrome", headless=False, no_viewport=True)
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto(url, wait_until="domcontentloaded", timeout=45000)
    time.sleep(5)
    pg.screenshot(path=os.path.expandvars(r"%USERPROFILE%\.job_hunt\work\form_top.png"))
    info = pg.evaluate("""() => [...document.querySelectorAll('input,textarea,select,button')].filter(e=>e.offsetParent!==null).map(e=>({tag:e.tagName,type:e.type,id:e.id,name:e.name,label:(document.querySelector('label[for="'+e.id+'"]')||{}).innerText||e.getAttribute('aria-label')||'',req:e.required||e.getAttribute('aria-required')}))""")
    for i in info: print(i)
    print(pg.url, pg.title())
    ctx.close()
