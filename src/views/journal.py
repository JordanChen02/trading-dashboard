# src/views/journal.py
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Tuple

import numpy as np
import pandas as pd
import streamlit as st

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

    # Earliest -> latest (ascending)
    df = df.sort_values(
        ["Date", "Entry Time"], ascending=[True, True], kind="mergesort"
    ).reset_index(drop=True)
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
            symbol = st.selectbox("Symbol", SYMBOLS, index=0)
            direction = st.selectbox("Direction", DIRECTIONS, index=0)
            timeframe = st.selectbox("Timeframe", TIMEFRAMES, index=2)
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

        submit = st.form_submit_button("Add Entry", use_container_width=True)
        if submit:
            # Build datetimes for entry/exit
            e_time = datetime.combine(date_val, _parse_time_string(entry_txt))
            x_time = datetime.combine(date_val, _parse_time_string(exit_txt))
            if x_time <= e_time:
                x_time = e_time + timedelta(minutes=15)

            # Enforce TP sum ≤ 100
            t_sum = tp1 + tp2 + tp3
            if t_sum > 100:
                # reduce TP3 then TP2 to fit
                over = t_sum - 100
                adj_tp3 = max(0, tp3 - over)
                over = max(0, over - (tp3 - adj_tp3))
                adj_tp2 = max(0, tp2 - over)
                tp3, tp2 = adj_tp3, adj_tp2

            df = st.session_state.journal_df.copy()
            next_trade_num = int(df["Trade #"].max()) + 1 if not df.empty else 1
            row = {
                "Trade #": next_trade_num,
                "Symbol": symbol,
                "Date": date_val,
                "Day of Week": date_val.strftime("%A"),
                "Direction": direction,
                "Timeframe": timeframe,
                "Type": typ,
                "Setup Tier": setup_tier,
                "Execution Tier": exec_tier,
                "Confirmations": conf,
                "Entry Time": e_time,
                "Exit Time": x_time,
                "Duration": "",
                "Duration (min)": (x_time - e_time).total_seconds() / 60.0,
                "PnL": float(pnl),
                "Win/Loss": "Win" if pnl > 0 else ("Loss" if pnl < 0 else "Break-even"),
                "Dollars Risked": float(risk),
                "R Ratio": round(float(pnl) / float(risk), 2) if risk else 0.0,
                "Chart URL": chart_url,
                "Comments": comments,
                "TP1 % Sold": int(tp1),
                "TP2 % Sold": int(tp2),
                "TP3 % Sold": int(tp3),
            }
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            st.session_state.journal_df = _compute_derived(df)
            st.success("Entry added.")
            st.session_state.show_new_entry = False


def _render_summary(df: pd.DataFrame):
    pnl_total = float(df["PnL"].sum())
    pnl_avg = float(df["PnL"].mean())
    wins = int((df["PnL"] > 0).sum())
    total = len(df)
    win_rate = (wins / total) * 100 if total else 0.0
    r_avg = float(pd.to_numeric(df["R Ratio"], errors="coerce").fillna(0).mean())
    risk_sum = float(pd.to_numeric(df["Dollars Risked"], errors="coerce").fillna(0).sum())
    dur_avg_min = float(pd.to_numeric(df["Duration (min)"], errors="coerce").fillna(0).mean())
    dur_total_min = float(pd.to_numeric(df["Duration (min)"], errors="coerce").fillna(0).sum())

    st.markdown("---")
    # Single-row summary
    s = st.columns([1, 1, 1, 1, 1, 1, 1, 1], gap="large")
    s[0].metric("Total Trades", f"{total:,}")
    s[1].metric("Win Rate", f"{win_rate:.1f}%")
    s[2].metric("Total PnL", f"${pnl_total:,.2f}")
    s[3].metric("Avg PnL", f"${pnl_avg:,.2f}")
    s[4].metric("Avg R", f"{r_avg:.2f}")
    s[5].metric("Total Risk", f"${risk_sum:,.2f}")
    s[6].metric("Avg Duration", _friendly_minutes(dur_avg_min))
    s[7].metric("Total Duration", _friendly_minutes(dur_total_min))


# ----------------------------- main render -----------------------------
def render(*_args, **_kwargs) -> None:
    """
    Journal page:
    - Notion-like table with rounded edges listing trades (earliest -> latest)
    - 50 placeholder entries on first load (overall profitable)
    - "+ New Entry" button opens a form to append a row
    - Summary metrics shown in a single row under the table

    Accepts and ignores args so it's compatible with app.py calls like
    render_journal(df_view).
    """
    _init_session_state()

    st.subheader("Journal")
    st.caption(
        "Manual trade log. Add notes, confirmations, and manage entries. (Fake data preloaded)"
    )

    # Table card container
    with st.container(border=True):
        st.markdown("#### Trades")

        # Editable table (earliest -> latest already enforced by _compute_derived)
        edited = st.data_editor(
            st.session_state.journal_df,
            num_rows="dynamic",
            use_container_width=True,
            height=520,
            hide_index=True,
            column_config={
                "Trade #": st.column_config.NumberColumn("Trade #", width="small", disabled=True),
                "Symbol": st.column_config.SelectboxColumn(
                    "Symbol", options=SYMBOLS, width="small"
                ),
                "Date": st.column_config.DateColumn("Date", format="MMM D, YYYY", width="medium"),
                "Day of Week": st.column_config.TextColumn(
                    "Day of Week", width="small", disabled=True
                ),
                "Direction": st.column_config.SelectboxColumn(
                    "Direction", options=DIRECTIONS, width="small"
                ),
                "Timeframe": st.column_config.SelectboxColumn(
                    "Timeframe", options=TIMEFRAMES, width="small"
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

        # Recompute derived fields and save back if user edited
        if not edited.equals(st.session_state.journal_df):
            st.session_state.journal_df = _compute_derived(edited)

        # "+ New Entry" button
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        add_col, _ = st.columns([1, 5])
        if add_col.button("+ New Entry", use_container_width=True):
            st.session_state.show_new_entry = True

    # New entry form (modal-like section)
    if st.session_state.show_new_entry:
        with st.container(border=True):
            _render_new_entry_form()

    # Summary metrics (single row)
    _render_summary(st.session_state.journal_df)
