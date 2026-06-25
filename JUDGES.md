# PitchIQ — Judge Quick Start

**Live demo:** https://pitchiq-aqx.streamlit.app/  
**GitHub:** https://github.com/trinik15/pitchiq  
**Methodology PDF:** `pitchiq/screenshots_devpost/pitchiq_methodology.pdf`

## 60-second walkthrough

1. Open the live demo — **Paul Skenes 2025** loads instantly from bundled Statcast data.
2. **Scouting Summary** — auto-narrative, letter grades (A+–F vs 2024 MLB baselines), **Scouting Recommendation** card.
3. Toggle **vs LHB** — all metrics recompute from filtered pitch logs.
4. **Count Tendencies** → **0-2** — count/pitch outlier insight (+71pp Curveball for Skenes).
5. **Sequencing** — full transition matrix.
6. **Matchup** → **1-2 vs LHB** — situational pitch mix.
7. **Full Report CSV** — export for staff distribution.

## Pre-cached demo pitchers (instant load)

Paul Skenes, Gerrit Cole, Shohei Ohtani, Zack Wheeler, Emmanuel Clase, Sandy Alcantara, Blake Snell.

Any other qualified MLB pitcher loads via live Statcast fetch (~45–90 seconds).

## Statistical rigor highlights

- Z-score grading vs pitch-type-specific 2024 MLB benchmarks (9 pitch types)
- Sample gates: 80 pitches/platoon side for recommendations, 20/count for insights, 15/transitions for sequencing, 15/situation for matchup
- Honesty design: insufficient data → explicit message, not fabricated insight

## Local run

```bash
git clone https://github.com/trinik15/pitchiq.git
cd pitchiq
pip install -r requirements.txt
streamlit run main.py
```
