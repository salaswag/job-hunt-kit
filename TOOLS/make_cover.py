"""Write and build a cover letter PDF from plain text .
    python TOOLS/make_cover.py <job folder name> <cover.json>
cover.json: {"title": "...", "slug": "Company_Exact_Title", "to": ["Hiring Team", "Company"], "paras": ["...", "...", "...", "..."]}
Four paragraphs, 150 to 250 words: a real story from EXPERIENCE_BANK.md, the fit in the posting's words, one checkable thing
about the employer, availability + thanks (rules in TEMPLATES/cover_letter.tex). Plain text in, LaTeX escaping done here."""
import json, os, subprocess, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BS = chr(92)


def esc(t):
    for ch in "&%$#_":
        t = t.replace(ch, BS + ch)
    return t


def main():
    folder, spec = sys.argv[1], json.load(open(sys.argv[2], encoding="utf-8"))
    me, c = kit.cfg()["name"], kit.cfg()["contact"]
    head = (BS + "begin{center}\n  {" + BS + "Huge " + BS + "bfseries " + esc(me["full"]) + "} " + BS + BS + " " + BS + "vspace{3pt}\n"
            "  {" + BS + "large " + esc(spec["title"]) + "} " + BS + BS + " " + BS + "vspace{2pt}\n"
            "  " + BS + "small " + esc(c["city_line"]) + " $|$ " + BS + "href{mailto:" + c["email"] + "}{" + esc(c["email"]) + "} $|$ " + esc(c["phone"])
            + ((" $|$\n  " + BS + "href{" + c["linkedin_url"] + "}{" + esc(c["linkedin_label"]) + "}") if c.get("linkedin_url") else "") + "\n" + BS + "end{center}\n"
            + BS + "vspace{4pt}" + BS + "hrule" + BS + "vspace{10pt}\n\n")
    date = datetime.date.today().strftime("%B %d, %Y").replace(" 0", " ")
    to = (" " + BS + BS + "\n").join(esc(x) for x in spec.get("to", ["Hiring Team"]))
    body = (head + date + "\n\n" + to + "\n\n" + BS + "textbf{Re: " + esc(spec["title"]) + "}\n\nDear Hiring Team,\n\n"
            + "\n\n".join(esc(p) for p in spec["paras"]) + "\n\nSincerely, " + BS + BS + "\n" + esc(me["full"]) + "\n")
    path = folder if os.path.isabs(folder) else os.path.join(ROOT, "APPLICATIONS", folder)
    open(os.path.join(path, "COVER_BODY.tex"), "w", encoding="utf-8").write(body)
    sys.exit(subprocess.run([sys.executable, os.path.join(ROOT, "TOOLS", "build_doc.py"), folder, "cover", spec["slug"]], cwd=ROOT).returncode)


if __name__ == "__main__":
    main()
