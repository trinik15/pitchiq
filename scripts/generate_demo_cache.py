"""Generate missing demo_data CSV.gz files from Baseball Savant via pybaseball.

Note: Shohei Ohtani and Sandy Alcantara did not pitch in 2024 (injury/rehab).
No 2024 Statcast pitching data exists for those two - use 2025 for instant demo load.
"""
import os
import sys

import pandas as pd

PITCHERS = {
    "shohei_ohtani": 660271,
    "sandy_alcantara": 645261,
}

SEASON = 2024
DEMO_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "pitchiq", "demo_data")

_KEEP_COLS = {
    "pitch_type", "pitch_label", "player_name", "pitcher", "stand", "p_throws",
    "balls", "strikes", "description", "zone", "plate_x", "plate_z",
    "release_speed", "release_spin_rate", "pfx_x", "pfx_z",
    "release_pos_x", "release_pos_z", "game_date",
    "home_team", "away_team", "inning_topbot",
    "count_label",
    "bb_type", "estimated_woba_using_speedangle", "launch_speed", "events",
    "at_bat_number", "pitch_number",
    "inning",
}


def fetch_and_save(slug: str, pitcher_id: int, season: int) -> bool:
    from pybaseball import statcast_pitcher

    out_path = os.path.join(DEMO_DATA_DIR, f"{slug}_{season}.csv.gz")
    if os.path.exists(out_path):
        print(f"SKIP (exists): {out_path}")
        return True

    print(f"Fetching {slug} {season} (id={pitcher_id})...")
    raw = statcast_pitcher(
        start_dt=f"{season}-03-01",
        end_dt=f"{season}-11-30",
        player_id=pitcher_id,
    )
    if raw is None or raw.empty:
        print(f"WARN: no pitching data for {slug} {season} (may not have pitched)")
        return False

    raw = raw[raw["pitch_type"].notna()].copy()
    raw = raw[~raw["pitch_type"].isin({"UN", "PO"})]
    if "game_type" in raw.columns:
        raw = raw[raw["game_type"] != "S"]

    extra = [c for c in raw.columns if c not in _KEEP_COLS]
    if extra:
        raw = raw.drop(columns=extra)

    os.makedirs(DEMO_DATA_DIR, exist_ok=True)
    raw.to_csv(out_path, index=False, compression="gzip")
    print(f"Saved {len(raw)} rows -> {out_path}")
    return True


if __name__ == "__main__":
    ok = all(fetch_and_save(slug, pid, SEASON) for slug, pid in PITCHERS.items())
    sys.exit(0 if ok else 1)
