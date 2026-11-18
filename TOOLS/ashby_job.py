"""Save an Ashby posting into its job folder: JOB.md (posting text, pay) and QUESTIONS.txt (form fields by DOM id).
    python TOOLS/ashby_job.py <org>/<posting id> <folder name under APPLICATIONS>
Ashby DOM: each field's input id is its path (_systemfield_name, _systemfield_email, a UUID for custom questions);
the resume is input#_systemfield_resume; Yes/No (Boolean) fields are two buttons; ValueSelect are radios or a select."""
import json, os, sys, requests

sys.stdout.reconfigure(encoding="utf-8")
(org, jid), name = sys.argv[1].split("/"), sys.argv[2]
d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "APPLICATIONS", name)
os.makedirs(d, exist_ok=True)
q = ("query ApiJobPosting($organizationHostedJobsPageName: String!, $jobPostingId: String!) { jobPosting(organizationHostedJobsPageName: "
     "$organizationHostedJobsPageName, jobPostingId: $jobPostingId) { id title applicationForm { sections { title fieldEntries { ... on FormFieldEntry "
     "{ id field isRequired } } } } } }")
form = requests.post("https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobPosting", timeout=30, json={"operationName": "ApiJobPosting",
                     "variables": {"organizationHostedJobsPageName": org, "jobPostingId": jid}, "query": q}).json()["data"]["jobPosting"]
j = next(x for x in requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{org}", params={"includeCompensation": "true"}, timeout=30).json()["jobs"] if x["id"] == jid)
pay = (j.get("compensation") or {}).get("compensationTierSummary")
open(os.path.join(d, "JOB.md"), "w", encoding="utf-8").write(
    f"# {j['title']} at {org}\n\n- URL: {j['jobUrl']}\n- Apply: {j['applyUrl']}\n- Location: {j.get('location')} ({j.get('workplaceType')})\n"
    f"- Published: {j.get('publishedAt', '')[:10]}\n- Pay: {pay}\n\n## Posting\n\n{j['descriptionPlain']}\n")
lines = []
for s in form["applicationForm"]["sections"]:
    for e in s["fieldEntries"]:
        f = e["field"]
        opts = " | ".join(v.get("label", "") for v in (f.get("selectableValues") or []))
        lines.append(f"{'REQ' if e['isRequired'] else 'opt'} {f.get('path')} [{f.get('type')}] {f.get('title')}" + (f"\n      options: {opts}" if opts else ""))
open(os.path.join(d, "QUESTIONS.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(d); print(f"{j['title']} | {j.get('location')} | {pay}"); print("\n".join(lines))
