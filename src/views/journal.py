# src/views/journal.py
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from src.styles import inject_journal_css

# ----------------------------- config -----------------------------
SYMBOLS = ["NQ", "BTCUSDT", "ETHUSDT", "ASTERUSDT", "AVAXUSDT", "PUMPUSDT", "SOLUSDT"]
DIRECTIONS = ["Long", "Short"]
TIMEFRAMES = ["m1", "m3", "m5", "m15", "m30", "H1", "H4"]
TYPES = ["Reversal", "Continuation"]
# Expanded tiers per request
TIER = ["S", "A+", "A", "A-", "B+", "B", "B-", "C"]
EXEC_TIER = ["S", "A+", "A", "A-", "B+", "B", "B-", "C"]

DEFAULT_CONFIRMATIONS = [
    "IFVG",
    "Liq Sweep",
    "Momentum",
    "Data H/L DOL",
    "Macro",
    "Breaker",
    "Confluence",
]


# --- Styler helpers for value-based coloring (read-only view) ---
def _style_pnl(val):
    try:
        v = float(val)
    except Exception:
        return ""
    if v > 0:
        return "color:#22c55e;font-weight:700;"  # green
    if v < 0:
        return "color:#ef4444;font-weight:700;"  # red
    return "color:#e5e7eb;font-weight:600;"


def _style_direction(val: str):
    if str(val).lower() == "long":
        return "color:#22c55e;font-weight:600;"
    if str(val).lower() == "short":
        return "color:#ef4444;font-weight:600;"
    return ""


def _style_tier(val: str):
    s = str(val).upper().strip()
    if s == "S":
        return "background:rgba(253,224,71,0.18);border-radius:12px;padding:2px 6px;"
    if s.startswith("A"):
        return "background:rgba(34,197,94,0.18);border-radius:12px;padding:2px 6px;"
    if s.startswith("B"):
        return "background:rgba(245,158,11,0.18);border-radius:12px;padding:2px 6px;"
    if s.startswith("C"):
        return "background:rgba(148,163,184,0.18);border-radius:12px;padding:2px 6px;"
    return ""


def _style_day(val: str):
    day = str(val)[:3].lower()
    palette = {
        "mon": "#60a5fa",  # blue
        "tue": "#14b8a6",  # teal
        "wed": "#a78bfa",  # purple
        "thu": "#f59e0b",  # amber
        "fri": "#38bdf8",  # sky
        "sat": "#94a3b8",  # slate
        "sun": "#94a3b8",
    }
    color = palette.get(day, "#e5e7eb")
    return f"color:{color};font-weight:600;"


def _styled_view(df: pd.DataFrame) -> "pd.io.formats.style.Styler":
    # keep display order as-is (you already sort & renumber in _compute_derived)
    styler = df.style

    # Column-wise applymap for value-based colors
    col_funcs = {
        "PnL": _style_pnl,
        "Direction": _style_direction,
        "Setup Tier": _style_tier,
        "Execution Tier": _style_tier,
        "Day of Week": _style_day,
    }
    for col, fn in col_funcs.items():
        if col in df.columns:
            styler = styler.applymap(fn, subset=pd.IndexSlice[:, [col]])

    # Optional: tighten fonts a touch for readability
    styler = styler.set_properties(**{"font-size": "0.95rem"})

    # Let Streamlit handle widths; you already use use_container_width=True
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
    """Make sure df has a Session column computed in the selected timezone."""
    if "Session" in df.columns:
        return df

    tz_label = st.session_state.get("journal_tz", "(UTC -4) America/New York")
    tz_name = _resolve_tz(tz_label)

    ts = pd.to_datetime(df["Entry Time"], errors="coerce", utc=False)
    try:
        if ts.dt.tz is None:
            ts = ts.dt.tz_localize(tz_name)
        else:
            ts = ts.dt.tz_convert(tz_name)
    except Exception:
        ts = pd.to_datetime(df["Entry Time"], errors="coerce").dt.tz_localize(tz_name)

    mins = ts.dt.hour * 60 + ts.dt.minute

    def in_range(m, start, end, wrap=False):
        if wrap:  # cross midnight
            return (m >= start) | (m < end)
        return (m >= start) & (m < end)

    asia = in_range(mins, 20 * 60, 0, wrap=True)  # 20:00–00:00
    london = in_range(mins, 2 * 60, 5 * 60)  # 02:00–05:00
    ny_am = in_range(mins, 9 * 60 + 30, 11 * 60)  # 09:30–11:00
    ny_lunch = in_range(mins, 12 * 60, 13 * 60)  # 12:00–13:00
    ny_pm = in_range(mins, 13 * 60 + 30, 16 * 60)  # 13:30–16:00

    session = pd.Series("", index=df.index, dtype="object")
    session[asia] = "Asia"
    session[london] = "London"
    session[ny_am] = "NY AM"
    session[ny_lunch] = "NY Lunch"
    session[ny_pm] = "NY PM"
    out = df.copy()
    out["Session"] = session
    return out


