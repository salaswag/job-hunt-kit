"""Triage Lever and Ashby postings (Greenhouse: gh_triage.py): years asked, French, pay, eligibility words.
    python TOOLS/posting_triage.py <jobs.lever.co or jobs.ashbyhq.com URL> [...]      (read-only, public APIs)"""
import re, sys, requests
sys.path.insert(0, __import__("os").path.dirname(__file__))
from scan import years_asked, FRENCH_REQ

sys.stdout.reconfigure(encoding="utf-8")
_ashby = {}
for url in sys.argv[1:]:
    m = re.search(r"jobs\.lever\.co/([^/]+)/([0-9a-f-]{36})", url)
    if m:
        j = requests.get(f"https://api.lever.co/v0/postings/{m.group(1)}/{m.group(2)}", timeout=30).json()
        title, loc = j.get("text"), (j.get("categories") or {}).get("location")
        text = j.get("descriptionPlain", "") + "\n" + "\n".join(l.get("text", "") + "\n" + re.sub("<[^>]+>", " ", l.get("content", "")) for l in j.get("lists", [])) + "\n" + j.get("additionalPlain", "")
    else:
        m = re.search(r"jobs\.ashbyhq\.com/([^/]+)/([0-9a-f-]{36})", url)
        org = m.group(1)
        if org not in _ashby:
            _ashby[org] = {x["id"]: x for x in requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{org}", params={"includeCompensation": "true"}, timeout=30).json().get("jobs", [])}
        j = _ashby[org].get(m.group(2), {})
        title, loc, text = j.get("title"), j.get("location"), j.get("descriptionPlain", "") + " " + str((j.get("compensation") or {}).get("compensationTierSummary", ""))
    elig = sorted({x.group(0).lower() for x in re.finditer(r"(must (be )?(located|based|reside)[^.]{0,60}|authori[sz]ed to work in[^.]{0,40}|canada|canadian|north america|eastern time|clearance|citizenship)", text, re.I)})
    pay = re.findall(r"\$\s?\d[\d,.]{2,}[kK]?(?:\s?(?:-|to)\s?\$?\s?\d[\d,.]{2,}[kK]?)?", text)
    print(f"== {title} | {loc} | years={years_asked(text)} french={bool(FRENCH_REQ.search(text))} pay={pay[:2]}\n   {url}\n   eligibility: {elig[:6]}")
    req = re.search(r"(?is)(what you.{0,20}(bring|have|need)|requirements|qualifications|about you|you have|you.ll need)(.{0,700})", text)
    print("   " + re.sub(r"\s+", " ", (req.group(0) if req else text[:700]))[:700] + "\n")
