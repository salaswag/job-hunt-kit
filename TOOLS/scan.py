"""Job scan: LinkedIn guest search (age + exact applicant count, no login), the public ATS feeds (Greenhouse, Lever,
Ashby) for company sites directly, Canada's Job Bank, YC startups, and the daily board sweep's finds.
Read-only, no account touched. WHAT to look for lives in TOOLS/search_config.py.

    python TOOLS/scan.py                 # new jobs from the last 6 h, writes %USERPROFILE%\\.job_hunt\\work\\candidates.json
    python TOOLS/scan.py --hours 24      # wider window (feeds); LinkedIn uses the nearest f_TPR
    python TOOLS/scan.py --test          # self-check (also checks search_config.py loads)

Skips (search_config.py): senior titles, too many years asked, too many applicants, heavy lifting on the tracks that
say so, and anything already seen. Scoring, the legit check and applying happen in the run, not here.
"""
import html, json, os, re, sys, time, random
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import WORK
from search_config import (TRACKS, SEARCHES, LOOKBACK_HOURS, TITLE_OK, NOT_FIT, BAD_TITLE, TIER, place_ok, FEED_TRACK, GH, LV,
                           ASHBY, YC, JOBBANK, JOBBANK_PLACE_WORD, JOBBANK_PLACE, MAX_YEARS, MAX_APPLICANTS, SKIP_FRENCH_REQUIRED,
                           HEAVY_LIFTING_SKIP)

SEEN = os.path.join(WORK, "seen.json")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0 Safari/537.36",
     "Accept-Language": "en-CA,en;q=0.9"}
LI = "https://www.linkedin.com/jobs-guest/jobs/api"
FRENCH_REQ = re.compile(r"((fluent|fluency|bilingual|proficien\w*)[^.\n]{0,40}french|french[^.\n]{0,30}(required|mandatory|essential|fluen|is a must))", re.I)
ACCENTS = re.compile("[àâçèéêîôùû]")  # French-language titles


def title_fits(track, title):
    return bool(title) and not BAD_TITLE.search(title) and not NOT_FIT[track].search(title) and bool(TITLE_OK[track].search(title)) \
        and not ACCENTS.search(title)


def age_days(text):
    """YC's relative ages: '2 hours', '1 day', '29 days', 'about 1 month', '3 months'."""
    t = text.lower()
    if "hour" in t or "minute" in t:
        return 0
    n = re.search(r"(\d+)", t)
    n = int(n.group(1)) if n else 1
    return n * (30 if "month" in t else 365 if "year" in t else 1)


def years_asked(text):
    """Largest lower bound of 'N years ... experience' in the text, or None. A regex heuristic: the run re-reads the posting."""
    best = None
    for m in re.finditer(r"(\d{1,2})\s*\+?\s*(?:-|to|or more)?\s*(?:\d{1,2})?\s*\+?\s*years?(?:'|’)?[^.\n]{0,60}?experience", text, re.I):
        n = int(m.group(1))
        if n <= 15:
            best = n if best is None else max(best, n)
    return best


def heavy_lifting(text):
    for m in re.finditer(r"lift(?:ing)?[^.\n]{0,25}?(\d{2,3})\s*(lbs?|pounds|kg)", text, re.I):
        n = int(m.group(1)) * (2.2 if m.group(2).lower() == "kg" else 1)
        if n >= 40:
            return True
    return False


def applicants(caption):
    if not caption:
        return None
    if re.search(r"first\s+\d+", caption, re.I):
        return 0
    m = re.search(r"(\d[\d,]*)", caption)
    return int(m.group(1).replace(",", "")) if m else None


def get(url, **kw):
    for attempt in range(3):
        try:
            r = requests.get(url, headers=H, timeout=25, **kw)
            if r.status_code == 429:
                time.sleep(30 * (attempt + 1)); continue
            return r
        except requests.RequestException:
            time.sleep(5)
    return None


def job(src, track, jid, title, company, loc, posted, url, apply_url, desc, **extra):
    return {"source": src, "track": track, "id": str(jid), "title": title, "company": company, "location": loc, "posted": posted,
            "applicants": extra.get("applicants"), "years": extra.get("years", years_asked(desc)), "heavy": heavy_lifting(desc),
            "url": url, "apply_url": apply_url, "easy_apply_only": extra.get("easy", False), "french": bool(FRENCH_REQ.search(desc)),
            "description": desc[:4000]}