def _resolve_tz(label: str | None) -> str:
    """
    Convert UI labels like '(UTC -4) America/New York' into valid tz names
    like 'America/New_York'. Falls back to 'UTC' if unknown.
    """
    if not label:
        return "UTC"
    s = str(label).strip()

    # If it has a leading '(UTC ...)' prefix, strip it
    if ") " in s and s.startswith("("):
        s = s.split(") ", 1)[1].strip()

    # Known special cases
    special = {
        "America/New York": "America/New_York",
        "America/Los Angeles": "America/Los_Angeles",
        "Asia/Hong Kong": "Asia/Hong_Kong",
    }
    if s in special:
        return special[s]

    # For Region/City names with spaces in City, replace spaces with underscores
    if "/" in s:
        reg, city = s.split("/", 1)
        return f"{reg}/{city.replace(' ', '_')}"

    # Allow 'UTC' or already-correct tz names to pass through
    return s


def _parse_time_string(t: str) -> datetime.time:
    """
    Accepts 'H:M', 'HH:MM', or 'HH:MM:SS'. Falls back to current minute on failure.
    """
    t = (t or "").strip()
    try:
        # Try explicit formats first
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(t, fmt).time()
            except ValueError:
                pass
        # Last resort: pandas parser
        return pd.to_datetime(t).time()
    except Exception:
        now = datetime.now().replace(second=0, microsecond=0)
        return now.time()


