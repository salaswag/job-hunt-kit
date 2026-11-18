"""career-ops as an extra job source (optional). career-ops v1.38.0 (MIT) lives at
%USERPROFILE%\\.job_hunt\\career-ops: about 150 public job-board readers, no login, no AI tokens.
Config there: portals.yml (titles and places to search; the setup writes it from your answers).

    python TOOLS/career_ops_feed.py            # Job Bank + HN, plus the daily sweep's log if it has not been read yet
    python TOOLS/career_ops_feed.py --sweep    # run the full sweep inline (every public Greenhouse, Lever, Ashby,
                                               # Workday, iCIMS and BambooHR board; about an hour)
    python TOOLS/career_ops_feed.py --log FILE # read a sweep log written elsewhere
    python TOOLS/career_ops_feed.py --live URL # liveness check of one posting before applying (prints live/expired/uncertain)

The daily sweep runs on its own (TOOLS/install_tasks.ps1 registers it, Task Scheduler "JobHunt career-ops sweep", 04:30) and
writes %USERPROFILE%\\.job_hunt\\work\\co_sweep.log; each run reads it once (stamp co_sweep_last.txt).

Run it AFTER scan.py: scan.py rewrites candidates.json, this appends to it. Every result is re-filtered with
scan.py's own rules. Ghost-job flags (`ghost` field): a repost cluster from career-ops detect-reposts.mjs, a posting
older than 30 days, or talent-pool wording. Ghost = lower priority, not a hard skip (the run decides).
"""
import json, os, re, subprocess, sys, time
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from scan import title_fits, place_ok, WORK, SEEN
from search_config import FEED_TRACK, JOBBANK, JOBBANK_PLACE

CO = os.path.expandvars(r"%USERPROFILE%\.job_hunt\career-ops")
STAMP = os.path.join(WORK, "co_sweep_last.txt")
GHOST_WORDS = re.compile(r"(talent pool|talent community|future opportunit|evergreen|general application|pipeline of candidates)", re.I)
NOT_A_JOB = re.compile(r"^\s*(i'?m |i am |hi,? i|seeking|looking for work)", re.I)  # HN job seekers parsed as posts


def node(args, timeout):
    r = subprocess.run(["node", *args], cwd=CO, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return r.stdout, r.stderr


def history():
    rows = {}
    path = os.path.join(CO, "data", "scan-history.tsv")
    if os.path.exists(path):
        lines = open(path, encoding="utf-8").read().splitlines()
        head = lines[0].split("\t")
        for ln in lines[1:]:
            rows[ln.split("\t")[0]] = dict(zip(head, ln.split("\t")))
    return rows


def reposted_urls():
    out, _ = node(["detect-reposts.mjs"], 120)
    try:
        data = json.loads(out)
    except ValueError:
        return set()
    return set(re.findall(r'"url"\s*:\s*"([^"]+)"', json.dumps(data)))


def live(url):
    out, err = node(["check-liveness.mjs", "--no-fallback", "--no-record", url], 120)
    m = re.search(r"\b(active|expired|uncertain)\s+https?://", out + err)  # per-URL line, not the "1 active 0 expired" total
    return {"active": "live"}.get(m.group(1), m.group(1)) if m else "uncertain"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if "--live" in sys.argv:
        print(live(sys.argv[sys.argv.index("--live") + 1])); return
    found = []
    out, _ = node(["scan.mjs", "--since", "3", "--json", "--quiet"], 600)
    try:
        added = json.loads(out.strip().splitlines()[-1]).get("added_urls", [])
    except (ValueError, IndexError):
        added = []
    hist = history()
    for u in added:
        h = hist.get(u, {})
        found.append({"url": u, "title": h.get("title", ""), "company": h.get("company", ""), "location": h.get("location", ""),
                      "posted": h.get("posted_at", ""), "source": "career-ops:" + h.get("portal", "")})
    daily = os.path.join(WORK, "co_sweep.log")
    sweep, err = False, ""
    if "--log" in sys.argv:  # parse a sweep that already ran: node scan-ats-full.mjs ... 2> file
        sweep, err = True, open(sys.argv[sys.argv.index("--log") + 1], encoding="utf-8", errors="replace").read()
    elif "--sweep" in sys.argv:
        sweep, (_, err) = True, node(["scan-ats-full.mjs", "--since", "2", "--json"], 5400)
    elif os.path.exists(daily) and (not os.path.exists(STAMP) or os.path.getmtime(daily) > os.path.getmtime(STAMP)) \
            and time.time() - os.path.getmtime(daily) > 120:  # finished writing, not read yet
        sweep, err = True, open(daily, encoding="utf-8", errors="replace").read()
    if sweep:
        for ln in err.splitlines():
            if '"kind":"offer"' in ln:
                o = json.loads(ln)
                found.append({"url": o["url"], "title": o.get("title", ""), "company": o.get("company", ""), "location": o.get("location", ""),
                              "posted": o.get("postedAt", ""), "source": "career-ops:" + o.get("source", "")})
        open(STAMP, "w").write(datetime.now(timezone.utc).isoformat())
    seen = json.load(open(SEEN, encoding="utf-8")) if os.path.exists(SEEN) else {}
    cand_path = os.path.join(WORK, "candidates.json")
    cands = json.load(open(cand_path, encoding="utf-8")) if os.path.exists(cand_path) else []
    have = {c.get("url") for c in cands} | {c.get("apply_url") for c in cands}
    reposts = reposted_urls()
    picks = []
    for j in found:
        key, title, loc = "co:" + j["url"], j["title"], j["location"] or ""
        if key in seen or j["url"] in have or NOT_A_JOB.search(title):
            continue
        near = [t for t in dict.fromkeys(t for t, _ in JOBBANK) if title_fits(t, title)] if "jobbank" in j["source"] else []
        if near and JOBBANK_PLACE.search(loc):  # a Job Bank hit near home goes to the first Job Bank track it fits
            track = near[0]
        elif title_fits(FEED_TRACK, title) and (place_ok(loc, title) or "hackernews" in j["source"] and re.search(r"remote", title, re.I)):
            track = FEED_TRACK
        else:
            continue
        seen[key] = datetime.now(timezone.utc).isoformat()
        ghost = []
        if j["url"] in reposts:
            ghost.append("reposted")
        try:
            if (date.today() - date.fromisoformat(j["posted"][:10])).days > 30:
                ghost.append("30+ days old")
        except ValueError:
            pass
        if GHOST_WORDS.search(title):
            ghost.append("talent pool")
        picks.append({"source": j["source"], "track": track, "id": j["url"], "title": title[:200], "company": j["company"], "location": loc,
                      "posted": j["posted"], "applicants": None, "years": None, "heavy": False, "url": j["url"], "apply_url": j["url"],
                      "easy_apply_only": False, "french": False, "ghost": ghost, "description": ""})
    json.dump(seen, open(SEEN, "w", encoding="utf-8"))
    json.dump(cands + picks, open(cand_path, "w", encoding="utf-8"), indent=1)
    for j in picks:
        print(f'{j["track"][:8]:8} | {j["title"][:55]} | {j["company"][:28]} | {j["location"][:30]} | {j["posted"][:10]} | '
              f'{j["source"]}{" | GHOST: " + ", ".join(j["ghost"]) if j["ghost"] else ""}')
    print(f"{len(picks)} kept of {len(found)} from career-ops ({'with' if sweep else 'without'} the full ATS sweep)")


if __name__ == "__main__":
    main()
