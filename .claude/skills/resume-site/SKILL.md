---
name: resume-site
description: Maintain gauravjain.org, resume.md, and the generated resume PDF. Use this whenever the user asks to update the resume, the website, or the PDF — adding or rewording a role, bullet, highlight, patent, publication, skill, or logo, changing page layout, fixing the PDF, or checking that everything is consistent and live. Even one-line edits should go through this skill, because every change flows through resume.md → scripts/build.py → GitHub Pages, and this skill carries the formatting conventions the build parses, the owner's standing style rules, and the audit steps.
---

# Maintaining the resume, site, and PDF

## Architecture: one source of truth

`resume.md` is the only place resume content lives. Everything else is generated,
so the page, PDF, and served markdown cannot drift — as long as edits go to the
right file:

```
resume.md ──► scripts/build.py ──► _site/index.html   (template + generated sections)
                              ├──► _site/resume.pdf   (print CSS + headless Chromium)
                              └──► _site/resume.md    (copy)
```

| To change… | Edit… |
|---|---|
| Any resume content (roles, bullets, patents, publications, skills, education) | `resume.md` only |
| Page-only copy: hero, tagline, About, highlight cards, nav, footer | `templates/index.template.html` |
| Company/school logos | `assets/logos/*.png` + the `LOGOS` map in `scripts/build.py` |
| PDF typography/spacing | `PRINT_CSS` in `scripts/build.py` |
| Page styling | the `<style>` block in the template |

Generated files are never committed (`_site/` is gitignored). GitHub Actions
builds and deploys on every push to `main` — there is no manual deploy step.

## Markdown conventions the build parses

The generators in `scripts/build.py` rely on these shapes; break them and
sections silently render wrong:

- Entry headings: `### Role, Company — Location | Dates`. Dates after ` | `
  are right-aligned in the PDF and shown in the page rail. Location is
  optional and omitted on the page. The company (text after the last `, `,
  before ` — Location`) must exactly match a `LOGOS` key to get its logo.
- `**Project** — *skills list*` starts a sub-section inside an entry
  (renders as a small-caps heading + muted skills line on the page).
- A standalone `*Skills: …*` line renders as a muted skills line.
- Patents and publications live as nested sub-bullets under the job bullet
  they came from — `- Patented: [Title](url)` / `- Published: [Title](url)`,
  or a grouped `- Patented work …:` list. There is deliberately no standalone
  Patents section (the owner removed it; interleaving keeps recent jobs deep).
- Open source entries: `### [project-name](url) — Role` — project first,
  em dash, then role. The card parser splits on ` — `.
- Education entries are `###` headings like jobs (school parses as the
  "company", so it gets the Waterloo crest); MASc research is a bullet
  under the degree.
- Entries with ≤3 bullets and no `**Project**` lines are kept on one PDF page.

## Style rules (the owner's standing decisions)

These came from explicit owner feedback — apply them to new content and flag
violations in old content rather than silently reintroducing them:

- **No hyperbole.** No "planet-scale", "widely used", "explosive",
  "cutting-edge". Verified numbers carry the claims instead.
- **Only verified, defensible claims.** Every metric must come from the
  owner, a published paper, or a measurement you actually ran. Verify
  authorship before adding any patent or paper (a Rubrik filing,
  WO2025034386, once slipped in that belonged to a different inventor).
  The "Top 50 all-time TensorFlow contributor" line is measured by
  `git shortlog` over tensorflow/tensorflow (446 commits as
  `gjn@google.com`; rank #39–41 in 2022, #55–57 by 2026) — the owner chose
  the unqualified "Top 50" knowingly; do not add qualifiers back, and do not
  inflate it.
- **Engineer framing, not "leader".** Titles stay factual; self-descriptions
  say engineer.
- **The webpage speaks in clipped, person-neutral voice** — no "I'm/I/my".
- **Names**: no "Inc" suffixes; "Blue Coat Systems" spelled out; no
  "Menlo Park, CA" anywhere (owner removed their current location).
- **Highlights**: the resume list is reverse-chronological (iPhone last);
  the page cards run chronological (iPhone first, $100M+ last, full-width).
  Patent counts are not highlights.
- **The page never references GitHub as the host** — the markdown button
  links to the site's own `/resume.md`.

## Update workflow

1. Edit the right file per the table above.
2. Build: `python3 scripts/build.py`
3. Audit: `python3 scripts/audit.py` — build success, 3-page PDF, banned
   terms, first-person check, logo coverage. Fix anything it reports.
4. If the PDF overflows 3 pages, tighten `PRINT_CSS` knobs in this order:
   body `line-height` (1.4 → 1.38 → …), `li`/`ul` margins, `h2`/`h3`
   margins, then `@page` margins. Re-read the PDF after layout changes —
   look for orphaned bullets and split short entries.
5. If page layout changed, screenshot before pushing:
   `chromium --headless --no-sandbox --hide-scrollbars --window-size=1440,5300 --screenshot=/tmp/check.png _site/index.html`
   (mobile: width 420). Check the split panes, rail logos, and dark-ish
   details you touched.
6. Commit to `main` with a clear message and push. Never commit `_site/`
   or `__pycache__/`.
7. Verify the deploy landed: `python3 scripts/audit.py --live` (polls
   gauravjain.org for the current content and checks `/resume.pdf`).
   Deploys typically land in 30–90 seconds.

## Auditing consistency

Run `python3 scripts/audit.py` for the mechanical checks. Beyond it, a full
audit means reading with intent:

- Read the generated PDF end to end after content changes — page breaks,
  right-aligned dates, and heading alignment regress in ways greps miss.
- Confirm new claims against their sources (papers on arXiv, patents on
  Google Patents) before they ship.
- The template's hero/About/highlight cards are the only hand-maintained
  copy — when resume facts change (new role, new headline number), check
  whether those need a matching touch.
