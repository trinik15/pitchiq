import os
import unicodedata
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="PitchIQ",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded",
)

PITCH_COLORS = {
    "FF": "#E63946",
    "SI": "#F4A261",
    "FC": "#E9C46A",
    "SL": "#2A9D8F",
    "ST": "#06D6A0",
    "CU": "#4361EE",
    "KC": "#7209B7",
    "CH": "#F72585",
    "FS": "#B5179E",
    "KN": "#AAAAAA",
    "SV": "#48CAE4",
    "CS": "#3A86FF",
    "EP": "#FFFFFF",
    "PO": "#999999",
    "FO": "#CCCCCC",
    "SC": "#FF9F1C",
    "OTHER": "#888888",
}

PITCH_NAMES = {
    "FF": "4-Seam Fastball",
    "SI": "Sinker",
    "FC": "Cutter",
    "SL": "Slider",
    "ST": "Sweeper",
    "CU": "Curveball",
    "KC": "Knuckle Curve",
    "CH": "Changeup",
    "FS": "Splitter",
    "KN": "Knuckleball",
    "SV": "Slurve",
    "CS": "Slow Curve",
    "EP": "Eephus",
    "PO": "Pitchout",
    "FO": "Forkball",
    "SC": "Screwball",
}

SWING_EVENTS = {
    "swinging_strike", "swinging_strike_blocked", "foul", "foul_tip",
    "hit_into_play", "hit_into_play_no_out", "hit_into_play_score",
    "missed_bunt", "foul_bunt", "foul_pitchout",
}
WHIFF_EVENTS = {"swinging_strike", "swinging_strike_blocked"}
CSW_EVENTS = {"called_strike", "swinging_strike", "swinging_strike_blocked"}
OUT_OF_ZONE = {11, 12, 13, 14}

COUNT_ORDER = [
    "0-0", "0-1", "0-2",
    "1-0", "1-1", "1-2",
    "2-0", "2-1", "2-2",
    "3-0", "3-1", "3-2",
]

# ── MLB 2024 league averages by pitch type (Baseball Savant, min 200 pitches) ─
MLB_AVG = {
    "FF": {"velo": 94.1, "spin": 2262, "whiff_pct": 23.8, "chase_pct": 28.1, "csw_pct": 28.5},
    "SI": {"velo": 93.4, "spin": 2183, "whiff_pct": 16.1, "chase_pct": 30.2, "csw_pct": 25.4},
    "FC": {"velo": 89.2, "spin": 2382, "whiff_pct": 24.3, "chase_pct": 30.8, "csw_pct": 30.2},
    "SL": {"velo": 84.2, "spin": 2405, "whiff_pct": 33.2, "chase_pct": 35.1, "csw_pct": 33.4},
    "ST": {"velo": 82.5, "spin": 2395, "whiff_pct": 37.8, "chase_pct": 38.2, "csw_pct": 34.1},
    "CU": {"velo": 78.5, "spin": 2526, "whiff_pct": 28.4, "chase_pct": 34.5, "csw_pct": 31.2},
    "KC": {"velo": 76.8, "spin": 2598, "whiff_pct": 26.2, "chase_pct": 32.1, "csw_pct": 30.1},
    "CH": {"velo": 85.2, "spin": 1790, "whiff_pct": 34.5, "chase_pct": 38.8, "csw_pct": 33.1},
    "FS": {"velo": 85.8, "spin": 1675, "whiff_pct": 37.8, "chase_pct": 40.2, "csw_pct": 34.2},
}
# ── Per-pitch-type σ from 2024 MLB Baseball Savant (qualified pitchers, ≥200 pitches) ─
# These are cross-pitcher standard deviations for each metric, not single-value windows.
# Faster pitch types cluster tightly (FF velo σ≈2.5), breaking balls spread wider (CU velo σ≈3.8).
# Whiff/CSW σ is larger for offspeed/breaking balls because pitcher quality varies more there.
MLB_SIGMA = {
    "FF": {"velo": 2.5, "spin": 220, "whiff_pct": 8.0,  "chase_pct": 7.5,  "csw_pct": 5.8},
    "SI": {"velo": 2.3, "spin": 195, "whiff_pct": 5.5,  "chase_pct": 7.0,  "csw_pct": 4.8},
    "FC": {"velo": 2.8, "spin": 225, "whiff_pct": 9.0,  "chase_pct": 8.2,  "csw_pct": 6.5},
    "SL": {"velo": 3.5, "spin": 275, "whiff_pct": 10.5, "chase_pct": 9.0,  "csw_pct": 7.5},
    "ST": {"velo": 3.2, "spin": 265, "whiff_pct": 11.0, "chase_pct": 10.0, "csw_pct": 7.8},
    "CU": {"velo": 3.8, "spin": 310, "whiff_pct": 9.5,  "chase_pct": 9.5,  "csw_pct": 7.0},
    "KC": {"velo": 3.5, "spin": 290, "whiff_pct": 9.0,  "chase_pct": 8.5,  "csw_pct": 6.8},
    "CH": {"velo": 3.0, "spin": 245, "whiff_pct": 10.5, "chase_pct": 10.0, "csw_pct": 7.8},
    "FS": {"velo": 3.2, "spin": 220, "whiff_pct": 11.0, "chase_pct": 10.5, "csw_pct": 8.0},
}
# Fallback (used only if a pitch type is missing from MLB_SIGMA)
_G_WIN_FALLBACK = {"velo": 3.0, "spin": 250, "whiff_pct": 10.0, "chase_pct": 9.0, "csw_pct": 7.0}

GRADE_COLORS = {
    "A+": "#06D6A0", "A": "#2ec4b6", "B": "#4361EE",
    "C": "#E9C46A", "D": "#F4A261", "F": "#E63946",
}

PITCH_LABEL_COLOR_MAP: dict[str, str] = {
    PITCH_NAMES.get(k, k): v for k, v in PITCH_COLORS.items()
}

# ── Comprehensive pitch category lookup ──────────────────────────────────────
PITCH_CATEGORY_MAP: dict[str, str] = {
    "FF": "fastball",    # 4-Seam Fastball
    "SI": "fastball",    # Sinker
    "FC": "fastball",    # Cutter
    "CH": "offspeed",    # Changeup
    "FS": "offspeed",    # Splitter
    "FO": "offspeed",    # Forkball
    "SC": "offspeed",    # Screwball
    "SL": "breaking",    # Slider
    "ST": "breaking",    # Sweeper
    "CU": "breaking",    # Curveball
    "KC": "breaking",    # Knuckle Curve
    "CS": "breaking",    # Slow Curve
    "SV": "breaking",    # Slurve
    "GY": "breaking",    # Gyroball
    "KN": "knuckleball",
    "EP": "other",
    "PO": "other",
    "UN": "other",
}

FASTBALL_TYPES    = {k for k, v in PITCH_CATEGORY_MAP.items() if v == "fastball"}
BREAKING_TYPES    = {k for k, v in PITCH_CATEGORY_MAP.items() if v == "breaking"}
OFFSPEED_TYPES    = {k for k, v in PITCH_CATEGORY_MAP.items() if v == "offspeed"}
NON_FASTBALL_TYPES = BREAKING_TYPES | OFFSPEED_TYPES

FASTBALL_LABELS = {PITCH_NAMES.get(k, k) for k in FASTBALL_TYPES}
# Legacy alias kept for internal references
FASTBALL_FAMILY = FASTBALL_TYPES


def pitch_category(pitch_type_code: str) -> str:
    return PITCH_CATEGORY_MAP.get(pitch_type_code, "other")


def _ordinal(n: int) -> str:
    """Return ordinal string e.g. 61 -> '61st', 11 -> '11th'."""
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    return f"{n}{['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]}"


def _indefinite_article(word: str) -> str:
    """Returns "an" if word starts with a vowel sound, else "a"."""
    return "an" if word and word[0].lower() in "aeiou" else "a"


def _format_display_df(df: "pd.DataFrame", format_map: dict) -> "pd.DataFrame":
    """Apply display formatting to a DataFrame copy."""
    df = df.copy()
    for col, fmt in format_map.items():
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: fmt.format(x) if pd.notna(x) else "-"
            )
    return df


def _grade_sanity_check(grades_df: "pd.DataFrame") -> list[str]:
    """Dev sanity check: a positive delta can NEVER produce D or F.
    A negative delta can NEVER produce A+ or A.
    Returns list of human-readable violation strings (empty = all clear).
    """
    import pandas as _pd
    _BAD_FOR_POSITIVE = {"D", "F"}
    _BAD_FOR_NEGATIVE = {"A+", "A"}
    _METRIC_PAIRS = [
        ("Delta Velo", "Velo Grade"),
        ("Delta Whiff%", "Whiff Grade"),
        ("Delta CSW%", "CSW Grade"),
        ("Delta Spin", "Spin Grade"),
        ("Delta Chase%", "Chase Grade"),
    ]
    # Normalise column names: the DataFrame uses Unicode delta signs
    col_alias = {}
    for dc, gc in _METRIC_PAIRS:
        raw_dc = dc.replace("Delta ", "Δ ")
        col_alias[dc] = raw_dc  # e.g. "Delta Velo" -> "Δ Velo"

    violations = []
    for _, row in grades_df.iterrows():
        pitch = row.get("Pitch", "?")
        for delta_key, grade_col in _METRIC_PAIRS:
            delta_col = col_alias[delta_key]
            delta = row.get(delta_col)
            grade = str(row.get(grade_col, ""))
            if delta is None or _pd.isna(delta) or not grade or grade in ("nan", ""):
                continue
            delta = float(delta)
            if delta > 0 and grade in _BAD_FOR_POSITIVE:
                violations.append(
                    f"IMPOSSIBLE GRADE  -  {pitch} {grade_col}: "
                    f"delta={delta:+.1f} (above MLB avg) but grade={grade}. "
                    f"Positive delta cannot produce D or F under z-score thresholds."
                )
            elif delta < 0 and grade in _BAD_FOR_NEGATIVE:
                violations.append(
                    f"IMPOSSIBLE GRADE  -  {pitch} {grade_col}: "
                    f"delta={delta:+.1f} (below MLB avg) but grade={grade}. "
                    f"Negative delta cannot produce A+ or A."
                )
    return violations


def _norm(val, avg, window):
    """0-100 score where 50 = MLB avg."""
    return max(0.0, min(100.0, 50.0 + (val - avg) / window * 25.0))


def _z_score(val, avg, window) -> float:
    return (val - avg) / window


def _grade(val, avg, window) -> str:
    """Letter grade from z-score.

    A+ ≥ +1.5σ | A ≥ +0.75σ | B ≥ +0.2σ | C ≥ -0.75σ | D ≥ -1.5σ | F < -1.5σ
    """
    z = _z_score(val, avg, window)
    if z >= 1.5:   return "A+"
    if z >= 0.75:  return "A"
    if z >= 0.2:   return "B"
    if z >= -0.75: return "C"
    if z >= -1.5:  return "D"
    return "F"


def _percentile_from_z(z: float) -> int:
    """Approximate normal-CDF percentile rank from a z-score (no scipy needed)."""
    import math
    pct = (1.0 + math.erf(z / math.sqrt(2))) / 2
    return max(1, min(99, round(pct * 100)))


def get_pitch_color(pitch_type):
    return PITCH_COLORS.get(pitch_type, PITCH_COLORS["OTHER"])


def get_pitch_name(pitch_type):
    return PITCH_NAMES.get(pitch_type, pitch_type)


def dark_layout(**kwargs):
    base = dict(
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#fafafa",
        margin=dict(t=70, b=40),
    )
    base.update(kwargs)
    return base


# ── Data loading ─────────────────────────────────────────────────────────────

DEMO_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_data")

# Reverse-lookup so _fetch_raw can also use bundled CSVs (keyed by MLBAM pitcher_id)
_DEMO_PITCHER_SLUGS: dict[int, str] = {
    694973: "paul_skenes",
    543037: "gerrit_cole",
    660271: "shohei_ohtani",
    554430: "zack_wheeler",
    661403: "emmanuel_clase",
    645261: "sandy_alcantara",
    605483: "blake_snell",
}


_EXCLUDE_PITCH_TYPES = {"UN", "PO"}

_KEEP_COLS = {
    "pitch_type", "pitch_label", "player_name", "pitcher", "stand", "p_throws",
    "balls", "strikes", "description", "zone", "plate_x", "plate_z",
    "release_speed", "release_spin_rate", "pfx_x", "pfx_z",
    "release_pos_x", "release_pos_z", "game_date",
    "home_team", "away_team", "inning_topbot",
    "count_label",
    # Contact quality columns
    "bb_type", "estimated_woba_using_speedangle", "launch_speed", "events",
    # Sequencing columns
    "at_bat_number", "pitch_number",
    # Fatigue / inning analysis
    "inning",
}


def _strip_diacritics(s: str) -> str:
    """Convert any accented/diacritic character to its ASCII base form.

    Examples:
        'Shohei Ohtani'   -> 'Shohei Ohtani'   (unchanged, already ASCII)
        'Shōhei Ōtani'    -> 'Shohei Otani'
        'Sandy Alcantara' -> 'Sandy Alcantara'  (unchanged)
        'Sandy Alcantara' -> 'Sandy Alcantara'
        'Jose Martinez'   -> 'Jose Martinez'
        'Jose Martinez'   -> 'Jose Martinez'
        Works for any Unicode diacritic via NFKD decomposition + Mn strip.
    """
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if unicodedata.category(c) != "Mn"
    )



# Slug aliases for demo pitchers whose name has a known romanization variant
# that NFKD stripping cannot recover automatically.
# "Ōtani" -> NFKD -> "Otani" (not "Ohtani"), because the 'h' is a romanization
# choice, not a diacritic. Map the stripped slug to the correct file slug.
_DEMO_SLUG_ALIASES: dict[str, str] = {
    "shohei_otani": "shohei_ohtani",  # macron o-bar variant
}


def _demo_csv_path(pitcher_name: str, season: int):
    """Return path to a bundled demo CSV if one exists for this pitcher+season."""
    # Normalize diacritics and collapse multiple spaces before slugging so that
    # e.g. "Shohei  Ohtani" (double space) and "Shohei Ohtani" both resolve to
    # the same slug, and accented variants like "Sandy Alcantara" also match.
    slug = "_".join(_strip_diacritics(pitcher_name).strip().lower().split())
    slug = _DEMO_SLUG_ALIASES.get(slug, slug)
    p = os.path.join(DEMO_DATA_DIR, f"{slug}_{season}.csv.gz")
    return p if os.path.exists(p) else None


@st.cache_data(ttl=3600, show_spinner=False)
def _load_demo_csv_cached(csv_path: str) -> pd.DataFrame:
    return pd.read_csv(csv_path, compression="gzip", low_memory=False)


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_statcast_live_cached(pitcher_id: int, season: int) -> pd.DataFrame | None:
    try:
        from pybaseball import statcast_pitcher as _sc
        raw = _sc(
            start_dt=f"{season}-03-01",
            end_dt=f"{season}-11-30",
            player_id=pitcher_id,
        )
        return raw if (raw is not None and not raw.empty) else None
    except Exception:
        return None


def _clean_data(data: pd.DataFrame) -> pd.DataFrame:
    """Exclude junk pitch types, spring training games, and drop columns we never use."""
    data = data[data["pitch_type"].notna()].copy()
    data = data[~data["pitch_type"].isin(_EXCLUDE_PITCH_TYPES)]
    # Strip spring training (game_type='S') - query window starts March 1 which
    # can include spring training Statcast events, causing phantom "14 pitch" rows
    # for injured pitchers who appeared only in exhibition games.
    if "game_type" in data.columns:
        data = data[data["game_type"] != "S"]
    keep = [c for c in _KEEP_COLS if c in data.columns]
    extra = [c for c in data.columns if c not in _KEEP_COLS]
    if extra:
        data = data.drop(columns=extra)
    return data


def _add_derived_cols(data: pd.DataFrame) -> pd.DataFrame:
    data["pitch_label"] = data["pitch_type"].apply(get_pitch_name)
    if "balls" in data.columns and "strikes" in data.columns:
        data["count_label"] = (
            data["balls"].astype(int).astype(str)
            + "-"
            + data["strikes"].astype(int).astype(str)
        )
    return data


def load_pitcher_data(pitcher_name: str, season: int):
    """Load pitcher data and return (data, display_name, pitcher_id, fallback_meta) or None.

    fallback_meta is always present when a tuple is returned:
        {
            "requested_season": int,
            "actual_season_used": int | None,
            "fallback_occurred": bool,
            "fallback_reason": str,
        }
    """
    requested_season = season

    # ── Fast path: pre-bundled demo CSV (instant load, no network) ───────────
    csv_path = _demo_csv_path(pitcher_name, season)
    if csv_path is not None:
        data = _load_demo_csv_cached(csv_path)
        if not data.empty:
            data = _clean_data(data)
            data = _add_derived_cols(data)
            pitcher_id = int(data["pitcher"].iloc[0]) if "pitcher" in data.columns else 0
            if "player_name" in data.columns:
                raw = str(data["player_name"].dropna().iloc[0])
                name_parts = [p.strip() for p in raw.split(",")]
                display_name = (
                    f"{name_parts[1]} {name_parts[0]}"
                    if len(name_parts) == 2
                    else raw
                )
            else:
                display_name = pitcher_name.title()

            # Detect actual season from game_date - bundled files may contain
            # data from a prior year (e.g. gerrit_cole_2025.csv.gz holds 2024
            # data because Cole did not pitch in 2025).
            actual_season = season
            fallback_occurred = False
            fallback_reason = ""
            if "game_date" in data.columns:
                _dates = pd.to_datetime(data["game_date"], errors="coerce").dropna()
                if not _dates.empty:
                    actual_season = int(_dates.dt.year.mode().iloc[0])
                    if actual_season != season:
                        fallback_occurred = True
                        fallback_reason = (
                            f"{display_name} did not pitch in the {season} MLB season. "
                            f"Showing {actual_season} data instead "
                            f"(bundled dataset contained {actual_season} game dates)."
                        )

            fallback_meta = {
                "requested_season": requested_season,
                "actual_season_used": actual_season,
                "fallback_occurred": fallback_occurred,
                "fallback_reason": fallback_reason,
            }
            return data, display_name, pitcher_id, fallback_meta

    # ── Slow path: live pybaseball fetch ─────────────────────────────────────
    # Normalize diacritics first so "Shōhei Ōtani" and "Sandy Alcántara"
    # resolve identically to their ASCII forms before any string operations.
    _normalized_input = _strip_diacritics(pitcher_name).strip()
    parts = _normalized_input.split()
    if len(parts) < 2:
        st.error("Please enter both first and last name (e.g. 'Gerrit Cole').")
        return None

    import pybaseball as _pybaseball
    from pybaseball import playerid_lookup
    from difflib import SequenceMatcher
    _pybaseball.cache.enable()

    first, last = parts[0], " ".join(parts[1:])
    with st.spinner(f"Looking up player ID for {pitcher_name}..."):
        try:
            lookup = playerid_lookup(last, first, fuzzy=True)
        except Exception as e:
            st.error(f"Player lookup failed: {e}")
            return None

    if lookup.empty:
        st.error(
            f"No MLB pitcher found matching '{pitcher_name}'. "
            "Check the spelling and try again."
        )
        return None

    # ── Strict similarity gate (Bug 1 fix) ───────────────────────────────────
    # pybaseball fuzzy=True uses a very loose threshold (~0.6 on last name),
    # which allows nonsense inputs like "Throwington" to silently match
    # "Harrington" (score 0.76). Require last >= 0.80 so common typos still
    # resolve while garbage inputs are rejected cleanly.
    # Both sides are diacritics-stripped before comparison so that e.g.
    # "alcantara" (user) matches "alcantara" (pybaseball) with sim=1.0 even
    # if the DB stores "Alcantara" with an accent internally.
    player = lookup.iloc[0]
    _matched_last  = _strip_diacritics(str(player.get("name_last",  ""))).lower()
    _matched_first = _strip_diacritics(str(player.get("name_first", ""))).lower()
    _last_sim  = SequenceMatcher(None, _strip_diacritics(last).lower(),  _matched_last).ratio()
    _first_sim = SequenceMatcher(None, _strip_diacritics(first).lower(), _matched_first).ratio()
    _MIN_LAST_SIM  = 0.80
    _MIN_FIRST_SIM = 0.50
    if _last_sim < _MIN_LAST_SIM or _first_sim < _MIN_FIRST_SIM:
        st.error(
            f"No MLB pitcher found matching '{pitcher_name}'. "
            "Check the spelling and try again."
        )
        return None

    pitcher_id = int(player["key_mlbam"])
    display_name = f"{player['name_first'].title()} {player['name_last'].title()}"

    # If pybaseball fuzzy-corrected the name, surface that to the user so a
    # near-miss is never invisibly substituted.
    _input_canonical = f"{first.title()} {last.title()}"
    _fuzzy_corrected = (
        _last_sim < 1.0 or _first_sim < 1.0
    ) and display_name.lower() != _input_canonical.lower()
    if _fuzzy_corrected:
        st.info(
            f"ℹ️ Showing results for **{display_name}** "
            f"(closest match to '{pitcher_name}')."
        )

    with st.spinner(f"Fetching {season} Statcast data for {display_name}… (30 - 90 s)"):
        data = _fetch_statcast_live_cached(pitcher_id, season)

    if data is None or data.empty:
        if season == 2026:
            # Suppress the inner warning - we'll show the correct year ourselves
            # if the whole lookback chain fails.
            inner = _load_pitcher_data_quiet(pitcher_name, 2025)
            if inner is not None:
                i_data, i_name, i_id, _ = inner
                fallback_meta = {
                    "requested_season": requested_season,
                    "actual_season_used": 2025,
                    "fallback_occurred": True,
                    "fallback_reason": f"No 2026 data found. Showing {i_name}'s 2025 season instead.",
                }
                return i_data, i_name, i_id, fallback_meta
            # Both 2026 and 2025 had no data - cite the year the USER asked for
            st.warning(
                f"⚠️ {display_name} did not pitch in the {requested_season} MLB season "
                f"(no Statcast data found for {requested_season} or 2025)."
            )
            return None
        st.warning(
            f"⚠️ {display_name} did not pitch in the {season} MLB season "
            f"(no Statcast data found for {season})."
        )
        return None

    data = _clean_data(data)
    data = _add_derived_cols(data)

    fallback_meta = {
        "requested_season": requested_season,
        "actual_season_used": season,
        "fallback_occurred": False,
        "fallback_reason": "",
    }
    return data, display_name, pitcher_id, fallback_meta