def linkedin(hours, seen):
    out = []
    for track, kw, extra in SEARCHES:
        fetched = 0
        tpr = f"r{int((max(hours, LOOKBACK_HOURS.get(track, 0)) + 1) * 3600)}"
        r = get(f"{LI}/seeMoreJobPostings/search", params={"keywords": kw, "f_TPR": tpr, "sortBy": "DD", "start": 0, **extra})
        time.sleep(random.uniform(2, 4))
        if not r or r.status_code != 200:
            print(f"linkedin search failed: {kw} {extra.get('location')} {r.status_code if r else 'no response'}", file=sys.stderr); continue
        for c in BeautifulSoup(r.text, "html.parser").select("div.base-card"):
            jid = (c.get("data-entity-urn") or "").split(":")[-1]
            title = c.select_one("h3").get_text(strip=True) if c.select_one("h3") else ""
            company = c.select_one("h4").get_text(strip=True) if c.select_one("h4") else ""
            loc = c.select_one(".job-search-card__location")
            loc = loc.get_text(strip=True) if loc else ""
            key = f"li:{jid}"
            if not jid or key in seen or not title_fits(track, title):
                continue
            if fetched >= 3:  # 3 job pages per search per scan keeps LinkedIn guest traffic low; the rest wait for the next scan
                break
            fetched += 1
            seen[key] = datetime.now(timezone.utc).isoformat()
            j = get(f"{LI}/jobPosting/{jid}")
            time.sleep(random.uniform(3, 6))
            if not j or j.status_code != 200:
                continue
            js = BeautifulSoup(j.text, "html.parser")
            cap = js.select_one(".num-applicants__caption")
            ago = js.select_one(".posted-time-ago__text")
            desc = js.select_one(".show-more-less-html__markup")
            desc = desc.get_text(" ", strip=True) if desc else ""
            easy = "apply-link-onsite" in j.text and "offsite-apply" not in j.text  # company-site jobs show the offsite icon
            out.append(job("LinkedIn", track, jid, title, company, loc, ago.get_text(strip=True) if ago else "",
                           f"https://www.linkedin.com/jobs/view/{jid}", None, desc,
                           applicants=applicants(cap.get_text(strip=True) if cap else ""), easy=easy))
    return out


def feeds(hours, seen):
    since = datetime.now(timezone.utc) - timedelta(hours=max(hours, LOOKBACK_HOURS.get(FEED_TRACK, 0)))
    out = []

    def add(src, tid, title, company, loc, posted, url, desc):
        key = f"{src}:{tid}"
        if key in seen or not title_fits(FEED_TRACK, title) or not place_ok(loc or "", title) or posted < since:
            return
        seen[key] = datetime.now(timezone.utc).isoformat()
        text = BeautifulSoup(desc or "", "html.parser").get_text(" ", strip=True)
        out.append(job(src, FEED_TRACK, tid, title, company, loc, posted.isoformat(), url, url, text))

    iso = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
    for t in GH:
        r = get(f"https://boards-api.greenhouse.io/v1/boards/{t}/jobs", params={"content": "true"})
        for j in (r.json().get("jobs", []) if r and r.status_code == 200 else []):
            add("Greenhouse", j["id"], j["title"], t, j.get("location", {}).get("name", ""),
                iso(j.get("first_published") or j["updated_at"]), j["absolute_url"], requests.utils.unquote(j.get("content", "")))
    for t in LV:
        r = get(f"https://api.lever.co/v0/postings/{t}", params={"mode": "json"})
        for j in (r.json() if r and r.status_code == 200 else []):
            add("Lever", j["id"], j["text"], t, (j.get("categories") or {}).get("location", ""),
                datetime.fromtimestamp(j["createdAt"] / 1000, timezone.utc), j["hostedUrl"], j.get("descriptionPlain", ""))
    for t in ASHBY:
        r = get(f"https://api.ashbyhq.com/posting-api/job-board/{t}")
        for j in (r.json().get("jobs", []) if r and r.status_code == 200 else []):
            loc = j.get("location", "") + (" Remote" if j.get("isRemote") else "")
            add("Ashby", j["id"], j["title"], t, loc, iso(j["publishedAt"]), j["jobUrl"], j.get("descriptionPlain", ""))
    return out


