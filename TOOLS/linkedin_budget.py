"""LinkedIn budget, so the job hunt never sends more connects or messages than a free account safely can.
Every run checks before a LinkedIn action and logs right after it. Agent name for the job hunt: jobhunt.

    python linkedin_budget.py check <connect|message|search|apply> <agent>    prints JSON, exit 0 = ok to send, 1 = over budget
    python linkedin_budget.py log <connect|message|search|apply> <agent> "<who>"
    python linkedin_budget.py status                                    today and last 7 days, per agent
    python linkedin_budget.py selftest

Ledger: %USERPROFILE%\\.job_hunt\\linkedin_ledger.jsonl. Limits are for a FREE account, kept under LinkedIn's ~100 invites a week.
"""
import json
import os
import sys
from datetime import datetime, timedelta

LEDGER = os.path.expandvars(r"%USERPROFILE%\.job_hunt\linkedin_ledger.jsonl")
# kind: (all agents per day, all agents per 7 days)
TOTAL = {"connect": (15, 80), "message": (15, 80), "search": (20, 100), "apply": (40, 250)}
# "apply" = Easy Apply. LinkedIn confirms a daily Easy Apply limit but no number; users report about 50.
# kind: {agent: per day}. Unknown agents get 3 a day.
AGENT_DAY = {"connect": {"jobhunt": 10, "jobpost": 5}, "message": {"jobhunt": 5, "jobpost": 10}, "search": {"jobhunt": 10, "jobpost": 10},
             "apply": {"jobhunt": 10, "jobpost": 30}}
JOBPOST_WEEK_STOP = 60  # jobpost stops at 60 of the 80 weekly, leaving 20 for the job search


def rows():
    if not os.path.exists(LEDGER):
        return []
    with open(LEDGER, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def check(kind, agent, now=None, data=None):
    now = now or datetime.now()
    data = rows() if data is None else data
    day = now.strftime("%Y-%m-%d")
    week0 = now - timedelta(days=7)
    same = [r for r in data if r["kind"] == kind]
    day_all = sum(r["at"][:10] == day for r in same)
    day_agent = sum(r["at"][:10] == day and r["agent"] == agent for r in same)
    week_all = sum(datetime.fromisoformat(r["at"]) > week0 for r in same)
    cap_day, cap_week = TOTAL[kind]
    cap_agent = AGENT_DAY[kind].get(agent, 3)
    week_stop = JOBPOST_WEEK_STOP if agent == "jobpost" and kind in ("connect", "message") else cap_week
    left = min(cap_day - day_all, cap_agent - day_agent, week_stop - week_all)
    return {"kind": kind, "agent": agent, "ok": left > 0, "left_now": max(left, 0),
            "today_all": day_all, "today_agent": day_agent, "week_all": week_all,
            "caps": {"day_all": cap_day, "day_agent": cap_agent, "week": week_stop}}


def log(kind, agent, who):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "kind": kind, "agent": agent, "who": who}) + "\n")


def selftest():
    t = datetime(2026, 11, 14, 12)
    ev = lambda k, a, d=0: {"at": (t - timedelta(days=d)).isoformat(), "kind": k, "agent": a, "who": "x"}
    assert check("connect", "jobpost", t, [])["left_now"] == 5
    assert not check("connect", "jobpost", t, [ev("connect", "jobpost")] * 5)["ok"]          # its own day cap
    assert check("connect", "jobhunt", t, [ev("connect", "jobpost")] * 5)["left_now"] == 10  # job hunt still has 10
    assert not check("connect", "jobhunt", t, [ev("connect", "jobpost")] * 5 + [ev("connect", "jobhunt")] * 10)["ok"]  # 15 all
    week = [ev("connect", "jobhunt", d) for d in range(1, 7) for _ in range(10)]  # 60 this week
    assert not check("connect", "jobpost", t, week)["ok"]          # jobpost stops at 60
    assert check("connect", "jobhunt", t, week)["left_now"] == 10  # job hunt keeps going to 80
    assert check("connect", "jobpost", t, [ev("connect", "jobhunt", 8)] * 100)["ok"]  # older than 7 days does not count
    assert check("apply", "jobpost", t, [])["left_now"] == 30
    assert check("apply", "jobpost", t, [ev("apply", "jobpost", d) for d in range(1, 7) for _ in range(30)])["left_now"] == 30  # no 60 week stop on applies
    assert not check("apply", "jobhunt", t, [ev("apply", "jobpost")] * 30 + [ev("apply", "jobhunt")] * 10)["ok"]  # 40 all
    print("linkedin_budget self-check ok")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    if a[:1] == ["check"] and len(a) == 3 and a[1] in TOTAL:
        res = check(a[1], a[2]); print(json.dumps(res)); sys.exit(0 if res["ok"] else 1)
    elif a[:1] == ["log"] and len(a) == 4 and a[1] in TOTAL:
        log(a[1], a[2], a[3]); print("logged")
    elif a[:1] == ["status"]:
        print(json.dumps({k: {ag: check(k, ag) for ag in ("jobhunt", "jobpost")} for k in TOTAL}, indent=1))
    elif a[:1] == ["selftest"]:
        selftest()
    else:
        sys.exit(__doc__)
