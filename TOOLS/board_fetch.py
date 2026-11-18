"""Fetch one job board search page and print it short, for the Haiku board sweep (TOOLS/BOARD_SWEEP_PROMPT.md).
Read-only, no login. Plain request first, Scrapling's stealth browser (headless, closed after) when the plain one is blocked.

    python TOOLS/board_fetch.py <board name from BOARDS.json>     # prints the job links and text, about 8000 characters max
    python TOOLS/board_fetch.py --test-all                         # fetch every board, write board_status.json, no AI
"""
import json, os, re, sys
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.expandvars(r"%USERPROFILE%\.job_hunt\work")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0 Safari/537.36",
     "Accept-Language": "en-CA,en;q=0.9"}
JOBISH = re.compile(r"(automation|workflow|n8n|zapier|rpa|uipath|power (automate|platform)|\bai\b|agent|llm|engineer|developer|specialist|analyst|"
                    r"consultant|manager|associate|coordinator|job|career|position|apply)", re.I)
LIMIT = 8000


def boards():
    return json.load(open(os.path.join(HERE, "BOARDS.json"), encoding="utf-8"))


def fetch(url):
    """(status, text, how). Stealth only when the plain request is refused or comes back empty of links."""
    try:
        r = requests.get(url, headers=H, timeout=25)
        status, body, ctype = r.status_code, r.text, r.headers.get("content-type", "")
    except requests.RequestException as e:
        status, body, ctype = 0, str(e), ""
    if status == 200 and ("json" in ctype or body.lstrip()[:1] in "[{" or body.count("<a ") >= 10):
        return status, body, "plain"
    try:
        from scrapling.fetchers import StealthyFetcher
        page = StealthyFetcher.fetch(url, headless=True, network_idle=True, timeout=45000)
        return page.status, page.html_content, "stealth"
    except Exception as e:  # noqa: BLE001  any browser failure = report it, the sweep moves on
        return status, body if status else str(e), "plain (stealth failed: %s)" % type(e).__name__


def short_json(data, base=""):
    """Job-like dicts from any JSON shape: title, company, location, date, url."""
    out = []
    if isinstance(data, dict) and "topic_list" in data:  # Discourse forums (n8n, Make): topics carry id + slug, no url
        root = re.match(r"https?://[^/]+", base).group(0)
        return [f"{t['title'][:140]} | {t.get('created_at', '')[:10]} | {root}/t/{t['slug']}/{t['id']}"
                for t in data["topic_list"].get("topics", []) if not t.get("pinned")]

    def walk(x):
        if isinstance(x, dict):
            keys = {k.lower(): k for k in x}
            title = next((x[keys[k]] for k in ("title", "position", "name", "job_title", "jobtitle") if k in keys and isinstance(x[keys[k]], str)), None)
            url = next((x[keys[k]] for k in ("url", "apply_url", "applyurl", "applicationlink", "link", "joburl", "absolute_url", "guid")
                        if k in keys and isinstance(x[keys[k]], str) and x[keys[k]].startswith("http")), None)
            if title and url:
                pick = lambda *ks: next((str(x[keys[k]])[:80] for k in ks if k in keys and x[keys[k]] not in (None, "", [])), "")
                comp = x[keys["company"]] if "company" in keys else pick("company_name", "companyname", "organization")
                comp = (comp.get("name") or comp.get("title") or "") if isinstance(comp, dict) else comp
                out.append(f"{title[:120]} | {str(comp)[:60]} | {pick('location', 'candidate_required_location', 'locations', 'locationrestrictions', 'region')} | "
                           f"{pick('date', 'publication_date', 'pubdate', 'posted_at', 'created_at', 'created', 'date_posted', 'epoch')} | {url}")
                return
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(data)
    return out


def short_html(html, base):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
        t.decompose()
    lines, seen = [], set()
    for a in soup.find_all("a", href=True):
        text = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        href = urljoin(base, a["href"])
        if len(text) < 8 or href in seen or not JOBISH.search(text + " " + href):
            continue
        seen.add(href)
        # the card around the link usually holds company, place and age
        card = a.find_parent(["li", "article", "tr", "div"])
        ctx = re.sub(r"\s+", " ", card.get_text(" ", strip=True))[:220] if card else ""
        lines.append(f"{text[:140]} | {ctx if ctx != text else ''} | {href}")
    return lines


def show(board):
    status, body, how = fetch(board["url"])
    try:
        rows = short_json(json.loads(body), board["url"])
    except ValueError:
        rows = short_html(body, board["url"])
    head = f"== {board['name']} | HTTP {status} via {how} | {len(rows)} links | {board['url']}"
    return head, rows


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if "--test-all" in sys.argv:
        status = {}
        for b in boards():
            head, rows = show(b)
            status[b["name"]] = {"links": len(rows), "line": head}
            print(head, flush=True)
        json.dump(status, open(os.path.join(WORK, "board_status.json"), "w", encoding="utf-8"), indent=1)
        return
    name = " ".join(a for a in sys.argv[1:])
    board = next((b for b in boards() if b["name"].lower() == name.lower()), None) or {"name": name, "url": name}
    head, rows = show(board)
    out = head + "\n" + "\n".join(rows)
    print(out[:LIMIT] + ("\n[cut at %d characters]" % LIMIT if len(out) > LIMIT else ""))


if __name__ == "__main__":
    main()
