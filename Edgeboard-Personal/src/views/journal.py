# src/views/journal.py
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from src.styles import inject_journal_css

# --- Demo flag (read from Streamlit secrets) ---
try:
    # if you later put DEMO_MODE in src/state.py, this import will work
    from src.state import DEMO_MODE  # optional
except Exception:
    import streamlit as st  # ensure st is in scope


DATA_DIR = Path(os.environ.get("EDGEBOARD_DATA_DIR", Path.home() / ".edgeboard"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
JOURNAL_PATH = DATA_DIR / "journal.csv"

# --- Demo flag is toggled by parent app (app.py / private_app.py) ---
DEMO_MODE = False  # app.py sets True for demo; private_app keeps False


# --- Minimal schema used when starting empty ---
_EMPTY_SCHEMA = [
    "Trade #",
    "Account",
    "Win/Loss",
    "Symbol",
    "Date",
    "Day of Week",
    "Direction",
    "Timeframe",
    "Type",
    "Setup Tier",
    "Score",
    "Grade",
    "Confirmations",
    "Entry Time",
    "Exit Time",
    "Duration (min)",
    "Duration",
    "PnL",
    "Dollars Risked",
    "R Ratio",
    "Chart URL",
    "Micromanaged?",
    "Comments",
]


def _df_checksum(df: pd.DataFrame) -> str:
    # small, fast checksum to detect changes
    try:
        return pd.util.hash_pandas_object(df.reset_index(drop=True), index=False).sum().__str__()
    except Exception:
        return str(hash(df.to_json(orient="split")))


def _load_persisted_journal() -> pd.DataFrame | None:
    if JOURNAL_PATH.exists():
        try:
            df = pd.read_csv(JOURNAL_PATH)
            # ensure columns exist (in case of older file)
            for col in _EMPTY_SCHEMA:
                if col not in df.columns:
                    df[col] = pd.Series(dtype=object)
            return df[_EMPTY_SCHEMA]
        except Exception:
            pass
    return None


def _save_persisted_journal(df: pd.DataFrame) -> None:
    # never save in demo
    if DEMO_MODE:
        return
    try:
        df[_EMPTY_SCHEMA].to_csv(JOURNAL_PATH, index=False)
    except Exception:
        pass


def _autosave_journal() -> None:
    """Persist journal_df if changed (private only). Call once near end of render()."""
    if DEMO_MODE:
        return
    df = st.session_state.get("journal_df")
    if not isinstance(df, pd.DataFrame):
        return
    new_sig = _df_checksum(df)
    if st.session_state.get("_journal_sig") != new_sig:
        _save_persisted_journal(df)
        st.session_state["_journal_sig"] = new_sig


# ----------------------------- config -----------------------------
SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "ASTERUSDT",
    "PUMPUSDT",
    "SOLUSDT",
    "SUIUSDT",
    "HYPEUSDT",
    "ADAUSDT",
]

DIRECTIONS = ["Long", "Short"]
TIMEFRAMES = ["m1", "m3", "m5", "m15", "m30", "H1", "H4"]
TYPES = ["Reversal", "Continuation"]
TIER = ["S", "A+", "A", "A-", "B+", "B", "B-", "C"]
EXEC_TIER = ["S", "A+", "A", "A-", "B+", "B", "B-", "C"]

DEFAULT_CONFIRMATIONS = [
    "IFVG",
    "Liq Sweep",
    "High Momentum",
    "Equal High/Low",
    "H4 FVG Delivery/Stairstep",
    "12 ema (4H)",
    "LRLR",
    "CVD",
]

# theme colors (fallbacks if module not present)
try:
    from src.theme import BLUE, BLUE_FILL, CARD_BG, FG, FG_MUTED
except Exception:
    BLUE = "#3AA4EB"
    BLUE_FILL = "rgba(58,164,235,0.15)"
    FG = "#dbe4ee"
    FG_MUTED = "#9aa6b2"


BG_CARD = "#10192B9E"


# --- modal helper (same pattern you use in checklist) ---
def modal_or_inline(title: str, render_body):
    dlg = getattr(st, "modal", None) or getattr(st, "dialog", None)
    if callable(dlg):
        decorator = dlg(title)

        @decorator
        def _show():
            render_body()

        _show()
    else:
        # Fallback overlay
        st.markdown(
            f"""
            <div style="position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9999;display:flex;align-items:center;justify-content:center;">
              <div style="background:#111827;border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:16px;min-width:1100px; max-width:96vw;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                  <div style="font-weight:700;">{title}</div>
                  <div>
                    <span title="Close">
                      {''}
                    </span>
                  </div>
                </div>
            """,
            unsafe_allow_html=True,
        )
        render_body()
        st.markdown("</div></div>", unsafe_allow_html=True)


# --- Styler helpers for value-based coloring (read-only view) ---
def _style_pnl(val):
    try:
        v = float(val)
    except Exception:
        return ""
    if v > 0:
        return "color:#22c55e;font-weight:700;"
    if v < 0:
        return "color:#ef4444;font-weight:700;"
    return "color:#e5e7eb;font-weight:600;"


def _style_direction(val: str):
    s = str(val).lower()
    if s == "long":
        return "color:#22c55e;font-weight:600;"
    if s == "short":
        return "color:#ef4444;font-weight:600;"
    return ""


def _style_day(val: str):
    day = str(val)[:3].lower()
    palette = {
        "mon": "#60a5fa",
        "tue": "#14b8a6",
        "wed": "#a78bfa",
        "thu": "#f59e0b",
        "fri": "#c7d13c",
        "sat": "#5f7da8",
        "sun": "#8d61aa",
    }
    color = palette.get(day, "#e5e7eb")
    return f"color:{color};font-weight:600;"


def _style_setup_tier(val: str):
    m = {
        "S": "#e8f160",
        "A+": "#c28dff",
        "A": "#c28dff",
        "A-": "#c28dff",
        "B+": "#1e97e7",
        "B": "#1b81c5",
        "B-": "#1e97e7",
        "C": "#41ce2f",
    }
    c = m.get(str(val).strip().upper(), "#e5e7eb")
    return f"color:{c}; font-weight:700;"


def _style_type(val: str):
    s = str(val).strip().lower()
    if s.startswith("cont"):
        return "color:#14b8a6; font-weight:400;"
    if s.startswith("rev"):
        return "color:#f59e0b; font-weight:400;"
    return ""


def _style_session(val: str):
    s = str(val).strip()
    cmap = {
        "Asia": "color:#60a5fa; font-weight:700;",
        "London": "color:#14b8a6; font-weight:700;",
        "NY AM": "color:#a78bfa; font-weight:700;",
        "NY Lunch": "color:#f59e0b; font-weight:700;",
        "NY PM": "color:#38bdf8; font-weight:700;",
    }
    return cmap.get(s, "color:#e5e7eb; font-weight:600;")


def _styled_view(df: pd.DataFrame) -> "pd.io.formats.style.Styler":
    styler = df.style

    # Column-wise applymap for value-based colors
    col_funcs = {
        "PnL": _style_pnl,
        "Direction": _style_direction,
        "Setup Tier": _style_setup_tier,
        "Day of Week": _style_day,
        "Type": _style_type,
        "Session": _style_session,
        # Confirmations: tint the cell using the first tag's color (not grey)
        "Confirmations": (
            lambda v: (
                (lambda _c: f"background:{_c}33;border-radius:10px;padding:2px 6px;")(
                    st.session_state.get("confirm_color_map", {}).get(
                        (v[0] if isinstance(v, list) and v else str(v).split(",")[0].strip()),
                        "#3b82f6",
                    )
                )
                if str(v).strip() not in ("", "[]", "None", "nan")
                else ""
            )
        ),
    }
    for col, fn in col_funcs.items():
        if col in df.columns:
            styler = styler.applymap(fn, subset=pd.IndexSlice[:, [col]])
    # <<< ADD THIS: enforce currency formatting in styled (read-only) view >>>
    styler = styler.format(
        {
            "PnL": lambda v: "" if pd.isna(v) else f"${float(v):,.2f}",
            "Dollars Risked": lambda v: "" if pd.isna(v) else f"${float(v):,.2f}",
        }
    )

    return styler


# ----------------------------- helpers -----------------------------
def _friendly_minutes(total_min: float) -> str:
    m = int(round(max(0.0, float(total_min))))
    d, rem = divmod(m, 1440)
    h, mm = divmod(rem, 60)
    parts: List[str] = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    if mm or not parts:
        parts.append(f"{mm}m")
    return " ".join(parts)


def _ensure_session_column(df: pd.DataFrame) -> pd.DataFrame:
    if "Entry Time" not in df.columns:
        return df
    times = pd.to_datetime(df["Entry Time"], errors="coerce")
    hours = times.dt.hour

    def _bucket(h: int) -> str:
        if (h >= 20) or (h < 2):
            return "Asia"
        if 2 <= h < 6:
            return "London"
        if 6 <= h < 12:
            return "NY AM"
        if 12 <= h < 13:
            return "NY Lunch"
        if 13 <= h < 20:
            return "NY PM"
        return "Other"

    out = df.copy()
    out["Session"] = hours.fillna(-1).astype(int).apply(_bucket)
    return out


def _parse_time_string(t: str) -> datetime.time:
    t = (t or "").strip()
    try:
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(t, fmt).time()
            except ValueError:
                pass
        return pd.to_datetime(t).time()
    except Exception:
        now = datetime.now().replace(second=0, microsecond=0)
        return now.time()


def _compute_derived(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    df["Day of Week"] = pd.to_datetime(df["Date"]).dt.day_name()

    et = pd.to_datetime(df["Entry Time"], errors="coerce")
    xt = pd.to_datetime(df["Exit Time"], errors="coerce")
    dur_min = (xt - et).dt.total_seconds() / 60.0
    df["Duration (min)"] = dur_min.round(0).astype("Int64")
    df["Duration"] = df["Duration (min)"].apply(
        lambda x: _friendly_minutes(x) if pd.notna(x) else "—"
    )

    df["Win/Loss"] = np.where(df["PnL"] > 0, "Win", np.where(df["PnL"] < 0, "Loss", "Break-even"))
    df["PnL"] = pd.to_numeric(df["PnL"], errors="coerce").round(2)
    df["Dollars Risked"] = pd.to_numeric(df["Dollars Risked"], errors="coerce").round(2)

    risk = pd.to_numeric(df["Dollars Risked"], errors="coerce").replace(0, np.nan)
    df["R Ratio"] = (df["PnL"] / risk).replace([np.inf, -np.inf], np.nan).round(2).fillna(0.0)

    df = df.sort_values(
        ["Date", "Entry Time"], ascending=[False, False], kind="mergesort"
    ).reset_index(drop=True)
    df["Trade #"] = df.index + 1
    return df


def _init_session_state() -> None:
    """Initialize journal session keys."""
    # --- Journal dataframe: DEMO vs PRIVATE ---
    if "journal_df" not in st.session_state or st.session_state.get("journal_df") is None:
        if DEMO_MODE:
            # DEMO: generate once per session
            st.session_state.journal_df = _generate_fake_journal(300)
        else:
            # PRIVATE: try load from disk; if missing, start EMPTY
            _loaded = _load_persisted_journal()
            st.session_state.journal_df = (
                _loaded if _loaded is not None else pd.DataFrame(columns=_EMPTY_SCHEMA)
            )

    # Ensure the Journal page date filter spans current data
    try:
        if not st.session_state.journal_df.empty and "Date" in st.session_state.journal_df.columns:
            _d = pd.to_datetime(st.session_state.journal_df["Date"], errors="coerce").dropna()
            if not _d.empty:
                st.session_state["jr_date_range"] = (_d.min().date(), _d.max().date())
    except Exception:
        pass

    # baseline sig for autosave
    st.session_state["_journal_sig"] = _df_checksum(st.session_state.journal_df)

    # Other keys you already use
    from datetime import date

    st.session_state.setdefault("accounts_options", ["NQ", "Crypto (Live)", "Crypto (Prop)"])
    st.session_state.setdefault("journal_view_mode", "Styled")
    st.session_state.setdefault("new_entry_force_once", False)
    st.session_state.setdefault("show_new_entry", False)
    st.session_state.setdefault("confirm_color_map", {})
    st.session_state.setdefault("confirm_color_idx", 0)
    st.session_state.setdefault(
        "confirm_color_palette",
        [
            "#1E3B8ACE",
            "#0E7490CE",
            "#065F46CE",
            "#7C2D12CE",
            "#6B21A8CE",
            "#0F766ECE",
            "#1F2937CE",
            "#1B4079CE",
            "#14532DCE",
            "#3F1D38CE",
            "#2B2D42CE",
            "#23395BCE",
            "#2F3E46CE",
            "#264653CE",
            "#3A0CA3CE",
        ],
    )
    st.session_state.setdefault("confirmations_options", list(DEFAULT_CONFIRMATIONS))
    st.session_state.setdefault("jr_date_range", (date.today(), date.today()))

    # If there is already data, (re)seed the color map for any seen confirmation tags
    try:
        known = set(st.session_state.get("confirmations_options", []))
        dfc = st.session_state.journal_df.get("Confirmations", pd.Series([], dtype=object))
        for cell in dfc:
            if isinstance(cell, list):
                known.update(x for x in cell if x)
            elif isinstance(cell, str):
                for x in [t.strip() for t in cell.split(",") if t.strip()]:
                    known.add(x)
        cmap = st.session_state["confirm_color_map"]
        pal = st.session_state["confirm_color_palette"]
        idx = st.session_state["confirm_color_idx"]
        for tag in sorted(known):
            if tag not in cmap:
                cmap[tag] = pal[idx % len(pal)]
                idx += 1
        st.session_state["confirm_color_idx"] = idx
        st.session_state["confirmations_options"] = sorted(set(known))
    except Exception:
        pass


def load_journal_for_page() -> pd.DataFrame:
    """
    Returns the journal DataFrame.
    DEMO_MODE: generate placeholder data once per session.
    PRIVATE: never require CSV; always use session (init empty schema if missing).
    """
    import pandas as pd
    import streamlit as st

    if DEMO_MODE:
        # Generate once and cache
        if (
            "journal_df" not in st.session_state
            or st.session_state.journal_df is None
            or st.session_state.journal_df.empty
        ):
            st.session_state.journal_df = _generate_fake_journal(300)
        return st.session_state.journal_df

    # PRIVATE MODE: no CSV dependency
    if "journal_df" not in st.session_state or st.session_state.journal_df is None:
        st.session_state.journal_df = pd.DataFrame(
            columns=[
                "Trade #",
                "Account",
                "Win/Loss",
                "Symbol",
                "Date",
                "Day of Week",
                "Direction",
                "Timeframe",
                "Type",
                "Setup Tier",
                "Score",
                "Grade",
                "Confirmations",
                "Entry Time",
                "Exit Time",
                "Duration (min)",
                "Duration",
                "PnL",
                "Dollars Risked",
                "R Ratio",
                "Chart URL",
                "Micromanaged?",
                "Comments",
            ]
        )
    return st.session_state.journal_df


def _fake_comment(win: bool) -> str:
    good = [
        "Clean execution. Followed plan.",
        "Great location confluence.",
        "Nice continuation off HTF level.",
        "Scaling worked well.",
    ]
    bad = [
        "Chased entry; late fill.",
        "Impatient exit; missed target.",
        "Break-even after partials.",
        "Fought bias; should’ve skipped.",
    ]
    neutral = ["Plan respected. Room to refine management."]
    pool = good if win else bad
    return np.random.choice(pool + neutral)


def _generate_tp_distribution(rng: np.random.Generator, is_win: bool) -> Tuple[int, int, int]:
    if is_win:
        tp1 = int(rng.integers(30, 61))
        tp2 = int(rng.integers(10, 41)) if rng.random() < 0.55 else 0
        max_tp3 = max(0, 100 - (tp1 + tp2))
        tp3 = 0
        if max_tp3 >= 10 and rng.random() < 0.18:
            tp3 = int(rng.integers(10, min(31, max_tp3 + 1)))
        s = tp1 + tp2 + tp3
        if s > 100:
            over = s - 100
            if tp3 >= over:
                tp3 -= over
            else:
                over -= tp3
                tp3 = 0
                tp2 = max(0, tp2 - over)
        return tp1, tp2, tp3
    if rng.random() < 0.35:
        return int(rng.integers(20, 51)), 0, 0
    return 0, 0, 0


def _generate_fake_journal(n: int = 200) -> pd.DataFrame:
    """
    Realistic-but-not-crazy placeholder:
      - ~1–3 trades per weekday; some days off; weekends skipped
      - Profitable overall with a right-skew (Mean > Median)
      - Includes losers (esp. in lower tiers)
      - Every tier present; few 'S' and they are 100% win
      - Mostly A+; fewer as quality decreases
    """
    rng = np.random.default_rng(1337)  # tweak this for a different "look"

    # --- Tier mix & win rates ---
    # Make A+ the workhorse; S is rare and 100% win; others taper down.
    tier_weights = {
        "S": 0.02,
        "A+": 0.38,
        "A": 0.20,
        "A-": 0.14,
        "B+": 0.10,
        "B": 0.08,
        "B-": 0.05,
        "C": 0.03,
    }
    # Target win probabilities per tier
    tier_winrate = {
        "S": 1.00,
        "A+": 0.64,
        "A": 0.60,
        "A-": 0.57,
        "B+": 0.54,
        "B": 0.50,
        "B-": 0.46,
        "C": 0.43,
    }
    # Score baselines by tier (for table chips)
    tier_score_baseline = {
        "S": 98,
        "A+": 94,
        "A": 90,
        "A-": 87,
        "B+": 83,
        "B": 78,
        "B-": 72,
        "C": 68,
    }

    def grade_from_score(s: int) -> str:
        if s >= 96:
            return "S"
        if s >= 90:
            return "A+"
        if s >= 85:
            return "A"
        if s >= 80:
            return "A-"
        if s >= 75:
            return "B+"
        if s >= 70:
            return "B"
        if s >= 65:
            return "B-"
        return "C"

    # Helper to pick respecting weights order in TIER list if present
    def weighted_choice_tier():
        # Keep only tiers that exist in your TIER list (in case it's customized)
        usable = [t for t in TIER if t in tier_weights]
        w = np.array([tier_weights[t] for t in usable], dtype=float)
        w = w / w.sum()
        return rng.choice(usable, p=w)

    rows = []

    # --- Ensure at least one of each tier (S will be win) ---
    today = date.today()
    start = date(today.year, 6, 1)  # June 1 of the current year
    end = date(today.year, 10, 17)  # Oct 17 of the current year
    preload_day = start
    for t in ["S", "A+", "A", "A-", "B+", "B", "B-", "C"]:
        if t not in TIER:
            continue
        d = preload_day
        # If weekend, bump to Monday
        while d.weekday() >= 5:
            d += timedelta(days=1)
        e_hour = int(rng.integers(6, 14))  # morning to early afternoon feel
        e_min = int(rng.integers(0, 60))
        e_time = datetime(d.year, d.month, d.day, e_hour, e_min)
        hold = int(rng.integers(10, 90))
        x_time = e_time + timedelta(minutes=hold)
        # Risk and R-multiple (S always win; others later use tier win prob)
        dollars_risked = float(rng.integers(50, 100))
        if t == "S":
            # clean winner 1.4–2.8R, sometimes a 3–3.8R runner
            r_mult = rng.choice([rng.uniform(1.4, 2.4), rng.uniform(2.4, 3.8)], p=[0.7, 0.3])
        else:
            r_mult = rng.choice([rng.uniform(0.9, 2.2), -rng.uniform(0.3, 1.0)], p=[0.6, 0.4])
        pnl = round(dollars_risked * r_mult, 2)

        sym = rng.choice(SYMBOLS)
        direction = rng.choice(DIRECTIONS, p=[0.6, 0.4])
        tf = rng.choice(TIMEFRAMES)
        typ = rng.choice(TYPES)
        confirmations = rng.choice(
            DEFAULT_CONFIRMATIONS, size=int(rng.integers(1, 4)), replace=False
        ).tolist()
        base = tier_score_baseline.get(str(t), 78)
        score = int(np.clip(rng.normal(loc=base, scale=3.0), 65, 99))
        grade = grade_from_score(score)

        rows.append(
            {
                "Trade #": len(rows) + 1,
                "Account": (
                    "NQ"
                    if sym == "NQ"
                    else ("Crypto (Prop)" if sym == "BTCUSDT" else "Crypto (Live)")
                ),
                "Win/Loss": "Win" if pnl > 0 else "Loss",
                "Symbol": sym,
                "Date": d,
                "Day of Week": d.strftime("%A"),
                "Direction": direction,
                "Timeframe": tf,
                "Type": typ,
                "Setup Tier": t,
                "Score": score,
                "Grade": grade,
                "Confirmations": confirmations,
                "Entry Time": e_time,
                "Exit Time": x_time,
                "Duration": "",
                "Duration (min)": float(hold),
                "PnL": pnl,
                "Dollars Risked": dollars_risked,
                "R Ratio": round(pnl / dollars_risked, 2),
                "Chart URL": "",
                "Micromanaged?": False,
                "Comments": _fake_comment(pnl > 0),
            }
        )
        preload_day += timedelta(days=1)

    # --- Fill remaining rows with weekday cadence (1–3 per day, some off days) ---
    needed = max(0, n - len(rows))
    d = start
    while needed > 0 and d <= end:
        if d.weekday() >= 5:
            # Saturday/Sunday: mostly 0–1 trade
            trades_today = rng.choice([0, 1, 2, 3], p=[0.55, 0.35, 0.09, 0.01])
        else:
            # Weekdays: 1–2 most common
            trades_today = rng.choice([0, 1, 2, 3], p=[0.12, 0.48, 0.30, 0.10])
        for _ in range(trades_today):
            if needed <= 0:
                break
            t = weighted_choice_tier()
            # date/time
            e_hour = int(
                rng.choice(
                    [6, 7, 8, 9, 10, 11, 12, 13, 14],
                    p=[0.06, 0.10, 0.14, 0.18, 0.18, 0.14, 0.10, 0.06, 0.04],
                )
            )
            e_min = int(rng.integers(0, 60))
            e_time = datetime(d.year, d.month, d.day, e_hour, e_min)
            hold = int(rng.integers(8, 160))
            x_time = e_time + timedelta(minutes=hold)

            # risk & outcome determined by tier win rate
            dollars_risked = float(rng.integers(50, 250))
            # Risk result: shape winners 1.5–3.0R with rare 6–10R; losers mostly 1.0–1.2R
            win = rng.random() < tier_winrate.get(t, 0.5)
            if win:
                r_mult = rng.choice([rng.uniform(1.5, 3.0), rng.uniform(6.0, 10.0)], p=[0.95, 0.05])
            else:
                r_mult = -rng.choice(
                    [rng.uniform(1.0, 1.2), rng.uniform(1.2, 1.6), rng.uniform(1.6, 2.0)],
                    p=[0.70, 0.20, 0.10],
                )

            pnl = round(dollars_risked * r_mult, 2)

            # symbol / meta
            # Slight tilt toward BTC/ETH/SOL; keep others present
            sym = rng.choice(
                SYMBOLS,
                p=np.array([0.20, 0.18] + [0.12] * max(0, len(SYMBOLS) - 2))[: len(SYMBOLS)]
                / np.array([0.20, 0.18] + [0.12] * max(0, len(SYMBOLS) - 2))[: len(SYMBOLS)].sum(),
            )
            direction = rng.choice(DIRECTIONS, p=[0.6, 0.4])
            tf = rng.choice(TIMEFRAMES, p=None)
            typ = rng.choice(TYPES)
            confirmations = rng.choice(
                DEFAULT_CONFIRMATIONS, size=int(rng.integers(1, 4)), replace=False
            ).tolist()

            # score & grade (tied loosely to tier)
            base = tier_score_baseline.get(str(t), 78)
            score = int(np.clip(rng.normal(loc=base, scale=3.5), 65, 99))
            grade = grade_from_score(score)

            rows.append(
                {
                    "Trade #": len(rows) + 1,
                    "Account": (
                        "NQ"
                        if sym == "NQ"
                        else ("Crypto (Prop)" if sym == "BTCUSDT" else "Crypto (Live)")
                    ),
                    "Win/Loss": "Win" if pnl > 0 else "Loss",
                    "Symbol": sym,
                    "Date": d,
                    "Day of Week": d.strftime("%A"),
                    "Direction": direction,
                    "Timeframe": tf,
                    "Type": typ,
                    "Setup Tier": t,
                    "Score": score,
                    "Grade": grade,
                    "Confirmations": confirmations,
                    "Entry Time": e_time,
                    "Exit Time": x_time,
                    "Duration": "",
                    "Duration (min)": float(hold),
                    "PnL": pnl,
                    "Dollars Risked": dollars_risked,
                    "R Ratio": round(pnl / dollars_risked, 2),
                    "Chart URL": "",
                    "Micromanaged?": False,
                    "Comments": _fake_comment(pnl > 0),
                }
            )
            needed -= 1
        d += timedelta(days=1)

    df = pd.DataFrame(rows)

    # Small shuffle so the pre-seeded tier rows aren’t all at the top visually
    df = (
        df.sample(frac=1.0, random_state=7)
        .sort_values(["Date", "Entry Time"])
        .reset_index(drop=True)
    )
    df["Trade #"] = np.arange(1, len(df) + 1)

    return _compute_derived(df)


if "journal_df" not in st.session_state:
    if DEMO_MODE:
        st.session_state.journal_df = _generate_fake_journal(300)
    else:
        st.session_state.journal_df = pd.DataFrame(
            columns=[
                "Trade #",
                "Account",
                "Win/Loss",
                "Symbol",
                "Date",
                "Day of Week",
                "Direction",
                "Timeframe",
                "Type",
                "Setup Tier",
                "Score",
                "Grade",
                "Confirmations",
                "Entry Time",
                "Exit Time",
                "Duration (min)",
                "Duration",
                "PnL",
                "Dollars Risked",
                "R Ratio",
                "Chart URL",
                "Micromanaged?",
                "Comments",
            ]
        )
    st.session_state.setdefault("new_entry_force_once", False)

    if "show_new_entry" not in st.session_state:
        st.session_state.show_new_entry = False

    # dynamic confirmation options + default selections
    st.session_state.setdefault("confirmations_options", list(DEFAULT_CONFIRMATIONS))
    st.session_state.setdefault("new_conf_text", "")
    st.session_state.setdefault("journal_conf_default", [])
    st.session_state.setdefault("new_entry_prelude", {})
    st.session_state.setdefault("accounts_options", ["NQ", "Crypto (Live)", "Crypto (Prop)"])

    # ---- Color mapping for confirmations (ASSIGN NOW so they're not grey) ----
    pal = st.session_state.setdefault(
        "confirm_color_palette",
        [
            "#1E3B8ACE",  # indigo-900
            "#0E7490CE",  # cyan-700
            "#065F46CE",  # emerald-800
            "#7C2D12CE",  # amber-900
            "#6B21A8CE",  # purple-800
            "#0F766ECE",  # teal-700
            "#1F2937CE",  # slate-800
            "#1B4079CE",  # deep steel
            "#14532DCE",  # green-900
            "#3F1D38CE",  # plum-900
            "#2B2D42CE",  # charcoal indigo
            "#23395BCE",  # dark denim
            "#2F3E46CE",  # blue-gray
            "#264653CE",  # slate teal
            "#3A0CA3CE",  # deep violet
        ],
    )

    cmap = st.session_state.setdefault("confirm_color_map", {})
    idx = st.session_state.setdefault("confirm_color_idx", 0)

    # all unique tags we know about (defaults + in current dataframe)
    known = set(DEFAULT_CONFIRMATIONS)
    try:
        dfc = st.session_state.journal_df["Confirmations"]
        for cell in dfc:
            if isinstance(cell, list):
                known.update(x for x in cell)
    except Exception:
        pass

    for tag in sorted(x for x in known if x):
        if tag not in cmap:
            cmap[tag] = pal[idx % len(pal)]
            idx += 1

    st.session_state["confirmations_options"] = sorted(st.session_state["confirm_color_map"].keys())

    st.session_state["confirm_color_idx"] = idx


def _render_new_entry_form():
    # Absolute-positioned close X (blue, borderless)
    with st.form("new_entry"):
        st.markdown('<div class="new-entry-inner">', unsafe_allow_html=True)
        # ===== Row 2: Account | Symbol | Type | Direction | Timeframe =====
        r2c0, r2c1, r2c2, r2c3, r2c4 = st.columns([1.2, 1.2, 1, 1, 1.2], gap="small")
        with r2c0:
            account = st.selectbox("Account", st.session_state.accounts_options, index=0)
        with r2c1:
            symbol = (
                st.text_input("Symbol", value="", placeholder="e.g., BTCUSDT / NQ / ETHUSDT")
                .strip()
                .upper()
            )
        with r2c2:
            typ = st.selectbox("Type", TYPES, index=1)
        with r2c3:
            direction = st.selectbox("Direction", DIRECTIONS, index=0)
        with r2c4:
            timeframe = st.text_input(
                "Timeframe", value="", placeholder="e.g., m3 / m15 / h1 / h4"
            ).strip()

        # ===== Row 1: Entry/Exit date & time =====
        r1c1, r1c2, r1c3, r1c4 = st.columns([1, 1, 1, 1], gap="small")
        with r1c1:
            date_val = st.date_input("Entry Date", value=date.today(), key="entry_date_input")
        with r1c2:
            entry_txt = st.text_input("Entry Time (HH:MM or HH:MM:SS)", value="09:30")
        with r1c3:
            exit_date_val = st.date_input("Exit Date", value=date_val, key="exit_date_input")
        with r1c4:
            exit_txt = st.text_input("Exit Time (HH:MM or HH:MM:SS)", value="10:05")

        # ===== Row 3: Dollars Risked | PnL | Chart URL =====
        r3c1, r3c2, r3c3 = st.columns([1, 1, 2], gap="small")
        with r3c1:
            risk = st.number_input("Dollars Risked ($)", value=50.0, step=5.0, format="%.2f")
        with r3c2:
            pnl = st.number_input("PnL ($)", value=100.0, step=10.0, format="%.2f")
        with r3c3:
            chart_url = st.text_input("Chart URL", value="", placeholder="https://...")

        # ===== Confirmations (full width) =====
        _conf_default = st.session_state.get("journal_conf_default") or []
        conf = st.multiselect(
            "Confirmations (multi-select)",
            st.session_state.confirmations_options,
            default=_conf_default,
            help="Loaded from Checklist (excludes Bias Confidence).",
        )

        # ===== Score / Grade (small row placed after Confirmations) =====
        SG = ["S", "A+", "A", "A-", "B+", "B", "B-", "C"]

        # defaults if "Load from Checklist" filled them earlier
        _score_default = st.session_state.get("new_entry_score_default", None)
        _grade_default = st.session_state.get("new_entry_grade_default", "")

        sg1, sg2, _ = st.columns([0.4, 0.4, 2.2], gap="small")
        with sg1:
            score = st.number_input(
                "Score (%)",
                value=_score_default if isinstance(_score_default, (int, float)) else 0,
                min_value=0,
                max_value=100,
                step=1,
                format="%d",
            )
        with sg2:
            # if grade default is in list, show it preselected; otherwise first option
            _g_idx = SG.index(_grade_default) if _grade_default in SG else 0
            grade = st.selectbox("Grade", SG, index=_g_idx)

        # Any newly typed confirmations become part of the global options + color map
        if conf:
            cmap = st.session_state["confirm_color_map"]
            pal = st.session_state["confirm_color_palette"]
            idx = st.session_state["confirm_color_idx"]
            for t in conf:
                if t not in st.session_state.confirmations_options:
                    st.session_state.confirmations_options.append(t)
                if t not in cmap:
                    cmap[t] = pal[idx % len(pal)]
                    idx += 1
            st.session_state["confirm_color_idx"] = idx

        # ===== Comments (full width) =====
        comments = st.text_area("Comments", value="")

        micro_flag = st.checkbox("Micromanaged?", value=False)

        # Footer buttons (blue outline)
        b1, b2, _, _ = st.columns([1.3, 2, 1, 7])
        with b1:
            submitted = st.form_submit_button("Add Entry")
        with b2:
            pending = st.session_state.get("pending_checklist")
            load_clicked = st.form_submit_button("Load from Checklist", disabled=(pending is None))

        if load_clicked and pending:
            confs = list(dict.fromkeys(pending.get("journal_confirms", [])))
            cmap = st.session_state["confirm_color_map"]
            pal = st.session_state["confirm_color_palette"]
            for t in confs:
                if t not in st.session_state.confirmations_options:
                    st.session_state.confirmations_options.append(t)
                if t not in cmap:
                    i = st.session_state["confirm_color_idx"] % len(pal)
                    cmap[t] = pal[i]
                    st.session_state["confirm_color_idx"] += 1

            # Prefill Score / Grade from checklist payload
            pct = pending.get("overall_pct", None)
            grd = pending.get("overall_grade", "")
            st.session_state["new_entry_score_default"] = (
                int(pct) if isinstance(pct, (int, float)) else None
            )
            st.session_state["new_entry_grade_default"] = grd

            # keep the dialog OPEN on rerun
            st.session_state["journal_conf_default"] = confs
            st.session_state["show_new_entry"] = True
            st.session_state["new_entry_force_once"] = True

            st.toast("Confirmations loaded from Checklist ✅")
            st.rerun()

        if submitted:
            entry_time = _parse_time_string(entry_txt)
            exit_time = _parse_time_string(exit_txt)
            entry_dt = datetime.combine(date_val, entry_time)
            exit_dt = datetime.combine(exit_date_val, exit_time)

            st.session_state["journal_conf_default"] = []
            st.session_state["new_entry_prelude"] = {}
            setup_tier = "A"

            new_row = {
                "Trade #": None,
                "Account": account,
                "Win/Loss": "",
                "Symbol": symbol,
                "Date": date_val,
                "Exit Date": exit_date_val,
                "Day of Week": date_val.strftime("%A"),
                "Direction": direction,
                "Timeframe": timeframe,
                "Type": typ,
                "Setup Tier": setup_tier,
                "Score": float(score) if score is not None else None,
                "Grade": grade,
                "Confirmations": conf,
                "Entry Time": entry_dt,
                "Exit Time": exit_dt,
                "Duration (min)": None,
                "Duration": "",
                "PnL": float(pnl),
                "Dollars Risked": float(risk),
                "R Ratio": None,
                "Chart URL": chart_url,
                "Micromanaged?": bool(micro_flag),
                "Comments": comments,
            }

            df = st.session_state.journal_df.copy()
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.journal_df = _compute_derived(df)

            # --- make sure the new row is visible after rerun by expanding the date filter
            rng = st.session_state.get("jr_date_range")
            new_start = date_val
            new_end = exit_date_val

            if isinstance(rng, tuple) and len(rng) == 2 and all(rng):
                cur_start, cur_end = rng
                # expand only if needed
                cur_start = min(cur_start, new_start)
                cur_end = max(cur_end, new_end)
                st.session_state["jr_date_range"] = (cur_start, cur_end)
            else:
                # if no range yet, set it to the new trade span
                st.session_state["jr_date_range"] = (new_start, new_end)

            st.session_state.show_new_entry = False
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def _render_summary(df: pd.DataFrame):
    pnl_total = float(df["PnL"].sum())
    pnl_avg = float(df["PnL"].mean())
    wins = int((df["PnL"] > 0).sum())
    total = len(df)
    win_rate = (wins / total) * 100 if total else 0.0
    r_total = float(pd.to_numeric(df["R Ratio"], errors="coerce").fillna(0).sum())
    risk_avg = float(pd.to_numeric(df["Dollars Risked"], errors="coerce").fillna(0).mean())
    dur_series = pd.to_numeric(df.get("Duration (min)", pd.Series(dtype=float)), errors="coerce")
    dur_avg_min = float(dur_series.dropna().mean()) if not dur_series.empty else 0.0

    st.markdown("---")

    if not st.session_state.get("laptop_mode", False):
        # desktop: original row of 7
        s = st.columns([1, 1, 1, 1, 1, 1, 1], gap="large")
        s[0].metric("Total Trades", f"{total:,}")
        s[1].metric("Win Rate", f"{win_rate:.1f}%")
        s[2].metric("Total PnL", f"${pnl_total:,.2f}")
        s[3].metric("Avg PnL", f"${pnl_avg:,.2f}")
        s[4].metric("Total R", f"{r_total:.2f}")
        s[5].metric("Avg Risk", f"${risk_avg:,.2f}")
        s[6].metric("Avg Duration", _friendly_minutes(dur_avg_min))
    else:
        # laptop: one wide card with compact text
        with st.container(border=False):
            st.markdown(
                f"""
                <style>
                .jr-kpi-grid{{display:grid;grid-template-columns:repeat(7,1fr);gap:12px}}
                .jr-kpi {{background:{CARD_BG};border-radius:14px;padding:10px 12px}}
                .jr-kpi h6{{margin:0 0 6px 0;font-weight:600;color:#A9B4C5;font-size:12px}}
                .jr-kpi div{{font-size:18px;color:#E8EEF7;white-space:nowrap}}
                @media (max-width:1300px){{ .jr-kpi-grid{{grid-template-columns:repeat(4,1fr)}} }}
                @media (max-width:1100px){{ .jr-kpi-grid{{grid-template-columns:repeat(3,1fr)}} }}
                </style>
                <div class="jr-kpi-grid">
                <div class="jr-kpi"><h6>Total Trades</h6><div>{total:,}</div></div>
                <div class="jr-kpi"><h6>Win Rate</h6><div>{win_rate:.1f}%</div></div>
                <div class="jr-kpi"><h6>Total PnL</h6><div>${pnl_total:,.2f}</div></div>
                <div class="jr-kpi"><h6>Avg PnL</h6><div>${pnl_avg:,.2f}</div></div>
                <div class="jr-kpi"><h6>Total R</h6><div>{r_total:.2f}</div></div>
                <div class="jr-kpi"><h6>Avg Risk</h6><div>${risk_avg:,.2f}</div></div>
                <div class="jr-kpi"><h6>Avg Duration</h6><div>{_friendly_minutes(dur_avg_min)}</div></div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ----------------------------- main render -----------------------------
df = st.session_state.get("journal_df", pd.DataFrame()).copy()


def render(*_args, **_kwargs) -> None:
    _init_session_state()

    inject_journal_css()

    # If not explicitly forcing, auto-close on rerun so it doesn’t keep popping back
    if st.session_state.get("show_new_entry") and not st.session_state.get("new_entry_force_once"):
        st.session_state["show_new_entry"] = False

    # ===== Journal-scoped CSS (overrides global date-input hiding, styles buttons/X/KPIs) =====
    st.markdown(
        f"""
<style>
/* Scope everything to Journal so we don't touch other pages */
.journal-scope * {{ box-sizing: border-box; }}


/* KPI tiles — leave as-is */
[data-testid="stMetric"],
[data-testid="stMetric"] > div {{
  background-color: {CARD_BG} !important;
  border-radius: 14px;
  padding: 18px 16px;
}}

/* Multiselect chips (uniform color) — match BaseWeb tag regardless of container */
[data-baseweb="tag"] {{
  background-color: {BLUE} !important;
  color: #0b1220 !important;
  border: 1px solid {BLUE} !important;
}}


/* dropdown menu items hover/focus (optional, to match blue theme) */
.journal-scope div[data-baseweb="select"] li[role="option"]:hover {{
  background-color: rgba(58,164,235,0.15) !important;  /* {BLUE} at ~15% */
}}

/* Inputs & dropdowns — NOT CARD_BG (slightly darker so they stand out) */
.journal-scope [data-testid="stSelectbox"],
.journal-scope [data-testid="stMultiSelect"],
.journal-scope [data-testid="stTextInput"],
.journal-scope [data-testid="stNumberInput"],
.journal-scope [data-testid="stDateInput"],
.journal-scope textarea {{
  background-color: rgba(255,255,255,0.02) !important;  /* darker than CARD_BG (0.04) */
  border: 1px solid rgba(255,255,255,0.06) !important;
  border-radius: 10px !important;
}}


/* Wrap table text (no clipping) */
.journal-scope [data-testid="stDataFrame"] td {{
  white-space: normal !important;
  word-break: break-word !important;
}}


/* Close X (inside wrapper), movable via CSS vars */
.journal-entry-wrapper {{ position: relative; }}
.journal-newentry-x {{
  position: absolute;
  top: var(--x-top, -10px);
  right: var(--x-right, -10px);
  z-index: 20;
}}
.journal-newentry-x .stButton > button {{
  color: {BLUE} !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}}

/* st.dataframe text color (explicit header + cell selectors) */
.journal-scope [data-testid="stDataFrame"] thead th {{
  color: {FG} !important;
}}

.journal-scope [data-testid="stDataFrame"] tbody td {{
  color: {FG} !important;
}}
/* Allow wrapping in the editor grid (best-effort; row height is still fixed) */
.journal-scope [data-testid="stDataEditor"] div[role="gridcell"] {{
  white-space: normal !important;
  overflow-wrap: anywhere !important;
  line-height: 2.3;
}}


/* Regular buttons: + New Entry, Add Column, Delete Column, ✕ (if you want it blue) */
[data-testid="stButton"] > button {{
  border: 1px solid var(--blue,#3AA4EB) !important;
  color: var(--blue,#3AA4EB) !important;
  background: transparent !important;
  box-shadow: none !important;
}}



/* Form submit buttons: Add Entry, Load from Checklist */
[data-testid="stFormSubmitButton"] > button {{
  border: 1px solid var(--blue,#3AA4EB) !important;
  color: var(--blue,#3AA4EB) !important;
  background: transparent !important;
  box-shadow: none !important;
}}



/* Only buttons rendered like the two Deletes (Styled view path with tooltip wrapper) */
[data-testid="stButton"] .stTooltipHoverTarget > button {{
  border: 1px solid #E06B6B !important;
  color: #E06B6B !important;
  background: transparent !important;
  box-shadow: none !important;
}}

</style>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
    <style>
    /* Dialog container = backdrop */
    div[data-testid="stDialog"] {
    /* lighten the dimmer (default is darker) */
    background-color: rgba(0,0,0,0.35) !important;
    padding: 0 !important;
    }

    /* Remove the white/grey sheet wrapper */
    div[data-testid="stDialog"] > div:first-child {
    background: transparent !important;
    box-shadow: none !important;
    width: auto !important;
    max-width: none !important;
    margin: 0 auto !important;
    }

    /* Actual dialog content node (make wide + solid background) */
    div[data-testid="stDialog"] > div > div {
    width: 1100px !important;          /* keep it 2–3× wider */
    max-width: 96vw !important;
    margin: 0 auto !important;
    background: #0f1829 !important;    /* solid card bg so it’s not transparent */
    border: none !important;
    border-radius: 12px !important;
    padding: 0 !important;
    z-index: 10001;                    /* ensure it sits above the backdrop */
    }

    /* (Optional) keep Modal parity if it appears elsewhere */
    div[data-testid="stModal"] { background-color: rgba(0,0,0,0.35) !important; padding:0 !important; }
    div[data-testid="stModal"] > div:first-child { background: transparent !important; box-shadow:none !important; }
    div[data-testid="stModal"] > div > div {
    width: 1100px !important; max-width:96vw !important; margin:0 auto !important;
    background:#0f1829 !important; border:1px solid rgba(255,255,255,0.06) !important;
    border-radius:12px !important; padding:0 !important; z-index:10001;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
    <style>
    /* ── New Entry popout: outlined inputs & selects ─────────────────────────── */
    div[data-testid="stDialog"] input,
    div[data-testid="stDialog"] textarea,
    div[data-testid="stDialog"] [data-baseweb="select"] > div,
    div[data-testid="stDialog"] [data-baseweb="input"] input {
    border: 1px solid rgba(255,255,255,0.18) !important;
    border-radius: 10px !important;
    box-shadow: none !important;
    }

    /* Hover: slightly brighter outline */
    div[data-testid="stDialog"] input:hover,
    div[data-testid="stDialog"] textarea:hover,
    div[data-testid="stDialog"] [data-baseweb="select"] > div:hover,
    div[data-testid="stDialog"] [data-baseweb="input"] input:hover {
    border-color: rgba(255,255,255,0.28) !important;
    }

    /* Focus: blue outline */
    div[data-testid="stDialog"] input:focus,
    div[data-testid="stDialog"] textarea:focus,
    div[data-testid="stDialog"] [data-baseweb="select"]:focus-within > div,
    div[data-testid="stDialog"] [data-baseweb="input"] input:focus {
    border-color: var(--blue, #3AA4EB) !important;
    box-shadow: 0 0 0 1px var(--blue, #3AA4EB) !important;
    }

    /* Disabled: keep subtle outline */
    div[data-testid="stDialog"] input[disabled],
    div[data-testid="stDialog"] [data-baseweb="select"][aria-disabled="true"] > div {
    border-color: rgba(255,255,255,0.10) !important;
    box-shadow: none !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
    <style>
    /* Fix double-outline in BaseWeb Select: remove inner input border/shadow */
    div[data-testid="stDialog"] [data-baseweb="select"] input,
    div[data-testid="stDialog"] [data-baseweb="select"] div[role="combobox"] input {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    outline: none !important;
    }

    /* Keep the border only on the outer select container */
    div[data-testid="stDialog"] [data-baseweb="select"] > div {
    border: 1px solid rgba(255,255,255,0.18) !important;
    border-radius: 10px !important;
    }
    div[data-testid="stDialog"] [data-baseweb="select"]:focus-within > div {
    border-color: var(--blue, #3AA4EB) !important;
    box-shadow: 0 0 0 1px var(--blue, #3AA4EB) !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Open scope
    st.markdown('<div class="journal-scope">', unsafe_allow_html=True)

    # ---------------- Filters ----------------
    df_all = load_journal_for_page().copy()
    df_all = _ensure_session_column(df_all)

    # Ensure Account exists for filtering
    if "Account" not in df_all.columns:
        df_all["Account"] = np.select(
            [df_all["Symbol"].eq("NQ"), df_all["Symbol"].eq("BTCUSDT")],
            ["NQ", "Crypto (Prop)"],
            default="Crypto (Live)",
        )
    else:
        backfill = np.select(
            [df_all["Symbol"].eq("NQ"), df_all["Symbol"].eq("BTCUSDT")],
            ["NQ", "Crypto (Prop)"],
            default="Crypto (Live)",
        )
        df_all["Account"] = df_all["Account"].fillna(pd.Series(backfill, index=df_all.index))

    df_all["Account"] = (
        df_all["Account"]
        .astype(str)
        .str.strip()
        .replace(
            {
                "Journal: NQ": "NQ",
                "Journal: Crypto": "Crypto (Live)",
                "Journal: Crypto (Live)": "Crypto (Live)",
                "Journal: Crypto (Prop)": "Crypto (Prop)",
            }
        )
    )

    # Row 1 (merged): Account | Date range | Direction | Day | Tier | Symbol | Session
    c_acct, c_range2, c_dir, c_day, c_tier, c_sym, c_sess = st.columns(
        [1.5, 1, 1, 1, 1, 1, 1], gap="small"
    )
    # Row 1: Account (compact) + blank space
    with c_acct:
        acct_options = sorted(df_all["Account"].astype(str).str.strip().unique().tolist())
        account_sel = st.multiselect(
            "Account", options=acct_options, default=[], help="Select none to show all accounts."
        )

    with c_range2:
        if df_all.empty:
            default_start = default_end = date.today()
        else:
            _dates_ts = pd.to_datetime(df_all["Date"], errors="coerce")
            _min_ts = _dates_ts.min()
            _max_ts = _dates_ts.max()
            default_start = _min_ts.date() if pd.notna(_min_ts) else date.today()
            default_end = _max_ts.date() if pd.notna(_max_ts) else date.today()

        # Avoid warning: don't pass a default `value` AND set the same key via Session State.
        if "jr_date_range" not in st.session_state:
            st.session_state["jr_date_range"] = (default_start, default_end)

        date_range = st.date_input(
            "Date range",
            key="jr_date_range",
            help="Filter trades between start and end date (inclusive).",
        )

        start_date, end_date = None, None
        if isinstance(date_range, tuple):
            if len(date_range) == 2 and all(date_range):
                start_date, end_date = date_range
            elif len(date_range) == 1 and date_range[0]:
                start_date = date_range[0]
        else:
            start_date = end_date = date_range

    with c_dir:
        dir_filter = st.multiselect("Direction", options=["Long", "Short"], default=[])
    with c_day:
        day_filter = st.multiselect(
            "Day of Week", options=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], default=[]
        )
    with c_tier:
        tier_filter = st.multiselect(
            "Setup Tier", options=["S", "A+", "A", "A-", "B+", "B", "B-", "C"], default=[]
        )
    with c_sym:
        sym_filter = st.multiselect("Symbol", options=sorted(df_all["Symbol"].unique()), default=[])
    with c_sess:
        session_filter = st.multiselect(
            "Session", options=["Asia", "London", "NY AM", "Lunch", "NY PM"], default=[]
        )

    # -------- Build filtered view --------
    df_view = df_all.copy()
    if account_sel:
        df_view = df_view[df_view["Account"].astype(str).str.strip().isin(account_sel)]

    if (start_date is not None) and (end_date is not None) and (not df_view.empty):
        _dates_ts = pd.to_datetime(df_view["Date"], errors="coerce")
        mask = (_dates_ts >= pd.Timestamp(start_date)) & (_dates_ts <= pd.Timestamp(end_date))
        df_view = df_view.loc[mask].copy()
    elif (start_date is not None) and (end_date is None):
        st.info("Select an end date to apply the date filter.", icon="🗓️")

    if dir_filter and not df_view.empty:
        df_view = df_view[df_view["Direction"].isin(dir_filter)]
    if day_filter and not df_view.empty:
        df_view = df_view[df_view["Day of Week"].str[:3].isin(day_filter)]
    if tier_filter and not df_view.empty:
        df_view = df_view[df_view["Setup Tier"].isin(tier_filter)]
    if sym_filter and not df_view.empty:
        df_view = df_view[df_view["Symbol"].isin(sym_filter)]
    if session_filter and not df_view.empty:
        if "Session" not in df_view.columns:
            df_view = _ensure_session_column(df_view)
        df_view = df_view[df_view["Session"].isin(session_filter)]

    if not df_view.empty:
        df_view = df_view.sort_values(
            ["Date", "Entry Time"], ascending=[True, True], kind="mergesort"
        )
        st.session_state["_view_orig_index"] = df_view.index.to_list()
        df_view = df_view.reset_index(drop=True)
        df_view["Trade #"] = df_view.index + 1
    else:
        st.session_state["_view_orig_index"] = []

    # --- Journal table (styled read-only view vs editable) ---
    view_col, _ = st.columns([1, 4])
    show_styled = view_col.toggle(
        "Styled view",
        value=True,
        help="Toggle read-only styled view (with colors) vs. editable table",
    )

    edited = None

    # --- Confirmations: build live options + colors for BOTH views ---
    # 1) start from whatever we’ve been tracking in session
    opts = list(st.session_state.get("confirmations_options", []))

    # 2) union with whatever is already in the dataframe column (lists or comma strings)
    if "Confirmations" in df_view.columns:
        series = df_view["Confirmations"].dropna()
        for v in series:
            if isinstance(v, list):
                for item in v:
                    if item and item not in opts:
                        opts.append(item)
            else:
                s = str(v).strip()
                if s and s not in ("[]", "None", "nan"):
                    for item in [x.strip() for x in s.split(",") if x.strip()]:
                        if item not in opts:
                            opts.append(item)

    # 3) ensure a stable color map (new labels get assigned a color once)
    cmap = st.session_state.get("confirm_color_map", {})
    pal = st.session_state.get("confirm_color_palette", [])
    idx = st.session_state.get("confirm_color_idx", 0)
    for t in opts:
        if t not in cmap and pal:
            cmap[t] = pal[idx % len(pal)]
            idx += 1
    st.session_state["confirm_color_map"] = cmap
    st.session_state["confirm_color_idx"] = idx

    # 4) finalize options/colors in order
    confirm_opts = sorted(opts)
    confirm_colors = [cmap.get(o, BLUE) for o in confirm_opts]
    st.session_state["confirmations_options"] = confirm_opts
    # ---------------------------------------------------------------

    if show_styled:
        df_disp = df_view.copy()

        if "Win/Loss" in df_disp.columns:

            def _wl_to_emoji(v):
                s = str(v).strip().lower()
                if s in ("win", "won", "w", "true", "1", "yes"):
                    return "✅"
                if s in ("loss", "lost", "l", "false", "0", "no"):
                    return "❌"
                return s

            df_disp["Win/Loss"] = df_disp["Win/Loss"].map(_wl_to_emoji)

        cols = list(df_disp.columns)
        if "Session" in cols and "Entry Time" in cols:
            cols.insert(cols.index("Entry Time"), cols.pop(cols.index("Session")))
            df_disp = df_disp[cols]
        cols = list(df_disp.columns)
        if "Account" in cols and "Trade #" in cols:
            acc = cols.pop(cols.index("Account"))
            cols.insert(cols.index("Trade #") + 1, acc)
            df_disp = df_disp[cols]

        base_cols = list(
            df_disp.columns
        )  # capture original order before adding any tag/display columns

        # ----- Tag columns (single-item lists) for styled view -----
        def _as_tag_list(x):
            s = "" if pd.isna(x) else str(x).strip()
            return [] if s == "" else [s]

        df_disp["Direction Tag"] = (
            df_disp["Direction"].map(_as_tag_list) if "Direction" in df_disp.columns else []
        )
        df_disp["Type Tag"] = df_disp["Type"].map(_as_tag_list) if "Type" in df_disp.columns else []
        df_disp["Session Tag"] = (
            df_disp["Session"].map(_as_tag_list) if "Session" in df_disp.columns else []
        )
        df_disp["Tier Tag"] = (
            df_disp["Setup Tier"].map(_as_tag_list) if "Setup Tier" in df_disp.columns else []
        )
        df_disp["DOW Tag"] = (
            df_disp["Day of Week"].map(_as_tag_list) if "Day of Week" in df_disp.columns else []
        )
        df_disp["Timeframe Tag"] = (
            df_disp["Timeframe"].map(_as_tag_list) if "Timeframe" in df_disp.columns else []
        )

        # Options + dark colors for each tag set (order matters: options[i] uses color[i])
        DIR_OPTS = ["Long", "Short"]
        DIR_COLORS = ["#065F46", "#7C2D12"]  # emerald-800, amber-900

        TYPE_OPTS = ["Continuation", "Reversal"]
        TYPE_COLORS = ["#0E7490", "#7C2D12"]  # cyan-700, amber-900

        SESS_OPTS = ["Asia", "London", "NY AM", "NY Lunch", "NY PM"]
        SESS_COLORS = ["#1E3A8A", "#0E7490", "#6B21A8", "#7C2D12", "#1B4079"]

        TIER_OPTS = ["S", "A+", "A", "A-", "B+", "B", "B-", "C"]
        TIER_COLORS = [
            "#e8f160",
            "#a78bfa",
            "#a78bfa",
            "#a78bfa",
            "#1e97e7",
            "#1e97e7",
            "#1e97e7",
            "#41ce2f",
        ]

        DOW_OPTS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        DOW_COLORS = ["#23395B", "#0F766E", "#6B21A8", "#7C2D12", "#1E3A8A", "#2F3E46", "#3F1D38"]

        TF_OPTS = ["m1", "m3", "m5", "m15", "m30", "H1", "H4"]
        TF_COLORS = ["#23395B", "#2F3E46", "#0E7490", "#1E3A8A", "#6B21A8", "#7C2D12", "#1B4079"]

        confirm_opts = sorted(st.session_state.confirmations_options)
        confirm_colors = [st.session_state.confirm_color_map.get(o, BLUE) for o in confirm_opts]

        # PnL display with negative sign before the currency symbol
        def _fmt_money_sign_after(x):
            if pd.isna(x):
                return ""
            v = float(x)
            if v < 0:
                return f"-${abs(v):,.2f}"
            return f"${v:,.2f}"

        df_disp["PnL ($)"] = df_disp["PnL"].apply(_fmt_money_sign_after)

        REQUIRED_COLS = ["Exit Time", "Score", "Grade"]
        for _c in REQUIRED_COLS:
            if _c not in df_disp.columns:
                df_disp[_c] = pd.NA

        # keep Score numeric for formatting/sorting
        df_disp["Score"] = pd.to_numeric(df_disp["Score"], errors="coerce")

        # Start from the original order only (no auto-added columns)
        col_order = base_cols[:]  # copy

        def _put_after_in(col_list, orig: str, tag: str):
            """Insert `tag` immediately after `orig` if both exist and tag not yet in order."""
            if orig in col_list and tag in df_disp.columns and tag not in col_list:
                col_list.insert(col_list.index(orig) + 1, tag)

        # Insert all tag columns right AFTER their originals (while originals are still present)
        _put_after_in(col_order, "Direction", "Direction Tag")
        _put_after_in(col_order, "Type", "Type Tag")
        _put_after_in(col_order, "Session", "Session Tag")
        _put_after_in(col_order, "Setup Tier", "Tier Tag")
        _put_after_in(col_order, "Day of Week", "DOW Tag")
        _put_after_in(col_order, "Win/Loss", "Result Tag")
        _put_after_in(col_order, "Timeframe", "Timeframe Tag")
        # Put Score & Grade immediately to the right of Setup Tier (or Tier Tag if you hide Setup Tier)
        anchor = "Setup Tier" if "Setup Tier" in col_order else "Tier Tag"
        _put_after_in(col_order, anchor, "Score")
        _put_after_in(col_order, "Score", "Grade")

        # Swap 'PnL' for the formatted display column (no duplicates)
        if "PnL" in col_order and "PnL ($)" in df_disp.columns:
            col_order[col_order.index("PnL")] = "PnL ($)"

        # Finally remove original text columns you no longer want to show
        for orig in ["Day of Week", "Direction", "Timeframe", "Type", "Setup Tier", "Session"]:
            if orig in col_order:
                col_order.remove(orig)

        st.dataframe(
            df_disp,  # styled view now uses the display DF with tag columns
            use_container_width=True,
            height=680,
            hide_index=True,
            column_order=col_order,
            column_config={
                # Native colored tags
                "Confirmations": st.column_config.MultiselectColumn(
                    "Confirmations",
                    options=confirm_opts,
                    color=confirm_colors,
                    width="large",
                ),
                "Direction Tag": st.column_config.MultiselectColumn(
                    "Direction", options=DIR_OPTS, color=DIR_COLORS, width="small"
                ),
                "Type Tag": st.column_config.MultiselectColumn(
                    "Type", options=TYPE_OPTS, color=TYPE_COLORS, width="small"
                ),
                "Session Tag": st.column_config.MultiselectColumn(
                    "Session", options=SESS_OPTS, color=SESS_COLORS, width="small"
                ),
                "Tier Tag": st.column_config.MultiselectColumn(
                    "Setup Tier", options=TIER_OPTS, color=TIER_COLORS, width="small"
                ),
                "Score": st.column_config.NumberColumn("Score (%)", format="%d", width="small"),
                "Grade": st.column_config.TextColumn("Grade", width="small"),
                "DOW Tag": st.column_config.MultiselectColumn(
                    "Day of Week", options=DOW_OPTS, color=DOW_COLORS, width="small"
                ),
                "Timeframe Tag": st.column_config.MultiselectColumn(
                    "Timeframe", options=TF_OPTS, color=TF_COLORS, width="small"
                ),
                "Micromanaged?": st.column_config.CheckboxColumn("Micromanaged?", width="small"),
                # Keep your existing configs for numbers/links etc. as needed (PnL, Dollars Risked…)
                # Example numeric configs if you want them here as well:
                "PnL ($)": st.column_config.TextColumn("PnL ($)", width="small"),
                "Dollars Risked": st.column_config.NumberColumn(
                    "Dollars Risked ($)", format="$%.2f", width="small"
                ),
                "R Ratio": st.column_config.NumberColumn(
                    "R:R", format="%.2f", width="small", disabled=True
                ),
                "Chart URL": st.column_config.LinkColumn("Chart URL", width="medium"),
            },
        )

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        t1, _ = st.columns([1, 5])
        if t1.button("+ New Entry", key="btn_new_entry_below"):
            st.session_state.show_new_entry = True
            st.session_state.new_entry_force_once = True
            st.rerun()

    else:
        if "__sel__" not in df_view.columns:
            df_view = df_view.copy()
            df_view.insert(0, "__sel__", False)

        cols = list(df_view.columns)
        if "Session" in cols and "Entry Time" in cols:
            s = cols.pop(cols.index("Session"))
            cols.insert(cols.index("Entry Time"), s)
            if "__sel__" in cols:
                cols.remove("__sel__")
                cols = ["__sel__"] + cols
            df_view = df_view[cols]
        cols = list(df_view.columns)
        if "Account" in cols and "Trade #" in cols:
            acc = cols.pop(cols.index("Account"))
            cols.insert(cols.index("Trade #") + 1, acc)
            if "__sel__" in cols:
                cols.remove("__sel__")
                cols = ["__sel__"] + cols
            df_view = df_view[cols]
        if "Micromanaged?" not in df_view.columns:
            df_view["Micromanaged?"] = False

        st.markdown('<div class="je-grid-root"></div>', unsafe_allow_html=True)

        cols = list(df_view.columns)
        if "Setup Tier" in cols:
            # place Score then Grade after "Setup Tier" if present
            for name in ["Grade", "Score"][::-1]:  # insert Score first, then Grade
                if name in cols:
                    # remove and reinsert right after "Setup Tier"
                    cols.insert(cols.index("Setup Tier") + 1, cols.pop(cols.index(name)))
            df_view = df_view[cols]

        REQ_EDITOR_COLS = ["Exit Time", "Score", "Grade"]
        for _c in REQ_EDITOR_COLS:
            if _c not in df_view.columns:
                df_view[_c] = pd.NA

        df_view["Score"] = pd.to_numeric(df_view["Score"], errors="coerce")

        # optional: place Score & Grade after Setup Tier
        cols = list(df_view.columns)
        if "Setup Tier" in cols:
            for name in ["Grade", "Score"][::-1]:
                if name in cols:
                    cols.insert(cols.index("Setup Tier") + 1, cols.pop(cols.index(name)))
            df_view = df_view[cols]

        edited = st.data_editor(
            df_view,
            key="journal_editor",
            num_rows="dynamic",
            use_container_width=True,
            height=680,
            hide_index=True,
            column_config={
                "__sel__": st.column_config.CheckboxColumn("", help="Select row", width="small"),
                "Trade #": st.column_config.NumberColumn("Trade #", width="small", disabled=True),
                "Account": st.column_config.SelectboxColumn(
                    "Account", options=st.session_state.accounts_options, width="medium"
                ),
                "Win/Loss": st.column_config.TextColumn("Win/Loss", disabled=True, width="small"),
                "Symbol": st.column_config.TextColumn(
                    "Symbol", width="small", help="Type any symbol, e.g., BTCUSDT, NQ"
                ),
                "Date": st.column_config.DateColumn("Date", format="MMM D, YYYY", width="medium"),
                "Day of Week": st.column_config.TextColumn(
                    "Day of Week", width="small", disabled=True
                ),
                "Direction": st.column_config.SelectboxColumn(
                    "Direction", options=DIRECTIONS, width="small"
                ),
                "Timeframe": st.column_config.TextColumn(
                    "Timeframe", width="small", help="e.g., 3m / 15m / 1h"
                ),
                "Type": st.column_config.SelectboxColumn("Type", options=TYPES, width="small"),
                "Setup Tier": st.column_config.SelectboxColumn(
                    "Setup Tier", options=TIER, width="small"
                ),
                "Score": st.column_config.NumberColumn("Score (%)", format="%d", width="small"),
                "Grade": st.column_config.SelectboxColumn(
                    "Grade", options=["S", "A+", "A", "A-", "B+", "B", "B-", "C"], width="small"
                ),
                "Confirmations": st.column_config.MultiselectColumn(
                    "Confirmations",
                    options=confirm_opts,
                    color=confirm_colors,
                    width="large",
                ),
                "Entry Time": st.column_config.DatetimeColumn(
                    "Entry Time", step=60, width="medium"
                ),
                "Exit Time": st.column_config.DatetimeColumn("Exit Time", step=60, width="medium"),
                "Duration (min)": st.column_config.NumberColumn(
                    "Duration (min)", format="%d", disabled=True, width="small"
                ),
                "Duration": st.column_config.TextColumn("Duration", disabled=True, width="small"),
                "PnL": st.column_config.NumberColumn("PnL ($)", format="$%.2f", width="small"),
                "Dollars Risked": st.column_config.NumberColumn(
                    "Dollars Risked ($)", format="$%.2f", width="small"
                ),
                "R Ratio": st.column_config.NumberColumn(
                    "R:R", format="%.2f", width="small", disabled=True
                ),
                "Chart URL": st.column_config.LinkColumn("Chart URL", width="medium"),
                "Micromanaged?": st.column_config.CheckboxColumn("Micromanaged?", width="small"),
                "Comments": st.column_config.TextColumn("Comments", width="large"),
            },
        )

        sel_mask = edited["__sel__"].fillna(False).astype(bool)
        sel_rows = edited.index[sel_mask].tolist()
        orig_index_map = st.session_state.get("_view_orig_index", []) or []
        rows_to_delete_idx = [orig_index_map[i] for i in sel_rows if 0 <= i < len(orig_index_map)]

        t1, t2, _ = st.columns([1, 1, 13])
        if t1.button("+ New Entry", key="btn_new_entry_styled"):
            st.session_state.show_new_entry = True
            st.rerun()

        delete_disabled = len(rows_to_delete_idx) == 0
        if t2.button(
            "Delete selected", disabled=delete_disabled, key="btn_delete_selected", help="danger"
        ):
            st.session_state["_pending_delete_idx"] = rows_to_delete_idx
            st.session_state["_show_delete_modal"] = True
            st.rerun()

        # --- Popout confirm using the same modal helper ---
        if st.session_state.get("_show_delete_modal"):

            def _delete_body():
                count = len(st.session_state.get("_pending_delete_idx", []))
                st.write(f"Are you sure you want to delete **{count}** trade(s)?")
                c_yes, c_no = st.columns(2)
                with c_yes:
                    if st.button(
                        "Yes, delete",
                        type="primary",
                        use_container_width=True,
                        key="confirm_delete_yes",
                    ):
                        idxs = st.session_state.get("_pending_delete_idx", [])
                        main = st.session_state.journal_df.copy()
                        main = main.drop(index=idxs, errors="ignore").reset_index(drop=True)
                        st.session_state.journal_df = _compute_derived(main)
                        st.session_state.pop("_pending_delete_idx", None)
                        st.session_state["_show_delete_modal"] = False
                        st.rerun()
                with c_no:
                    if st.button("Cancel", use_container_width=True, key="confirm_delete_no"):
                        st.session_state.pop("_pending_delete_idx", None)
                        st.session_state["_show_delete_modal"] = False
                        st.rerun()

            modal_or_inline("Confirm deletion", _delete_body)

        st.markdown("---")

        col_add, col_del = st.columns([1, 1], gap="small")
        with col_add:
            new_col_name = st.text_input(
                "Add new column", value="", placeholder="e.g., 'Mistake Tag'"
            )
            if st.button("Add Column", key="btn_add_col") and new_col_name.strip():
                name = new_col_name.strip()
                if name not in st.session_state.journal_df.columns:
                    st.session_state.journal_df[name] = ""
                    st.rerun()

        with col_del:
            existing_cols = [
                c for c in st.session_state.journal_df.columns if c not in ("Trade #",)
            ]
            del_choice = st.selectbox(
                "Delete column", options=["(Select)"] + existing_cols, index=0
            )
            if (
                st.button("Delete Column", key="btn_del_col", help="danger")
                and del_choice
                and del_choice != "(Select)"
            ):
                df_tmp = st.session_state.journal_df.copy()
                if del_choice in df_tmp.columns:
                    df_tmp = df_tmp.drop(columns=[del_choice])
                    st.session_state.journal_df = df_tmp
                    st.rerun()

        existing_mask = edited["Trade #"].notna()
        new_mask = edited["Trade #"].isna()

        main = st.session_state.journal_df.copy()
        editable_cols = [
            c
            for c in edited.columns
            if c in main.columns
            and c
            not in (
                "Trade #",
                "__sel__",
                "Duration",
                "Duration (min)",
                "R Ratio",
                "Win/Loss",
                "Day of Week",
            )
        ]
        orig_index_map = st.session_state.get("_view_orig_index", []) or []

        ed_existing = edited.loc[existing_mask, editable_cols].copy()
        if not ed_existing.empty and orig_index_map:
            try:
                ed_existing.index = [orig_index_map[i] for i in ed_existing.index]
                main.loc[ed_existing.index, editable_cols] = ed_existing
            except Exception:
                pass

        ed_new = edited.loc[new_mask].copy()
        if not ed_new.empty:
            ed_new = ed_new.drop(columns=["__sel__"], errors="ignore")
            ed_new = ed_new[[c for c in ed_new.columns if c in main.columns]]
            combined = pd.concat([main, ed_new], ignore_index=True)
        else:
            combined = main

        if not combined.equals(st.session_state.journal_df):
            st.session_state.journal_df = _compute_derived(combined)

    # New entry form (centered 15/70/15; borderless; movable X)
    if st.session_state.show_new_entry:

        def _new_entry_body():
            _render_new_entry_form()  # no extra containers/cards

        modal_or_inline("New Entry", _new_entry_body)

        if st.session_state.get("new_entry_force_once"):
            st.session_state["new_entry_force_once"] = False

    # Summary metrics (single row)
    _render_summary(df_view)

    # Close scope
    st.markdown("</div>", unsafe_allow_html=True)

    # Persist journal on any change (private only)
    _autosave_journal()