def _load_pitcher_data_quiet(pitcher_name: str, season: int):
    """Internal helper: load pitcher data without showing any st.warning/error.

    Used for intermediate fallback probes (e.g. 2026 → 2025) so that only the
    outermost caller decides what message to surface to the user.
    Returns same 4-tuple as load_pitcher_data, or None.
    """
    import types, unittest.mock
    _noop = lambda *a, **kw: None
    with unittest.mock.patch("streamlit.warning", _noop), \
         unittest.mock.patch("streamlit.error",   _noop), \
         unittest.mock.patch("streamlit.info",    _noop):
        return load_pitcher_data(pitcher_name, season)


# ── Effectiveness metrics ─────────────────────────────────────────────────────

def compute_effectiveness(data: pd.DataFrame) -> pd.DataFrame:
    """Return per-pitch-type Whiff%, Chase%, CSW% rounded to one decimal."""
    if "description" not in data.columns:
        return pd.DataFrame()

    rows = []
    for (pt, pl), grp in data.groupby(["pitch_type", "pitch_label"]):
        desc = grp["description"]
        total = len(grp)

        swings = desc.isin(SWING_EVENTS).sum()
        whiffs = desc.isin(WHIFF_EVENTS).sum()
        csw = desc.isin(CSW_EVENTS).sum()

        whiff_pct = round(whiffs / swings * 100, 1) if swings > 0 else 0.0
        csw_pct = round(csw / total * 100, 1) if total > 0 else 0.0

        chase_pct = None
        if "zone" in grp.columns:
            ooz = grp[grp["zone"].isin(OUT_OF_ZONE)]
            ooz_swings = ooz["description"].isin(SWING_EVENTS).sum()
            chase_pct = round(ooz_swings / len(ooz) * 100, 1) if len(ooz) > 0 else 0.0

        row = {
            "pitch_type": pt,
            "pitch_label": pl,
            "Whiff%": whiff_pct,
            "CSW%": csw_pct,
        }
        if chase_pct is not None:
            row["Chase%"] = chase_pct
        rows.append(row)

    return pd.DataFrame(rows)


