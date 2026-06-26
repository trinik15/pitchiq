# Devpost About Section - Paste into Devpost Story

Use this to replace the dashboard list and fix hosting/dash issues. Keep your existing Inspiration, Challenges, Learned, and What's next sections.

---

## What it does (updated - 8 tabs)

PitchIQ pulls real Statcast pitch-by-pitch data for any MLB pitcher and turns it into a complete scouting report computed live from raw data, not pre-built static charts.

The dashboard includes **8 analytical tabs**:

* **Scouting Summary** - Auto-generated narrative, letter grades (A+-F vs 2024 MLB baselines), Scouting Recommendation card, contact quality (xwOBA), effectiveness charts, dual CSV export
* **Pitch Arsenal** - Movement scatter, velocity distribution, release point consistency
* **Location and Zones** - Catcher-view heatmap by pitch type, movement and velocity charts
* **Count Tendencies** - First-pitch strategy, pitch mix by count, zone location for any specific count, outlier detection
* **Sequencing** - Full pitch-to-pitch transition matrix, most predictable sequence insight
* **Pitch Grades** - Radar chart vs MLB average, physical + effectiveness grade breakdown
* **Season Trends** - Inning-by-inning velocity and fatigue index, multi-season game-by-game velocity
* **Matchup** - Count + batter-hand situational pitch mix, Whiff%/CSW% per pitch type

**Cross-cutting features:**
- Platoon split toggle (vs LHB / vs RHB / All Batters) - every chart and metric updates live
- Auto **Scouting Recommendation** card with platoon usage insight
- **Contact quality** metrics (xwOBA, GB/LD/FB by pitch type)
- **Dual CSV export** (Pitch Summary + Full Report for staff distribution)
- 7 demo pitchers pre-cached for instant load (2,000-5,000 pitches each)

**Demo season note:** Shohei Ohtani and Sandy Alcantara did not pitch in 2024 (injury). Use **2025** for instant load on those two.

Deployed on **Streamlit Community Cloud** for zero-infrastructure hosting.

Data source: **Baseball Savant / Statcast** public pitch-level data via pybaseball (no API keys required).

---

## How we built it (add one sentence)

We ingest pitch-level Statcast data from Baseball Savant via pybaseball, compute z-score grades against 2024 MLB pitch-type baselines, and render interactive Plotly charts in a Streamlit dashboard hosted on Streamlit Community Cloud.

---

## Dash replacements (find/replace in existing Devpost copy)

| Find | Replace |
|------|---------|
| 2,000–5,000 | 2,000-5,000 |
| 15–30 | 15-30 |
| 45–90 | 45-90 |
| A+–F | A+-F |
| Deployed on Replit | Deployed on Streamlit Community Cloud for zero-infrastructure hosting |
| 6 analytical views / 6 views | 8 analytical tabs (list all 8 above) |

---

## Devpost Update (post after fixes)

**Judge quick start:** Open [live demo](https://pitchiq-aqx.streamlit.app/) - Paul Skenes 2025 loads instantly. Try **Count Tendencies → 0-2** for the outlier insight, then **Sequencing** and **Matchup → 1-2 vs LHB**. Full 60-second walkthrough: [JUDGES.md](https://github.com/trinik15/pitchiq/blob/main/JUDGES.md). Methodology PDF attached with corrected filename.

---

## Gallery upload order

1. Scouting Summary (hero)
2. Count Tendencies (0-2 selected)
3. Pitch Grades
4. Location and Zones **NEW**
5. Sequencing **NEW**
6. Pitch Arsenal
7. Season Trends
8. Matchup **NEW**

Re-upload methodology PDF as `pitchiq_methodology.pdf` (fix typo: was `pitchiq_metodology.pdf`).
