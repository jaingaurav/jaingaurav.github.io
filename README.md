# gauravjain.org

Personal site and resume for Gaurav Jain, served by GitHub Pages at
[gauravjain.org](https://gauravjain.org).

## Single source of truth

`resume.md` is the only place resume content lives. The build generates
everything else from it, so the page, the PDF, and the markdown can never
drift apart:

```
resume.md ──► scripts/build.py ──► _site/index.html   (template + generated sections)
                              ├──► _site/resume.pdf   (print-rendered resume)
                              └──► _site/resume.md    (copy of the source)
```

| File | Purpose |
|------|---------|
| `resume.md` | All resume content: summary, highlights, experience (patents interleaved), skills, open source, education. |
| `templates/index.template.html` | Page-only chrome: hero, tagline, about, highlight cards, styling — plus `{{EXPERIENCE}}`, `{{OPEN_SOURCE}}`, and `{{EDUCATION}}` placeholders filled from `resume.md`. |
| `scripts/build.py` | Builds `_site/` (never committed; see `.gitignore`). |
| `scripts/audit.py` | Consistency audit: build, 3-page PDF, style rules, logo coverage; `--live` also checks gauravjain.org. |
| `.claude/skills/resume-site/` | Claude Code skill carrying the editing conventions, style rules, and update/audit workflow. |
| `.github/workflows/pages.yml` | Rebuilds and deploys the site on every push to `main`. |
| `CNAME` | Custom domain for GitHub Pages. |

## Editing

- **Resume content** (roles, bullets, patents, education, open source):
  edit `resume.md` and push — the page and PDF regenerate automatically.
- **Page-only copy** (tagline, about, interests, highlight cards):
  edit `templates/index.template.html`.

Markdown conventions the build relies on:

- `###` entry headings end in ` | <dates>`; dates are right-aligned in the
  PDF and shown in the page timeline. The text before the dates is parsed as
  `Role, Company — Location` (location is omitted on the page).
- A `**Project** — *skills*` line starts a sub-section within an entry.
- A standalone `*Skills: …*` line renders as a muted skills line.
- Entries with three or fewer bullets are kept on one PDF page.

## Local build

```sh
pip install markdown
python3 scripts/build.py        # writes _site/
```

Needs a Chrome/Chromium binary for the PDF (auto-detected; override with
`CHROME_BIN=/path/to/chrome`). Open `_site/index.html` to preview.

## Deployment

GitHub Pages must be configured with **Source: GitHub Actions**
(Settings → Pages), with the custom domain `gauravjain.org` set on the same
screen. Every push to `main` then builds and deploys automatically.
