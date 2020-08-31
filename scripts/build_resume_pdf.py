#!/usr/bin/env python3
"""Generate resume.pdf from resume.md.

Pipeline: resume.md -> styled HTML -> headless Chromium print-to-PDF.

Usage:
    python3 scripts/build_resume_pdf.py

Requires: the `markdown` package (pip install markdown) and a Chromium/Chrome
binary (set CHROME_BIN to override auto-detection). If the Inter font is not
installed, the script tries to fetch it from Google Fonts; otherwise the PDF
falls back to the system sans-serif.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESUME_MD = REPO_ROOT / "resume.md"
RESUME_PDF = REPO_ROOT / "resume.pdf"

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

CSS = """
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


def render_html(md_text: str) -> str:
    import markdown

    body = markdown.markdown(md_text, output_format="html5")
    # "Heading text | 2018 – Present" -> role left, dates right.
    body = re.sub(
        r"<h3>(.*?) \| (.*?)</h3>",
        r'<h3><span class="role">\1</span><span class="dates">\2</span></h3>',
        body,
    )
    # Same convention inside list items (education entries).
    body = re.sub(
        r"<li>(.*?) \| (.*?)</li>",
        r'<li>\1<span class="dates">\2</span></li>',
        body,
    )
    body = wrap_short_entries(body)
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>Resume</title><style>{CSS}</style></head>"
        f"<body>{body}</body></html>"
    )


def main() -> None:
    chrome = find_chrome()
    ensure_inter_font()
    html = render_html(RESUME_MD.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "resume.html"
        page.write_text(html, encoding="utf-8")
        subprocess.run(
            [
                chrome,
                "--headless",
                "--no-sandbox",
                "--disable-gpu",
                f"--print-to-pdf={RESUME_PDF}",
                "--no-pdf-header-footer",
                page.as_uri(),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
    print(f"wrote {RESUME_PDF}")


if __name__ == "__main__":
    main()
