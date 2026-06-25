# PitchIQ

MLB pitcher scouting dashboard powered by Baseball Savant / Statcast data. Built with Streamlit.

**Live demo:** [https://pitchiq-aqx.streamlit.app/](https://pitchiq-aqx.streamlit.app/)

---

## Features

### Scouting Dashboard (8 tabs)

| Tab | What it shows |
|---|---|
| **Scouting Summary** | Auto-generated narrative, arsenal grades (A+ to F), platoon recommendation, contact quality (xwOBA), effectiveness charts, CSV export |
| **Pitch Arsenal** | Movement scatter, velocity distribution, release point consistency |
| **Location & Zones** | Catcher-view heatmap by pitch type, movement chart, velocity chart |
| **Count Tendencies** | First-pitch strategy, pitch mix by count, zone location for any specific count |
| **Sequencing** | Full pitch-to-pitch transition matrix, most predictable sequence insight |
| **Pitch Grades** | Radar chart vs MLB average, physical + effectiveness grade breakdown tables |
| **Season Trends** | Inning-by-inning velocity and fatigue index, multi-season game-by-game velocity chart |
| **Matchup** | Count + batter-hand situational pitch mix, Whiff%/CSW% per pitch type |

### Key capabilities

- **Demo cache** - 7 pitchers load instantly with no internet required:
  Paul Skenes, Gerrit Cole, Shohei Ohtani, Zack Wheeler, Emmanuel Clase, Sandy Alcantara, Blake Snell (2024 and/or 2025 data pre-bundled as CSV.gz)
- **Live Statcast fetch** - any other MLB pitcher via pybaseball + Baseball Savant (45-90 seconds first load)
- **Platoon filter** - toggle All Batters / vs LHB / vs RHB across every tab instantly (all results cached per split in session state)
- **Actionable recommendation** - platoon-based scouting insight with 80-pitch minimum gate and 15pp delta threshold; returns "no split detected" when data doesn't support a claim
- **Arsenal grades** - A+ to F grading vs 2024 MLB averages for each pitch type (velocity, spin, Whiff%, CSW%, Chase%)
- **Dual CSV export** - Pitch Summary CSV and Full Report CSV (grades + recommendation + metadata)

---

## Data

| Source | What it covers |
|---|---|
| **Baseball Savant via pybaseball** | Live Statcast pitch-by-pitch data for any MLB pitcher (fetched on demand) |
| **`demo_data/` CSV.gz files** | Pre-cached Statcast exports for 7 pitchers stored in the repo. Loaded from disk - no network needed |

The app calls `pybaseball.statcast_pitcher()` for live fetches. No API key required. pybaseball caches responses locally at `~/.pybaseball/` to speed up repeated queries within the same session.

---

## Local setup

**Requirements:** Python 3.11, pip

```bash
git clone https://github.com/trinik15/pitchiq.git
cd pitchiq
pip install -r requirements.txt
streamlit run main.py
```

The app opens at `http://localhost:8501`. Demo pitchers (Skenes, Cole, Ohtani, Wheeler, Clase, Alcantara, Snell) load instantly. Any other pitcher triggers a live Statcast fetch (~45-90 seconds).

---

## Streamlit Community Cloud deployment

### Exact steps

1. Push this repo to GitHub (public or private)
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
3. Click **New app**
4. Fill in:
   - **Repository:** `<your-github-username>/<your-repo-name>`
   - **Branch:** `main`
   - **Main file path:** `pitchiq/app.py`
     - If your repo root IS the `pitchiq/` directory (not a monorepo), use `app.py` instead
5. Under **Advanced settings:** Python version = **3.11** (leave everything else at defaults)
6. **No secrets required** - the app uses zero API keys or environment variables
7. Click **Deploy**

Streamlit Cloud installs `requirements.txt` automatically. First deploy takes 3-5 minutes. After that, demo pitchers load instantly; live pitcher searches take 45-90 seconds (same as local).

### Environment variables / secrets

None required. If you ever add a feature that needs secrets, add them in the Streamlit Cloud app's **Settings > Secrets** panel as TOML key=value pairs.

---

## Project structure

```
pitchiq/
- app.py              Main application - all logic and UI in a single Streamlit file
- requirements.txt    Python dependencies (pinned for reproducibility)
- demo_data/          Pre-cached Statcast CSV.gz files for 7 demo pitchers
- .streamlit/
    config.toml       Streamlit theme config (dark mode, custom colors) - no [server] section
- .gitignore          Excludes pybaseball cache, secrets.toml, __pycache__, temp files
```

---

## Performance

| Scenario | Speed |
|---|---|
| Demo pitcher (any of the 7 pre-cached) | Instant |
| Live fetch - first search | 45-90 seconds (Statcast API) |
| Platoon toggle (LHB / RHB / All) after first render | Instant (session-state cache) |
| Tab switch without changing filter | Instant (no recomputation) |

All expensive aggregations (pitch grades, sequencing matrix, contact quality, fatigue index, first-pitch analysis) are computed once per (pitcher, season, split) and stored in session state. Switching tabs or re-rendering without changing the platoon filter costs zero recomputation.
