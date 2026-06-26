# PitchIQ Final Submission Checklist

## GitHub (manual push when ready)

- [x] `.gitignore` added (`.cursor/`, `__pycache__/`, `.env`, secrets)
- [x] Em/en-dashes replaced with ASCII hyphens in README, JUDGES, main.py, app.py
- [x] JUDGES.md linked prominently from README
- [x] Playwright E2E suite: 9/9 passing against live URL
- [x] Gallery screenshots captured (8 tabs) in `pitchiq/screenshots_devpost/`
- [x] Devpost copy prepared in `pitchiq/screenshots_devpost/DEVPOST_COPY.md`
- [ ] **Note:** `shohei_ohtani_2024.csv.gz` and `sandy_alcantara_2024.csv.gz` cannot be generated - neither pitcher threw in 2024. Docs updated to use 2025 for instant load.

Before push, verify git identity:
```bash
git config user.name "nicola"
git config user.email "nicola.trinca15@gmail.com"
git log --format="%an|%ae|%cn|%ce" -3
```

## Devpost (manual edits on devpost.com)

- [ ] Paste updated About section from `DEVPOST_COPY.md` (8 tabs, Streamlit Cloud, no em/en-dashes)
- [ ] Add Baseball Savant sentence to "How we built it"
- [ ] Upload 8 gallery images (order in DEVPOST_COPY.md)
- [ ] Re-upload methodology PDF as `pitchiq_methodology.pdf` (fix typo)
- [ ] Post Devpost Update with judge walkthrough (text in DEVPOST_COPY.md)

## Validation

- [x] Playwright E2E: all 9 tests green
- [ ] Incognito test: https://github.com/trinik15/pitchiq
- [ ] Incognito test: https://pitchiq-aqx.streamlit.app/ (Paul Skenes 2025, Count Tendencies 0-2)

## Methodology PDF review

See `pitchiq/screenshots_devpost/PDF_REVIEW.md` for checklist results.
