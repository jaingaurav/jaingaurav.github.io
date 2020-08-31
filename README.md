# gauravjain.org

Personal site and resume for Gaurav Jain, served by GitHub Pages at
[gauravjain.org](https://gauravjain.org) (see `CNAME`).

## Contents

| File | Purpose |
|------|---------|
| `index.html` | Profile page — self-contained (no build step), responsive, light/dark aware. |
| `resume.md` | Resume, canonical source. Readable on GitHub and used to generate the PDF. |
| `resume.pdf` | PDF resume, generated from `resume.md`. Linked from the profile page — commit the regenerated file alongside any `resume.md` change. |
| `scripts/build_resume_pdf.py` | Generator: `resume.md` → styled HTML → headless Chromium print-to-PDF. |

## Updating the resume

1. Edit `resume.md`. Formatting conventions the PDF build relies on:
   - Job/entry headings are `###` lines ending in ` | <dates>` — the dates are
     right-aligned in the PDF (same for ` | <dates>` at the end of a list item).
   - A `**Project**` or `*Skills: …*` line directly above a bullet list is kept
     on the same page as that list.
2. Regenerate the PDF:

   ```sh
   pip install markdown
   python3 scripts/build_resume_pdf.py
   ```

   The script needs a Chromium/Chrome binary (auto-detected; override with
   `CHROME_BIN=/path/to/chrome`). It uses the Inter font, fetching it from
   Google Fonts into `~/.local/share/fonts` if it isn't installed, and falls
   back to system fonts offline.

3. Commit `resume.md` and `resume.pdf` together.

Remember to mirror any substantive resume change (new role, dates, highlights)
on the profile page in `index.html` — it is hand-maintained, not generated.

## Deployment

Nothing to build or deploy manually: GitHub Pages serves the repository as-is
from the default branch. `.nojekyll` disables Jekyll processing.