def jobbank(seen):
    """Canada's Job Bank public Atom feed. Its location filter does not work, so the place word goes into the search
    text and JOBBANK_PLACE checks the result. Crawl-delay 5 s (robots.txt)."""
    out = []
    for track, kw in JOBBANK:
        since = datetime.now(timezone.utc) - timedelta(hours=max(72, LOOKBACK_HOURS.get(track, 0)))
        r = get("https://www.jobbank.gc.ca/jobsearch/feed/jobSearchRSSfeed", params={"searchstring": f"{kw} {JOBBANK_PLACE_WORD}", "locationstring": "", "page": "1"})
        time.sleep(5)
        for e in (r.text.split("<entry")[1:] if r and r.status_code == 200 else []):
            title = html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", (re.search(r"<title[^>]*>(.*?)</title>", e, re.S) or ["", ""])[1])).strip()
            url = (re.search(r'href="([^"]+)"', e) or ["", ""])[1]
            summ = html.unescape(e)
            loc = (re.search(r"Location:</strong>\s*([^<]+)", summ) or ["", ""])[1].strip()
            company = (re.search(r"Employer:</strong>\s*([^<]+)", summ) or ["", ""])[1].strip()
            pay = (re.search(r"Salary:</strong>\s*([^<\]]+)", summ) or ["", ""])[1].strip()
            upd = re.search(r"<updated>([^<]+)</updated>", e)
            key = f"jb:{url}"
            if not url or key in seen or not JOBBANK_PLACE.search(loc) or not title_fits(track, title) \
                    or (upd and datetime.fromisoformat(upd.group(1).replace("Z", "+00:00")) < since):
                continue
            seen[key] = datetime.now(timezone.utc).isoformat()
            out.append(job("Job Bank", track, url, title, company, loc, upd.group(1) if upd else "", url, url, f"Pay: {pay}", years=None))
    return out


def yc(seen):
    """YC startups from this year's batches that are hiring (freshly funded), once a day: public job JSON."""
    stamp = os.path.join(WORK, "yc_last.txt")
    if not YC or (os.path.exists(stamp) and time.time() - os.path.getmtime(stamp) < 20 * 3600):
        return []
    r = get("https://yc-oss.github.io/api/companies/hiring.json")
    year = str(datetime.now().year)
    cos = [c for c in (r.json() if r and r.status_code == 200 else []) if year in (c.get("batch") or "")]
    out = []
    for c in cos:
        r = get(f"https://www.ycombinator.com/companies/{c['slug']}/jobs")
        time.sleep(random.uniform(1, 2))
        m = re.search(r'data-page="([^"]+)"', r.text) if r and r.status_code == 200 else None
        if not m:
            continue
        for j in json.loads(html.unescape(m.group(1))).get("props", {}).get("jobPostings", []):
            key, title, loc = f"yc:{j.get('url')}", j.get("title", ""), j.get("location", "")
            if key in seen or age_days(j.get("createdAt", "99 months")) > 7 or not title_fits(FEED_TRACK, title) or not place_ok(loc, title):
                continue
            seen[key] = datetime.now(timezone.utc).isoformat()
            yrs = re.search(r"(\d+)", j.get("minExperience", ""))
            u = "https://www.ycombinator.com" + j.get("url", "")
            out.append(job("YC", FEED_TRACK, j.get("url", ""), title, c["name"], loc, j.get("createdAt", "") + " ago", u, u,
                           f'{c.get("one_liner", "")} | YC {c.get("batch")} | {j.get("salaryRange", "")} | {j.get("minExperience", "")}',
                           years=int(yrs.group(1)) if yrs else 0))
    open(stamp, "w").write(datetime.now(timezone.utc).isoformat())
    return out


