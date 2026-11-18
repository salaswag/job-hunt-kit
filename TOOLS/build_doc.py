"""Build a tailored resume or cover letter PDF from a body-only file, using the TEMPLATES preamble.
    python TOOLS/build_doc.py <job folder> resume|cover <Company_Exact_Title>
Reads <job folder>/RESUME_BODY.tex or COVER_BODY.tex (everything between \\begin{document} and \\end{document}),
writes <Your_Name>_Resume_<Company_Exact_Title>.tex/.pdf (or _Cover_Letter_), compiles with Tectonic,
then fails loudly if the PDF is not one page or contains an em or en dash."""
import os, re, subprocess, sys
from pypdf import PdfReader
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TECTONIC = os.path.expandvars(r"%LOCALAPPDATA%\Programs\tectonic\tectonic.exe")
folder, kind, slug = sys.argv[1], sys.argv[2], sys.argv[3]
folder = folder if os.path.isabs(folder) else os.path.join(ROOT, "APPLICATIONS", folder)
tpl = open(os.path.join(ROOT, "TEMPLATES", "resume.tex" if kind == "resume" else "cover_letter.tex"), encoding="utf-8").read()
pre = tpl.split("\\begin{document}")[0]
if "\\resumeProjectHeading" not in pre:
    pre += "\\newcommand{\\resumeProjectHeading}[2]{\\item\\small{#1}\\vspace{-4pt}}\n"
body = open(os.path.join(folder, "RESUME_BODY.tex" if kind == "resume" else "COVER_BODY.tex"), encoding="utf-8").read()
if re.search("[\u2013\u2014]", body):
    sys.exit("em or en dash in the body: replace it first")
name = f"{kit.cfg()['name']['file_prefix']}_{'Resume' if kind == 'resume' else 'Cover_Letter'}_{slug}"
tex = os.path.join(folder, name + ".tex")
open(tex, "w", encoding="utf-8").write(pre + "\\begin{document}\n" + body.strip() + "\n\\end{document}\n")
r = subprocess.run([TECTONIC, "-X", "compile", tex], cwd=folder, capture_output=True, text=True)
if r.returncode:
    sys.exit(r.stderr[-1500:])
pdf = tex[:-4] + ".pdf"
reader = PdfReader(pdf)
text = "".join(p.extract_text() for p in reader.pages)
print(f"{pdf}\npages={len(reader.pages)} words={len(text.split())}")
if len(reader.pages) != 1:
    sys.exit("NOT ONE PAGE: trim the body")
if kind == "resume":
    # config/kit.json "resume_banned": regexes that must never appear on a resume (labels, names you keep off it)
    bad = [m for p in kit.cfg().get("resume_banned", []) for m in re.findall(p, text, re.I)]
    if bad:
        sys.exit(f"BANNED ON RESUMES: {sorted(set(bad))} (config/kit.json resume_banned)")
    import fitz
    page = fitz.open(pdf)[0]
    gap = page.rect.height - max(b[3] for b in page.get_text("blocks") if b[4].strip())
    print(f"bottom gap={gap:.0f} pt")
    if gap > 60:
        sys.exit(f"PAGE NOT FULL: {gap:.0f} pt empty at the bottom (max 60): add a bullet, a skills line or a project")