def effectiveness_chart(eff: pd.DataFrame) -> go.Figure:
    metrics = [c for c in ["Whiff%", "Chase%", "CSW%"] if c in eff.columns]
    eff_long = eff.melt(
        id_vars=["pitch_label"],
        value_vars=metrics,
        var_name="Metric",
        value_name="Value",
    )

    METRIC_COLORS = {"Whiff%": "#E63946", "Chase%": "#F4A261", "CSW%": "#4361EE"}

    fig = px.bar(
        eff_long,
        x="pitch_label",
        y="Value",
        color="Metric",
        barmode="group",
        color_discrete_map=METRIC_COLORS,
        text_auto=".1f",
        labels={"pitch_label": "Pitch Type", "Value": "%", "Metric": ""},
        title="Pitch Effectiveness - Whiff%, Chase%, CSW%",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        **dark_layout(),
        xaxis=dict(gridcolor="#1e2130"),
        yaxis=dict(gridcolor="#1e2130", range=[0, max(eff_long["Value"].max() * 1.25, 10)]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    return fig


# ── Arsenal charts ────────────────────────────────────────────────────────────

def pitch_distribution_chart(data):
    counts = (
        data.groupby(["pitch_type", "pitch_label"])
        .size()
        .reset_index(name="count")
    )
    counts["pct"] = (counts["count"] / counts["count"].sum() * 100).round(1)
    counts = counts.sort_values("count", ascending=False)
    counts["color"] = counts["pitch_type"].apply(get_pitch_color)

    fig = go.Figure(
        go.Bar(
            x=counts["pitch_label"],
            y=counts["pct"],
            marker_color=counts["color"],
            text=counts["pct"].apply(lambda x: f"{x}%"),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Usage: %{y:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        title="Pitch Usage Distribution",
        xaxis_title="Pitch Type",
        yaxis_title="Usage (%)",
        **dark_layout(),
        showlegend=False,
        yaxis=dict(gridcolor="#1e2130"),
        xaxis=dict(gridcolor="#1e2130"),
    )
    return fig


def movement_chart(data):
    df = data.dropna(subset=["pfx_x", "pfx_z"]).copy()
    if df.empty:
        return None

    df["pfx_x_in"] = df["pfx_x"] * 12
    df["pfx_z_in"] = df["pfx_z"] * 12

    pitch_types = df["pitch_type"].unique()
    colors = [get_pitch_color(p) for p in pitch_types]

    fig = px.scatter(
        df,
        x="pfx_x_in",
        y="pfx_z_in",
        color="pitch_label",
        color_discrete_sequence=colors,
        opacity=0.5,
        labels={
            "pfx_x_in": "Horizontal Break (in) - Pitcher's POV",
            "pfx_z_in": "Vertical Break (in)",
            "pitch_label": "Pitch Type",
        },
        title="Pitch Movement Profile",
        hover_data={"pitch_label": True, "pfx_x_in": ":.1f", "pfx_z_in": ":.1f"},
    )
    fig.add_hline(y=0, line_color="#444", line_width=1)
    fig.add_vline(x=0, line_color="#444", line_width=1)
    fig.update_traces(marker=dict(size=4))
    fig.update_layout(
        **dark_layout(),
        legend_title_text="Pitch Type",
        xaxis=dict(gridcolor="#1e2130", zeroline=False),
        yaxis=dict(gridcolor="#1e2130", zeroline=False),
    )
    return fig


def release_point_chart(data):
    df = data.dropna(subset=["release_pos_x", "release_pos_z"]).copy()
    if df.empty:
        return None

    pitch_types = df["pitch_type"].unique()
    colors = [get_pitch_color(p) for p in pitch_types]

    fig = px.scatter(
        df,
        x="release_pos_x",
        y="release_pos_z",
        color="pitch_label",
        color_discrete_sequence=colors,
        opacity=0.5,
        labels={
            "release_pos_x": "Horizontal Release (ft) - Catcher's POV",
            "release_pos_z": "Vertical Release (ft)",
            "pitch_label": "Pitch Type",
        },
        title="Release Point",
        hover_data={"pitch_label": True, "release_pos_x": ":.2f", "release_pos_z": ":.2f"},
    )
    fig.update_traces(marker=dict(size=4))
    fig.update_layout(
        **dark_layout(),
        legend_title_text="Pitch Type",
        xaxis=dict(gridcolor="#1e2130"),
        yaxis=dict(gridcolor="#1e2130"),
    )
    return fig


def velocity_chart(data):
    df = data.dropna(subset=["release_speed"]).copy()
    if df.empty:
        return None

    order = (
        df.groupby("pitch_label")["release_speed"]
        .median()
        .sort_values(ascending=False)
        .index.tolist()
    )
    pitch_color_map = {get_pitch_name(k): v for k, v in PITCH_COLORS.items()}

    fig = px.box(
        df,
        x="pitch_label",
        y="release_speed",
        color="pitch_label",
        color_discrete_map=pitch_color_map,
        category_orders={"pitch_label": order},
        labels={"pitch_label": "Pitch Type", "release_speed": "Velocity (mph)"},
        title="Velocity by Pitch Type",
        points="outliers",
    )
    fig.update_layout(
        **dark_layout(),
        showlegend=False,
        xaxis=dict(gridcolor="#1e2130"),
        yaxis=dict(gridcolor="#1e2130"),
    )
    return fig


# ── Zone heatmap ──────────────────────────────────────────────────────────────

def _build_heatmap(df, title):
    import numpy as np
    fig = go.Figure()
    fig.add_shape(
        type="rect",
        x0=-0.708, x1=0.708,
        y0=1.5, y1=3.5,
        line=dict(color="#ffffff", width=2),
        fillcolor="rgba(0,0,0,0)",
    )
    heatmap_data, x_edges, y_edges = np.histogram2d(
        df["plate_x"], df["plate_z"],
        bins=25,
        range=[[-2.5, 2.5], [0, 5]],
    )
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2
    fig.add_trace(go.Heatmap(
        x=x_centers,
        y=y_centers,
        z=heatmap_data.T,
        colorscale="Hot",
        showscale=True,
        colorbar=dict(
            title=dict(text="Count", font=dict(color="#fafafa")),
            tickfont=dict(color="#fafafa"),
        ),
        hovertemplate="x: %{x:.2f}<br>z: %{y:.2f}<br>Count: %{z}<extra></extra>",
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Horizontal Location (ft) - Catcher's POV",
        yaxis_title="Height (ft)",
        **dark_layout(),
        xaxis=dict(range=[-2.5, 2.5], gridcolor="#1e2130"),
        yaxis=dict(range=[0, 5], gridcolor="#1e2130"),
    )
    return fig


def zone_heatmap(data, pitch_filter=None):
    df = data.dropna(subset=["plate_x", "plate_z"]).copy()
    if pitch_filter and pitch_filter != "All":
        df = df[df["pitch_label"] == pitch_filter]
    if df.empty:
        return None
    label = pitch_filter if pitch_filter and pitch_filter != "All" else "All Pitches"
    return _build_heatmap(df, f"Zone Heatmap - {label}")


def zone_heatmap_by_count(data, count):
    if "count_label" not in data.columns:
        return None
    df = data[data["count_label"] == count].dropna(subset=["plate_x", "plate_z"]).copy()
    if df.empty:
        return None
    return _build_heatmap(df, f"Zone Heatmap - Count {count} ({len(df)} pitches)")


# ── Count analysis ────────────────────────────────────────────────────────────

def count_pitch_mix_chart(data):
    if "count_label" not in data.columns:
        return None

    df = data[data["count_label"].isin(COUNT_ORDER)].copy()
    if df.empty:
        return None

    grp = df.groupby(["count_label", "pitch_label"]).size().reset_index(name="n")
    totals = grp.groupby("count_label")["n"].sum().reset_index(name="total")
    grp = grp.merge(totals, on="count_label")
    grp["pct"] = (grp["n"] / grp["total"] * 100).round(1)

    fig = px.bar(
        grp,
        x="count_label",
        y="pct",
        color="pitch_label",
        color_discrete_map=PITCH_LABEL_COLOR_MAP,
        category_orders={"count_label": COUNT_ORDER},
        labels={"count_label": "Count (Balls-Strikes)", "pct": "Usage (%)", "pitch_label": "Pitch Type"},
        title="Pitch Mix by Count",
        text_auto=False,
    )
    fig.update_layout(
        **dark_layout(),
        barmode="stack",
        legend_title_text="Pitch Type",
        xaxis=dict(gridcolor="#1e2130"),
        yaxis=dict(gridcolor="#1e2130", range=[0, 105]),
        legend=dict(orientation="h", y=-0.2),
    )
    return fig


# ── Summary table ─────────────────────────────────────────────────────────────

def summary_table(data: pd.DataFrame, eff: pd.DataFrame) -> pd.DataFrame:
    stat_cols = {
        "release_speed": "Avg Velo",
        "release_spin_rate": "Avg Spin",
        "pfx_x": "H-Break (in)",
        "pfx_z": "V-Break (in)",
    }
    available = {k: v for k, v in stat_cols.items() if k in data.columns}
    agg = {col: (col, "mean") for col in available}

    summary = data.groupby(["pitch_type", "pitch_label"]).agg(
        count=("pitch_type", "count"), **agg
    ).reset_index()

    summary["Usage %"] = (summary["count"] / summary["count"].sum() * 100).round(1)
    summary = summary.sort_values("count", ascending=False)

    rename = {"pitch_label": "Pitch Type", "count": "Count"}
    for col, label in available.items():
        if col in ["pfx_x", "pfx_z"]:
            summary[col] = (summary[col] * 12).round(1)
        else:
            summary[col] = summary[col].round(1)
        rename[col] = label
    summary = summary.rename(columns=rename)

    if not eff.empty:
        eff_cols = [c for c in ["Whiff%", "Chase%", "CSW%"] if c in eff.columns]
        merge_cols = ["pitch_type"] + eff_cols
        summary = summary.merge(eff[merge_cols], on="pitch_type", how="left")

    display_cols = (
        ["Pitch Type", "Count", "Usage %"]
        + list(available.values())
        + [c for c in ["Whiff%", "Chase%", "CSW%"] if c in summary.columns]
    )
    return summary[[c for c in display_cols if c in summary.columns]]


# ── Pitch grading vs MLB avg ──────────────────────────────────────────────────

_MIN_PITCHES_FOR_GRADE = 30

MIN_PITCHES_FOR_CLAIM = {
    "profile_grade":    100,   # lowered from 200 so mid-season data gets a real tier
    "pitch_grade":       30,
    "count_insight":     20,
    "count_pitch_cell":  10,
    "contact_insight":   25,
    "sequencing_cell":   15,
    "fatigue":          100,
    "matchup":           20,
    "fps_outcome":       30,
}


def pitch_grades(data: pd.DataFrame, eff: pd.DataFrame) -> pd.DataFrame:
    """Per-pitch letter-grade table compared to 2024 MLB averages."""
    import numpy as np
    rows = []
    for (pt, pl), grp in data.groupby(["pitch_type", "pitch_label"]):
        if pt not in MLB_AVG:
            continue
        if len(grp) < _MIN_PITCHES_FOR_GRADE:
            continue
        avg = MLB_AVG[pt]
        sig = MLB_SIGMA.get(pt, _G_WIN_FALLBACK)
        r = {"Pitch": pl, "_pt": pt}

        if "release_speed" in grp.columns:
            v = grp["release_speed"].mean()
            if pd.notna(v):
                r["Velo"] = round(v, 1)
                r["MLB Avg Velo"] = avg["velo"]
                r["Δ Velo"] = round(v - avg["velo"], 1)
                r["Velo Grade"] = _grade(v, avg["velo"], sig["velo"])

        if "release_spin_rate" in grp.columns:
            s = grp["release_spin_rate"].mean()
            if pd.notna(s):
                r["Spin"] = round(s)
                r["MLB Avg Spin"] = avg["spin"]
                r["Δ Spin"] = round(s - avg["spin"])
                r["Spin Grade"] = _grade(s, avg["spin"], sig["spin"])

        if not eff.empty:
            er = eff[eff["pitch_type"] == pt]
            if not er.empty:
                w = er.iloc[0].get("Whiff%", np.nan)
                if pd.notna(w):
                    r["Whiff%"] = round(w, 1)
                    r["Δ Whiff%"] = round(w - avg["whiff_pct"], 1)
                    r["Whiff Grade"] = _grade(w, avg["whiff_pct"], sig["whiff_pct"])
                csw = er.iloc[0].get("CSW%", np.nan)
                if pd.notna(csw):
                    r["CSW%"] = round(csw, 1)
                    r["Δ CSW%"] = round(csw - avg["csw_pct"], 1)
                    r["CSW Grade"] = _grade(csw, avg["csw_pct"], sig["csw_pct"])
                if "Chase%" in er.columns:
                    ch = er.iloc[0].get("Chase%", np.nan)
                    if pd.notna(ch):
                        r["Chase%"] = round(ch, 1)
                        r["Δ Chase%"] = round(ch - avg["chase_pct"], 1)
                        r["Chase Grade"] = _grade(ch, avg["chase_pct"], sig["chase_pct"])
        rows.append(r)

    df = pd.DataFrame(rows)
    if "_pt" in df.columns:
        df = df.drop(columns=["_pt"])
    return df


def style_grades(df: pd.DataFrame):
    grade_cols = [c for c in df.columns if "Grade" in c]
    delta_cols = [c for c in df.columns if c.startswith("Δ")]

    def color_grade(val):
        bg = GRADE_COLORS.get(str(val), "#1e2130")
        return f"background-color: {bg}; color: #000000; font-weight: bold"

    def color_delta(val):
        try:
            v = float(val)
            color = "#06D6A0" if v > 0 else "#E63946" if v < 0 else "#fafafa"
            return f"color: {color}; font-weight: bold"
        except (ValueError, TypeError):
            return ""

    styled = df.style
    if grade_cols:
        styled = styled.map(color_grade, subset=grade_cols)
    if delta_cols:
        styled = styled.map(color_delta, subset=delta_cols)
    return styled


# ── Pitcher meta (team + handedness from statcast data) ───────────────────────

def get_pitcher_meta(data: pd.DataFrame) -> tuple[str, str]:
    """Return (team_abbr, p_throws) derived from statcast pitch data."""
    hand = "R"
    if "p_throws" in data.columns:
        mode = data["p_throws"].dropna().mode()
        if not mode.empty:
            hand = str(mode.iloc[0])

    team = ""
    if all(c in data.columns for c in ["home_team", "away_team", "inning_topbot"]):
        top_teams = data[data["inning_topbot"] == "Top"]["home_team"].dropna()
        bot_teams = data[data["inning_topbot"] == "Bot"]["away_team"].dropna()
        all_teams = pd.concat([top_teams, bot_teams]).tolist()
        if all_teams:
            from collections import Counter
            team = Counter(all_teams).most_common(1)[0][0]

    return team, hand


# ── Grade badge helpers ────────────────────────────────────────────────────────

_GRADE_SCORE = {"A+": 5, "A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
_SCORE_GRADE_LIST = [(4.5, "A+"), (3.5, "A"), (2.5, "B"), (1.5, "C"), (0.5, "D"), (-1, "F")]


def _compute_overall_profile(overall_csw_pct: float | None, total_pitches: int) -> str:
    """Classify pitcher profile using overall CSW% percentile rank vs MLB starters.

    Uses normal CDF (mean=26.5%, sigma=1.8% - MLB 2024 starter distribution).
    Returns "active" for very small samples (< profile_grade threshold).

    Tier boundaries (percentile vs MLB starters):
      >= 85th  -> elite          (top 15%)
      >= 65th  -> above-average  (next 20%)
      >= 40th  -> average        (middle 25%)
      >= 20th  -> solid          (next 20%)
      else     -> below-average  (bottom 20%)
    """
    if total_pitches < MIN_PITCHES_FOR_CLAIM["profile_grade"] or overall_csw_pct is None:
        return "active"

    import math
    # MLB starter distribution: mean=26.5%, sigma=1.8%.
    # Examples: Skenes 29.3% -> pct~94 (elite), Wheeler 28.0% -> pct~79 (above-average)
    z = (overall_csw_pct - 26.5) / 1.8
    pct = 50.0 * (1.0 + math.erf(z / math.sqrt(2)))

    if pct >= 85:
        return "elite"
    elif pct >= 65:
        return "above-average"
    elif pct >= 40:
        return "average"
    elif pct >= 20:
        return "solid"
    else:
        return "below-average"


def _overall_grade_from_row(row) -> str:
    grade_cols = [c for c in row.index if c.endswith("Grade")]
    scores = [_GRADE_SCORE.get(str(row[c]), 2) for c in grade_cols if pd.notna(row.get(c))]
    if not scores:
        return "C"
    avg = sum(scores) / len(scores)
    for threshold, grade in _SCORE_GRADE_LIST:
        if avg >= threshold:
            return grade
    return "F"


def _overall_percentile_from_row(row, data: pd.DataFrame) -> int | None:
    """Return an approximate overall percentile rank for the pitch based on CSW z-score."""
    pt = row.get("_pt_hidden")
    if pt is None or pt not in MLB_AVG or pt not in MLB_SIGMA:
        return None
    csw_val = row.get("CSW%")
    if csw_val is None or pd.isna(csw_val):
        return None
    avg_csw = MLB_AVG[pt]["csw_pct"]
    sig_csw = MLB_SIGMA[pt]["csw_pct"]
    z = _z_score(float(csw_val), avg_csw, sig_csw)
    return _percentile_from_z(z)


def render_grade_badges(grades_df: pd.DataFrame, data: pd.DataFrame):
    """Render large colored A - F badge cards at the top of Overview, one per pitch."""
    if grades_df.empty:
        return

    usage_map: dict[str, float] = {}
    pt_map: dict[str, str] = {}
    if not data.empty:
        total = len(data)
        for (pt, pl), grp in data.groupby(["pitch_type", "pitch_label"]):
            usage_map[pl] = round(len(grp) / total * 100, 1)
            pt_map[pl] = pt

    cards = []
    for _, row in grades_df.iterrows():
        pitch = row.get("Pitch", "?")
        overall = _overall_grade_from_row(row)
        color = GRADE_COLORS.get(overall, "#888888")
        usage_pct = usage_map.get(pitch, 0.0)
        usage_str = f"{usage_pct}%" if pitch in usage_map else ""
        vg = row.get("Velo Grade", "")
        wg = row.get("Whiff Grade", "")
        csw_g = row.get("CSW Grade", "")
        sub = "  ·  ".join(
            f"{k}: {v}"
            for k, v in [("Velocity", vg), ("Whiff", wg), ("CSW", csw_g)]
            if v
        )
        # Compute percentile from CSW z-score + velo/whiff z-scores for mismatch note
        pt = pt_map.get(pitch, "")
        pct_rank = None
        velo_z = None
        whiff_z = None
        csw_val = row.get("CSW%")
        if pt in MLB_AVG and pt in MLB_SIGMA:
            if csw_val is not None and pd.notna(csw_val):
                z = _z_score(float(csw_val), MLB_AVG[pt]["csw_pct"], MLB_SIGMA[pt]["csw_pct"])
                pct_rank = _percentile_from_z(z)
            velo_val = row.get("Velo")
            if velo_val is not None and pd.notna(velo_val):
                velo_z = _z_score(float(velo_val), MLB_AVG[pt]["velo"], MLB_SIGMA[pt]["velo"])
            whiff_val = row.get("Whiff%")
            if whiff_val is not None and pd.notna(whiff_val):
                whiff_z = _z_score(float(whiff_val), MLB_AVG[pt]["whiff_pct"], MLB_SIGMA[pt]["whiff_pct"])
        cards.append((pitch, overall, color, usage_str, usage_pct, sub, pct_rank, velo_z, whiff_z))

    cards.sort(key=lambda x: x[4], reverse=True)

    html = ['<div style="display:flex;flex-wrap:wrap;gap:14px;margin-bottom:24px;">']
    mismatch_notes = []
    for pitch, grade, color, usage_str, _usage_pct, sub, pct_rank, velo_z, whiff_z in cards:
        pct_str = f"<div style='font-size:10px;color:{color};margin-top:3px;font-weight:700;'>{_ordinal(pct_rank)} %ile (CSW)</div>" if pct_rank is not None else ""
        html.append(f"""
<div style="background:{color}1a;border:2px solid {color};border-radius:14px;
            padding:16px 20px;text-align:center;min-width:120px;flex:1;max-width:160px;">
  <div style="font-size:11px;color:#aaa;margin-bottom:2px;">{pitch}</div>
  <div style="font-size:46px;font-weight:900;color:{color};line-height:1.1;">{grade}</div>
  <div style="font-size:13px;color:#ccc;margin-top:4px;">{usage_str}</div>
  {pct_str}
  <div style="font-size:10px;color:#777;margin-top:5px;">{sub}</div>
</div>""")
        if velo_z is not None and whiff_z is not None and velo_z >= 0.75 and whiff_z <= -0.75:
            mismatch_notes.append(pitch)
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)
    for pitch in mismatch_notes:
        st.caption(
            f"**{pitch}**  -  High velocity, low whiff rate: this pitch generates "
            "weak contact rather than swings-and-misses."
        )


# ── Arsenal radar chart ───────────────────────────────────────────────────────

def arsenal_radar_chart(data: pd.DataFrame, eff: pd.DataFrame) -> go.Figure:
    """Polar radar: top-4 pitch types by usage, axes normalized to MLB avg = 50."""
    import numpy as np
    categories = ["Velocity", "Spin Rate", "Whiff%", "CSW%", "Chase%"]

    # Cap to top 4 pitch types by usage to keep the chart readable
    top4 = (
        data.groupby("pitch_type").size()
        .sort_values(ascending=False)
        .head(4)
        .index.tolist()
    )

    fig = go.Figure()

    for (pt, pl), grp in data.groupby(["pitch_type", "pitch_label"]):
        if pt not in MLB_AVG or pt not in top4:
            continue
        avg = MLB_AVG[pt]
        sig = MLB_SIGMA.get(pt, _G_WIN_FALLBACK)
        color = get_pitch_color(pt)
        scores = []

        v = grp["release_speed"].mean() if "release_speed" in grp.columns else np.nan
        scores.append(_norm(v, avg["velo"], sig["velo"]) if pd.notna(v) else 50.0)

        s = grp["release_spin_rate"].mean() if "release_spin_rate" in grp.columns else np.nan
        scores.append(_norm(s, avg["spin"], sig["spin"]) if pd.notna(s) else 50.0)

        er = eff[eff["pitch_type"] == pt] if not eff.empty else pd.DataFrame()
        if not er.empty:
            w = er.iloc[0].get("Whiff%", np.nan)
            scores.append(_norm(w, avg["whiff_pct"], sig["whiff_pct"]) if pd.notna(w) else 50.0)
            csw = er.iloc[0].get("CSW%", np.nan)
            scores.append(_norm(csw, avg["csw_pct"], sig["csw_pct"]) if pd.notna(csw) else 50.0)
            ch = er.iloc[0].get("Chase%", np.nan) if "Chase%" in er.columns else np.nan
            scores.append(_norm(ch, avg["chase_pct"], sig["chase_pct"]) if pd.notna(ch) else 50.0)
        else:
            scores.extend([50.0, 50.0, 50.0])

        closed_r = scores + [scores[0]]
        closed_t = categories + [categories[0]]

        hover_lines = [
            f"{cat}: {sc:.0f}/100"
            for cat, sc in zip(categories, scores)
        ]
        fig.add_trace(go.Scatterpolar(
            r=closed_r,
            theta=closed_t,
            fill="toself",
            opacity=0.22,
            name=pl,
            line=dict(color=color, width=2.5),
            fillcolor=color,
            hovertemplate="<b>" + pl + "</b><br>" + "<br>".join(hover_lines) + "<extra></extra>",
        ))

    fig.add_trace(go.Scatterpolar(
        r=[50] * (len(categories) + 1),
        theta=categories + [categories[0]],
        mode="lines",
        name="MLB Avg",
        line=dict(color="#888888", width=1.5, dash="dot"),
        hoverinfo="skip",
    ))

    fig.update_layout(
        title="Arsenal Radar - Top 4 Pitches by Usage vs MLB Average (50 = League Avg)",
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[25, 50, 75, 100],
                ticktext=["Below", "MLB Avg", "Above", "Elite"],
                tickfont=dict(color="#aaaaaa", size=9),
                gridcolor="#2a2a3a",
                linecolor="#2a2a3a",
            ),
            angularaxis=dict(
                tickfont=dict(color="#fafafa", size=12),
                gridcolor="#2a2a3a",
                linecolor="#3a3a4a",
            ),
            bgcolor="#0e1117",
        ),
        paper_bgcolor="#0e1117",
        font_color="#fafafa",
        margin=dict(t=70, b=70, l=90, r=90),
        legend=dict(orientation="v", x=1.05, y=0.5),
    )
    return fig


# ── Year-over-year helpers ────────────────────────────────────────────────────

def _fetch_raw(pitcher_id: int, season: int) -> pd.DataFrame | None:
    # Fast path: bundled demo CSV
    if pitcher_id in _DEMO_PITCHER_SLUGS:
        slug = _DEMO_PITCHER_SLUGS[pitcher_id]
        csv_path = os.path.join(DEMO_DATA_DIR, f"{slug}_{season}.csv.gz")
        if os.path.exists(csv_path):
            raw = _load_demo_csv_cached(csv_path)
            if not raw.empty:
                raw = _clean_data(raw)
                raw["pitch_label"] = raw["pitch_type"].apply(get_pitch_name)
                return raw
    # Slow path: cached live fetch
    raw = _fetch_statcast_live_cached(pitcher_id, season)
    if raw is None or raw.empty:
        return None
    raw = _clean_data(raw)
    raw["pitch_label"] = raw["pitch_type"].apply(get_pitch_name)
    return raw


def yoy_delta_table(curr: pd.DataFrame, prev: pd.DataFrame,
                    season_curr: int, season_prev: int) -> pd.DataFrame:
    def agg(data, season):
        total = len(data)
        rows = []
        for (pt, pl), grp in data.groupby(["pitch_type", "pitch_label"]):
            r = {"pitch_type": pt, "Pitch": pl}
            r[f"Usage% ({season})"] = round(len(grp) / total * 100, 1)
            if "release_speed" in grp.columns:
                r[f"Velo ({season})"] = round(grp["release_speed"].mean(), 1)
            if "release_spin_rate" in grp.columns:
                r[f"Spin ({season})"] = int(round(grp["release_spin_rate"].mean()))
            rows.append(r)
        return pd.DataFrame(rows)

    df_c = agg(curr, season_curr)
    df_p = agg(prev, season_prev)
    merged = df_c.merge(df_p, on=["pitch_type", "Pitch"], how="outer")

    for metric, fmt in [("Velo", ".1f"), ("Spin", ".0f"), ("Usage%", ".1f")]:
        cc = f"{metric} ({season_curr})"
        pc = f"{metric} ({season_prev})"
        if cc in merged.columns and pc in merged.columns:
            delta = pd.to_numeric(merged[cc], errors="coerce") - pd.to_numeric(merged[pc], errors="coerce")
            merged[f"Δ {metric}"] = delta.round(1 if metric != "Spin" else 0)

    merged = merged.drop(columns=["pitch_type"])
    return merged.fillna("-")


# ── Multi-season helpers ──────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_multi_season(pitcher_id: int, curr_year: int,
                       n_years: int = 5) -> dict[int, pd.DataFrame]:
    """Fetch up to n_years seasons of pitch data going back from curr_year.

    Returns {year: DataFrame} for seasons that have >= 50 pitches.
    Relies on _fetch_raw which is already cached for both demo and live data.
    """
    seasons: dict[int, pd.DataFrame] = {}
    for year in range(curr_year, curr_year - n_years, -1):
        try:
            df = _fetch_raw(pitcher_id, year)
            if df is not None and len(df) >= 50:
                seasons[year] = df
        except Exception:
            continue
        if len(seasons) >= n_years:
            break
    return seasons


def multi_season_stats_table(seasons_data: dict[int, pd.DataFrame]) -> pd.DataFrame:
    """Build a wide-format pitch stats table across multiple seasons.

    Columns: Pitch | Velo (yr) … | Spin (yr) … | Usage% (yr) … | Velo Trend
    """
    if not seasons_data:
        return pd.DataFrame()

    sorted_years = sorted(seasons_data.keys())
    all_pitches: set[str] = set()
    for df in seasons_data.values():
        if "pitch_label" in df.columns:
            all_pitches.update(df["pitch_label"].unique())

    rows = []
    for pitch in sorted(all_pitches):
        row: dict = {"Pitch": pitch}
        velo_vals: dict[int, float | None] = {}

        for yr in sorted_years:
            df = seasons_data[yr]
            if "pitch_label" not in df.columns:
                continue
            grp = df[df["pitch_label"] == pitch]
            if len(grp) >= 10:
                total = max(len(df), 1)
                row[f"Velo ({yr})"] = round(grp["release_speed"].mean(), 1) \
                    if "release_speed" in grp.columns else None
                row[f"Spin ({yr})"] = int(round(grp["release_spin_rate"].mean())) \
                    if "release_spin_rate" in grp.columns else None
                row[f"Usage% ({yr})"] = round(len(grp) / total * 100, 1)
                velo_vals[yr] = row[f"Velo ({yr})"]
            else:
                row[f"Velo ({yr})"] = None
                row[f"Spin ({yr})"] = None
                row[f"Usage% ({yr})"] = None
                velo_vals[yr] = None

        # Trend arrow based on last 2-3 available velo points
        recent = [velo_vals[y] for y in sorted_years if velo_vals.get(y) is not None]
        if len(recent) >= 3:
            if recent[-1] > recent[-2] and recent[-2] > recent[-3]:
                row["Velo Trend"] = "↑"
            elif recent[-1] < recent[-2] and recent[-2] < recent[-3]:
                row["Velo Trend"] = "↓"
            else:
                row["Velo Trend"] = "~"
        elif len(recent) == 2:
            row["Velo Trend"] = "↑" if recent[-1] > recent[-2] else ("↓" if recent[-1] < recent[-2] else "~")
        else:
            row["Velo Trend"] = "-"

        rows.append(row)

    result = pd.DataFrame(rows)
    # Build desired column order: Pitch | grouped by year | Velo Trend
    ordered_cols = ["Pitch"]
    for yr in sorted_years:
        for metric in ["Velo", "Spin", "Usage%"]:
            col = f"{metric} ({yr})"
            if col in result.columns:
                ordered_cols.append(col)
    if "Velo Trend" in result.columns:
        ordered_cols.append("Velo Trend")
    return result[[c for c in ordered_cols if c in result.columns]]


def multi_season_gamebygame_chart(seasons_data: dict[int, pd.DataFrame],
                                   pitcher_name: str) -> go.Figure | None:
    """Game-by-game fastball velocity chart across all available seasons.

    Each data point = one game start (avg fastball velo that day).
    Seasons appear as separate arcs since game dates don't overlap.
    """
    if not seasons_data:
        return None

    # Newest season = red, prior seasons = blue, green, yellow, orange
    season_colors = ["#E63946", "#4361EE", "#06D6A0", "#E9C46A", "#F4A261"]
    sorted_years = sorted(seasons_data.keys(), reverse=True)

    traces = []
    for i, yr in enumerate(sorted_years):
        df = seasons_data[yr]
        if "game_date" not in df.columns or "release_speed" not in df.columns:
            continue
        if "pitch_type" in df.columns:
            fb_df = df[df["pitch_type"].isin(FASTBALL_TYPES)].copy()
        else:
            fb_df = df.copy()
        if fb_df.empty:
            continue
        fb_df["game_date"] = pd.to_datetime(fb_df["game_date"])
        daily = (
            fb_df.groupby("game_date")["release_speed"]
            .mean()
            .reset_index()
            .sort_values("game_date")
        )
        if daily.empty:
            continue
        season_start = daily["game_date"].min()
        daily["day_of_season"] = (daily["game_date"] - season_start).dt.days
        color = season_colors[i % len(season_colors)]
        traces.append(go.Scatter(
            x=daily["day_of_season"],
            y=daily["release_speed"].round(1),
            mode="lines+markers",
            name=str(yr),
            line=dict(color=color, width=2),
            marker=dict(size=7, color=color),
            hovertemplate=(
                f"<b>{yr}</b> - Day %{{x}}<br>"
                f"Avg Fastball: %{{y:.1f}} mph<extra></extra>"
            ),
        ))

    if not traces:
        return None

    all_years = sorted(seasons_data.keys())
    title = f"{pitcher_name} - Fastball Velocity by Start (Day of Season)"
    if len(all_years) >= 2:
        title += f" ({all_years[0]} - {all_years[-1]})"

    fig = go.Figure(data=traces)
    fig.update_layout(
        **dark_layout(margin=dict(t=80, b=40, r=100)),
        title=title,
        xaxis=dict(title="Day of Season (0 = First Start)", gridcolor="#1e2130"),
        yaxis=dict(title="Avg Fastball Velocity (mph)", gridcolor="#1e2130"),
        legend=dict(
            title="Season",
            orientation="v",
            yanchor="middle",
            y=0.5,
            x=1.01,
            xanchor="left",
        ),
    )
    return fig


# ── Natural language scouting narrative ──────────────────────────────────────

def generate_narrative(
    display_name: str,
    hand_label: str,
    team: str,
    grades_df: pd.DataFrame,
    eff_df: pd.DataFrame,
    avg_fb_velo: float | None,
    insight_str: str | None,
    platoon_label: str,
    vdata: pd.DataFrame | None = None,
    overall_csw_pct: float | None = None,
) -> str:
    """Auto-generate a 4-sentence plain-English scouting summary.
    No LLM calls  -  pure conditional string formatting.
    """
    # ── S1: overall profile from CSW% percentile rank vs MLB ──────────────
    _total_p = len(vdata) if vdata is not None and not vdata.empty else 0
    profile = _compute_overall_profile(overall_csw_pct, _total_p)

    n_pitches = len(eff_df) if not eff_df.empty else 0
    velo_part = (
        f", featuring a primary fastball averaging {avg_fb_velo:.1f} mph"
        if avg_fb_velo and pd.notna(avg_fb_velo)
        else ""
    )
    _article = _indefinite_article(profile)
    s1 = (
        f"{display_name} is {_article} {profile} {hand_label} pitcher with a "
        f"{n_pitches}-pitch arsenal{velo_part}."
    )

    # ── S2: best pitch by composite score (Whiff%*0.5 + CSW%*0.3 + usage%*0.2) ─
    # Uses the SAME eligibility gates as the Scouting Summary's _ps() function:
    #   1. usage >= 8% of vdata pitches (same 8% floor)
    #   2. per-pitch count >= MIN_PITCHES_FOR_CLAIM["pitch_grade"] (30 minimum)
    # If no pitch survives both gates, emit a small-sample notice instead.
    s2 = ""
    if not eff_df.empty and "Whiff%" in eff_df.columns and "pitch_label" in eff_df.columns:
        valid_eff = eff_df[eff_df["Whiff%"].notna()].copy()
        _usage_counts_s2: "pd.Series | None" = None
        if not valid_eff.empty and vdata is not None and not vdata.empty:
            _usage_counts_s2 = vdata.groupby("pitch_label").size()
            _total = _usage_counts_s2.sum()
            _usage_pct_map = (_usage_counts_s2 / _total * 100).to_dict()
            valid_eff["_usage_pct"] = valid_eff["pitch_label"].map(_usage_pct_map).fillna(0.0)
            valid_eff["_raw_count"] = valid_eff["pitch_label"].map(_usage_counts_s2.to_dict()).fillna(0)
            valid_eff = valid_eff[
                (valid_eff["_usage_pct"] >= 8.0)
                & (valid_eff["_raw_count"] >= MIN_PITCHES_FOR_CLAIM["pitch_grade"])
            ]
        if not valid_eff.empty:
            _csw_col = valid_eff["CSW%"] if "CSW%" in valid_eff.columns else 0
            _up = valid_eff["_usage_pct"] if "_usage_pct" in valid_eff.columns else 0
            valid_eff = valid_eff.copy()
            valid_eff["_composite"] = (
                valid_eff["Whiff%"] * 0.5
                + (_csw_col * 0.3 if "CSW%" in valid_eff.columns else 0)
                + (_up * 0.2)
            )
            best_row = valid_eff.loc[valid_eff["_composite"].idxmax()]
            platoon_suffix = f" {platoon_label}" if platoon_label != "All Batters" else ""
            s2 = (
                f"{display_name}'s best out-pitch is the {best_row['pitch_label']}, "
                f"generating a {best_row['Whiff%']:.0f}% Whiff rate{platoon_suffix}."
            )
        else:
            # Sample too small - no pitch meets both the usage and count thresholds.
            s2 = (
                f"With only {_total_p} pitches tracked this season, "
                f"the sample is too small to reliably identify a standout pitch."
            )

    # ── S3: count insight ─────────────────────────────────────────────────
    if insight_str:
        stripped = insight_str.lstrip("⚡").strip()
        if "*(→" in stripped:
            stripped = stripped[: stripped.index("*(→")].strip()
        stripped = stripped.replace("**", "")
        s3 = f"Situationally, {stripped[0].lower()}{stripped[1:]}"
    else:
        s3 = (
            f"{display_name}'s count-based tendencies reveal exploitable patterns - "
            "see the Count Tendencies tab."
        )

    # ── S4: platoon note ──────────────────────────────────────────────────
    if platoon_label != "All Batters":
        s4 = f"This report reflects performance exclusively {platoon_label}."
    else:
        s4 = (
            f"{display_name} shows consistent performance against both left- and "
            "right-handed batters."
        )

    sentences = [x for x in [s1, s2, s3, s4] if x]
    return " ".join(sentences)


# ── Batted ball / contact quality ─────────────────────────────────────────────

def contact_quality(data: pd.DataFrame, min_bip: int = 20) -> pd.DataFrame:
    """Return per-pitch-type batted ball profile + xwOBA.

    Columns: pitch_type, pitch_label, n_bip, GB%, LD%, FB%, PU%,
             avg_xwoba, avg_exit_velo
    Only rows with >= min_bip balls in play are included.
    Sorted ascending by avg_xwoba (best pitch = lowest xwOBA allowed).
    """
    if "bb_type" not in data.columns or "pitch_type" not in data.columns:
        return pd.DataFrame()

    contact = data[data["bb_type"].notna()].copy()
    if contact.empty:
        return pd.DataFrame()

    rows = []
    for (pt, pl), grp in contact.groupby(["pitch_type", "pitch_label"]):
        n_bip = len(grp)
        if n_bip < min_bip:
            continue
        avg_xwoba = (
            grp["estimated_woba_using_speedangle"].mean()
            if "estimated_woba_using_speedangle" in grp.columns
            else float("nan")
        )
        avg_exit_velo = (
            grp["launch_speed"].mean()
            if "launch_speed" in grp.columns
            else float("nan")
        )
        rows.append({
            "pitch_type": pt,
            "pitch_label": pl,
            "n_bip": n_bip,
            "GB%": round((grp["bb_type"] == "ground_ball").mean() * 100, 1),
            "LD%": round((grp["bb_type"] == "line_drive").mean() * 100, 1),
            "FB%": round((grp["bb_type"] == "fly_ball").mean() * 100, 1),
            "PU%": round((grp["bb_type"] == "popup").mean() * 100, 1),
            "avg_xwoba": round(avg_xwoba, 3) if pd.notna(avg_xwoba) else None,
            "avg_exit_velo": round(avg_exit_velo, 1) if pd.notna(avg_exit_velo) else None,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    valid_xwoba = df["avg_xwoba"].notna()
    df = df.sort_values(
        "avg_xwoba", ascending=True, na_position="last"
    ).reset_index(drop=True)
    return df


def render_contact_quality(cq_df: pd.DataFrame) -> None:
    """Render the contact quality table + GB% horizontal bar chart."""
    if cq_df.empty:
        st.info(
            "Not enough balls in play to compute contact quality "
            "(minimum 20 per pitch type)."
        )
        return

    st.caption(
        "When batters DO make contact, what happens? GB% = ground balls "
        "(outs more likely), LD% = line drives (hardest hits, most "
        "dangerous), FB% = fly balls. xwOBA measures expected scoring "
        "value of contact allowed - lower is better for the pitcher. "
        "MLB average xwOBA is approximately 0.320."
    )

    col_tbl, col_chart = st.columns(2)


    with col_tbl:
        display = cq_df[
            ["pitch_label", "n_bip", "GB%", "LD%", "FB%", "avg_xwoba", "avg_exit_velo"]
        ].copy()
        display.columns = ["Pitch", "BIP", "GB%", "LD%", "FB%", "xwOBA", "Exit Velo (mph)"]
        display = _format_display_df(display, {
            "GB%":            "{:.1f}",
            "LD%":            "{:.1f}",
            "FB%":            "{:.1f}",
            "xwOBA":          "{:.3f}",
            "Exit Velo (mph)":"{:.1f}",
        })

        def _color_xwoba(val):
            try:
                v = float(val)
                if v < 0.280:
                    return "background-color:#06D6A020;color:#06D6A0;font-weight:bold"
                if v > 0.340:
                    return "background-color:#E6394620;color:#E63946;font-weight:bold"
                return "background-color:#E9C46A20;color:#E9C46A;font-weight:bold"
            except (TypeError, ValueError):
                return ""

        def _color_ld(val):
            try:
                v = float(val)
                if v > 25:
                    return "color:#E63946;font-weight:bold"
                if v < 18:
                    return "color:#06D6A0;font-weight:bold"
                return ""
            except (TypeError, ValueError):
                return ""

        def _color_gb(val):
            try:
                if float(val) > 50:
                    return "color:#06D6A0;font-weight:bold"
                return ""
            except (TypeError, ValueError):
                return ""

        styled = (
            display.style
            .map(_color_xwoba, subset=["xwOBA"])
            .map(_color_ld, subset=["LD%"])
            .map(_color_gb, subset=["GB%"])
        )
        st.dataframe(styled, hide_index=True)

    with col_chart:
        bar_colors = []
        for xw in cq_df["avg_xwoba"]:
            if xw is None or pd.isna(xw):
                bar_colors.append("#888888")
            elif xw < 0.280:
                bar_colors.append("#06D6A0")
            elif xw > 0.340:
                bar_colors.append("#E63946")
            else:
                bar_colors.append("#E9C46A")

        fig = go.Figure(go.Bar(
            x=cq_df["GB%"],
            y=cq_df["pitch_label"],
            orientation="h",
            marker_color=bar_colors,
            text=cq_df["GB%"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>GB%: %{x:.1f}%<extra></extra>",
        ))
        max_gb = cq_df["GB%"].max() if not cq_df.empty else 60
        fig.add_vline(
            x=44, line_dash="dash", line_color="#888888",
            annotation_text="MLB avg 44%", annotation_position="top right",
        )
        fig.update_layout(
            title="Ground Ball % by Pitch Type",
            xaxis=dict(
                title="GB%",
                range=[0, max(max_gb * 1.3, 60)],
                gridcolor="#1e2130",
            ),
            yaxis=dict(gridcolor="#1e2130"),
            showlegend=False,
            **dark_layout(),
        )
        st.plotly_chart(fig, width="stretch")

    # Insight lines (sample size and confidence qualifier always shown)
    valid = cq_df[cq_df["avg_xwoba"].notna()]
    if not valid.empty:
        best = valid.iloc[0]
        n_best = int(best["n_bip"])
        conf_best = " (small sample - interpret with caution)" if n_best < MIN_PITCHES_FOR_CLAIM["contact_insight"] else (" (moderate sample)" if n_best < 50 else "")
        st.markdown(
            f"💡 **{best['pitch_label']}** induces the weakest contact: "
            f"**{best['avg_xwoba']:.3f} xwOBA** on {n_best} balls in play{conf_best}."
        )
        if len(valid) >= 2:
            worst = valid.iloc[-1]
            n_worst = int(worst["n_bip"])
            conf_worst = " (small sample - interpret with caution)" if n_worst < MIN_PITCHES_FOR_CLAIM["contact_insight"] else (" (moderate sample)" if n_worst < 50 else "")
            st.markdown(
                f"⚠️ **{worst['pitch_label']}** gets hit the hardest when put in play: "
                f"**{worst['avg_xwoba']:.3f} xwOBA** on {n_worst} BIP{conf_worst}  -  "
                f"consider limiting use when behind in count."
            )


# ── Fatigue & inning-by-inning velocity ──────────────────────────────────────

def fatigue_velocity(data: pd.DataFrame, min_starts: int = 3) -> dict | None:
    """Compute inning-by-inning velocity and fatigue index.

    Returns None if fewer than min_starts unique game dates exist (not
    enough starting appearances for meaningful inning analysis).

    Return dict keys:
        "by_inning"     - DataFrame: inning, pitch_label, mean_velo, std_velo, n
        "fatigue_index" - dict {pitch_label: velo_drop_mph}
    """
    if "inning" not in data.columns or "release_speed" not in data.columns:
        return None

    n_starts = data["game_date"].nunique() if "game_date" in data.columns else 0
    if n_starts < min_starts:
        return None

    # Use the module-level FASTBALL_FAMILY constant (FF, SI, FC) so any future
    # pitch-type additions to PITCH_CATEGORY_MAP are picked up automatically.
    # (Previously a local FASTBALL_TYPES = {"FF", "SI", "FC"} shadowed the module
    # constant, silently diverging if PITCH_CATEGORY_MAP was ever updated.)

    # by_inning: all pitch types, inning <= 9, min 10 pitches per cell
    inn_data = data[data["inning"] <= 9].copy()
    rows = []
    for (inn, pt, pl), grp in inn_data.groupby(["inning", "pitch_type", "pitch_label"]):
        if len(grp) < 10:
            continue
        rows.append({
            "inning": inn,
            "pitch_type": pt,
            "pitch_label": pl,
            "mean_velo": round(grp["release_speed"].mean(), 2),
            "std_velo": round(grp["release_speed"].std(), 2),
            "n": len(grp),
        })
    by_inning = pd.DataFrame(rows)

    # fatigue_index: fastballs only, early (inn <= 3) vs late (inn >= 6)
    fatigue_index: dict[str, float] = {}
    early = data[data["inning"] <= 3]
    late = data[data["inning"] >= 6]

    for pt in FASTBALL_TYPES:
        mask = data["pitch_type"] == pt
        if not mask.any():
            continue
        pl = data.loc[mask, "pitch_label"].iloc[0]
        e_velo = early.loc[early["pitch_type"] == pt, "release_speed"].dropna()
        l_velo = late.loc[late["pitch_type"] == pt, "release_speed"].dropna()
        if len(e_velo) >= 10 and len(l_velo) >= 10:
            fatigue_index[pl] = round(float(e_velo.mean()) - float(l_velo.mean()), 2)

    _late_fb_count = len(late[late["pitch_type"].isin(FASTBALL_TYPES)])
    _early_fb_count = len(early[early["pitch_type"].isin(FASTBALL_TYPES)])
    return {"by_inning": by_inning, "fatigue_index": fatigue_index,
            "late_fastball_count": _late_fb_count,
            "early_fastball_count": _early_fb_count}


def render_fatigue_section(fatigue_data: dict | None, pitcher_name: str) -> None:
    """Render the inning-by-inning velocity & fatigue section."""
    if fatigue_data is None:
        st.info(
            "Inning-by-inning analysis requires data from at least 3 starts. "
            "Not enough starting appearances found."
        )
        return

    by_inning = fatigue_data["by_inning"]
    fatigue_index = fatigue_data["fatigue_index"]
    late_fastball_count = fatigue_data.get("late_fastball_count", 0)
    early_fastball_count = fatigue_data.get("early_fastball_count", 0)
    _enough_late = late_fastball_count >= MIN_PITCHES_FOR_CLAIM["fatigue"]

    # Pure reliever / no early-inning fastballs - empty index is expected here.
    # This MUST be checked first, before any code that iterates the index dict.
    if not fatigue_index:
        st.info(
            f"Fatigue comparison is not available for {pitcher_name} - "
            f"a pitcher needs fastballs in both early innings (1-3) and late innings (6+) "
            f"to compute a velocity drop. "
            + (
                f"Only {early_fastball_count} early-inning fastball(s) found "
                f"(typical for a relief pitcher who doesn't appear until the 7th-9th). "
                if early_fastball_count < 10
                else f"Only {late_fastball_count} late-inning fastball(s) found. "
            )
            + "Showing inning-by-inning velocity chart if available."
        )
    # Metric tiles (only when both early and late samples are sufficient)
    elif fatigue_index and _enough_late:
        cols = st.columns(max(len(fatigue_index), 1))
        for i, (pl, drop) in enumerate(fatigue_index.items()):
            if drop <= 0.5:
                dc = "normal"
            elif drop <= 1.5:
                dc = "off"
            else:
                dc = "inverse"
            cols[i].metric(f"{pl} Fatigue Index", f"{drop:+.1f} mph (inn. 1-3 vs 6+)",
                           delta_color=dc)
        st.caption(
            "Fatigue Index = average fastball velocity in innings 1-3 minus innings 6+. "
            "Negative = velocity GAINED late (rare). > 1.5 mph drop = fatigue signal."
        )
    elif fatigue_index and not _enough_late:
        st.info(
            f"Fatigue analysis requires {MIN_PITCHES_FOR_CLAIM['fatigue']}+ fastballs in "
            f"innings 6+ ({late_fastball_count} found). {pitcher_name} may not pitch deep "
            f"enough into games yet for a reliable fatigue comparison. "
            f"Showing inning-by-inning velocity chart only."
        )

    if by_inning.empty:
        st.warning("Not enough per-inning pitch data to plot velocity trend.")
        return

    # Multi-line chart - fastball family only (FF, SI, FC); fallback to top 1 by usage
    _fb_labels_in_data = by_inning[by_inning["pitch_type"].isin(FASTBALL_FAMILY)]["pitch_label"].unique().tolist() if "pitch_type" in by_inning.columns else []
    if _fb_labels_in_data:
        top_pitches = (
            by_inning[by_inning["pitch_label"].isin(_fb_labels_in_data)]
            .groupby("pitch_label")["n"].sum().nlargest(3).index.tolist()
        )
    else:
        top_pitches = (
            by_inning.groupby("pitch_label")["n"].sum().nlargest(1).index.tolist()
        )
    fig = go.Figure()
    for pl in top_pitches:
        grp = by_inning[by_inning["pitch_label"] == pl].sort_values("inning")
        fig.add_trace(go.Scatter(
            x=grp["inning"],
            y=grp["mean_velo"],
            error_y=dict(type="data", array=grp["std_velo"].tolist(), visible=True),
            mode="lines+markers",
            name=pl,
            line=dict(width=2),
            hovertemplate=(
                "Inning %{x}<br>Avg Velo: %{y:.1f} mph"
                "<extra>%{fullData.name}</extra>"
            ),
        ))
    fig.update_layout(
        title=f"{pitcher_name} - Velocity by Inning",
        xaxis_title="Inning",
        yaxis_title="Avg Velocity (mph)",
        template="plotly_dark",
        height=400,
        margin=dict(t=70, b=40, r=100),
        xaxis=dict(tickmode="linear", dtick=1),
        legend=dict(
            title="Pitch Type",
            orientation="v",
            yanchor="middle",
            y=0.5,
            x=1.01,
            xanchor="left",
        ),
    )
    st.plotly_chart(fig, width="stretch")

    # Auto-insight - only shown when late-inning sample is reliable
    if fatigue_index and _enough_late:
        worst = max(fatigue_index, key=fatigue_index.get)
        drop = fatigue_index[worst]
        if drop > 1.5:
            st.warning(
                f"Fatigue signal detected: {pitcher_name}'s {worst} loses {drop:.1f} mph on "
                f"average from innings 1-3 to innings 6+. MLB teams use a >1.5 mph threshold "
                f"as an early hook signal."
            )
        elif drop <= 0.5:
            st.success(
                f"Elite durability: {pitcher_name}'s velocity holds within {drop:.1f} mph "
                f"across innings - a sign of exceptional conditioning and repeatable mechanics."
            )
        else:
            st.info(
                f"{pitcher_name} shows a modest {drop:.1f} mph velocity decline from innings "
                f"1-3 to innings 6+, within the normal range for MLB starters."
            )


# ── First-pitch strike analysis ───────────────────────────────────────────────

def first_pitch_analysis(data: pd.DataFrame) -> dict:
    """Analyze first-pitch strategy and outcomes.

    Returns dict with keys: fps_pct, fps_mlb_avg, fps_delta,
    pitch_mix_fp, after_fps, after_fpb.
    """
    FPS_MLB_AVG = 59.8

    has_pitch_number = "pitch_number" in data.columns
    if has_pitch_number:
        fp = data[data["pitch_number"] == 1].copy()
    else:
        fp = data[(data["balls"] == 0) & (data["strikes"] == 0)].copy()

    empty_result = {
        "fps_pct": 0.0, "fps_mlb_avg": FPS_MLB_AVG, "fps_delta": round(-FPS_MLB_AVG, 1),
        "pitch_mix_fp": pd.DataFrame(), "after_fps": {}, "after_fpb": {},
    }

    if fp.empty:
        return empty_result

    # Derive type column if missing
    if "type" not in fp.columns:
        _strike_descs = {
            "called_strike", "swinging_strike", "swinging_strike_blocked",
            "foul", "foul_tip", "missed_bunt", "foul_bunt",
        }
        fp = fp.copy()
        fp["type"] = fp["description"].apply(
            lambda d: "S" if d in _strike_descs else ("X" if d == "hit_into_play" else "B")
        )

    total_fp = len(fp)
    fps_pct = round((fp["type"] == "S").sum() / total_fp * 100, 1) if total_fp > 0 else 0.0
    fps_delta = round(fps_pct - FPS_MLB_AVG, 1)

    pitch_mix_fp = (
        fp.groupby("pitch_label").size().reset_index(name="count")
        .assign(usage_pct=lambda df: (df["count"] / df["count"].sum() * 100).round(1))
        .sort_values("usage_pct", ascending=False)
        .reset_index(drop=True)
    )

    # Outcomes after first-pitch strike vs ball
    after_fps: dict = {}
    after_fpb: dict = {}

    if "events" in data.columns and "game_date" in data.columns and has_pitch_number:
        fps_ab_keys = fp.loc[fp["type"] == "S", ["game_date", "at_bat_number"]].drop_duplicates()
        fpb_ab_keys = fp.loc[fp["type"] == "B", ["game_date", "at_bat_number"]].drop_duplicates()

        def _outcome_pcts(ab_keys: pd.DataFrame) -> dict:
            merged = ab_keys.merge(data, on=["game_date", "at_bat_number"], how="left")
            terminal = (
                merged[merged["events"].notna()]
                .drop_duplicates(subset=["game_date", "at_bat_number"])
            )
            if terminal.empty:
                return {}
            n = len(terminal)
            k_pct = round(terminal["events"].isin(
                ["strikeout", "strikeout_double_play"]).sum() / n * 100, 1)
            bb_pct = round(terminal["events"].isin(
                ["walk", "intent_walk"]).sum() / n * 100, 1)
            ip_pct = round(100 - k_pct - bb_pct, 1)
            return {"K%": k_pct, "BB%": bb_pct, "In-Play%": ip_pct}

        after_fps = _outcome_pcts(fps_ab_keys)
        after_fpb = _outcome_pcts(fpb_ab_keys)

    return {
        "fps_pct": fps_pct,
        "fps_mlb_avg": FPS_MLB_AVG,
        "fps_delta": fps_delta,
        "pitch_mix_fp": pitch_mix_fp,
        "after_fps": after_fps,
        "after_fpb": after_fpb,
    }


def render_first_pitch_section(fp_data: dict, pitcher_name: str) -> None:
    """Render the first-pitch strategy section."""
    fps = fp_data["fps_pct"]
    fps_delta = fp_data["fps_delta"]
    pitch_mix_fp = fp_data["pitch_mix_fp"]
    after_fps = fp_data["after_fps"]
    after_fpb = fp_data["after_fpb"]

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "First-Pitch Strike %",
        f"{fps:.1f}%",
        delta=f"{fps_delta:+.1f}pp vs MLB avg",
        delta_color="normal" if fps_delta >= 0 else "inverse",
    )
    c2.metric("MLB Avg (2024)", "59.8%")
    if not pitch_mix_fp.empty:
        top_fp = pitch_mix_fp.iloc[0]
        c3.metric(
            "0-0 Most Used Pitch",
            top_fp["pitch_label"],
            delta=f"{top_fp['usage_pct']:.1f}% usage",
            delta_color="off",
        )

    col_pie, col_table = st.columns(2)

    with col_pie:
        if not pitch_mix_fp.empty:
            pull = [0.1] + [0.0] * (len(pitch_mix_fp) - 1)
            fig_pie = go.Figure(go.Pie(
                labels=pitch_mix_fp["pitch_label"],
                values=pitch_mix_fp["usage_pct"],
                pull=pull,
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
            ))
            fig_pie.update_layout(
                title=f"What does {pitcher_name} throw on 0-0?",
                template="plotly_dark",
                height=320,
                margin=dict(t=60, b=20, l=20, r=20),
            )
            st.plotly_chart(fig_pie, width="stretch")

    with col_table:
        if after_fps and after_fpb:
            rows = [
                {"Outcome": k, "After FP Strike": f"{after_fps.get(k, 0):.1f}%",
                 "After FP Ball": f"{after_fpb.get(k, 0):.1f}%"}
                for k in ["K%", "BB%", "In-Play%"]
            ]
            out_df = pd.DataFrame(rows)

            def _hl(row):
                try:
                    fs = float(str(row["After FP Strike"]).rstrip("%"))
                    fb = float(str(row["After FP Ball"]).rstrip("%"))
                    better_fps = (fs > fb) if row["Outcome"] in ["K%", "In-Play%"] else (fs < fb)
                    return ["", "color:#06D6A0;font-weight:bold" if better_fps else "",
                            "" if better_fps else "color:#06D6A0;font-weight:bold"]
                except Exception:
                    return ["", "", ""]

            st.markdown("**Outcome comparison: 0-1 count vs 1-0 count**")
            st.dataframe(out_df.style.apply(_hl, axis=1), hide_index=True)
        else:
            st.caption(
                "Outcome comparison requires event data "
                "(available after live Statcast fetch)."
            )

    # Auto-insight
    if fps >= 65:
        st.success(
            f"{pitcher_name} gets ahead of hitters aggressively: {fps:.1f}% first-pitch "
            f"strike rate, {fps_delta:+.1f}pp above MLB average. Working from 0-1 is "
            f"foundational to his strikeout profile."
        )
    elif fps >= 55:
        st.info(
            f"{pitcher_name}'s first-pitch strike rate of {fps:.1f}% is near the MLB "
            f"average of 59.8%."
        )
    else:
        st.warning(
            f"{pitcher_name} works from behind in counts more often than average: "
            f"{fps:.1f}% FPS rate, {fps_delta:.1f}pp below MLB average. Hitters can "
            f"sit on off-speed pitches early in counts."
        )


# ── Pitch sequencing transition matrix ───────────────────────────────────────

def pitch_sequence_matrix(
    data: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """Build a pitch-to-pitch transition matrix.

    Returns:
        matrix_pct   -  NxN DataFrame, row = current pitch, col = next pitch,
                      values are row-normalised percentages (0-100).
        top_sequences  -  top-8 two-pitch combos sorted by count desc,
                        columns: from_label, to_label, count, pct
        n_transitions  -  total pitch transitions (for caption)
    """
    required = {"at_bat_number", "pitch_number", "game_date", "pitch_type", "pitch_label"}
    if not required.issubset(data.columns):
        return pd.DataFrame(), pd.DataFrame(), 0

    df = data.sort_values(["game_date", "at_bat_number", "pitch_number"]).copy()

    df["next_pitch_type"] = df.groupby(
        ["game_date", "at_bat_number"]
    )["pitch_type"].shift(-1)
    df["next_pitch_label"] = df.groupby(
        ["game_date", "at_bat_number"]
    )["pitch_label"].shift(-1)

    seq_df = df[df["next_pitch_type"].notna()].copy()
    n_transitions = len(seq_df)

    if seq_df.empty or seq_df["pitch_label"].nunique() < 2:
        return pd.DataFrame(), pd.DataFrame(), 0

    matrix_pct = (
        pd.crosstab(
            seq_df["pitch_label"],
            seq_df["next_pitch_label"],
            normalize="index",
        ) * 100
    ).round(1)

    seq_counts = (
        seq_df.groupby(["pitch_label", "next_pitch_label"])
        .size()
        .reset_index(name="count")
    )
    seq_counts["pct"] = (
        seq_counts.groupby("pitch_label")["count"]
        .transform(lambda x: x / x.sum() * 100)
        .round(1)
    )
    seq_counts = seq_counts.rename(
        columns={"pitch_label": "from_label", "next_pitch_label": "to_label"}
    )
    top_sequences = (
        seq_counts.sort_values("count", ascending=False).head(8).reset_index(drop=True)
    )

    return matrix_pct, top_sequences, n_transitions


def render_sequencing_tab(data: pd.DataFrame, pitcher_name: str, precomputed=None) -> None:
    """Render the full Sequencing tab content."""
    if "at_bat_number" not in data.columns or "pitch_number" not in data.columns:
        st.warning(
            "Sequencing data unavailable for cached data. "
            "Search this pitcher again to load the full dataset."
        )
        return

    if precomputed is not None:
        matrix_pct, top_seq, n_transitions = precomputed
    else:
        matrix_pct, top_seq, n_transitions = pitch_sequence_matrix(data)

    if matrix_pct.empty or matrix_pct.shape[0] < 2:
        st.warning(
            "Not enough sequential pitch data to build a transition "
            "matrix for this pitcher."
        )
        return

    st.caption(
        "A pitcher rarely throws pitches randomly - they follow patterns. "
        "This matrix shows what pitch comes NEXT after each pitch type, "
        "as a percentage. Example: if the FF -> SL cell shows 38%, it "
        "means after a fastball, this pitcher throws a slider 38% of "
        "the time. Advance scouts use this to predict what's coming next."
    )

    # ── Transition heatmap ────────────────────────────────────────────────
    fig = go.Figure(go.Heatmap(
        z=matrix_pct.values,
        x=matrix_pct.columns.tolist(),
        y=matrix_pct.index.tolist(),
        colorscale="Blues",
        zmin=0,
        zmax=100,
        text=(matrix_pct.round(1).astype(str) + "%").values,
        texttemplate="%{text}",
        textfont={"size": 13},
        hovertemplate=(
            "After <b>%{y}</b> → throws <b>%{x}</b><br>%{z:.1f}% of the time"
            "<extra></extra>"
        ),
        showscale=True,
        colorbar=dict(title="Usage %", ticksuffix="%"),
    ))
    fig.update_layout(
        title=f"{pitcher_name}  -  Pitch Sequencing Transition Matrix",
        xaxis_title="Next Pitch Thrown",
        yaxis_title="Current Pitch",
        template="plotly_dark",
        height=480,
        margin=dict(l=140, r=40, t=60, b=120),
        xaxis=dict(side="bottom", tickangle=-30),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Based on {n_transitions:,} pitch transitions this season.")

    # ── Top two-pitch combinations ────────────────────────────────────────
    st.subheader("Most Common Two-Pitch Combinations")
    col_tbl, col_chart = st.columns(2)

    with col_tbl:
        disp = top_seq[["from_label", "to_label", "count", "pct"]].copy()
        disp.columns = ["Current Pitch", "Next Pitch", "Count", "Usage %"]
        disp["Usage %"] = disp["Usage %"].apply(lambda v: f"{v:.1f}%")
        st.dataframe(disp, hide_index=True)

    with col_chart:
        labels = top_seq["from_label"] + " → " + top_seq["to_label"]
        fig2 = go.Figure(go.Bar(
            x=top_seq["pct"],
            y=labels,
            orientation="h",
            marker=dict(color=top_seq["pct"], colorscale="Blues", showscale=False),
            text=top_seq["pct"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>%{x:.1f}% of the time<extra></extra>",
        ))
        fig2.update_layout(
            title="Top Pitch-to-Pitch Sequences",
            xaxis_title="Usage %",
            yaxis=dict(autorange="reversed"),
            template="plotly_dark",
            height=320,
            margin=dict(l=10, r=70, t=50, b=40),
        )
        st.plotly_chart(fig2, width="stretch")

    # ── Auto-insight callout ──────────────────────────────────────────────
    if top_seq.empty:
        return

    dominant = top_seq.iloc[0]

    if dominant["count"] < MIN_PITCHES_FOR_CLAIM["sequencing_cell"]:
        st.caption(
            f"Insufficient transition data for reliable sequencing insights "
            f"(minimum {MIN_PITCHES_FOR_CLAIM['sequencing_cell']} transitions per pitch pair)."
        )
        return

    non_fb_follow = top_seq[
        (top_seq["from_label"] != top_seq["to_label"]) &
        (~top_seq["to_label"].isin(FASTBALL_LABELS)) &
        (top_seq["count"] >= MIN_PITCHES_FOR_CLAIM["sequencing_cell"])
    ]
    if not non_fb_follow.empty:
        surprising = non_fb_follow.nlargest(1, "pct").iloc[0]
        predictable_text = (
            f"📌 **Most predictable off-speed sequence:** A "
            f"**{surprising['to_label']}** after a **{surprising['from_label']}** "
            f"occurs {surprising['pct']:.0f}% of the time "
            f"({int(surprising['count'])} occurrences)  -  "
            f"the pattern a hitter would sit on."
        )
    else:
        cross = top_seq[
            (top_seq["from_label"] != top_seq["to_label"]) &
            (top_seq["count"] >= MIN_PITCHES_FOR_CLAIM["sequencing_cell"])
        ]
        surprising = (cross if not cross.empty else top_seq).nlargest(1, "pct").iloc[0]
        predictable_text = (
            f"📌 **Most predictable follow-up:** A **{surprising['to_label']}** after a "
            f"**{surprising['from_label']}** occurs {surprising['pct']:.0f}% of the time "
            f"({int(surprising['count'])} occurrences)  -  "
            f"the combination a hitter or advance scout would look for."
        )

    st.info(
        f"🔀 **Most common sequence:** After a **{dominant['from_label']}**, "
        f"{pitcher_name} throws a **{dominant['to_label']}** "
        f"{dominant['pct']:.0f}% of the time ({dominant['count']} occurrences).\n\n"
        + predictable_text
    )


# ── Count insight helper (shared by Overview + Count Tendencies tabs) ─────────

def _compute_count_insight(vdata: pd.DataFrame, eff_split: pd.DataFrame,
                            display_name: str) -> str | None:
    """Return the auto-insight callout string or None if none qualifies (Δ < 5pp)."""
    if "description" not in vdata.columns or "count_label" not in vdata.columns:
        return None
    sea_whiff: dict[str, float] = {}
    if not eff_split.empty and "Whiff%" in eff_split.columns:
        ptl = vdata.groupby("pitch_type")["pitch_label"].first().to_dict()
        for _, r in eff_split.iterrows():
            sea_whiff[ptl.get(r["pitch_type"], "")] = float(r["Whiff%"])
    best_delta, best_combo = -999.0, None
    for cnt in vdata["count_label"].unique():
        cg = vdata[vdata["count_label"] == cnt]
        if len(cg) < MIN_PITCHES_FOR_CLAIM["count_insight"]:   # 20
            continue
        for pl, pg in cg.groupby("pitch_label"):
            if len(pg) < MIN_PITCHES_FOR_CLAIM["count_pitch_cell"]:  # 10
                continue
            sw = pg[pg["description"].isin(SWING_EVENTS)]
            wh = pg[pg["description"].isin(WHIFF_EVENTS)]
            if len(sw) == 0:
                continue
            cw = len(wh) / len(sw) * 100
            sw_avg = sea_whiff.get(str(pl), cw)
            dlt = cw - sw_avg
            if dlt > best_delta:
                best_delta = dlt
                best_combo = (cnt, str(pl), cw, sw_avg, dlt, len(pg))
    if best_combo and best_combo[4] >= 10.0:   # raised from 5pp to 10pp
        bc_cnt, bc_pl, bc_cw, bc_sw, bc_dlt, bc_n = best_combo
        last = display_name.split()[-1]
        return (
            f"⚡ **In {bc_cnt} counts,** {last}'s **{bc_pl}** "
            f"generates a **{bc_cw:.0f}% Whiff rate**  -  "
            f"**{bc_dlt:.0f} pp above** their season average "
            f"for {bc_pl}s ({bc_sw:.0f}% overall, based on {bc_n} pitches). "
            f"*(→ see Count Tendencies tab for full breakdown)*"
        )
    return None


def _compute_actionable_recommendation(
    data: pd.DataFrame,
    vdata: pd.DataFrame,
    eff_split: pd.DataFrame,
    display_name: str,
) -> str | None:
    """Return a data-driven recommendation based on platoon splits, or None/low-sample string.

    Requires ≥80 pitches vs each batter hand to report.  Returns None if columns are missing.
    The recommendation is purely internal: it compares THIS pitcher's own splits.
    """
    MIN_N_HAND = 80       # minimum pitches vs each hand for a trustworthy platoon split
    MIN_SPLIT_PP = 15     # minimum whiff% delta (percentage points) to surface

    if "stand" not in data.columns or "description" not in data.columns:
        return None

    lhb_all = data[data["stand"] == "L"]
    rhb_all = data[data["stand"] == "R"]

    if len(lhb_all) < MIN_N_HAND or len(rhb_all) < MIN_N_HAND:
        return "insufficient_sample"

    def _whiff_by_pitch(df: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for pl, grp in df.groupby("pitch_label"):
            if len(grp) < 20:
                continue
            swings = grp["description"].isin(SWING_EVENTS).sum()
            whiffs = grp["description"].isin(WHIFF_EVENTS).sum()
            if swings == 0:
                continue
            rows.append({
                "pitch_label": pl,
                "n": len(grp),
                "whiff_pct": whiffs / swings * 100,
            })
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    lhb_eff = _whiff_by_pitch(lhb_all)
    rhb_eff = _whiff_by_pitch(rhb_all)
    if lhb_eff.empty or rhb_eff.empty:
        return "insufficient_sample"

    merged = lhb_eff.merge(rhb_eff, on="pitch_label", suffixes=("_lhb", "_rhb"))
    if merged.empty:
        return "insufficient_sample"

    merged["delta"] = merged["whiff_pct_lhb"] - merged["whiff_pct_rhb"]
    merged["abs_delta"] = merged["delta"].abs()

    significant = merged[merged["abs_delta"] >= MIN_SPLIT_PP]
    if significant.empty:
        return None  # no large platoon split - no recommendation to surface

    best = significant.nlargest(1, "abs_delta").iloc[0]
    pitch = best["pitch_label"]
    delta = float(best["delta"])

    if delta > 0:
        good_hand, bad_hand = "LHB", "RHB"
        good_whiff, bad_whiff = float(best["whiff_pct_lhb"]), float(best["whiff_pct_rhb"])
        good_n, bad_n = int(best["n_lhb"]), int(best["n_rhb"])
        good_data = lhb_all
    else:
        good_hand, bad_hand = "RHB", "LHB"
        good_whiff, bad_whiff = float(best["whiff_pct_rhb"]), float(best["whiff_pct_lhb"])
        good_n, bad_n = int(best["n_rhb"]), int(best["n_lhb"])
        good_data = rhb_all

    # Usage comparison: how often is this pitch thrown in that matchup vs overall?
    total = max(len(data), 1)
    overall_usage_pct = len(data[data["pitch_label"] == pitch]) / total * 100
    hand_total = max(len(good_data), 1)
    hand_usage_pct = len(good_data[good_data["pitch_label"] == pitch]) / hand_total * 100

    last = display_name.split()[-1]
    usage_comment = (
        f"Currently used {hand_usage_pct:.0f}% vs {good_hand} vs {overall_usage_pct:.0f}% overall - "
        + ("consider increasing usage in this matchup." if hand_usage_pct < overall_usage_pct
           else "usage is already elevated in this matchup.")
    )
    return (
        f"**{last}'s {pitch}** generates **{good_whiff:.0f}% Whiff vs {good_hand}** "
        f"vs only **{bad_whiff:.0f}% vs {bad_hand}** - a **{abs(delta):.0f}pp split** "
        f"(n={good_n} vs {good_hand}, n={bad_n} vs {bad_hand}). {usage_comment}"
    )


# ── Matchup Prediction ────────────────────────────────────────────────────────

def matchup_prediction(
    data: pd.DataFrame,
    count_label: str,
    batter_hand: str,
    pitcher_name: str = "",
) -> dict:
    """Return pitch probability distribution for a specific count/handedness situation."""
    filtered = data.copy()
    if "count_label" in filtered.columns:
        filtered = filtered[filtered["count_label"] == count_label]

    if batter_hand != "Both" and "stand" in filtered.columns:
        hand_code = "L" if batter_hand == "Left" else "R"
        filtered = filtered[filtered["stand"] == hand_code]

    sample_size = len(filtered)
    if sample_size < 15:
        return {"predictions": [], "sample_size": sample_size, "too_few": True}

    rows = []
    for pt, grp in filtered.groupby("pitch_label"):
        count = len(grp)
        pct = count / sample_size * 100
        desc = grp["description"] if "description" in grp.columns else pd.Series(dtype=str)
        swings = desc.isin(SWING_EVENTS).sum()
        whiffs = desc.isin(WHIFF_EVENTS).sum()
        csw_count = desc.isin(CSW_EVENTS).sum()
        whiff_pct = round(float(whiffs) / float(swings) * 100, 1) if swings > 0 else 0.0
        csw_pct = round(float(csw_count) / float(count) * 100, 1) if count > 0 else 0.0
        rows.append({
            "pitch_label": pt,
            "count": count,
            "pct": round(pct, 1),
            "whiff_pct": whiff_pct,
            "csw_pct": csw_pct,
        })

    rows.sort(key=lambda x: x["pct"], reverse=True)

    if not rows:
        return {"predictions": [], "sample_size": sample_size, "too_few": True}

    dominant = rows[0]
    second = rows[1] if len(rows) > 1 else None

    if dominant["pct"] >= 50:
        insight = (
            f"In {count_label} counts, {dominant['pitch_label']} is thrown MORE THAN HALF "
            f"the time ({dominant['pct']:.0f}%). A hitter should be sitting on this pitch."
        )
    elif dominant["pct"] >= 35:
        second_part = (
            f" Second most common: {second['pitch_label']} ({second['pct']:.0f}%)."
            if second else ""
        )
        insight = (
            f"{dominant['pitch_label']} is the clear primary pitch in {count_label} counts "
            f"({dominant['pct']:.0f}% usage).{second_part}"
        )
    else:
        name = pitcher_name or "this pitcher"
        insight = (
            f"No dominant pitch in {count_label} counts - "
            f"{name} keeps hitters guessing with an even distribution across pitch types."
        )

    return {
        "predictions": rows,
        "sample_size": sample_size,
        "dominant": dominant["pitch_label"],
        "insight": insight,
        "too_few": False,
    }


def render_matchup_tab(data: pd.DataFrame, pitcher_name: str) -> None:
    """Render the Matchup Prediction tab."""
    st.markdown("### What pitch is coming next?")
    st.caption(
        "Select a count and batter handedness to see the historical "
        "pitch distribution for this pitcher in that exact situation. "
        "This is how advance scouts prepare hitters before a game."
    )

    if "count_label" not in data.columns:
        st.warning("Count data not available for this dataset.")
        return

    count_options = [
        "0-0", "0-1", "0-2", "1-0", "1-1", "1-2",
        "2-0", "2-1", "2-2", "3-0", "3-1", "3-2",
    ]

    col1, col2, col3 = st.columns(3)
    with col1:
        selected_count = st.selectbox("Count (Balls-Strikes)", count_options, index=4)
    with col2:
        selected_hand = st.radio(
            "Batter Handedness", ["Both", "Left", "Right"], horizontal=True
        )

    pred = matchup_prediction(data, selected_count, selected_hand, pitcher_name)

    with col3:
        st.metric("Pitches in situation", pred["sample_size"])

    if pred.get("too_few"):
        st.warning(
            f"Only {pred['sample_size']} pitches found for this situation - not enough "
            f"data for a reliable prediction. Try a different count or 'Both' for handedness."
        )
        return

    # donut chart
    fig = go.Figure(go.Pie(
        labels=[p["pitch_label"] for p in pred["predictions"]],
        values=[p["pct"] for p in pred["predictions"]],
        hole=0.5,
        textinfo="label+percent",
        textfont=dict(size=14),
        hovertemplate="%{label}<br>Usage: %{value:.1f}%<br><extra></extra>",
        pull=[0.08] + [0] * (len(pred["predictions"]) - 1),
    ))
    fig.update_layout(
        title=(
            f"{pitcher_name} - Pitch Mix in {selected_count} counts "
            f"({selected_hand} batters)"
        ),
        template="plotly_dark",
        height=420,
        annotations=[dict(
            text=f"{pred['dominant']}<br>most likely",
            x=0.5,
            y=0.5,
            font_size=14,
            showarrow=False,
        )],
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
    )
    st.plotly_chart(fig, width='stretch')

    # effectiveness table
    tbl = pd.DataFrame(pred["predictions"])[["pitch_label", "pct", "whiff_pct", "csw_pct"]]
    tbl.columns = ["Pitch", "Usage %", "Whiff%", "CSW%"]
    tbl_fmt = {"Usage %": "{:.1f}", "Whiff%": "{:.1f}", "CSW%": "{:.1f}"}
    tbl_display = _format_display_df(tbl, tbl_fmt)
    max_whiff = tbl["Whiff%"].max()

    def _highlight_best_whiff(row):
        try:
            w = float(str(row["Whiff%"]).rstrip("%"))
        except (ValueError, TypeError):
            w = 0.0
        if w == max_whiff and max_whiff > 0:
            return ["background-color:#06D6A020;color:#06D6A0;font-weight:bold"] * len(row)
        return [""] * len(row)

    st.dataframe(tbl_display.style.apply(_highlight_best_whiff, axis=1), hide_index=True)
    st.caption(
        "Whiff% and CSW% shown for this specific count only, not season averages. "
        "High Whiff% in a specific count reveals the pitcher's go-to out pitch."
    )

    st.info(f"🎯 {pred['insight']}")

    _MIN_SCOUT = 10    # suppress entirely below this
    _CONF_SCOUT = 20   # no caveat above this
    _eligible = [p for p in pred["predictions"] if p.get("count", 0) >= _MIN_SCOUT]
    two_strike = selected_count.split("-")[1] == "2"
    if not _eligible:
        st.caption(
            f"No pitch in {selected_count} counts has enough pitches "
            f"(minimum {_MIN_SCOUT}) for a reliable effectiveness claim."
        )
    else:
        most_effective = max(_eligible, key=lambda x: x["whiff_pct"])
        me_n = most_effective.get("count", 0)
        me_conf = (
            f" ({me_n} pitches - small sample, interpret carefully)" if me_n < _CONF_SCOUT
            else f" ({me_n} pitches)"
        )
        st.success(
            f"**Scout's note:** The most effective pitch in {selected_count} counts is the "
            f"**{most_effective['pitch_label']}** with a "
            f"{most_effective['whiff_pct']:.0f}% Whiff rate{me_conf}. "
            + (
                "Look for this pitch in two-strike counts."
                if two_strike
                else "Watch for this in the sequence."
            )
        )


# ── Admin batch verification panel ───────────────────────────────────────────

def _run_full_diagnostic(pitcher_name: str, year: int) -> dict:
    """Run the full PitchIQ pipeline for one pitcher-year and collect all claims."""
    result: dict = {"pitcher": pitcher_name, "year": year, "status": "OK",
                    "requested_season": year}  # always populated, even on FAILED

    raw = load_pitcher_data(pitcher_name, year)
    if raw is None:
        result["status"] = "FAILED"
        result["error"] = "load_pitcher_data returned None"
        result["failure_detail"] = (
            f"{pitcher_name} - no data found for {year} or prior seasons."
        )
        return result

    data, display_name, _pid, fallback_meta = raw
    result["display_name"] = display_name
    result["requested_season"] = fallback_meta["requested_season"]
    result["actual_season_used"] = fallback_meta["actual_season_used"]
    result["fallback_occurred"] = fallback_meta["fallback_occurred"]
    result["fallback_reason"] = fallback_meta["fallback_reason"]
    result["total_pitches"] = len(data)
    result["pitch_types"] = int(data["pitch_type"].nunique()) if "pitch_type" in data.columns else 0

    eff = compute_effectiveness(data)
    grades_df = pitch_grades(data, eff)
    result["sanity_violations"] = _grade_sanity_check(grades_df)

    # Derived metrics needed for narrative
    team, hand = get_pitcher_meta(data)
    hand_label = "RHP" if hand == "R" else "LHP"
    fastballs = data[data["pitch_type"].isin(["FF", "SI"])] if "pitch_type" in data.columns else pd.DataFrame()
    avg_fb_velo = fastballs["release_speed"].mean() if not fastballs.empty and "release_speed" in fastballs.columns else None
    overall_csw = None
    if not eff.empty and "CSW%" in eff.columns:
        total_n = data.groupby("pitch_type").size()
        csw_vals = eff.set_index("pitch_type")["CSW%"]
        weights = total_n / total_n.sum()
        overall_csw = round((csw_vals * weights).sum(), 1)

    insight_str = None
    if "count_label" in data.columns and "description" in data.columns:
        insight_str = _compute_count_insight(data, eff, display_name)
    result["count_insight"] = insight_str

    # Narrative - All Batters
    result["narrative_all"] = generate_narrative(
        display_name=display_name, hand_label=hand_label, team=team,
        grades_df=grades_df, eff_df=eff, avg_fb_velo=avg_fb_velo,
        insight_str=insight_str, platoon_label="All Batters",
        vdata=data, overall_csw_pct=overall_csw,
    )

    # Narratives - platoon splits
    for hand_filter, col_val in [("vs LHB", "L"), ("vs RHB", "R")]:
        if "stand" not in data.columns:
            continue
        hdata = data[data["stand"] == col_val]
        if len(hdata) < 50:
            continue
        heff = compute_effectiveness(hdata)
        hgrades = pitch_grades(hdata, heff)
        key = hand_filter.replace(" ", "_")
        result[f"narrative_{key}"] = generate_narrative(
            display_name=display_name, hand_label=hand_label, team=team,
            grades_df=hgrades, eff_df=heff, avg_fb_velo=avg_fb_velo,
            insight_str=None, platoon_label=hand_filter,
            vdata=hdata, overall_csw_pct=overall_csw,
        )
        result[f"sanity_violations_{key}"] = _grade_sanity_check(hgrades)

    # Best / needs-work pitch (simple version from grades table)
    if not grades_df.empty:
        _whiff_map = {r["pitch_type"]: r.get("Whiff%", None) for r in eff.to_dict("records")} if not eff.empty and "pitch_type" in eff.columns else {}
        _pt_map = data.groupby("pitch_label")["pitch_type"].first().to_dict() if "pitch_label" in data.columns and "pitch_type" in data.columns else {}
        _ranked = grades_df.copy()
        _ranked["_rank"] = _ranked.apply(_overall_grade_from_row, axis=1).map(_GRADE_SCORE).fillna(2)
        best_row = _ranked.nlargest(1, "_rank").iloc[0]
        worst_row = _ranked.nsmallest(1, "_rank").iloc[0]
        def _fmt_pitch(row, show_weakest=False):
            p = row.get("Pitch", "")
            g = _overall_grade_from_row(row)
            pt = _pt_map.get(p, "")
            if show_weakest:
                ws = _GRADE_SCORE.get(str(row.get("Whiff Grade", "")), 99)
                cs = _GRADE_SCORE.get(str(row.get("CSW Grade", "")), 99)
                vs = _GRADE_SCORE.get(str(row.get("Velo Grade", "")), 99)
                best_s = min(ws, cs, vs)
                if best_s == ws and row.get("Whiff%") is not None:
                    return f"{p} ({g} - {row['Whiff%']:.0f}% Whiff)"
                if best_s == cs and row.get("CSW%") is not None:
                    return f"{p} ({g} - {row['CSW%']:.0f}% CSW)"
                if best_s == vs and row.get("Velo") is not None:
                    return f"{p} ({g} - {row['Velo']:.1f} mph Velo)"
            w = _whiff_map.get(pt)
            return f"{p} ({g} - {w:.0f}% Whiff)" if w is not None else f"{p} ({g})"
        result["best_pitch"] = _fmt_pitch(best_row)
        # Fix: if best and worst are the same pitch (single-pitch arsenal or tied scores),
        # try to pick the next-worst different pitch instead.
        if best_row.get("Pitch") == worst_row.get("Pitch"):
            _other_ranked = _ranked[_ranked["Pitch"] != best_row.get("Pitch")]
            if not _other_ranked.empty:
                worst_row = _other_ranked.nsmallest(1, "_rank").iloc[0]
                result["needs_work_pitch"] = _fmt_pitch(worst_row, show_weakest=True)
            else:
                result["needs_work_pitch"] = "N/A - Single pitch arsenal"
        else:
            result["needs_work_pitch"] = _fmt_pitch(worst_row, show_weakest=True)

    # Contact quality
    cq_df = contact_quality(data)
    if not cq_df.empty and "avg_xwoba" in cq_df.columns:
        valid_cq = cq_df[cq_df["avg_xwoba"].notna()]
        if not valid_cq.empty:
            best_cq = valid_cq.iloc[0]
            result["contact_quality_best"] = f"{best_cq['pitch_label']}: {best_cq['avg_xwoba']:.3f} xwOBA on {int(best_cq['n_bip'])} BIP"
            if len(valid_cq) >= 2:
                worst_cq = valid_cq.iloc[-1]
                result["contact_quality_worst"] = f"{worst_cq['pitch_label']}: {worst_cq['avg_xwoba']:.3f} xwOBA on {int(worst_cq['n_bip'])} BIP"

    # Sequencing
    _mat, top_seq, n_trans = pitch_sequence_matrix(data)
    result["sequencing_n_transitions"] = n_trans
    result["sequencing_dominant"] = top_seq.iloc[0].to_dict() if not top_seq.empty else None

    # Fatigue
    fatigue = fatigue_velocity(data)
    result["fatigue_index"] = fatigue.get("fatigue_index") if fatigue else None
    result["fatigue_late_count"] = fatigue.get("late_fastball_count", 0) if fatigue else 0
    result["fatigue_early_count"] = fatigue.get("early_fastball_count", 0) if fatigue else 0
    # fatigue_suppressed = True when no meaningful comparison could be shown.
    # This means: no fatigue data at all, OR the computed index is empty
    # (pure reliever with no early-inning fastballs), OR insufficient late
    # innings. Matching the exact same logic as render_fatigue_section().
    result["fatigue_suppressed"] = (
        fatigue is None
        or not fatigue.get("fatigue_index")  # empty dict {} for pure relievers
        or fatigue.get("late_fastball_count", 0) < MIN_PITCHES_FOR_CLAIM["fatigue"]
    )

    # First-pitch strike
    fp = first_pitch_analysis(data)
    result["fps_pct"] = fp.get("fps_pct")
    result["fps_sample_warning"] = fp.get("too_few", False)

    # Matchup predictions for sample counts
    for count in ["0-0", "1-1", "0-2", "3-0"]:
        pred = matchup_prediction(data, count, "Both")
        result[f"matchup_{count}_n"] = pred.get("sample_size", 0)
        result[f"matchup_{count}_too_few"] = pred.get("too_few", False)
        if pred.get("predictions"):
            top_p = max(pred["predictions"], key=lambda x: x["whiff_pct"])
            result[f"matchup_{count}_top"] = f"{top_p['pitch_label']} {top_p['whiff_pct']:.0f}% Whiff (n={top_p.get('count',0)})"

    return result


def _build_summary_csv(results: list) -> bytes:
    rows = []
    for r in results:
        sv = r.get("sanity_violations") or []
        row = {
            "pitcher": r.get("pitcher"),
            "year": r.get("year"),
            "requested_season": r.get("requested_season"),
            "actual_season_used": r.get("actual_season_used"),
            "fallback_occurred": r.get("fallback_occurred"),
            "fallback_reason": r.get("fallback_reason"),
            "status": r.get("status", "OK"),
            "total_pitches": r.get("total_pitches"),
            "pitch_types": r.get("pitch_types"),
            "sanity_violations_count": len(sv),
            "sanity_violations_detail": "; ".join(sv),
            "best_pitch": r.get("best_pitch"),
            "needs_work_pitch": r.get("needs_work_pitch"),
            "count_insight": r.get("count_insight"),
            "fps_pct": r.get("fps_pct"),
            "fps_low_sample_flag": r.get("fps_sample_warning"),
            "sequencing_n_transitions": r.get("sequencing_n_transitions"),
            "fatigue_early_count": r.get("fatigue_early_count"),
            "fatigue_late_count": r.get("fatigue_late_count"),
            "fatigue_suppressed": r.get("fatigue_suppressed"),
            "contact_quality_best": r.get("contact_quality_best"),
            "contact_quality_worst": r.get("contact_quality_worst"),
            "failure_detail": r.get("failure_detail"),
        }
        for count in ["0-0", "1-1", "0-2", "3-0"]:
            row[f"matchup_{count}_n"] = r.get(f"matchup_{count}_n")
            row[f"matchup_{count}_too_few"] = r.get(f"matchup_{count}_too_few")
            row[f"matchup_{count}_top"] = r.get(f"matchup_{count}_top")
        rows.append(row)
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8")


def _build_narrative_dump(results: list) -> str:
    lines = []
    for r in results:
        sep = "=" * 70
        lines += [sep, f"{r.get('pitcher')} - {r.get('year')}", sep]
        if r.get("status") == "FAILED":
            lines += [f"FAILED: {r.get('error', 'unknown')}", ""]
            continue
        lines += ["--- NARRATIVE (All Batters) ---", r.get("narrative_all", "N/A"), ""]
        for hand_key in ["vs_LHB", "vs_RHB"]:
            if f"narrative_{hand_key}" in r:
                lines += [f"--- NARRATIVE ({hand_key}) ---", r[f"narrative_{hand_key}"], ""]
        lines += ["--- COUNT INSIGHT ---", str(r.get("count_insight") or "Suppressed / N/A"), ""]
        lines += [
            "--- CONTACT QUALITY ---",
            f"Best:  {r.get('contact_quality_best', 'N/A')}",
            f"Worst: {r.get('contact_quality_worst', 'N/A')}",
            "",
        ]
        lines += [
            "--- SEQUENCING ---",
            f"Dominant transition: {r.get('sequencing_dominant')}",
            f"Total transitions: {r.get('sequencing_n_transitions')}",
            "",
        ]
        lines += [
            "--- FATIGUE ---",
            f"Fatigue index: {r.get('fatigue_index')}",
            f"Late fastballs: {r.get('fatigue_late_count')}  |  Suppressed: {r.get('fatigue_suppressed')}",
            "",
        ]
        lines.append("--- MATCHUP (sample counts) ---")
        for count in ["0-0", "1-1", "0-2", "3-0"]:
            lines.append(
                f"{count}: n={r.get(f'matchup_{count}_n',0)}, "
                f"too_few={r.get(f'matchup_{count}_too_few')}, "
                f"top={r.get(f'matchup_{count}_top','N/A')}"
            )
        sv = r.get("sanity_violations") or []
        if sv:
            lines += ["", "--- GRADE SANITY VIOLATIONS ---"] + [f"  - {v}" for v in sv]
        lines += ["", ""]
    return "\n".join(lines)


def render_admin_panel():
    st.title("PitchIQ Admin - Batch Claim Verification")
    st.caption(
        "Internal debugging tool. Not visible to normal users. "
        "Paste pitcher names and seasons below, run the batch, "
        "and download the verification report."
    )
    st.markdown(
        "Enter one pitcher per line, format: `Pitcher Name, Year`\n\n"
        "Example:\n```\nPaul Skenes, 2025\nGerrit Cole, 2025\n"
        "Freddy Peralta, 2025\nLogan Webb, 2025\n```"
    )

    batch_input = st.text_area(
        "Pitcher batch list", height=200,
        placeholder="Paul Skenes, 2025\nGerrit Cole, 2025\n..."
    )
    run_batch = st.button("Run Batch Verification", type="primary")

    if run_batch and batch_input.strip():
        lines_in = [l.strip() for l in batch_input.strip().split("\n") if l.strip()]
        pairs = []
        for line in lines_in:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 2:
                try:
                    pairs.append((parts[0], int(parts[1])))
                except ValueError:
                    st.warning(f"Skipping malformed line: '{line}'")
            else:
                st.warning(f"Skipping malformed line: '{line}'")

        if not pairs:
            st.error("No valid pitcher-year pairs found.")
            return

        progress = st.progress(0, text="Starting batch...")
        results = []
        for i, (name, yr) in enumerate(pairs):
            progress.progress(
                (i + 1) / len(pairs),
                text=f"Processing {name} ({yr})... [{i + 1}/{len(pairs)}]",
            )
            try:
                results.append(_run_full_diagnostic(name, yr))
            except Exception as exc:
                results.append({
                    "pitcher": name, "year": yr,
                    "error": str(exc), "status": "FAILED",
                })
        progress.empty()

        n_ok = sum(1 for r in results if r.get("status") != "FAILED")
        n_fail = len(results) - n_ok
        st.success(f"Batch complete: {n_ok} succeeded, {n_fail} failed.")

        csv_bytes = _build_summary_csv(results)
        narrative_text = _build_narrative_dump(results)

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Download Summary CSV", csv_bytes,
                file_name="pitchiq_claims_summary.csv", mime="text/csv",
            )
        with col2:
            st.download_button(
                "Download Full Narrative Dump", narrative_text.encode("utf-8"),
                file_name="pitchiq_claims_narrative.txt", mime="text/plain",
            )

        flagged = [r for r in results if r.get("sanity_violations") or r.get("status") == "FAILED"]
        if flagged:
            st.error(f"{len(flagged)} pitcher(s) have flagged issues:")
            for r in flagged:
                with st.expander(f"{r.get('pitcher')} ({r.get('year')})"):
                    if r.get("status") == "FAILED":
                        st.code(r.get("error"))
                    for v in r.get("sanity_violations") or []:
                        st.write(f"- {v}")
        else:
            st.success("No grade sanity violations found in this batch.")

        st.markdown("### Inline preview")
        st.dataframe(
            pd.DataFrame([{
                "Pitcher": r.get("pitcher"),
                "Requested": r.get("requested_season", r.get("year")),
                "Actual Season": r.get("actual_season_used", r.get("year")),
                "Fallback?": r.get("fallback_occurred", False),
                "Status": r.get("status", "OK"),
                "Pitches": r.get("total_pitches"),
                "Violations": len(r.get("sanity_violations") or []),
                "Best": r.get("best_pitch"),
                "FPS%": r.get("fps_pct"),
                "Fatigue Suppressed": r.get("fatigue_suppressed"),
            } for r in results]),
            hide_index=True,
        )


# ── Main app ──────────────────────────────────────────────────────────────────

def main():
    import warnings
    warnings.filterwarnings("ignore")

    # ── Admin gate: ?admin=true shows the batch verification panel ────────────
    query_params = st.query_params
    if query_params.get("admin") == "true":
        render_admin_panel()
        return

    with st.sidebar:
        st.header("Search")
        pitcher_name = st.text_input(
            "Pitcher Name",
            value="Paul Skenes",
            placeholder="e.g. Gerrit Cole",
        )
        season = st.selectbox(
            "Season",
            [2026, 2025, 2024],
            index=1,
            format_func=lambda y: f"{y} (→ loads 2025)" if y == 2026 else str(y),
            help=(
                "2026 Statcast data is not yet available. Selecting 2026 automatically "
                "loads the pitcher's most recent 2025 season instead."
            ),
        )
        search = st.button("Analyze", type="primary")

        # ── BUG FIX: update displayed state IMMEDIATELY on click, before the
        # warning check below reads it.  Without this, the check runs with the
        # OLD session_state values on the very run where Analyze was clicked,
        # so the warning only clears on the second click (stale read-then-write).
        if search:
            st.session_state["displayed_pitcher"] = pitcher_name
            st.session_state["displayed_season"] = season

        st.markdown("---")
        if "display_name" in st.session_state:
            dn = st.session_state.get("displayed_pitcher", st.session_state["display_name"])
            ds = st.session_state.get("displayed_season", season)
            _inputs_changed = (
                pitcher_name != st.session_state.get("displayed_pitcher", pitcher_name)
                or season != st.session_state.get("displayed_season", season)
            )
            if _inputs_changed:
                st.warning(
                    f"\u26a0\ufe0f **Showing outdated data:**\n"
                    f"**{dn} ({ds})**\n\n"
                    "You changed the search inputs. Click **Analyze** to update the report."
                )
            else:
                st.success(
                    f"\U0001f4ca **Currently showing:**\n"
                    f"**{dn} ({ds})**\n\n"
                    "Type any pitcher name above to load a new report."
                )
        else:
            st.markdown(
                """
                **Data source:** MLB Statcast via pybaseball  
                **Charts:** Plotly  
                **Note:** 2026 falls back to 2025 if no data
                """
            )

        with st.expander("📖 Metric Glossary", expanded=False):
            st.markdown("""
**Whiff%** - Percentage of swings that completely miss the ball.
Higher = harder to make contact with.

**CSW%** - Called Strike + Whiff %. Every pitch that results in
a strike (whether swung at or not) divided by total pitches.
The best single measure of per-pitch dominance.

**Chase%** - How often batters swing at pitches OUTSIDE the
strike zone. Higher = pitcher is more deceptive.

**xwOBA** - Expected Weighted On-Base Average. Measures the
quality of contact allowed, based on launch angle and exit
velocity. Lower = weaker contact allowed. MLB average ~0.320.

**Platoon Split** - Performance difference vs left-handed
batters (LHB) vs right-handed batters (RHB). Most pitchers
are more effective against same-handed hitters.

**FPS%** - First-Pitch Strike %. Getting ahead 0-1 vs falling
behind 1-0 dramatically changes a pitcher's effectiveness.

**Z-Score** - How many standard deviations above or below the
MLB average a metric falls. Used to assign letter grades.
            """)

    if not search and "pitcher_data" not in st.session_state:
        result = load_pitcher_data("Paul Skenes", 2025)
        if result is None:
            st.info("Enter a pitcher's name in the sidebar and click **Analyze** to get started.")
            return
        data, display_name, pitcher_id, _fm = result
        st.session_state["pitcher_data"] = data
        st.session_state["display_name"] = display_name
        st.session_state["season"] = 2025
        st.session_state["actual_season"] = _fm["actual_season_used"]
        st.session_state["fallback_meta"] = _fm
        st.session_state["pitcher_id"] = pitcher_id
        st.session_state["displayed_pitcher"] = display_name
        st.session_state["displayed_season"] = 2025
        with st.spinner("Fetching 2024 season for comparison..."):
            prev_yoy = _fetch_raw(pitcher_id, 2024)
        st.session_state["yoy_data"] = prev_yoy
        st.session_state["yoy_season"] = 2024
        st.rerun()

    if search:
        _is_demo = _demo_csv_path(pitcher_name, season) is not None
        if _is_demo:
            result = load_pitcher_data(pitcher_name, season)
        else:
            with st.status("Loading pitcher data from Baseball Savant…", expanded=True) as _load_status:
                st.write(f"🔍 **Step 1/3** - Searching MLB player database for **{pitcher_name}**…")
                st.write("⬇️ **Step 2/3** - Downloading Statcast pitch-by-pitch data (typically 45-90 seconds for a full season)…")
                st.write("⚙️ **Step 3/3** - Computing pitch grades, platoon splits, and count tendencies…")
                result = load_pitcher_data(pitcher_name, season)
                if result is not None:
                    _load_status.update(label="✅ Data loaded!", state="complete", expanded=False)
                else:
                    _load_status.update(label="❌ Pitcher not found or no data available.", state="error", expanded=False)
        if result is None:
            return
        data, display_name, pitcher_id, fallback_meta = result
        st.session_state["pitcher_data"] = data
        st.session_state["display_name"] = display_name
        st.session_state["pitcher_id"] = pitcher_id
        # Reset platoon split so stale LHB/RHB filter from previous pitcher doesn't persist
        st.session_state["platoon_split"] = "All Batters"
        # Use actual season from fallback_meta (load_pitcher_data now derives this authoritatively)
        actual_season = fallback_meta["actual_season_used"]
        # Store both: requested (for subtitle) and actual (for data processing)
        st.session_state["season"] = season            # user-selected → shown in subtitle
        st.session_state["actual_season"] = actual_season  # real data year
        st.session_state["fallback_meta"] = fallback_meta
        st.session_state["displayed_pitcher"] = display_name
        st.session_state["displayed_season"] = season
        _prev_s = actual_season - 1
        with st.spinner(f"Fetching {_prev_s} season for comparison..."):
            prev_yoy = _fetch_raw(pitcher_id, _prev_s)
        st.session_state["yoy_data"] = prev_yoy
        st.session_state["yoy_season"] = _prev_s

    data = st.session_state["pitcher_data"]
    display_name = st.session_state["display_name"]
    used_season = st.session_state["season"]
    pitcher_id = st.session_state.get("pitcher_id")

    # ── Combined header: ⚾ PitchIQ | Pitcher name + one subtitle line ─────────
    team, hand = get_pitcher_meta(data)
    hand_label = "RHP" if hand == "R" else "LHP"
    _actual_s_hdr = st.session_state.get("actual_season", used_season)
    _fallback_occurred_hdr = st.session_state.get("fallback_meta", {}).get("fallback_occurred", False)
    _season_label = (
        f"{_actual_s_hdr} Season ({used_season} had no data)"
        if _fallback_occurred_hdr and _actual_s_hdr != used_season
        else f"{used_season} Season"
    )
    meta_parts = [p for p in [team, hand_label, _season_label, "live data via MLB Statcast"] if p]
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:18px;margin-bottom:2px;'>"
        f"<span style='font-size:1.9rem;font-weight:900;'>⚾ PitchIQ</span>"
        f"<span style='color:#444;font-size:1.6rem;font-weight:200;'>|</span>"
        f"<span style='font-size:1.9rem;font-weight:700;'>{display_name}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<span style='font-size:15px;color:#aaaaaa;'>"
        + "  ·  ".join(meta_parts)
        + "</span>",
        unsafe_allow_html=True,
    )

    # Fallback warning: user asked for season X but data only exists for Y.
    # Uses fallback_meta from load_pitcher_data - authoritative, not re-derived.
    _actual_s = st.session_state.get("actual_season", used_season)
    _fallback_meta = st.session_state.get("fallback_meta", {})
    _req_s = _fallback_meta.get("requested_season", used_season)
    _act_s = _fallback_meta.get("actual_season_used", _actual_s)
    if _fallback_meta.get("fallback_occurred") or _actual_s != used_season:
        st.warning(
            f"⚠️ No {_req_s} Statcast data found for {display_name}. "
            f"Showing **{_act_s} season** instead. "
            f"Data will update automatically when {_req_s} pitches are recorded.",
            icon="⚠️",
        )

    st.markdown("---")

    # ── Screencap / CI mode: pre-select platoon from ?p=lhb|rhb query param ──
    _qp_p = st.query_params.get("p", "")
    if _qp_p == "lhb" and st.session_state.get("platoon_split") not in ("vs LHB", "vs RHB"):
        st.session_state["platoon_split"] = "vs LHB"
    elif _qp_p == "rhb" and st.session_state.get("platoon_split") not in ("vs LHB", "vs RHB"):
        st.session_state["platoon_split"] = "vs RHB"

    # ── Global platoon toggle (filters all tabs) ─────────────────────────────
    if "stand" in data.columns:
        split = st.radio(
            "🔀 Batter Handedness",
            ["All Batters", "vs LHB", "vs RHB"],
            horizontal=True,
            key="platoon_split",
        )
        if split == "vs LHB":
            vdata = data[data["stand"] == "L"].copy()
        elif split == "vs RHB":
            vdata = data[data["stand"] == "R"].copy()
        else:
            vdata = data.copy()

        if vdata.empty:
            st.warning(f"No data for {split}.")
            return
    else:
        vdata = data.copy()

    eff_split = compute_effectiveness(vdata)

    # -- Pre-compute all expensive aggregations once per (pitcher, season, split) ----
    # Cached in session_state so switching tabs or toggling the platoon filter on an
    # already-seen split is instant -- no redundant recomputation.
    _perf_key = (
        st.session_state.get("pitcher_id"),
        used_season,
        split if "stand" in data.columns else "all",
    )
    if st.session_state.get("_perf_key") != _perf_key:
        _grades_df_c    = pitch_grades(vdata, eff_split)
        _count_insight_c = (
            _compute_count_insight(vdata, eff_split, display_name)
            if "count_label" in vdata.columns and "description" in vdata.columns
            else None
        )
        _rec_c          = _compute_actionable_recommendation(data, vdata, eff_split, display_name)
        _seq_result_c   = pitch_sequence_matrix(vdata)
        _cq_df_c        = contact_quality(vdata)
        _fp_data_c      = first_pitch_analysis(vdata)
        _fatigue_c      = fatigue_velocity(vdata)
        st.session_state.update({
            "_perf_key":        _perf_key,
            "_grades_df_c":     _grades_df_c,
            "_count_insight_c": _count_insight_c,
            "_rec_c":           _rec_c,
            "_seq_result_c":    _seq_result_c,
            "_cq_df_c":         _cq_df_c,
            "_fp_data_c":       _fp_data_c,
            "_fatigue_c":       _fatigue_c,
        })
    else:
        _grades_df_c     = st.session_state["_grades_df_c"]
        _count_insight_c = st.session_state["_count_insight_c"]
        _rec_c           = st.session_state["_rec_c"]
        _seq_result_c    = st.session_state["_seq_result_c"]
        _cq_df_c         = st.session_state["_cq_df_c"]
        _fp_data_c       = st.session_state["_fp_data_c"]
        _fatigue_c       = st.session_state["_fatigue_c"]


    # ── Metric tiles  -  computed from vdata so they respect the platoon filter ─
    total_pitches = len(vdata)
    pitch_types_n = vdata["pitch_type"].nunique()
    fastballs = vdata[vdata["pitch_type"].isin(["FF", "SI"])]
    avg_fb_velo = (
        fastballs["release_speed"].mean()
        if not fastballs.empty and "release_speed" in fastballs.columns
        else None
    )
    avg_spin = vdata["release_spin_rate"].mean() if "release_spin_rate" in vdata.columns else None

    overall_csw = None
    if not eff_split.empty and "CSW%" in eff_split.columns:
        total_n = vdata.groupby("pitch_type").size()
        csw_vals = eff_split.set_index("pitch_type")["CSW%"]
        weights = total_n / total_n.sum()
        overall_csw = round((csw_vals * weights).sum(), 1)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Pitches", f"{total_pitches:,}")
    c2.metric("Pitch Types", pitch_types_n)
    if avg_fb_velo:
        c3.metric("FB Velo (avg)", f"{avg_fb_velo:.1f} mph")
    if avg_spin:
        c4.metric("Avg Spin Rate", f"{avg_spin:,.0f} rpm")
    if overall_csw is not None:
        c5.metric("Overall CSW%", f"{overall_csw}%")

    # Low-sample warning: shown for any season with fewer than 150 pitches
    if total_pitches < 150:
        st.info(
            f"ℹ️ Small sample size: {total_pitches:,} pitches recorded so far in {used_season}. "
            "Metrics will stabilize as the season progresses."
        )

    st.markdown("---")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_overview, tab_arsenal, tab_location, tab_counts, tab_seq, tab_grades, tab_yoy, tab_matchup = st.tabs(
        ["📋 Scouting Summary", "⚾ Pitch Arsenal", "🎯 Location & Zones",
         "🔢 Count Tendencies", "🔀 Sequencing", "🏅 Pitch Grades", "📈 Season Trends",
         "🔮 Matchup"]
    )

    # ── Tab 1: Overview ───────────────────────────────────────────────────────
    with tab_overview:
        grades_df_ov = _grades_df_c

        # ── Auto-generated scouting narrative (first element) ─────────────
        _ov_insight_for_narrative = _count_insight_c

        _narrative = generate_narrative(
            display_name=display_name,
            hand_label=hand_label,
            team=team,
            grades_df=grades_df_ov,
            eff_df=eff_split,
            avg_fb_velo=avg_fb_velo,
            insight_str=_ov_insight_for_narrative,
            platoon_label=split if "stand" in data.columns else "All Batters",
            vdata=vdata,
            overall_csw_pct=overall_csw,
        )
        st.markdown(
            "<span style='font-size:12px;color:#aaaaaa;font-style:italic;'>"
            "Auto-generated scouting report</span>",
            unsafe_allow_html=True,
        )
        st.info(f"⚡ {_narrative}")

        # ── Grade badges ──────────────────────────────────────────────────
        if not grades_df_ov.empty:
            st.caption(
                "Each pitch is graded A+ to F by comparing velocity, spin rate, "
                "Whiff%, CSW%, and Chase% (when available) against the 2024 "
                "MLB average for that specific pitch type. A+ = top 7% of MLB "
                "pitchers for that pitch. Hover over any chart for exact values."
            )
            st.markdown("#### Arsenal Grades vs MLB Average")
            render_grade_badges(grades_df_ov, vdata)

            # Auto-generated best / worst pitch callout (composite score + usage filter)
            _grade_order = {"A+": 7, "A": 6, "B": 5, "C": 4, "D": 3, "F": 2, "": 1}
            _ranked = grades_df_ov.copy()
            _ranked["_rank"] = _ranked.apply(
                lambda r: _grade_order.get(_overall_grade_from_row(r), 1), axis=1
            )
            if len(_ranked) >= 2:
                _whiff_map = (
                    eff_split.set_index("pitch_type")["Whiff%"].to_dict()
                    if not eff_split.empty and "Whiff%" in eff_split.columns
                    else {}
                )
                _csw_map = (
                    eff_split.set_index("pitch_type")["CSW%"].to_dict()
                    if not eff_split.empty and "CSW%" in eff_split.columns
                    else {}
                )
                _pt_map = vdata.groupby("pitch_label")["pitch_type"].first().to_dict()
                _ov_usage_counts = vdata.groupby("pitch_label").size()
                _ov_total = _ov_usage_counts.sum()
                _ov_usage_pct_map = (_ov_usage_counts / _ov_total * 100).to_dict()

                def _ps(row):
                    """Best-pitch display: always show Whiff% as primary selling point."""
                    p = row.get("Pitch", "")
                    g = _overall_grade_from_row(row)
                    pt = _pt_map.get(p, "")
                    w = _whiff_map.get(pt, None)
                    return f"{p} ({g} · {w:.0f}% Whiff)" if w is not None else f"{p} ({g})"

                def _ps_worst(row):
                    """Needs-work display: show the metric that drove the poor composite score."""
                    p = row.get("Pitch", "")
                    g = _overall_grade_from_row(row)
                    # Find the metric with the lowest grade score (= weakest relative to MLB)
                    whiff_score = _GRADE_SCORE.get(str(row.get("Whiff Grade", "")), 99)
                    csw_score   = _GRADE_SCORE.get(str(row.get("CSW Grade", "")),   99)
                    velo_score  = _GRADE_SCORE.get(str(row.get("Velo Grade", "")),  99)
                    best_metric_score = min(whiff_score, csw_score, velo_score)
                    if best_metric_score == whiff_score and row.get("Whiff%") is not None:
                        val = row.get("Whiff%")
                        metric = "Whiff"
                    elif best_metric_score == csw_score and row.get("CSW%") is not None:
                        val = row.get("CSW%")
                        metric = "CSW"
                    elif best_metric_score == velo_score and row.get("Velo") is not None:
                        val = row.get("Velo")
                        metric = "Velo"
                    else:
                        # Final fallback: show whiff from efficiency map
                        pt = _pt_map.get(p, "")
                        val = _whiff_map.get(pt, None)
                        metric = "Whiff"
                    return f"{p} ({g} · {val:.0f}% {metric})" if val is not None else f"{p} ({g})"

                # Best pitch: composite score with usage >= 8% AND min count filter
                _pitch_raw_counts = vdata.groupby("pitch_label").size().to_dict()
                _ranked_best = _ranked.copy()
                _ranked_best["_usage"] = _ranked_best["Pitch"].map(_ov_usage_pct_map).fillna(0.0)
                _ranked_best["_raw_n"] = _ranked_best["Pitch"].map(_pitch_raw_counts).fillna(0)
                _ranked_best = _ranked_best[
                    (_ranked_best["_usage"] >= 8.0)
                    & (_ranked_best["_raw_n"] >= MIN_PITCHES_FOR_CLAIM["pitch_grade"])
                ]
                if not _ranked_best.empty:
                    _ranked_best = _ranked_best.copy()
                    _ranked_best["_composite"] = _ranked_best.apply(lambda r: (
                        _whiff_map.get(_pt_map.get(r.get("Pitch", ""), ""), 0.0) * 0.5
                        + _csw_map.get(_pt_map.get(r.get("Pitch", ""), ""), 0.0) * 0.3
                        + _ov_usage_pct_map.get(r.get("Pitch", ""), 0.0) * 0.2
                    ), axis=1)
                    _best_row = _ranked_best.nlargest(1, "_composite").iloc[0]
                else:
                    _best_row = _ranked.nlargest(1, "_rank").iloc[0]
                _worst_row = _ranked.nsmallest(1, "_rank").iloc[0]
                # Fix: if best and worst landed on the same pitch, pick next-worst
                if _best_row.get("Pitch") == _worst_row.get("Pitch"):
                    _others = _ranked[_ranked["Pitch"] != _best_row.get("Pitch")]
                    _worst_row = _others.nsmallest(1, "_rank").iloc[0] if not _others.empty else None
                if _worst_row is not None:
                    st.markdown(
                        f"**Best pitch:** {_ps(_best_row)}"
                        f"&nbsp;&nbsp;·&nbsp;&nbsp;"
                        f"**Needs work:** {_ps_worst(_worst_row)}"
                    )
                else:
                    st.markdown(f"**Best pitch:** {_ps(_best_row)}&nbsp;&nbsp;·&nbsp;&nbsp;**Needs work:** N/A (single-pitch arsenal)")

            # Surface auto-insight teaser on Scouting Summary
            if _count_insight_c:
                st.info(_count_insight_c)

            # ── Actionable Recommendation ──────────────────────────────────
            st.markdown("---")
            st.markdown("#### 🎯 Scouting Recommendation")
            _rec = _rec_c
            if _rec == "insufficient_sample":
                st.info(
                    "**Insufficient data for a confident recommendation.** "
                    "A minimum of 80 pitches vs left-handed batters AND 80 vs right-handed batters "
                    "is required to compute a reliable platoon split."
                )
            elif _rec is not None:
                st.success(f"💡 {_rec}")
            else:
                st.info(
                    "No strong platoon split detected (all pitch types perform similarly vs LHB and RHB). "
                    "This pitcher may have good arm-side neutrality - no specific matchup adjustment recommended."
                )

            # ── Mini Sequencing: top 3 transitions ────────────────────────
            st.markdown("---")
            st.markdown("#### 🔀 Top Pitch Sequences")
            _req_seq = {"at_bat_number", "pitch_number", "game_date", "pitch_type", "pitch_label"}
            if _req_seq.issubset(vdata.columns):
                _sm, _top_seq_mini, _n_trans_mini = _seq_result_c
                if not _top_seq_mini.empty:
                    _mini3 = _top_seq_mini.head(3)
                    _seq_cols = st.columns(len(_mini3))
                    for _si, (_si_idx, _srow) in enumerate(zip(_mini3.index, _mini3.itertuples())):
                        with _seq_cols[_si]:
                            st.metric(
                                label=f"{_srow.from_label} → {_srow.to_label}",
                                value=f"{_srow.pct:.0f}%",
                                help=f"{int(_srow.count)} of {_n_trans_mini:,} transitions",
                            )
                    st.caption("Most frequent pitch-to-pitch sequences this season. See **Sequencing** tab for full transition matrix.")
                else:
                    st.caption("Not enough transition data to compute sequences.")

            st.markdown("---")

        col_l, col_r = st.columns(2)
        with col_l:
            st.plotly_chart(pitch_distribution_chart(vdata), width="stretch")
        with col_r:
            if not eff_split.empty:
                st.plotly_chart(effectiveness_chart(eff_split), width="stretch")
                st.caption(
                    "**Whiff%** = swinging strikes ÷ swings &nbsp;|&nbsp; "
                    "**Chase%** = swings on out-of-zone pitches ÷ out-of-zone pitches &nbsp;|&nbsp; "
                    "**CSW%** = (called strikes + whiffs) ÷ total pitches"
                )

        st.markdown("#### Pitch Summary")
        summary = summary_table(vdata, eff_split)
        st.dataframe(summary, hide_index=True)

        # ── Downloads ─────────────────────────────────────────────────────
        _dl_col1, _dl_col2 = st.columns(2)
        with _dl_col1:
            csv = summary.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇ Pitch Summary CSV",
                data=csv,
                file_name=f"pitchiq_{display_name.replace(' ', '_')}_{used_season}_summary.csv",
                mime="text/csv",
                help="Downloads the pitch summary table (velocity, whiff%, CSW%, usage, spin).",
            )
        with _dl_col2:
            # Full report CSV: grades + recommendation + summary combined
            grades_df_for_dl = _grades_df_c
            _rec_for_dl = _rec_c
            _report_sections = [
                pd.DataFrame([{
                    "section": "meta",
                    "pitcher": display_name,
                    "season": used_season,
                    "platoon_filter": split if "stand" in data.columns else "All Batters",
                    "total_pitches": len(vdata),
                }]),
                summary.assign(section="pitch_summary"),
            ]
            if not grades_df_for_dl.empty:
                _report_sections.append(grades_df_for_dl.assign(section="grades"))
            if _rec_for_dl and _rec_for_dl != "insufficient_sample":
                _report_sections.append(pd.DataFrame([{
                    "section": "recommendation",
                    "text": _rec_for_dl,
                }]))
            _full_report_csv = pd.concat(_report_sections, ignore_index=True).to_csv(index=False).encode("utf-8")
            st.download_button(
                "📊 Full Report CSV",
                data=_full_report_csv,
                file_name=f"pitchiq_{display_name.replace(' ', '_')}_{used_season}_full_report.csv",
                mime="text/csv",
                help="Includes pitch summary, grades table, and scouting recommendation in a single CSV.",
            )

        # ── Contact Quality by Pitch Type ─────────────────────────────────
        cq_df = _cq_df_c
        st.divider()
        st.subheader("🎯 Contact Quality by Pitch Type")
        render_contact_quality(cq_df)

    # ── Tab 2: Arsenal ────────────────────────────────────────────────────────
    with tab_arsenal:
        col_l, col_r = st.columns(2)
        with col_l:
            fig_move = movement_chart(vdata)
            if fig_move:
                st.plotly_chart(fig_move, width="stretch")
            else:
                st.warning("Movement data not available.")
        with col_r:
            fig_vel = velocity_chart(vdata)
            if fig_vel:
                st.plotly_chart(fig_vel, width="stretch")
            else:
                st.warning("Velocity data not available.")

        col_l2, col_r2 = st.columns(2)
        with col_l2:
            fig_rel = release_point_chart(vdata)
            if fig_rel:
                st.plotly_chart(fig_rel, width="stretch")
            else:
                st.warning("Release point data not available.")
        with col_r2:
            st.markdown("##### Reading the movement chart")
            st.markdown(
                """
                - **X-axis** - horizontal break from pitcher's POV  
                  (positive = arm-side, negative = glove-side)
                - **Y-axis** - vertical break vs. gravity  
                  (positive = rises, negative = drops)
                - Each dot is a single pitch; clusters show the typical profile
                - Pitches with similar tunnel points but different break  
                  are harder for hitters to distinguish
                """
            )
            st.markdown("##### Release point")
            st.markdown(
                """
                A consistent release point across all pitch types makes  
                the pitcher harder to read. Look for tight clustering.
                """
            )

    # ── Tab 3: Location ───────────────────────────────────────────────────────
    with tab_location:
        pitch_options = ["All"] + sorted(vdata["pitch_label"].unique().tolist())
        selected_pitch = st.selectbox("Filter by pitch type", pitch_options, key="loc_pitch_filter")

        fig_zone = zone_heatmap(vdata, pitch_filter=selected_pitch)
        if fig_zone:
            col_z, col_pad = st.columns([1, 1])
            with col_z:
                st.plotly_chart(fig_zone, width="stretch")
            with col_pad:
                st.markdown("##### About this chart")
                st.markdown(
                    """
                    The white rectangle is the **strike zone** (roughly 1.5 - 3.5 ft height,  
                    ±0.71 ft wide). Hot colours = high pitch density.

                    **How to use:**  
                    - Select a pitch type to see where it typically lands  
                    - Pitches clustered low and away to opposite-hand hitters  
                      are generally most effective  
                    - Compare glove-side vs arm-side tendencies across counts  
                      using the **Counts** tab
                    """
                )
        else:
            st.warning("No location data available for this selection.")

    # ── Tab 4: Count Tendencies ───────────────────────────────────────────────
    with tab_counts:
        st.subheader("First-Pitch Strategy")
        st.caption(
            "Getting ahead in the count (0-1) vs falling behind (1-0) "
            "is one of the most important strategic variables in baseball. "
            "Pitchers with high first-pitch strike rates force hitters to "
            "protect the plate early, making them easier to get out."
        )
        fp_data = _fp_data_c
        render_first_pitch_section(fp_data, display_name)
        st.divider()
        if "count_label" not in vdata.columns:
            st.warning("Count data not available.")
        else:
            st.markdown(
                "Pitch selection varies significantly by count. "
                "Use this view to spot tendencies a hitter or coach could exploit."
            )

            fig_counts = count_pitch_mix_chart(vdata)
            if fig_counts:
                st.plotly_chart(fig_counts, width="stretch")

            st.markdown("---")
            st.markdown("#### Zone location for a specific count")

            available_counts = [c for c in COUNT_ORDER if c in vdata["count_label"].values]
            if available_counts:
                col_sel, col_m1, col_m2 = st.columns([1, 1, 2])
                with col_sel:
                    selected_count = st.selectbox("Select count", available_counts, key="count_selector")
                with col_m1:
                    count_n = (vdata["count_label"] == selected_count).sum()
                    st.metric("Pitches in count", f"{count_n:,}")
                with col_m2:
                    count_grp = vdata[vdata["count_label"] == selected_count]
                    if not count_grp.empty:
                        top_pitch = count_grp["pitch_label"].value_counts().idxmax()
                        top_pct = count_grp["pitch_label"].value_counts(normalize=True).iloc[0] * 100
                        st.metric("Most used pitch", f"{top_pitch} ({top_pct:.0f}%)")

                fig_count_zone = zone_heatmap_by_count(vdata, selected_count)
                col_cz, col_cp = st.columns([1, 1])
                with col_cz:
                    if fig_count_zone:
                        st.plotly_chart(fig_count_zone, width="stretch")
                    else:
                        st.info("Not enough location data for this count.")
                with col_cp:
                    count_grp2 = vdata[vdata["count_label"] == selected_count].copy()
                    if not count_grp2.empty and "description" in count_grp2.columns:
                        rows_eff = []
                        for pt_label, grp in count_grp2.groupby("pitch_label"):
                            n = len(grp)
                            usage_pct = round(n / len(count_grp2) * 100, 1)
                            swings = grp[grp["description"].isin(SWING_EVENTS)]
                            whiffs = grp[grp["description"].isin(WHIFF_EVENTS)]
                            csw = grp[grp["description"].isin(CSW_EVENTS)]
                            whiff_pct = (
                                round(len(whiffs) / len(swings) * 100, 1)
                                if len(swings) > 0 else 0.0
                            )
                            csw_pct = round(len(csw) / n * 100, 1)
                            rows_eff.append({
                                "Pitch": pt_label,
                                "Usage%": usage_pct,
                                "Whiff%": whiff_pct,
                                "CSW%": csw_pct,
                                "_n": n,
                            })
                        if rows_eff:
                            count_eff_df = (
                                pd.DataFrame(rows_eff)
                                .sort_values("Usage%", ascending=False)
                            )
                            st.markdown(f"**Pitch effectiveness in {selected_count} counts**")
                            _matchup_fmt = {"Usage%": "{:.1f}", "Whiff%": "{:.1f}", "CSW%": "{:.1f}"}
                            st.dataframe(
                                _format_display_df(count_eff_df[["Pitch", "Usage%", "Whiff%", "CSW%"]], _matchup_fmt),
                                hide_index=True,
                            )
                            valid = count_eff_df[count_eff_df["_n"] >= 5]
                            if not valid.empty:
                                best = valid.loc[valid["Whiff%"].idxmax()]
                                st.markdown(
                                    f"🎯 **Most effective in {selected_count}:** "
                                    f"{best['Pitch']} "
                                    f"({best['Whiff%']:.0f}% Whiff, "
                                    f"{best['CSW%']:.0f}% CSW)"
                                )

                # Auto-insight shown once: at the bottom of this section
                if _count_insight_c:
                    st.info(_count_insight_c)
                else:
                    st.info(
                        "Insufficient data for count-level analysis at this stage of the season. "
                        f"At least {MIN_PITCHES_FOR_CLAIM['count_insight']} pitches per count "
                        "are required for a reliable insight."
                    )


    # ── Tab 5: Sequencing ─────────────────────────────────────────────────────
    with tab_seq:
        render_sequencing_tab(vdata, display_name, precomputed=_seq_result_c)

    # ── Tab 6: Grades ─────────────────────────────────────────────────────────
    with tab_grades:
        st.markdown(
            "Each pitch is graded **A+ to F** against 2024 MLB averages for that pitch type. "
            "Deltas show the difference from league average - **green = above avg**, **red = below avg**."
        )

        grades_df = _grades_df_c
        if grades_df.empty:
            st.info("No graded pitch types found. Pitch types must be in MLB_AVG (FF, SI, FC, SL, ST, CU, KC, CH, FS).")
        else:
            _violations = _grade_sanity_check(grades_df)
            if _violations:
                with st.expander("Grade sanity check violations (debug)", expanded=False):
                    for v in _violations:
                        st.error(v)
        if not grades_df.empty:
            # Radar chart  -  full width
            fig_radar = arsenal_radar_chart(vdata, eff_split)
            st.plotly_chart(fig_radar, width='stretch')
            st.caption(
                "Each axis is normalized so **50 = MLB league average** for that pitch type. "
                "Scores above 50 are above league average; below 50 are below."
            )

            st.markdown("#### Pitch Grade Breakdown")

            # Split into two focused half-width tables to avoid horizontal scrolling:
            # Left = Physical metrics (velocity & spin)
            # Right = Effectiveness metrics (whiff, CSW, chase)
            col_phys, col_eff = st.columns(2)

            with col_phys:
                st.markdown("**Physical Metrics**")
                phys_want = ["Pitch", "Velo", "Δ Velo", "Velo Grade", "Spin", "Δ Spin", "Spin Grade"]
                phys_cols = [c for c in phys_want if c in grades_df.columns]
                phys_df = _format_display_df(grades_df[phys_cols].copy(), {
                    "Velo":  "{:.1f}", "Δ Velo": "{:+.1f}",
                    "Spin":  "{:.0f}", "Δ Spin": "{:+.0f}",
                })
                st.dataframe(style_grades(phys_df), hide_index=True)

            with col_eff:
                st.markdown("**Effectiveness Metrics**")
                eff_want = ["Pitch", "Whiff%", "Δ Whiff%", "Whiff Grade",
                            "CSW%", "Δ CSW%", "CSW Grade",
                            "Chase%", "Δ Chase%", "Chase Grade"]
                eff_cols = [c for c in eff_want if c in grades_df.columns]
                eff_df = _format_display_df(grades_df[eff_cols].copy(), {
                    "Whiff%": "{:.1f}", "Δ Whiff%": "{:+.1f}",
                    "CSW%":   "{:.1f}", "Δ CSW%":   "{:+.1f}",
                    "Chase%": "{:.1f}", "Δ Chase%":  "{:+.1f}",
                })
                st.dataframe(style_grades(eff_df), hide_index=True)

            st.markdown("---")
            st.markdown("**Grading thresholds vs. league avg for pitch type:**")
            st.markdown(
                "| Grade | Threshold |\n"
                "|---|---|\n"
                "| **A+** | +1.5 std above avg |\n"
                "| **A**  | +0.75 std |\n"
                "| **B**  | +0.2 std |\n"
                "| **C**  | ±0.2 std (avg) |\n"
                "| **D**  | -0.75 std |\n"
                "| **F**  | -1.5 std or more |"
            )

    # ── Tab 6: Season Trends ──────────────────────────────────────────────────
    with tab_yoy:
        st.subheader("Inning-by-Inning Velocity & Fatigue Index")
        fatigue_data = _fatigue_c
        render_fatigue_section(fatigue_data, display_name)
        st.divider()

        # Use the actual data year (may differ from user-selected if fallback occurred)
        actual_s = st.session_state.get("actual_season", used_season)
        curr_year = actual_s
        prev_year = st.session_state.get("yoy_season", curr_year - 1)

        st.markdown(
            f"Compare **{display_name}**'s arsenal across seasons. "
            f"Highlights changes in velocity, spin, and pitch usage."
        )

        # ── Multi-year fetch ─────────────────────────────────────────────────
        if pitcher_id is not None:
            with st.spinner(f"Loading up to 5 seasons of data for {display_name}…"):
                all_seasons = fetch_multi_season(pitcher_id, curr_year, n_years=5)
        else:
            # Fallback: use whatever we already have
            all_seasons = {curr_year: data}
            prev_data = st.session_state.get("yoy_data")
            if prev_data is not None and not (hasattr(prev_data, "empty") and prev_data.empty):
                all_seasons[prev_year] = prev_data

        if not all_seasons:
            st.warning(f"No Statcast data found for {display_name}.")
        else:
            sorted_years = sorted(all_seasons.keys())
            min_yr, max_yr = sorted_years[0], sorted_years[-1]

            # ── SECTION 1: Game-by-game fastball velocity chart ──────────────
            fig_gbg = multi_season_gamebygame_chart(all_seasons, display_name)
            if fig_gbg:
                st.plotly_chart(fig_gbg, width='stretch')
                st.caption(
                    "X-axis = days since each pitcher's first start of that season (0 = first start). "
                    "Seasons overlap on the same scale for direct comparison. "
                    "Each dot = one start. Filtered to fastball types (4-seam, sinker, cutter)."
                )
            else:
                st.info("No fastball game-by-game data found to plot.")

            st.markdown("---")

            # ── SECTION 2: Season-by-Season stats table ──────────────────────
            st.markdown("#### Season-by-Season Pitch Stats")
            if len(all_seasons) >= 2:
                multi_df = multi_season_stats_table(all_seasons)
                if not multi_df.empty:
                    def _color_trend(val):
                        if val == "↑":
                            return "color:#06D6A0;font-weight:bold"
                        if val == "↓":
                            return "color:#E63946;font-weight:bold"
                        return "color:#aaaaaa"

                    def _color_ms_delta(val):
                        try:
                            v = float(val)
                            if v > 0:
                                return "color:#06D6A0;font-weight:bold"
                            if v < 0:
                                return "color:#E63946;font-weight:bold"
                        except (TypeError, ValueError):
                            pass
                        return ""

                    # Format numeric columns
                    velo_cols = [c for c in multi_df.columns if c.startswith("Velo (")]
                    spin_cols = [c for c in multi_df.columns if c.startswith("Spin (")]
                    usage_cols = [c for c in multi_df.columns if c.startswith("Usage% (")]
                    fmt_map = {c: "{:.1f}" for c in velo_cols + usage_cols}
                    fmt_map.update({c: "{:.0f}" for c in spin_cols})
                    multi_df_fmt = _format_display_df(multi_df, fmt_map)
                    for _col in multi_df_fmt.columns:
                        if _col != "Pitch":
                            multi_df_fmt[_col] = multi_df_fmt[_col].replace("nan", "-").replace("None", "-")

                    styled_ms = multi_df_fmt.style
                    if "Velo Trend" in multi_df_fmt.columns:
                        styled_ms = styled_ms.map(_color_trend, subset=["Velo Trend"])

                    st.dataframe(styled_ms, hide_index=True)

                # Also show the 2-season Δ table if we have the two most recent
                if len(sorted_years) >= 2:
                    curr_pair = sorted_years[-1]
                    prev_pair = sorted_years[-2]
                    delta_df = yoy_delta_table(
                        all_seasons[curr_pair], all_seasons[prev_pair],
                        curr_pair, prev_pair
                    )

                    def color_yoy_delta(val):
                        try:
                            v = float(val)
                            c = "#06D6A0" if v > 0 else "#E63946" if v < 0 else "#fafafa"
                            return f"color: {c}; font-weight: bold"
                        except (ValueError, TypeError):
                            return ""

                    st.markdown(f"**Year-over-year change ({prev_pair} → {curr_pair})**")
                    delta_delta_cols = [c for c in delta_df.columns if c.startswith("Δ")]
                    delta_df_obj = delta_df.copy()
                    for _col in delta_df_obj.columns:
                        delta_df_obj[_col] = delta_df_obj[_col].astype(str).replace("nan", "-")
                    styled_delta = delta_df_obj.style
                    if delta_delta_cols:
                        styled_delta = styled_delta.map(color_yoy_delta, subset=delta_delta_cols)
                    st.dataframe(styled_delta, hide_index=True)
                    st.caption(
                        f"**Δ columns** = {curr_pair} value minus {prev_pair} value. "
                        "Green = increased, red = decreased."
                    )

            else:
                # Single season fallback table
                prev_data = st.session_state.get("yoy_data")
                yoy_s = st.session_state.get("yoy_season", curr_year - 1)
                if prev_data is not None and not (hasattr(prev_data, "empty") and prev_data.empty):
                    delta_df = yoy_delta_table(data, prev_data, curr_year, yoy_s)

                    def color_yoy_delta(val):
                        try:
                            v = float(val)
                            c = "#06D6A0" if v > 0 else "#E63946" if v < 0 else "#fafafa"
                            return f"color: {c}; font-weight: bold"
                        except (ValueError, TypeError):
                            return ""

                    delta_delta_cols = [c for c in delta_df.columns if c.startswith("Δ")]
                    delta_df_obj = delta_df.copy()
                    for _col in delta_df_obj.columns:
                        delta_df_obj[_col] = delta_df_obj[_col].astype(str).replace("nan", "-")
                    styled_delta = delta_df_obj.style
                    if delta_delta_cols:
                        styled_delta = styled_delta.map(color_yoy_delta, subset=delta_delta_cols)
                    st.dataframe(styled_delta, hide_index=True)
                    st.caption(
                        f"**Δ columns** = {curr_year} value minus {yoy_s} value. "
                        "Green = increased, red = decreased."
                    )
                else:
                    st.warning(
                        f"No prior season data found for {display_name}. "
                        "They may not have pitched in earlier seasons."
                    )

            # ── SECTION 3: Data availability disclaimer ───────────────────────
            st.divider()
            st.caption(
                f"Historical data sourced from MLB Statcast via Baseball Savant. "
                f"Coverage: 2015 - present for MLB regular season. "
                f"Seasons shown: {', '.join(str(y) for y in sorted_years)}. "
                f"Minimum 50 pitches required to include a season. "
                f"Data for the current season ({curr_year}) may be incomplete "
                f"if the season is in progress."
            )


    # ── Tab 8: Matchup Prediction ─────────────────────────────────────────────
    with tab_matchup:
        render_matchup_tab(vdata, display_name)


if __name__ == "__main__":
    main()