def boards(seen):
    """The daily board sweep's finds (TOOLS/BOARD_SWEEP_PROMPT.md writes board_sweep.json), through the same filters."""
    try:
        found = json.load(open(os.path.join(WORK, "board_sweep.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for j in found if isinstance(found, list) else []:
        title, loc, url = str(j.get("title", "")), str(j.get("location", "")), str(j.get("url", ""))
        track = j.get("track") if j.get("track") in TRACKS else FEED_TRACK
        key = "board:" + url
        if not url or key in seen or not title_fits(track, title) or not place_ok(loc, title):
            continue
        seen[key] = datetime.now(timezone.utc).isoformat()
        out.append(job("board:" + str(j.get("board", "")), track, url, title[:200], str(j.get("company", "")), loc, str(j.get("posted", "")),
                       url, url, str(j.get("note", ""))[:300], years=j.get("years")))
    return out


def tier(title):
    return next((i for i, p in enumerate(TIER) if p.search(title)), len(TIER))


def keep(j):
    if SKIP_FRENCH_REQUIRED and j.get("french"):
        return False
    if j["years"] is not None and j["years"] > MAX_YEARS:
        return False
    if j["applicants"] is not None and j["applicants"] >= MAX_APPLICANTS:
        return False
    return not (j["track"] in HEAVY_LIFTING_SKIP and j["heavy"])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    hours = float(sys.argv[sys.argv.index("--hours") + 1]) if "--hours" in sys.argv else 6
    os.makedirs(WORK, exist_ok=True)
    seen = json.load(open(SEEN, encoding="utf-8")) if os.path.exists(SEEN) else {}
    found = linkedin(hours, seen) + feeds(hours, seen) + yc(seen) + jobbank(seen) + boards(seen)
    picks = [j for j in found if keep(j)]
    order = {t: i for i, t in enumerate(TRACKS)}
    picks.sort(key=lambda j: (order.get(j["track"], 99), tier(j["title"]), j["applicants"] or 0))
    json.dump(seen, open(SEEN, "w", encoding="utf-8"))
    json.dump(picks, open(os.path.join(WORK, "candidates.json"), "w", encoding="utf-8"), indent=1)
    for j in picks:
        print(f'{j["track"][:8]:8} | {("<25" if j["applicants"] == 0 else j["applicants"]) if j["applicants"] is not None else "-":>3} appl | {j["years"] if j["years"] is not None else "-"} yrs | '
              f'{j["title"][:50]} | {j["company"][:28]} | {j["location"][:30]} | {j["posted"][:16]}{" | EASY APPLY ONLY" if j["easy_apply_only"] else ""}')
    print(f"{len(picks)} kept of {len(found)} new")


if __name__ == "__main__":
    if "--test" in sys.argv:
        assert years_asked("Requires 3-5 years of experience in IT") == 3
        assert years_asked("6+ years of professional experience") == 6
        assert years_asked("2+ years Python experience and 7 years of industry experience") == 7
        assert years_asked("No experience needed") is None
        assert applicants("45 applicants") == 45 and applicants("Over 200 applicants") == 200
        assert applicants("Be among the first 25 applicants") == 0
        assert heavy_lifting("must be able to lift up to 50 lbs") and not heavy_lifting("lift 10 lbs")
        assert heavy_lifting("lifting 25 kg boxes")
        assert age_days("29 days") == 29 and age_days("about 1 month") == 30 and age_days("2 hours") == 0 and age_days("1 day") == 1
        assert FRENCH_REQ.search("Fluency in French and English is required") and not FRENCH_REQ.search("French is an asset")
        # search_config.py is complete and consistent
        assert TRACKS and FEED_TRACK in TRACKS, "FEED_TRACK must be one of TRACKS"
        for t in TRACKS:
            assert t in TITLE_OK and t in NOT_FIT, f"track {t!r} needs a TITLE_OK and a NOT_FIT pattern"
        for t, _, _ in SEARCHES:
            assert t in TRACKS, f"search track {t!r} is not in TRACKS"
        for t, _ in JOBBANK:
            assert t in TRACKS, f"Job Bank track {t!r} is not in TRACKS"
        assert not place_ok("Remote - UK") and place_ok("Canada")
        assert BAD_TITLE.search("Senior Analyst") and not BAD_TITLE.search("Analyst")
        print(f"scan.py self-check ok ({len(TRACKS)} tracks, {len(SEARCHES)} LinkedIn searches)")
    else:
        main()
