#!/usr/bin/env python3
"""Audit the consistency of resume.md, the generated site, and the PDF.

Checks (see .claude/skills/resume-site/SKILL.md for the conventions):
  - the build succeeds and the PDF is exactly 3 pages
  - no banned terms (hyperbole, "Inc" suffixes, removed location)
  - no first-person voice in the page template
  - every experience/education entry's company resolves against the LOGOS
    map (missing logo = warning), and no LOGOS key is dead
  - every asset the generated page references exists on disk
  - with --live: gauravjain.org serves the current content and the PDF

Usage:
    python3 scripts/audit.py [--live]

Exits non-zero if any check fails.
"""

import argparse
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

REPO = build.REPO
SITE = REPO / "_site"
BANNED = {
    "planet-scale": "hyperbole",
    "widely used": "hyperbole",
    "explosive": "hyperbole",
    "cutting-edge": "hyperbole",
    "Menlo Park": "removed location",
    r"\bInc\b": '"Inc" suffixes are dropped from company names',
}
FIRST_PERSON = [r"\bI'm\b", r"\bI am\b", r"\bI\b", r"\bmy\b"]

failures = []
warnings = []


def check(ok: bool, message: str) -> None:
    if not ok:
        failures.append(message)
    print(("ok    " if ok else "FAIL  ") + message)


def warn(message: str) -> None:
    warnings.append(message)
    print("warn  " + message)


def companies() -> list:
    body = build.md_body((REPO / "resume.md").read_text(encoding="utf-8"))
    sections = build.sections_of(body)
    names = []
    for sec in ("Work Experience", "Education"):
        for group in build.entry_groups(sections[sec]):
            heading = re.match(r"<h3>(.*?)</h3>", group).group(1)
            left = heading.rpartition(" | ")[0] or heading
            if sec == "Work Experience" and " — " in left:
                left = left.rsplit(" — ", 1)[0]
            names.append(left.rsplit(", ", 1)[1] if ", " in left else left)
    return names


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="also verify gauravjain.org")
    args = parser.parse_args()

    result = subprocess.run([sys.executable, str(REPO / "scripts/build.py")],
                            capture_output=True, text=True)
    check(result.returncode == 0, "build succeeds" + ("" if result.returncode == 0
          else f" — {result.stderr.strip()[-200:]}"))
    if result.returncode != 0:
        sys.exit(1)

    pdf = (SITE / "resume.pdf").read_bytes()
    pages = len(re.findall(rb"/Type\s*/Page[^s]", pdf))
    check(pages == 3, f"PDF is exactly 3 pages (got {pages})")

    for path in (REPO / "resume.md", REPO / "templates/index.template.html"):
        text = path.read_text(encoding="utf-8")
        for pattern, why in BANNED.items():
            hits = re.findall(pattern, text)
            check(not hits, f"{path.name}: no '{pattern}' ({why})")

    template = (REPO / "templates/index.template.html").read_text(encoding="utf-8")
    body_text = re.sub(r"<style>.*?</style>", "", template, flags=re.S)
    body_text = re.sub(r"<[^>]+>", " ", body_text)
    for pattern in FIRST_PERSON:
        hits = re.findall(pattern, body_text)
        check(not hits, f"template page copy avoids first person ('{pattern}')")

    names = companies()
    for name in names:
        if name not in build.LOGOS:
            warn(f"no logo mapped for '{name}' (renders without one)")
    for key in build.LOGOS:
        check(key in names, f"LOGOS key '{key}' matches a resume entry")
        logo = REPO / build.LOGOS[key]
        check(logo.is_file(), f"logo file exists: {build.LOGOS[key]}")

    page = (SITE / "index.html").read_text(encoding="utf-8")
    for ref in set(re.findall(r'src="(assets/[^"]+)"', page)):
        check((SITE / ref).is_file(), f"page asset exists in _site: {ref}")

    if args.live:
        marker = "Snowflake"
        m = re.search(r"^- (.+?)[.\n]", (REPO / "resume.md").read_text().split("## Highlights")[1],
                      re.M)
        if m:
            marker = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", m.group(1))[:60]
        live_ok = pdf_ok = False
        for _ in range(9):
            try:
                html = urllib.request.urlopen("https://gauravjain.org", timeout=15).read().decode()
                head = urllib.request.urlopen("https://gauravjain.org/resume.pdf", timeout=15)
                live_ok = marker in html
                pdf_ok = head.status == 200 and head.read(4) == b"%PDF"
            except Exception:
                pass
            if live_ok and pdf_ok:
                break
            time.sleep(10)
        check(live_ok, f"live site serves current content ('{marker[:40]}…')")
        check(pdf_ok, "live /resume.pdf serves a PDF")

    print()
    if failures:
        print(f"AUDIT FAILED — {len(failures)} failure(s), {len(warnings)} warning(s)")
        sys.exit(1)
    print(f"AUDIT PASSED — {len(warnings)} warning(s)")


if __name__ == "__main__":
    main()
