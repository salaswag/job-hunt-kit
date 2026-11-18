"""Save a Greenhouse posting into its job folder: JOB.md (posting text) and QUESTIONS.txt (every form field with its id,
type and options) so ANSWERS.json can be written by field id.
    python TOOLS/gh_job.py <board>:<job_id> <folder name under APPLICATIONS>"""
import html, json, os, sys, requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")
(board, jid), name = sys.argv[1].split(":"), sys.argv[2]
d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "APPLICATIONS", name)
os.makedirs(d, exist_ok=True)
j = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{jid}", params={"questions": "true"}, timeout=30).json()
text = BeautifulSoup(html.unescape(j.get("content", "")), "html.parser").get_text("\n", strip=True)
open(os.path.join(d, "JOB.md"), "w", encoding="utf-8").write(
    f"# {j['title']} at {j.get('company_name', board)}\n\n- URL: {j['absolute_url']}\n- Form: https://job-boards.greenhouse.io/{board}/jobs/{jid}\n"
    f"- Location: {j.get('location', {}).get('name')}\n- Updated: {j.get('updated_at', '')[:10]}\n\n## Posting\n\n{text}\n")
lines = []
for group in ("questions", "location_questions"):
    for q in j.get(group, []):
        for f in q.get("fields", []):
            opts = " | ".join(v["label"] for v in f.get("values", []))
            lines.append(f"{'REQ ' if q.get('required') else 'opt '}{f['name']} [{f['type']}] {q['label']}" + (f"\n      options: {opts}" if opts else ""))
for c in j.get("compliance", []) or []:
    for q in c.get("questions", []):
        for f in q.get("fields", []):
            lines.append(f"EEO {f['name']} [{f['type']}] {q['label']}\n      options: " + " | ".join(v["label"] for v in f.get("values", [])))
dq = j.get("demographic_questions") or {}
for q in dq.get("questions", []):
    lines.append(f"DEM {q.get('id')} [{q.get('type')}] {q.get('label')}\n      options: " + " | ".join(a.get('label', '') for a in q.get('answer_options', [])))
open(os.path.join(d, "QUESTIONS.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(d); print("\n".join(lines))
