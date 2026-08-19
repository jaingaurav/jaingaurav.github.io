#!/usr/bin/env python3
"""Build the site into _site/ from resume.md — the single source of truth.

resume.md drives everything shared: the resume PDF, and the Experience,
Open Source, and Education sections of the profile page. Page-only copy
(hero, tagline, about, highlight cards) lives in templates/index.template.html.

Outputs (default --out _site):
    index.html   profile page (template + sections generated from resume.md)
    resume.pdf   print-rendered resume
    resume.md    copy of the source

Usage:
    python3 scripts/build.py [--out DIR]

Requires: the `markdown` package (pip install markdown) and a Chromium/Chrome
binary (set CHROME_BIN to override auto-detection). If the Inter font is not
installed, the script tries to fetch it from Google Fonts; otherwise the PDF
falls back to the system sans-serif.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESUME_MD = REPO / "resume.md"
TEMPLATE = REPO / "templates" / "index.template.html"

CHROME_CANDIDATES = [
    os.environ.get("CHROME_BIN"),
    "/opt/pw-browsers/chromium",
    shutil.which("chromium"),
    shutil.which("chromium-browser"),
    shutil.which("google-chrome"),
    shutil.which("chrome"),
]

GOOGLE_FONTS_CSS = (
    "https://fonts.googleapis.com/css2"
    "?family=Inter:ital,wght@0,400;0,600;0,700;1,400&display=swap"
)

PRINT_CSS = """
@page { size: Letter; margin: 0.5in 0.6in; }
* { margin: 0; padding: 0; box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  font-family: 'Inter', 'DejaVu Sans', 'Helvetica Neue', Arial, sans-serif;
  font-size: 9.5pt; line-height: 1.4; color: #1f2430;
}
a { color: #175d8d; text-decoration: none; }

h1 { font-size: 21pt; font-weight: 700; letter-spacing: 0.02em; color: #10151f; }
h1 + p { font-size: 9pt; color: #4a5262; margin: 2pt 0 0; }
h1 + p a { color: #175d8d; }

h2 {
  font-size: 9.5pt; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.14em; color: #175d8d;
  margin: 9.5pt 0 4pt; padding-bottom: 2.5pt;
  border-bottom: 1.2pt solid #c8d3de;
  break-after: avoid;
}
h1 + p + h2 { margin-top: 8pt; }

h3 {
  display: flex; justify-content: space-between; align-items: baseline;
  gap: 12pt; font-size: 10pt; font-weight: 600; color: #10151f;
  margin: 6.5pt 0 1.5pt; break-after: avoid;
}
h3 .dates { font-weight: 400; font-size: 8.5pt; color: #6a7284; white-space: nowrap; }

p { margin: 1pt 0; }
/* Project name + skills line, and standalone italic skills line */
p:has(> strong:first-child), p:has(> em:first-child) { break-after: avoid; }
p > strong { color: #10151f; font-weight: 600; }
p > em, li > em { font-style: italic; font-size: 8.5pt; color: #6a7284; }

ul { margin: 1pt 0 2.5pt; padding-left: 13pt; }
li { margin: 0 0 1pt; padding-left: 2pt; break-inside: avoid; }
li::marker { color: #9aa3b2; }
li .dates { float: right; font-size: 8.5pt; color: #6a7284; }
li strong { font-weight: 600; color: #10151f; }
.keep { break-inside: avoid; }
"""


def find_chrome() -> str:
    for candidate in CHROME_CANDIDATES:
        if candidate and Path(candidate).exists():
            return candidate
    sys.exit("error: no Chromium/Chrome binary found; set CHROME_BIN")


def ensure_inter_font() -> None:
    """Best-effort: install Inter via fontconfig if it is not already present."""
    try:
        have = subprocess.run(
            ["fc-list", ":family"], capture_output=True, text=True, timeout=30
        )
        if "Inter" in have.stdout:
            return
        css = subprocess.run(
            ["curl", "-sS", "--max-time", "30", GOOGLE_FONTS_CSS],
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout
        font_dir = Path.home() / ".local/share/fonts/inter"
        font_dir.mkdir(parents=True, exist_ok=True)
        for i, block in enumerate(re.findall(r"@font-face\s*{[^}]*}", css)):
            url = re.search(r"url\((https://[^)]+)\)", block)
            if not url:
                continue
            subprocess.run(
                ["curl", "-sS", "--max-time", "60", "-o",
                 str(font_dir / f"inter-{i}.ttf"), url.group(1)],
                timeout=90, check=True,
            )
        subprocess.run(["fc-cache", "-f", str(font_dir)], capture_output=True, timeout=60)
    except Exception as exc:  # noqa: BLE001 - font install is optional
        print(f"note: could not install Inter font ({exc}); using fallback fonts")


def md_body(md_text: str) -> str:
    import markdown

    return markdown.markdown(md_text, output_format="html5")


# ---------------------------------------------------------------- PDF

def wrap_short_entries(body: str) -> str:
    """Keep short entries on a single page.

    Long job entries must be allowed to split across pages, but short ones
    look broken when split, so wrap each short h3 group in a no-break div:
    everything from 'Open Source Projects' onward, plus any job entry with
    at most three bullets and no project sub-sections.
    """
    marker = body.find(">Open Source Projects</h2>")
    parts = re.split(r"(?=<h3>)", body)
    out = [parts[0]]
    pos = len(parts[0])
    for part in parts[1:]:
        cut = part.find("<h2")
        group, rest = (part, "") if cut == -1 else (part[:cut], part[cut:])
        in_tail = marker != -1 and pos >= marker
        small = group.count("<li>") <= 3 and "<strong>" not in group
        out.append(f'<div class="keep">{group}</div>{rest}' if in_tail or small else part)
        pos += len(part)
    return "".join(out)


def render_print_html(body: str) -> str:
    # "Heading text | 2018 – Present" -> role left, dates right.
    body = re.sub(
        r"<h3>(.*?) \| (.*?)</h3>",
        r'<h3><span class="role">\1</span><span class="dates">\2</span></h3>',
        body,
    )
    # Same convention inside list items.
    body = re.sub(
        r"<li>(.*?) \| (.*?)</li>",
        r'<li>\1<span class="dates">\2</span></li>',
        body,
    )
    body = wrap_short_entries(body)
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>Resume</title><style>{PRINT_CSS}</style></head>"
        f"<body>{body}</body></html>"
    )


def build_pdf(body: str, out_pdf: Path) -> None:
    chrome = find_chrome()
    ensure_inter_font()
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "resume.html"
        page.write_text(render_print_html(body), encoding="utf-8")
        subprocess.run(
            [
                chrome,
                "--headless",
                "--no-sandbox",
                "--disable-gpu",
                f"--print-to-pdf={out_pdf}",
                "--no-pdf-header-footer",
                page.as_uri(),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )


# ---------------------------------------------------------------- page

def sections_of(body: str) -> dict:
    parts = re.split(r"<h2>(.*?)</h2>", body)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def entry_groups(section_html: str) -> list:
    return [p for p in re.split(r"(?=<h3>)", section_html) if p.startswith("<h3>")]


def transform_entry_body(html: str) -> str:
    # **Project** — *skills* paragraphs -> sub-heading + muted skills line.
    html = re.sub(
        r"<p><strong>(.*?)</strong> — <em>(.*?)</em></p>",
        r'<h4>\1</h4><div class="skills-line">\2</div>',
        html,
    )
    # Standalone *Skills: …* paragraphs -> muted skills line.
    html = re.sub(r"<p><em>(.*?)</em></p>", r'<div class="skills-line">\1</div>', html)
    return html.strip()


def job_block(group: str, strip_location: bool) -> str:
    heading, rest = re.match(r"<h3>(.*?)</h3>(.*)", group, re.S).groups()
    left, _, dates = heading.rpartition(" | ")
    if not left:
        left, dates = dates, ""
    if strip_location and " — " in left:
        left = left.rsplit(" — ", 1)[0]
    if ", " in left:
        role, company = left.rsplit(", ", 1)
    else:
        role, company = "", left
    body = transform_entry_body(rest)
    return (
        '    <div class="job">\n'
        f'      <div class="dates">{dates}</div>\n'
        "      <div>\n"
        f"        <h3>{company}</h3>\n"
        f'        <div class="role">{role}</div>\n'
        f"        {body}\n"
        "      </div>\n"
        "    </div>"
    )


def card_block(group: str) -> str:
    heading, rest = re.match(r"<h3>(.*?)</h3>(.*)", group, re.S).groups()
    sub, _, name = heading.partition(", ")
    if not name:
        sub, name = "", heading
    rest = re.sub(r"<p><em>.*?</em></p>", "", rest).strip()  # cards omit skill lists
    return (
        '      <div class="card">\n'
        f'        <div class="sub">{sub}</div>\n'
        f"        <h3>{name}</h3>\n"
        f"        {rest}\n"
        "      </div>"
    )


def build_page(body: str, out_html: Path) -> None:
    sections = sections_of(body)
    experience = "\n".join(
        job_block(g, strip_location=True)
        for g in entry_groups(sections["Work Experience"])
    )
    education = "\n".join(
        job_block(g, strip_location=False)
        for g in entry_groups(sections["Education"])
    )
    open_source = "\n".join(
        card_block(g) for g in entry_groups(sections["Open Source Projects"])
    )
    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace("{{EXPERIENCE}}", experience)
    page = page.replace("{{EDUCATION}}", education)
    page = page.replace("{{OPEN_SOURCE}}", open_source)
    if "{{" in page:
        sys.exit("error: unfilled placeholder left in the page template")
    out_html.write_text(page, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPO / "_site"), help="output directory")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    body = md_body(RESUME_MD.read_text(encoding="utf-8"))

    build_page(body, out / "index.html")
    build_pdf(body, out / "resume.pdf")
    shutil.copy(RESUME_MD, out / "resume.md")
    print(f"wrote {out}/index.html, {out}/resume.pdf, {out}/resume.md")


if __name__ == "__main__":
    main()
