"""(TOOLS/ats_find.py, 2026-11-12) For LinkedIn finds: look for the same job on a no-account ATS (Greenhouse, Lever, Ashby, SmartRecruiters).
    python ats_find.py <candidates.json>      prints: company | title | ATS apply URL or "-"
Read-only public APIs. Slug guesses: company name lowercased with spaces, dots and suffixes removed."""
import json, re, sys, requests
from difflib import SequenceMatcher
sys.stdout.reconfigure(encoding="utf-8")
H = {"User-Agent": "Mozilla/5.0"}


def slugs(company):
    c = re.sub(r"\b(inc|ltd|llc|corp|corporation|canada|technologies|technology|group|software|labs?)\b\.?", "", company.lower())
    c = re.sub(r"[^a-z0-9 ]", "", c).strip()
    out = [c.replace(" ", ""), c.replace(" ", "-"), c.split(" ")[0] if c else ""]
    return [s for i, s in enumerate(out) if s and s not in out[:i]]


def boards(slug):
    found = []
    try:
        r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", headers=H, timeout=15)
        if r.status_code == 200:
            found += [(j["title"], j["absolute_url"]) for j in r.json().get("jobs", [])]
        r = requests.get(f"https://api.lever.co/v0/postings/{slug}?mode=json", headers=H, timeout=15)
        if r.status_code == 200 and isinstance(r.json(), list):
            found += [(j["text"], j["hostedUrl"] + "/apply") for j in r.json()]
        r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", headers=H, timeout=15)
        if r.status_code == 200:
            found += [(j["title"], j["jobUrl"] + "/application") for j in r.json().get("jobs", [])]
        r = requests.get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100", headers=H, timeout=15)
        if r.status_code == 200:
            found += [(j["name"], f"https://jobs.smartrecruiters.com/{slug}/{j['id']}") for j in r.json().get("content", [])]
    except (requests.RequestException, ValueError):
        pass
    return found


for j in json.load(open(sys.argv[1], encoding="utf-8")):
    best = (0, None, None)
    for s in slugs(j["company"]):
        for title, url in boards(s):
            score = SequenceMatcher(None, title.lower(), j["title"].lower()).ratio()
            if score > best[0]:
                best = (score, title, url)
        if best[0] >= 0.8:
            break
    hit = best[2] if best[0] >= 0.75 else "-"
    print(f'{j["company"][:28]} | {j["title"][:55]} | {round(best[0], 2)} | {hit}')