def _compute_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Recompute derived fields and sort earliest->latest."""
    df = df.copy()

    # Normalize dates/times
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    df["Day of Week"] = pd.to_datetime(df["Date"]).dt.day_name()

    et = pd.to_datetime(df["Entry Time"], errors="coerce")
    xt = pd.to_datetime(df["Exit Time"], errors="coerce")
    dur_min = (xt - et).dt.total_seconds() / 60.0
    df["Duration (min)"] = dur_min.round(1)
    df["Duration"] = df["Duration (min)"].apply(
        lambda x: _friendly_minutes(x) if pd.notna(x) else "—"
    )

    # Labels & R
    df["Win/Loss"] = np.where(df["PnL"] > 0, "Win", np.where(df["PnL"] < 0, "Loss", "Break-even"))
    risk = pd.to_numeric(df["Dollars Risked"], errors="coerce").replace(0, np.nan)
    df["R Ratio"] = (df["PnL"] / risk).replace([np.inf, -np.inf], np.nan).round(2).fillna(0.0)

    # Clean partials 0..100
    for c in ["TP1 % Sold", "TP2 % Sold", "TP3 % Sold"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).clip(0, 100).astype(int)

    # ---- Derived: Session from Entry Time in selected timezone ----
    # Pull chosen tz (default to America/New_York)
    tz_label = st.session_state.get("journal_tz", "(UTC -4) America/New York")
    tz_name = _resolve_tz(tz_label)

    ts = pd.to_datetime(df["Entry Time"], errors="coerce")
    try:
        if ts.dt.tz is None:
            ts = ts.dt.tz_localize(tz_name)
        else:
            ts = ts.dt.tz_convert(tz_name)
    except Exception:
        ts = pd.to_datetime(df["Entry Time"], errors="coerce").dt.tz_localize(tz_name)

    mins = ts.dt.hour * 60 + ts.dt.minute

    # Windows (in the chosen timezone). You said these are in EST; we interpret them
    # in whatever tz is selected so the logic remains consistent for the user.
    # Asia   = 20:00–00:00
    # London = 02:00–05:00
    # NY AM  = 09:30–11:00
    # NY Lunch = 12:00–13:00
    # NY PM  = 13:30–16:00
    def in_range(m, start, end, wrap=False):
        if wrap:  # across midnight (e.g., 20:00–00:00)
            return (m >= start) | (m < end)
        return (m >= start) & (m < end)

    asia = in_range(mins, 20 * 60, 0, wrap=True)
    london = in_range(mins, 2 * 60, 5 * 60)
    ny_am = in_range(mins, 9 * 60 + 30, 11 * 60)
    ny_lunch = in_range(mins, 12 * 60, 13 * 60)
    ny_pm = in_range(mins, 13 * 60 + 30, 16 * 60)

    session = pd.Series("", index=df.index, dtype="object")
    session[asia] = "Asia"
    session[london] = "London"
    session[ny_am] = "NY AM"
    session[ny_lunch] = "NY Lunch"
    session[ny_pm] = "NY PM"
    df["Session"] = session

    # ---- Sort + renumber (earliest → latest) ----
    df = df.sort_values(
        ["Date", "Entry Time"], ascending=[True, True], kind="mergesort"
    ).reset_index(drop=True)
    df["Trade #"] = df.index + 1

    return df


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
    """
    Return (tp1, tp2, tp3) where values are % of position sold.
    Rules:
      - Winners: TP1 almost always hits; TP2 sometimes; TP3 rarely. Sum <= 100.
      - Losers: partial at TP1 occasionally then BE (e.g., 40/0/0), often 0/0/0.
    """
    if is_win:
        # TP1 30-60%, TP2 0-40% (40–60% chance), TP3 0-30% (10–20% chance)
        tp1 = int(rng.integers(30, 61))
        tp2 = int(rng.integers(10, 41)) if rng.random() < 0.55 else 0
        # keep headroom for tp3: don't exceed 100
        max_tp3 = max(0, 100 - (tp1 + tp2))
        tp3 = 0
        # Only try for TP3 when there's at least 10% left to allocate
        if max_tp3 >= 10 and rng.random() < 0.18:
            tp3 = int(rng.integers(10, min(31, max_tp3 + 1)))
        # ensure sum <= 100
        s = tp1 + tp2 + tp3
        if s > 100:
            # trim tp3 first, then tp2
            over = s - 100
            if tp3 >= over:
                tp3 -= over
            else:
                over -= tp3
                tp3 = 0
                tp2 = max(0, tp2 - over)
        return tp1, tp2, tp3
    # Losers: sometimes partial TP1 then BE; otherwise no partials
    if rng.random() < 0.35:
        return int(rng.integers(20, 51)), 0, 0  # e.g., 40/0/0
    return 0, 0, 0


def _generate_fake_journal(n: int = 50) -> pd.DataFrame:
    """Generate a realistic, overall-profitable set of placeholder trades."""
    rng = np.random.default_rng(42)
    rows = []
    start = date.today() - timedelta(days=120)

    # Bias to profitable overall: ~58-62% wins
    win_flags = rng.random(n) < rng.uniform(0.58, 0.62)

    for i in range(n):
        sym = rng.choice(SYMBOLS, p=[0.18, 0.2, 0.18, 0.1, 0.12, 0.1, 0.12])
        direction = rng.choice(DIRECTIONS, p=[0.6, 0.4])
        tf = rng.choice(TIMEFRAMES, p=[0.15, 0.08, 0.3, 0.25, 0.12, 0.07, 0.03])
        typ = rng.choice(TYPES, p=[0.45, 0.55])
        setup_tier = rng.choice(TIER, p=[0.03, 0.12, 0.25, 0.12, 0.15, 0.2, 0.08, 0.05])
        exec_tier = rng.choice(EXEC_TIER, p=[0.03, 0.15, 0.35, 0.12, 0.12, 0.15, 0.06, 0.02])

        # Date & times
        d = start + timedelta(days=int(rng.integers(0, 120)))
        start_hour = int(rng.integers(8, 20))
        start_min = int(rng.integers(0, 60))
        e_time = datetime(d.year, d.month, d.day, start_hour, start_min)
        hold_minutes = int(rng.integers(5, 180))
        x_time = e_time + timedelta(minutes=hold_minutes)

        # Risk & PnL
        dollars_risked = float(rng.integers(50, 250))
        r = float(rng.uniform(0.5, 3.0)) if win_flags[i] else -float(rng.uniform(0.2, 1.5))
        pnl = round(dollars_risked * r, 2)

        # Partials
        tp1, tp2, tp3 = _generate_tp_distribution(rng, pnl > 0)

        # Confirmations (1–3)
        confirmations = rng.choice(
            DEFAULT_CONFIRMATIONS, size=int(rng.integers(1, 4)), replace=False
        ).tolist()

        rows.append(
            {
                "Trade #": i + 1,  # earliest first by number, but we'll sort by date/time
                "Symbol": sym,
                "Date": d,
                "Day of Week": d.strftime("%A"),
                "Direction": direction,
                "Timeframe": tf,
                "Type": typ,
                "Setup Tier": setup_tier,
                "Execution Tier": exec_tier,
                "Confirmations": confirmations,
                "Entry Time": e_time,
                "Exit Time": x_time,
                "Duration": "",
                "Duration (min)": float(hold_minutes),
                "PnL": pnl,
                "Win/Loss": "Win" if pnl > 0 else "Loss",
                "Dollars Risked": dollars_risked,
                "R Ratio": round(pnl / dollars_risked, 2),
                "Chart URL": "",
                "Comments": _fake_comment(pnl > 0),
                "TP1 % Sold": tp1,
                "TP2 % Sold": tp2,
                "TP3 % Sold": tp3,
            }
        )

    df = pd.DataFrame(rows)
    return _compute_derived(df)


def _init_session_state():
    if "journal_df" not in st.session_state:
        st.session_state.journal_df = _generate_fake_journal(50)
    if "show_new_entry" not in st.session_state:
        st.session_state.show_new_entry = False
    # dynamic confirmation options (add by typing + Enter)
    if "confirmations_options" not in st.session_state:
        st.session_state.confirmations_options = list(DEFAULT_CONFIRMATIONS)
    if "new_conf_text" not in st.session_state:
        st.session_state.new_conf_text = ""


# ----------------------------- UI -----------------------------
def _add_confirmation_tag():
    txt = (st.session_state.new_conf_text or "").strip()
    if txt and txt not in st.session_state.confirmations_options:
        st.session_state.confirmations_options.append(txt)
    st.session_state.new_conf_text = ""  # clear after add


def _render_new_entry_form():
    # --- Minimal close "X" (no box) ---
    st.markdown('<div class="journal-newentry-x">', unsafe_allow_html=True)
    hx1, hx2 = st.columns([10, 1], gap="small")
    with hx2:
        if st.button("✕", key="close_new_entry", help="Close"):
            st.session_state.show_new_entry = False
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # Quick-add confirmation tag (type & Enter to add to options)
    st.markdown("**Add a custom confirmation (type and press Enter):**")
    st.text_input(
        "New confirmation",
        value=st.session_state.new_conf_text,
        key="new_conf_text",
        label_visibility="collapsed",
        on_change=_add_confirmation_tag,
        placeholder="e.g., 'Breaker Retest'",
        help="Type a new confirmation and press Enter to add it to the dropdown.",
    )

    with st.form("new_entry"):
        st.markdown("### New Journal Entry")

        c1, c2, c3 = st.columns(3)
        with c1:
            date_val = st.date_input("Date", value=date.today())
            symbol = (
                st.text_input(
                    "Symbol",
                    value="",
                    placeholder="e.g., BTCUSDT / NQ / ETHUSDT",
                )
                .strip()
                .upper()
            )
            direction = st.selectbox("Direction", DIRECTIONS, index=0)
            timeframe = st.text_input(
                "Timeframe",
                value="",
                placeholder="e.g., m3 / m15 / h1 / h4",
            ).strip()
        with c2:
            # Free text times
            entry_txt = st.text_input("Entry Time (HH:MM or HH:MM:SS)", value="09:30")
            exit_txt = st.text_input("Exit Time (HH:MM or HH:MM:SS)", value="10:05")
            typ = st.selectbox("Type", TYPES, index=1)
            setup_tier = st.selectbox("Setup Tier", TIER, index=2)
        with c3:
            exec_tier = st.selectbox("Execution Tier", EXEC_TIER, index=2)
            pnl = st.number_input("PnL ($)", value=100.0, step=10.0, format="%.2f")
            risk = st.number_input("Dollars Risked ($)", value=50.0, step=5.0, format="%.2f")
            chart_url = st.text_input("Chart URL", value="", placeholder="https://...")

        conf = st.multiselect(
            "Confirmations (multi-select)",
            st.session_state.confirmations_options,
            default=["Momentum"] if "Momentum" in st.session_state.confirmations_options else [],
            help="Use the box above to add a new option, then select it here.",
        )
        comments = st.text_area("Comments", value="")

        p1, p2, p3 = st.columns(3)
        with p1:
            tp1 = st.number_input("TP1 % Sold", 0, 100, 50, step=5)
        with p2:
            tp2 = st.number_input("TP2 % Sold", 0, 100, 25, step=5)
        with p3:
            tp3 = st.number_input("TP3 % Sold", 0, 100, 25, step=5)
        st.caption(
            "Tip: Values mean how much of the position you sold at each TP (e.g., 50/25/25). Total ≤ 100."
        )

        submitted = st.form_submit_button("Add Entry", use_container_width=True)
        if submitted:
            # Convert the free-text HH:MM to datetimes on the chosen date
            entry_time = _parse_time_string(entry_txt)
            exit_time = _parse_time_string(exit_txt)
            entry_dt = datetime.combine(date_val, entry_time)
            exit_dt = datetime.combine(date_val, exit_time)

            new_row = {
                "Trade #": None,  # will be set by _compute_derived
                "Symbol": symbol,
                "Date": date_val,
                "Day of Week": date_val.strftime("%A"),
                "Direction": direction,
                "Timeframe": timeframe,
                "Type": typ,
                "Setup Tier": setup_tier,
                "Execution Tier": exec_tier,
                "Confirmations": conf,
                "Entry Time": entry_dt,
                "Exit Time": exit_dt,
                "Duration (min)": None,  # computed in _compute_derived
                "Duration": "",  # computed in _compute_derived
                "PnL": float(pnl),
                "Win/Loss": "",  # computed in _compute_derived
                "Dollars Risked": float(risk),
                "R Ratio": None,  # computed in _compute_derived
                "Chart URL": chart_url,
                "Comments": comments,
                "TP1 % Sold": int(tp1),
                "TP2 % Sold": int(tp2),
                "TP3 % Sold": int(tp3),
            }

            df = st.session_state.journal_df.copy()
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.journal_df = _compute_derived(df)

            # Close the form and refresh immediately so filters/options update
            st.session_state.show_new_entry = False
            st.rerun()


def _render_summary(df: pd.DataFrame):
    pnl_total = float(df["PnL"].sum())
    pnl_avg = float(df["PnL"].mean())
    wins = int((df["PnL"] > 0).sum())
    total = len(df)
    win_rate = (wins / total) * 100 if total else 0.0
    r_total = float(pd.to_numeric(df["R Ratio"], errors="coerce").fillna(0).sum())
    risk_avg = float(pd.to_numeric(df["Dollars Risked"], errors="coerce").fillna(0).mean())
    dur_avg_min = float(pd.to_numeric(df["Duration (min)"], errors="coerce").fillna(0).mean())

    st.markdown("---")
    # Single-row summary
    s = st.columns([1, 1, 1, 1, 1, 1, 1], gap="large")
    s[0].metric("Total Trades", f"{total:,}")
    s[1].metric("Win Rate", f"{win_rate:.1f}%")
    s[2].metric("Total PnL", f"${pnl_total:,.2f}")
    s[3].metric("Avg PnL", f"${pnl_avg:,.2f}")
    s[4].metric("Total R", f"{r_total:.2f}")
    s[5].metric("Avg Risk", f"${risk_avg:,.2f}")
    s[6].metric("Avg Duration", _friendly_minutes(dur_avg_min))


# ----------------------------- main render -----------------------------
def render(*_args, **_kwargs) -> None:
    _init_session_state()

    inject_journal_css()

    st.subheader("Journal")

    st.caption(
        "Manual trade log. Add notes, confirmations, and manage entries. (Fake data preloaded)"
    )

    # ---------------- Filters: Journal switcher + Timezone + Date range + facets ----------------
    df_all = st.session_state.journal_df

    # Row 1: Journal | Timezone | Date range
    c_journal, c_tz, c_range = st.columns([1, 1, 2], gap="small")

    with c_journal:
        journal_choice = st.selectbox(
            "Journal",
            ["All", "NQ", "Crypto"],
            index=0,
            help="Choose which journal to view.",
        )

    with c_tz:
        tz_default = st.session_state.get("journal_tz", "(UTC -4) America/New York")
        tz_options = [
            "UTC",
            "(UTC -4) America/New York",
            "(UTC -5) America/Chicago",
            "(UTC -7) America/Los Angeles",
            "(UTC +1) Europe/London",
            "(UTC +2) Europe/Berlin",
            "(UTC +9) Asia/Tokyo",
            "(UTC +8) Asia/Hong Kong",
        ]
        tz_choice = st.selectbox(
            "Timezone",
            tz_options,
            index=tz_options.index(tz_default),
            help="Used to compute Session buckets and time-based filters.",
        )
        if tz_choice != tz_default:
            st.session_state["journal_tz"] = tz_choice
            st.session_state.journal_df = _compute_derived(st.session_state.journal_df.copy())
            df_all = st.session_state.journal_df  # refresh local ref after recompute

    with c_range:
        if df_all.empty:
            default_start = default_end = date.today()
        else:
            # Work in Timestamp, then convert to date—avoids comparing dates to NaN
            _dates_ts = pd.to_datetime(df_all["Date"], errors="coerce")
            _min_ts = _dates_ts.min()
            _max_ts = _dates_ts.max()
            default_start = _min_ts.date() if pd.notna(_min_ts) else date.today()
            default_end = _max_ts.date() if pd.notna(_max_ts) else date.today()

        date_range = st.date_input(
            "Date range",
            value=(default_start, default_end),
            help="Filter trades between start and end date (inclusive).",
        )
        # Normalize safely
        start_date, end_date = None, None
        if isinstance(date_range, tuple):
            if len(date_range) == 2 and all(date_range):
                start_date, end_date = date_range
            elif len(date_range) == 1 and date_range[0]:
                start_date = date_range[0]  # wait for end_date
        else:
            start_date = end_date = date_range

    # Row 2: Direction | Day | Tier | Symbol | Session  (compact dropdowns)
    c_dir, c_day, c_tier, c_sym, c_sess = st.columns([1, 1, 1, 1, 1], gap="small")

    with c_dir:
        dir_filter = st.multiselect("Direction", options=["Long", "Short"], default=[])

    with c_day:
        day_filter = st.multiselect(
            "Day of Week",
            options=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            default=[],
            help="Matches first three letters (Mon…Sun).",
        )

    with c_tier:
        tier_filter = st.multiselect(
            "Tier",
            options=["S", "A+", "A", "A-", "B+", "B", "B-", "C"],
            default=[],
            help="Matches either Setup or Execution tier.",
        )

    with c_sym:
        sym_options = sorted(df_all["Symbol"].dropna().unique().tolist())
        sym_filter = st.multiselect("Symbol", options=sym_options, default=[])

    with c_sess:
        session_filter = st.multiselect(
            "Session",
            options=["Asia", "London", "NY AM", "NY Lunch", "NY PM"],
            default=[],
        )
    # ---------------- End filters header ----------------

    # -------- Build filtered view --------
    df_view = df_all.copy()

    # Journal switcher
    if journal_choice == "NQ":
        df_view = df_view[df_view["Symbol"] == "NQ"]
    elif journal_choice == "Crypto":
        df_view = df_view[df_view["Symbol"] != "NQ"]

    # Date filter (inclusive) — only when both dates chosen
    if (start_date is not None) and (end_date is not None) and (not df_view.empty):
        _dates_ts = pd.to_datetime(df_view["Date"], errors="coerce")
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        mask = (_dates_ts >= start_ts) & (_dates_ts <= end_ts)
        df_view = df_view.loc[mask].copy()

    elif (start_date is not None) and (end_date is None):
        st.info("Select an end date to apply the date filter.", icon="🗓️")

    # Direction
    if dir_filter and not df_view.empty:
        df_view = df_view[df_view["Direction"].isin(dir_filter)]

    # Day of Week (by 3-letter prefix)
    if day_filter and not df_view.empty:
        df_view = df_view[df_view["Day of Week"].str[:3].isin(day_filter)]

    # Tier (either setup or execution)
    if tier_filter and not df_view.empty:
        df_view = df_view[
            df_view["Setup Tier"].isin(tier_filter) | df_view["Execution Tier"].isin(tier_filter)
        ]

    # Symbols
    if sym_filter and not df_view.empty:
        df_view = df_view[df_view["Symbol"].isin(sym_filter)]

    # Session
    if session_filter and not df_view.empty:
        if "Session" not in df_view.columns:
            df_view = _ensure_session_column(df_view)
        df_view = df_view[df_view["Session"].isin(session_filter)]

    # Keep chronological order and renumber Trade # for the view
    # Also keep a mapping back to the underlying df_all index for selection/deletion
    if not df_view.empty:
        df_view = df_view.sort_values(
            ["Date", "Entry Time"], ascending=[True, True], kind="mergesort"
        )
        st.session_state["_view_orig_index"] = df_view.index.to_list()
        df_view = df_view.reset_index(drop=True)
        df_view["Trade #"] = df_view.index + 1
    else:
        st.session_state["_view_orig_index"] = []

    # ---------------- End filters ----------------

    # Table card container
    with st.container(border=True):
        st.markdown("#### Trades")

    # ---- Journal table (styled read-only view vs editable) ----
    view_col, _ = st.columns([1, 4])
    show_styled = view_col.toggle(
        "Styled view",
        value=False,
        help="Toggle read-only styled view (with colors) vs. editable table",
    )
    edited = None  # important: defined regardless of branch

    if show_styled:
        # Read-only, value-colored view (filtered)
        st.dataframe(
            _styled_view(df_view),
            use_container_width=True,
            height=520,
            hide_index=True,
        )
    else:
        # Ensure our own selection column exists in the view (first column)
        if "__sel__" not in df_view.columns:
            df_view = df_view.copy()
            df_view.insert(0, "__sel__", False)  # insert as first col

        # Editable table (filtered)
        edited = st.data_editor(
            df_view,
            key="journal_editor",
            num_rows="dynamic",
            use_container_width=True,
            height=520,
            hide_index=True,
            column_config={
                "__sel__": st.column_config.CheckboxColumn(
                    "",  # blank header, looks like a native selector
                    help="Select row",
                    width="small",
                ),
                "Trade #": st.column_config.NumberColumn("Trade #", width="small", disabled=True),
                "Symbol": st.column_config.TextColumn(
                    "Symbol", width="small", help="Type any symbol, e.g., BTCUSDT, NQ, ETHUSDT"
                ),
                "Date": st.column_config.DateColumn("Date", format="MMM D, YYYY", width="medium"),
                "Day of Week": st.column_config.TextColumn(
                    "Day of Week", width="small", disabled=True
                ),
                "Direction": st.column_config.SelectboxColumn(
                    "Direction", options=["Long", "Short"], width="small"
                ),
                "Timeframe": st.column_config.TextColumn(
                    "Timeframe", width="small", help="Type any timeframe, e.g., 3m / 1h / 4h"
                ),
                "Type": st.column_config.SelectboxColumn("Type", options=TYPES, width="small"),
                "Setup Tier": st.column_config.SelectboxColumn(
                    "Setup Tier", options=TIER, width="small"
                ),
                "Execution Tier": st.column_config.SelectboxColumn(
                    "Execution Tier", options=EXEC_TIER, width="small"
                ),
                "Confirmations": st.column_config.ListColumn(
                    "Confirmations",
                    help="Checklist items that confirmed the setup.",
                    width="medium",
                ),
                "Entry Time": st.column_config.DatetimeColumn(
                    "Entry Time", step=60, width="medium"
                ),
                "Exit Time": st.column_config.DatetimeColumn("Exit Time", step=60, width="medium"),
                "Duration (min)": st.column_config.NumberColumn(
                    "Duration (min)", disabled=True, width="small"
                ),
                "Duration": st.column_config.TextColumn("Duration", disabled=True, width="small"),
                "PnL": st.column_config.NumberColumn("PnL ($)", format="$%.2f", width="small"),
                "Win/Loss": st.column_config.TextColumn("Win/Loss", disabled=True, width="small"),
                "Dollars Risked": st.column_config.NumberColumn(
                    "Dollars Risked ($)", format="$%.2f", width="small"
                ),
                "R Ratio": st.column_config.NumberColumn(
                    "R Ratio", format="%.2f", width="small", disabled=True
                ),
                "Chart URL": st.column_config.LinkColumn("Chart URL", width="medium"),
                "Comments": st.column_config.TextColumn("Comments", width="large"),
                "TP1 % Sold": st.column_config.NumberColumn(
                    "TP1 % Sold", min_value=0, max_value=100, step=5
                ),
                "TP2 % Sold": st.column_config.NumberColumn(
                    "TP2 % Sold", min_value=0, max_value=100, step=5
                ),
                "TP3 % Sold": st.column_config.NumberColumn(
                    "TP3 % Sold", min_value=0, max_value=100, step=5
                ),
            },
        )

    # --- Handle selection, toolbar, deletion, and merge-back ---
    # Rows marked via our selection column
    sel_mask = edited["__sel__"].fillna(False).astype(bool) if "__sel__" in edited.columns else None
    sel_rows = edited.index[sel_mask].tolist() if sel_mask is not None else []

    # Map selected *view* rows to underlying df indices we saved earlier
    orig_index_map = st.session_state.get("_view_orig_index", []) or []
    rows_to_delete_idx = [orig_index_map[i] for i in sel_rows if 0 <= i < len(orig_index_map)]

    ed_state = st.session_state.get("journal_editor") or {}
    sel_dict = ed_state.get("selection") or ed_state.get("selected") or {}

    raw_rows = []
    if isinstance(sel_dict, dict):
        raw_rows = sel_dict.get("rows", []) or []

    # Accept ints, numpy ints, or dicts like {"row": 3}
    from numbers import Integral

    for item in list(raw_rows) if not isinstance(raw_rows, (set, tuple)) else list(raw_rows):
        if isinstance(item, Integral):
            sel_rows.append(int(item))
        elif isinstance(item, dict) and "row" in item:
            try:
                sel_rows.append(int(item["row"]))
            except Exception:
                pass

    # Map selected view-row indices -> underlying df indices saved earlier
    orig_index_map = st.session_state.get("_view_orig_index", []) or []
    rows_to_delete_idx = [orig_index_map[i] for i in sel_rows if 0 <= i < len(orig_index_map)]

    # 3B) Toolbar: + New Entry and Delete selected
    t1, t2, _ = st.columns([1, 1, 4])
    if t1.button("+ New Entry", use_container_width=True, key="btn_new_entry_below"):
        st.session_state.show_new_entry = True
        st.rerun()

    delete_disabled = len(rows_to_delete_idx) == 0
    if t2.button(
        "Delete selected",
        use_container_width=True,
        disabled=delete_disabled,
        key="btn_delete_selected",
    ):
        st.session_state["_pending_delete_idx"] = rows_to_delete_idx
        st.session_state["_show_delete_modal"] = True
        st.rerun()

    # 3C) Confirm deletion (pseudo-modal that works on all Streamlit versions)
    confirm_box = st.empty()
    if st.session_state.get("_show_delete_modal"):
        with confirm_box.container():
            st.markdown("### Confirm deletion")
            count = len(st.session_state.get("_pending_delete_idx", []))
            st.write(f"Are you sure you want to delete **{count}** trade(s)?")

            c_yes, c_no = st.columns(2)
            yes = c_yes.button(
                "Yes, delete",
                type="primary",
                use_container_width=True,
                key="confirm_delete_yes",
            )
            no = c_no.button(
                "Cancel",
                use_container_width=True,
                key="confirm_delete_no",
            )

            if yes:
                idxs = st.session_state.get("_pending_delete_idx", [])
                if idxs:
                    main = st.session_state.journal_df.copy()
                    main = main.drop(index=idxs, errors="ignore").reset_index(drop=True)
                    st.session_state.journal_df = _compute_derived(main)
                # clear state + close box
                st.session_state.pop("_pending_delete_idx", None)
                st.session_state["_show_delete_modal"] = False
                confirm_box.empty()
                st.rerun()

            if no:
                st.session_state.pop("_pending_delete_idx", None)
                st.session_state["_show_delete_modal"] = False
                confirm_box.empty()
                st.rerun()

    # 3D) Merge normal edits back (robust for new rows)
    if not st.session_state.get("_show_delete_modal", False):
        # Split edited into existing vs newly added by presence of Trade #
        existing_mask = edited["Trade #"].notna()
        new_mask = edited["Trade #"].isna()

        # Existing rows: de-duplicate by Trade # and update only overlapping IDs
        ed_existing = edited.loc[existing_mask].copy()
        main = st.session_state.journal_df.copy()
        if not ed_existing.empty:
            ed_existing = ed_existing.drop_duplicates(subset=["Trade #"], keep="last")
            editable_cols = [
                c for c in ed_existing.columns if c in main.columns and c not in ("Trade #",)
            ]
            main_idx = main.set_index("Trade #", drop=False)
            ed_idx = ed_existing.set_index("Trade #", drop=False)
            ed_slice = ed_idx[editable_cols]
            common_ids = ed_slice.index.intersection(main_idx.index)
            if not common_ids.empty:
                main_idx.loc[common_ids, editable_cols] = ed_slice.loc[common_ids, editable_cols]
            main_updated = main_idx.reset_index(drop=True)
        else:
            main_updated = main

        # New rows (from the "+" in the table): append safely
        ed_new = edited.loc[new_mask].copy()
        if not ed_new.empty:
            # Keep only columns that the main df has
            ed_new = ed_new[[c for c in ed_new.columns if c in main_updated.columns]]
            combined = pd.concat([main_updated, ed_new], ignore_index=True)
        else:
            combined = main_updated

        if not combined.equals(st.session_state.journal_df):
            st.session_state.journal_df = _compute_derived(combined)

    # New entry form (modal-like section)
    if st.session_state.show_new_entry:
        with st.container(border=True):
            _render_new_entry_form()

    # Summary metrics (single row)
    _render_summary(df_view)
