"""Quick triage of Greenhouse postings before tailoring: years asked, Canada/US eligibility words, French, and the form's
required questions.  python TOOLS/gh_triage.py <board>:<job_id> [<board>:<job_id> ...]   (read-only, public API)"""
import html, re, sys, requests
from bs4 import BeautifulSoup
sys.path.insert(0, __import__("os").path.dirname(__file__))
from scan import years_asked, FRENCH_REQ

sys.stdout.reconfigure(encoding="utf-8")
for arg in sys.argv[1:]:
    board, jid = arg.split(":")
    r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{jid}", params={"questions": "true"}, timeout=30)
    if r.status_code != 200:
        print(f"== {arg}: HTTP {r.status_code}\n"); continue
    j = r.json()
    text = BeautifulSoup(html.unescape(j.get("content", "")), "html.parser").get_text(" ", strip=True)
    elig = sorted({m.group(0).lower() for m in re.finditer(r"(must (be )?(located|based|reside)[^.]{0,60}|authori[sz]ed to work in[^.]{0,40}|"
                                                           r"(us|u\.s\.|united states)[- ]based|canada|canadian|north america|eastern time|est\b|clearance|citizenship)", text, re.I)})
    pay = re.findall(r"\$\s?\d[\d,]{2,}(?:\s?(?:-|to)\s?\$?\s?\d[\d,]{2,})?", text)
    print(f"== {board} | {j['title']} | {j.get('location', {}).get('name')} | updated {j.get('updated_at', '')[:10]}")
    print(f"   years={years_asked(text)} french={bool(FRENCH_REQ.search(text))} pay={pay[:2]}")
    print(f"   eligibility words: {elig[:8]}")
    req = [q['label'][:70] for q in j.get("questions", []) if q.get("required") and not re.search(r"^(first name|last name|email|phone|resume|cover letter)", q["label"], re.I)]
    print(f"   required questions: {req}")
    print(f"   {text[:600]}\n")
