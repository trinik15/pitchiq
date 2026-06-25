# ⚾ PitchIQ — MLB Pitcher Scouting Dashboard powered by Statcast

> Live pitch-level scouting reports for any MLB pitcher, built on free Baseball Savant data.

**Live demo:** [https://pitchiq-aqx.streamlit.app/](https://pitchiq-aqx.streamlit.app/)

---

## What it does

PitchIQ pulls real Statcast pitch data for any MLB pitcher and turns it into a complete scouting report — pitch mix, movement, velocity trends, zone heatmaps, count tendencies, sequencing patterns, and matchup strategy — all computed live from raw data, not pre-built static charts. A coach can type in any pitcher's name and get the same kind of analysis that MLB front offices pay six figures for.

The dashboard is designed for a real use case: a pitching coach preparing for an upcoming series, a scout evaluating a prospect, or a pitcher reviewing their own tendencies. Every visualization is interactive and filterable by batter handedness (vs LHB / vs RHB) so the analysis reflects real game situations.

---

## Features

### Scouting Dashboard (8 tabs)

| Tab | What it shows |
|-----|--------------|
| **Scouting Summary** | Auto-generated narrative, arsenal grades (A+ to F), platoon recommendation, contact quality (xwOBA), effectiveness charts, CSV export |
| **Pitch Arsenal** | Movement scatter, velocity distribution, release point consistency |
| **Location & Zones** | Catcher-view heatmap by pitch type, movement chart, velocity chart |
| **Count Tendencies** | First-pitch strategy, pitch mix by count, zone location for any specific count |
| **Sequencing** | Full pitch-to-pitch transition matrix, most predictable sequence insight |
| **Pitch Grades** | Radar chart vs MLB average, physical + effectiveness grade breakdown tables |
| **Season Trends** | Inning-by-inning velocity and fatigue index, multi-season game-by-game velocity chart |
| **Matchup** | Count + batter-hand situational pitch mix, Whiff%/CSW% per pitch type |

**Cross-cutting features:**
- 🔀 **Platoon split toggle** — every chart and metric updates live for vs LHB / vs RHB / All Batters
- ⚡ **Instant demo load** — 7 pitchers pre-cached from bundled Statcast data (no network wait)
- 🔍 **Search any pitcher** — 700+ active MLB pitchers via live pybaseball / Baseball Savant fetch
- ⬇ **Dual CSV export** — Pitch Summary CSV and Full Report CSV

**Demo pitchers (instant load):** Paul Skenes, Gerrit Cole, Shohei Ohtani, Zack Wheeler, Emmanuel Clase, Sandy Alcantara, Blake Snell

---

## How to run locally

```bash
git clone https://github.com/trinik15/pitchiq.git
cd pitchiq
pip install -r requirements.txt
streamlit run main.py
```

(`main.py` is at the repo root; run from the cloned directory, not from `pitchiq/`.)

Then open [http://localhost:8501](http://localhost:8501) in your browser.

> **Note:** Demo pitchers load instantly from bundled CSV.gz files. The first live search for a new pitcher fetches data from Baseball Savant (~45–90 seconds).

---

## Data sources

- **[Baseball Savant](https://baseballsavant.mlb.com/)** — Statcast pitch-level data (velocity, spin rate, movement, location, pitch result)
- **[pybaseball](https://github.com/jldbc/pybaseball)** — Python wrapper for Baseball Savant / FanGraphs API
- MLB average benchmarks from 2024 Statcast season aggregates (hardcoded in `pitchiq/app.py`)

No proprietary data. No API keys required. Everything is free and open.

---

## Stack

- **Python 3.11** + **Streamlit** — app framework
- **pybaseball** — Statcast data ingestion
- **Plotly** — all interactive charts
- **pandas / numpy** — data processing
- **Hosting** — [Streamlit Community Cloud](https://share.streamlit.io)

---

## Project structure

```
pitchiq/
├── app.py              # Full Streamlit app (~4,000 lines)
├── requirements.txt    # Pinned Python dependencies
├── demo_data/          # Pre-cached Statcast CSV.gz for 7 demo pitchers
└── .streamlit/
    └── config.toml     # Dark theme
main.py                 # Root launcher (streamlit run main.py)
requirements.txt        # Root deps for Streamlit Cloud
```

---

## Performance

| Scenario | Speed |
|---|---|
| Demo pitcher (any of the 7 pre-cached) | Instant |
| Live fetch — first search | 45–90 seconds (Statcast API) |
| Platoon toggle (LHB / RHB / All) | Instant (session-state cache) |
| Tab switch without changing filter | Instant (no recomputation) |

---

## Built for

AQX Sports Analytics Hackathon 2026 — Deadline June 26, 2026

License: MIT
