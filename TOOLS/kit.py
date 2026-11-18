"""Shared settings for every kit script.

- config/kit.json: your details (name, contact, Notion IDs, caps). The setup writes it (START_HERE.md).
- %USERPROFILE%\\.job_hunt\\credentials.env: the Notion token and passwords. It lives outside this folder on purpose,
  so a copy or a push of this folder never carries a password.
- %USERPROFILE%\\.job_hunt\\work: scan results, logs and screenshots.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expandvars(r"%USERPROFILE%\.job_hunt")
WORK = os.path.join(HOME, "work")
_cfg = None


def cfg():
    global _cfg
    if _cfg is None:
        p = os.path.join(ROOT, "config", "kit.json")
        if not os.path.exists(p):
            sys.exit("config/kit.json is missing. Open this folder in Claude Code and say \"set me up\" (START_HERE.md).")
        _cfg = json.load(open(p, encoding="utf-8"))
    return _cfg


def cred():
    p = os.path.join(HOME, "credentials.env")
    if not os.path.exists(p):
        sys.exit(r"%USERPROFILE%\.job_hunt\credentials.env is missing (START_HERE.md, step 5).")
    return dict(l.strip().split("=", 1) for l in open(p, encoding="utf-8") if "=" in l and not l.startswith("#"))


def master_resume():
    """The general resume PDF, used when a job folder has no tailored one."""
    return os.path.join(ROOT, cfg()["name"]["file_prefix"] + "_Resume.pdf")
