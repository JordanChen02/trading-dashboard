# src/views/calendar.py
from __future__ import annotations

import calendar as pycal
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

# Theme (fall back safely if your theme module differs)
try:
    from src.theme import BLUE, BLUE_FILL, CARD_BG, FG, FG_MUTED, RED
except Exception:
    FG = "#dbe4ee"
    FG_MUTED = "rgba(219,228,238,.6)"
    BLUE = "#3AA4EB"
    BLUE_FILL = "rgba(58,164,235,.12)"
    RED = "#ef4444"

GREEN = "#22c55e"
AMBER = "#f59e0b"
GREEN_BG = "rgba(34,197,94,0.16)"
GREEN_BD = "rgba(34,197,94,0.30)"
RED_BG = "rgba(224,107,107,0.18)"
RED_BD = "rgba(224,107,107,0.35)"
AMBER_BG = "rgba(245,158,11,0.16)"
AMBER_BD = "rgba(245,158,11,0.32)"
NEUTRAL_BG = "rgba(148,163,184,0.12)"
NEUTRAL_BD = "rgba(148,163,184,0.28)"


@dataclass
class DayStats:
    pnl: float = 0.0
    r: float = 0.0
    pct: float = 0.0  # % vs equity *before* this day
    equity_before: float = 0.0
    equity_after: float = 0.0


# ---------- CSS ----------
def _inject_css():
    st.markdown(
        f"""
<style>
  .cal-wrap {{ margin-top: 4px; }}

  .cal-header {{
    display:flex; align-items:center; justify-content:space-between;
    margin: 4px 0 12px 0;
  }}

  .cal-left {{ display:flex; align-items:center; gap:10px; }}
  .cal-title {{
    margin:0; font-size:18px; color:{FG}; font-weight:800; letter-spacing:.2px;
    position: relative; top: -6px;  /* title nudge */
  }}

  /* Outline buttons (VIEW TRADES, legacy) */
  .btn-outline {{
    background: transparent; color:{BLUE};
    border:1px solid {BLUE}; padding:6px 12px; border-radius:10px; font-weight:800;
    cursor:pointer; text-transform:uppercase;
  }}
  .btn-outline:hover {{ background:{BLUE_FILL}; }}

  /* Chevron buttons (legacy HTML variant — harmless if unused) */
  .chev-btn {{
    background: transparent; color:{FG};
    border:none; padding:6px 10px; border-radius:10px; font-weight:900; font-size:18px;
    cursor:pointer; line-height:1; transform: translateY(-2px);
  }}
  .chev-btn:hover {{ background:{BLUE_FILL}; }}

  /* Right side: chips next to view trades */
  .cal-agg {{
    display:flex; align-items:center; gap:10px; flex-wrap:nowrap; white-space:nowrap;
  }}

  .chip-plain {{
    display:inline-flex; align-items:center; gap:6px;
    padding: 0; border:none; background: transparent; font-weight:800; color:{FG};
  }}

  .tri-up {{
    width:0;height:0;border-left:5px solid transparent;border-right:5px solid transparent;border-bottom:8px solid {GREEN};
    display:inline-block; transform: translateY(1px);
  }}
  .tri-down {{
    width:0;height:0;border-left:5px solid transparent;border-right:5px solid transparent;border-top:8px solid {RED};
    display:inline-block; transform: translateY(-1px);
  }}

  .chip-rr {{
    display:inline-flex; align-items:center; gap:6px;
    padding: 6px 10px; border-radius:10px; font-weight:800;
  }}

  .view-btn .btn-outline {{ padding:6px 16px; min-width:140px; }}

  /* GRID */
  .cal-grid {{
    display:grid;
    grid-template-columns: repeat(8, 1fr);
    gap: 8px;
  }}

  .cal-colhead {{
    text-align:center;
    font-size:16px;
    color:{FG_MUTED};
    border: 1px solid rgba(255,255,255,0.06);  
    border-radius: 12px; padding: 8px;
    background: {CARD_BG};
    padding:8px;
    font-weight:700;
    text-transform:capitalize;
  }}

  .cal-cell, .week-wrap {{
    position: relative;
    min-height: 180px;
    background: {CARD_BG};
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px; padding: 8px;
  }}

  .cal-cell.blank {{ background: rgba(0,0,0,0.22); }}
  .cal-cell.today {{ box-shadow: 0 0 0 1.5px {BLUE} inset; }}

  .day-num {{ position:absolute; top:6px; left:8px; font-size:14px; color:{FG_MUTED}; font-weight:700; }}

  .day-card, .week-card {{
    margin-top: 20px; padding: 25px 10px 8px; border-radius: 14px; border: 1px solid transparent; font-size:17px; font-weight:600;min-height: 130px;text-align:center;
  }}

  .day-card .money .pct {{ font-size:14px; font-weight:800; color:{FG}; margin-bottom:4px; text-align:center; }}

  .pct {{
    color:{FG_MUTED}; display:flex; align-items:center; justify-content:center; gap:6px; margin-bottom:6px;
  }}
  .rr {{
    display:inline-block; font-weight:800; font-size:16px; letter-spacing:.2px;
    padding: 2px 8px; border-radius: 999px; color:#d1d5db; background: rgba(255,255,255,0.06);
  }}

  .week-label {{ display:none; }}

/* TODAY (col 1): blue text + blue 1px border */
div[data-testid="stHorizontalBlock"]:has(h2.cal-title)
  [data-testid="stColumn"]:nth-of-type(1) [data-testid="stButton"] > button {{
  background: transparent !important;
  border: 1px solid {BLUE} !important;
  color: {BLUE} !important;
  box-shadow: none !important;
  font-weight: 900;
  font-size: 18px;
  padding: 6px 10px;
  border-radius: 10px;
  line-height: 1;
  transform: translateY(62px);
}}
div[data-testid="stHorizontalBlock"]:has(h2.cal-title)
  [data-testid="stColumn"]:nth-of-type(1) [data-testid="stButton"] > button:hover {{
  background: {BLUE_FILL} !important;
}}

/* CHEVRONS (cols 2 & 4): white text, NO border, slight upward nudge */
div[data-testid="stHorizontalBlock"]:has(h2.cal-title)
  [data-testid="stColumn"]:nth-of-type(2) [data-testid="stButton"] > button,
div[data-testid="stHorizontalBlock"]:has(h2.cal-title)
  [data-testid="stColumn"]:nth-of-type(4) [data-testid="stButton"] > button {{
  background: transparent !important;
  border: none !important;
  color: {FG} !important;
  box-shadow: none !important;
  font-weight: 900;
  font-size: 18px;
  padding: 0px 24px;
  border-radius: 10px;
  line-height: 1;
  transform: translateY(46px);
}}

/***** Style the 'VIEW TRADES' popover trigger like the blue outline button *****/
div[data-testid="stHorizontalBlock"]:has(h2.cal-title)
  [data-testid="stColumn"]:nth-of-type(5) [data-testid="stPopover"] > div > button {{
  background: transparent !important;
  border: 1px solid {BLUE} !important;
  color: {BLUE} !important;
  box-shadow: none !important;
  font-weight: 800 !important;
  text-transform: uppercase;
  border-radius: 10px !important;
  padding: 6px 16px !important;
  min-width: 140px;
  line-height: 1.1;
  transform: translateY(16px);
}}
div[data-testid="stHorizontalBlock"]:has(h2.cal-title)
  [data-testid="stColumn"]:nth-of-type(5) [data-testid="stPopover"] > div > button:hover {{
  background: {BLUE_FILL} !important;
}}

div[data-testid="stHorizontalBlock"]:has(h2.cal-title)
  [data-testid="stColumn"]:nth-of-type(2) [data-testid="stButton"] > button:hover,
div[data-testid="stHorizontalBlock"]:has(h2.cal-title)
  [data-testid="stColumn"]:nth-of-type(4) [data-testid="stButton"] > button:hover {{
  background: {BLUE_FILL} !important;
}}

/* Pull the whole header row (the one with the month title) upward to close the top gap */
div[data-testid="stHorizontalBlock"]:has(h2.cal-title) {{
  margin-top: -50px !important;   /* adjust: -20 to -36px as needed */
  padding-top: 0 !important;
}}

  /* colors for numbers in hover rows */
  .cal-pos {{ color: #22c55e !important; }}
  .cal-neg {{ color: #ef4444 !important; }}
  .cal-zero {{ color: rgba(229,231,235,0.72) !important; }}

  /* ensure the tooltip works on the day card */
  .day-card {{ position: relative; }}
  .day-card .hover-tip {{
    visibility: hidden;
    opacity: 0;
    transition: opacity 120ms ease;
    position: absolute;
    left: 8px;
    bottom: calc(100% + 8px);
    min-width: 400px;
    max-width: 420px;
    padding: 10px 12px;
    background: rgba(13,18,30,0.98);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    z-index: 30;
    box-shadow: 0 8px 24px rgba(0,0,0,0.35);
  }}
  .day-card:hover .hover-tip {{ visibility: visible; opacity: 1; }}

  .hover-tip .tr {{ display: grid; grid-template-columns: 1fr 0.9fr 1fr 0.8fr 0.7fr; gap: 10px; align-items: center; padding: 4px 0; }}
  .hover-tip .tr.head {{
    font-size: 12px;
    color: rgba(229,231,235,0.70);
    border-bottom: 1px dashed rgba(229,231,235,0.14);
    margin-bottom: 6px;
    padding-bottom: 6px;
  }}
  .hover-tip .sym {{ color: #E5E7EB; font-weight: 700; font-size: 13px; }}
  .hover-tip .dir {{ color: rgba(229,231,235,0.85); font-size: 13px; }}
  .hover-tip .pnl, .hover-tip .pct, .hover-tip .rr {{ font-size: 13px; }}
  
    /* ensure the tooltip works on the week (Total) card */
  .week-card {{ position: relative; }}
  .week-card .hover-tip {{
    visibility: hidden;
    opacity: 0;
    transition: opacity 120ms ease;
    position: absolute;
    right: 8px;  
    left: auto;  
    bottom: calc(100% + 8px);
    min-width: 320px;
    max-width: 420px;
    padding: 10px 12px;
    background: rgba(13,18,30,0.98);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    z-index: 30;
    box-shadow: 0 8px 24px rgba(0,0,0,0.35);
  }}
  .week-card:hover .hover-tip {{ visibility: visible; opacity: 1; }}

  /* wider layout for Total (weekly) tooltip – day tooltip unchanged */
  .hover-tip.total {{ min-width: 640px; max-width: 640px; }}

  /* 6 columns: Date | Symbol | PnL | Direction | % | R:R */
  .hover-tip.total .tr {{
    display: grid;
    grid-template-columns: 0.9fr 1fr 1fr 0.9fr 0.7fr 0.7fr;
    gap: 10px;
    align-items: center;
    padding: 4px 0;
  }}


  /* wider layout for Total (weekly) tooltip – leaves day tooltip unchanged */
  .hover-tip.total {{ min-width: 520px; max-width: 640px; }}

  /* 6 columns: Date | Symbol | PnL | Direction | % | R:R */
  .hover-tip.total .tr {{
    display: grid;
    grid-template-columns: 0.9fr 1fr 1fr 0.9fr 0.7fr 0.7fr;
    gap: 10px;
    align-items: center;
    padding: 4px 0;
  }}
/* Date column text size in week (Total) hover */
.hover-tip.total .dt {{
  font-size: 14px;    /* try 11–13 to taste */
  line-height: 1.2;   /* optional: tighten vertical spacing */
  font-weight: 600;   /* optional: make it a bit lighter/heavier */
}}

# ----- VIEW TRADES popover table layout -----
.view-trades-table {{
  min-width: 520px;   /* keeps the table wide enough to avoid wraps */
  max-width: 720px;
}}
.view-trades-table .vt-row {{
  display: grid !important;
  grid-template-columns: 0.9fr 1fr 0.9fr 0.9fr 0.7fr 0.7fr; /* Date | Symbol | Direction | PnL | % | R:R */
  gap: 10px;
  align-items: center;
  padding: 6px 0;
}}
.view-trades-table .vt-row.vt-hdr {{
  font-weight: 700;
  color: rgba(229,231,235,0.80);
  border-bottom: 1px dashed rgba(229,231,235,0.18);
  margin-bottom: 6px;
  padding-bottom: 6px;
}}
.view-trades-table .pnl,
.view-trades-table .pct,
.view-trades-table .rr {{ text-align: left; }}

/* reuse your color classes */
.view-trades-table .cal-pos {{ color: #22c55e !important; }}
.view-trades-table .cal-neg {{ color: #ef4444 !important; }}
.view-trades-table .cal-zero {{ color: rgba(229,231,235,0.72) !important; }}


</style>
        """,
        unsafe_allow_html=True,
    )


# ---------- data ----------
def _ensure_df() -> pd.DataFrame:
    # First preference: a pre-filtered, normalized view injected by app.py
    cal_df = st.session_state.get("cal_df")
    if isinstance(cal_df, pd.DataFrame):
        return cal_df.copy()

    # Fallback (legacy): raw journal_df from session (no global selector)
    if "journal_df" in st.session_state and isinstance(st.session_state.journal_df, pd.DataFrame):
        df = st.session_state.journal_df.copy()
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
        else:
            df["Date"] = pd.NaT
        if "PnL" not in df.columns and "pnl" in df.columns:
            df["PnL"] = pd.to_numeric(df["pnl"], errors="coerce")
        elif "PnL" in df.columns:
            df["PnL"] = pd.to_numeric(df["PnL"], errors="coerce")
        else:
            df["PnL"] = 0.0
        if "R Ratio" not in df.columns and "r" in df.columns:
            df["R Ratio"] = pd.to_numeric(df["r"], errors="coerce")
        elif "R Ratio" in df.columns:
            df["R Ratio"] = pd.to_numeric(df["R Ratio"], errors="coerce")
        else:
            df["R Ratio"] = 0.0
        return df

    return pd.DataFrame(columns=["Date", "PnL", "R Ratio"])


def _normalize_view(df_view: pd.DataFrame, date_col: str | None) -> pd.DataFrame:
    """Normalize df_view coming from app.py so Calendar can use it directly."""
    if df_view is None or len(df_view) == 0:
        return pd.DataFrame(columns=["Date", "PnL", "R Ratio", "Symbol", "Direction", "Account"])

    d = df_view.copy()

    # Date
    if date_col and date_col in d.columns:
        d["Date"] = pd.to_datetime(d[date_col], errors="coerce").dt.date
    elif "Date" in d.columns:
        d["Date"] = pd.to_datetime(d["Date"], errors="coerce").dt.date
    else:
        d["Date"] = pd.NaT

    # PnL / R
    if "PnL" not in d.columns and "pnl" in d.columns:
        d["PnL"] = pd.to_numeric(d["pnl"], errors="coerce")
    else:
        d["PnL"] = pd.to_numeric(d.get("PnL", 0.0), errors="coerce")

    if "R Ratio" not in d.columns and "r" in d.columns:
        d["R Ratio"] = pd.to_numeric(d["r"], errors="coerce")
    else:
        d["R Ratio"] = pd.to_numeric(d.get("R Ratio", 0.0), errors="coerce")

    # Optional standardizations
    if "Symbol" not in d.columns and "symbol" in d.columns:
        d["Symbol"] = d["symbol"]
    if "Direction" not in d.columns and "Side" in d.columns:
        d["Direction"] = d["Side"]

    return d


def _fmt_money(x: float) -> str:
    s = "-" if x < 0 else ""
    return f"{s}${abs(x):,.2f}"


def _fmt_pct(x: float) -> str:
    sgn = "-" if x < 0 else ""
    return f"{sgn}{abs(x):.2f} %"


def _fmt_rr(x: float) -> str:
    s = "+" if x > 0 else ("−" if x < 0 else "")
    return f"{s}{abs(x):.2f}R"


def _palette(pnl: float, r_sum: float) -> Tuple[str, str]:
    if pnl > 0:
        return GREEN_BG, GREEN_BD
    if pnl == 0:
        return NEUTRAL_BG, NEUTRAL_BD
    if pnl < 0 and abs(r_sum) < 0.10:
        return AMBER_BG, AMBER_BD
    return RED_BG, RED_BD


def _build_day_stats(df: pd.DataFrame, start_equity: float) -> Dict[date, DayStats]:
    if df.empty:
        return {}
    dfg = (
        pd.DataFrame(
            {
                "d": pd.to_datetime(df["Date"]).dt.date,
                "PnL": pd.to_numeric(df["PnL"], errors="coerce").fillna(0.0),
                "R": pd.to_numeric(df["R Ratio"], errors="coerce").fillna(0.0),
            }
        )
        .groupby("d", sort=True, as_index=False)
        .agg(pnl=("PnL", "sum"), r=("R", "sum"))
        .sort_values("d")
    )
    equity = float(start_equity)
    out: Dict[date, DayStats] = {}
    for _, row in dfg.iterrows():
        d = row["d"]
        pnl = float(row["pnl"])
        r = float(row["r"])
        before = equity
        pct = (pnl / before * 100.0) if before != 0 else 0.0
        after = before + pnl
        out[d] = DayStats(pnl=pnl, r=r, pct=pct, equity_before=before, equity_after=after)
        equity = after
    return out


def _month_weeks(y: int, m: int) -> List[List[date]]:
    cal = pycal.Calendar(firstweekday=0)  # Monday
    return cal.monthdatescalendar(y, m)


def _month_aggregates(month_anchor: date, stats: Dict[date, DayStats], start_equity: float):
    days = [d for d in stats if d.year == month_anchor.year and d.month == month_anchor.month]
    pnl = sum(stats[d].pnl for d in days)
    r = sum(stats[d].r for d in days)

    prior = month_anchor - timedelta(days=1)
    eq_start = None
    guard = 370
    while eq_start is None and guard > 0:
        if prior in stats:
            eq_start = stats[prior].equity_after
            break
        prior -= timedelta(days=1)
        guard -= 1
    if eq_start is None:
        eq_start = start_equity
    pct = (pnl / eq_start * 100.0) if eq_start else 0.0
    return pnl, pct, r


def _render_header(month_dt: date, sum_pnl: float, sum_pct: float, sum_r: float):
    scope_id = "cal-scope"
    st.markdown(f'<div id="{scope_id}"></div>', unsafe_allow_html=True)
    st.markdown('<div class="cal-wrap">', unsafe_allow_html=True)

    # R:R chip color (reuse your colors)
    rr_bg = (
        "rgba(34,197,94,0.22)"
        if sum_r > 0
        else ("rgba(239,68,68,0.22)" if sum_r < 0 else "rgba(148,163,184,0.22)")
    )
    rr_fg = GREEN if sum_r > 0 else (RED if sum_r < 0 else FG)

    # --- Nav controls (no HTML, no query params) ---
    c_today, c_prev, c_title, c_next, c_stats = st.columns([0.30, 0.2, 0.70, 0.60, 3.0])
    today = date.today()

    with c_today:
        if st.button("TODAY", key="cal_today"):
            st.session_state["cal_month"] = date(today.year, today.month, 1)
            st.rerun()

    with c_prev:
        st.markdown('<div class="cal-prev-wrap">', unsafe_allow_html=True)
        if st.button("◀", key="cal_prev"):
            base = st.session_state.get("cal_month", date(today.year, today.month, 1))
            prev_m = (base.replace(day=1) - timedelta(days=1)).replace(day=1)
            st.session_state["cal_month"] = prev_m
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with c_title:
        st.markdown(
            f"<h2 class='cal-title' style='text-align:center;margin:0;position:relative;top:45px'>{month_dt.strftime('%B %Y')}</h2>",
            unsafe_allow_html=True,
        )

    with c_next:
        st.markdown('<div class="cal-next-wrap">', unsafe_allow_html=True)
        if st.button("▶", key="cal_next"):
            base = st.session_state.get("cal_month", date(today.year, today.month, 1))
            next_m = (base.replace(day=28) + timedelta(days=7)).replace(day=1)
            st.session_state["cal_month"] = next_m
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Right-side chips (reuse your HTML so visuals stay the same)
    with c_stats:
        col_chips, col_btn = st.columns([0.86, 0.14], vertical_alignment="bottom")

        with col_chips:
            st.markdown(
                f"""
                <div class="cal-agg" style="display:flex;justify-content:flex-end;align-items:center;gap:10px; margin-top:60px">
                  <div class="chip-plain">{_fmt_money(sum_pnl)}</div>
                  <div class="chip-plain">{'<span class="tri-down"></span>' if sum_pct < 0 else '<span class="tri-up"></span>'}{_fmt_pct(sum_pct)}</div>
                  <div class="chip-rr" style="background:{rr_bg}; color:{rr_fg}; border:none;">{_fmt_rr(sum_r)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_btn:
            with st.popover("VIEW TRADES", use_container_width=False):
                df_all = _ensure_df().copy()
                if not df_all.empty and "Date" in df_all.columns:
                    df_all["Date"] = pd.to_datetime(df_all["Date"], errors="coerce").dt.date

                    month_start = month_dt.replace(day=1)
                    month_end_excl = (
                        pd.Timestamp(month_start) + pd.offsets.MonthEnd(1) + pd.Timedelta(days=1)
                    ).date()
                    dft = df_all[
                        (df_all["Date"] >= month_start) & (df_all["Date"] < month_end_excl)
                    ].copy()

                    start_equity_local = float(
                        st.session_state.get("calendar_start_equity", 100000.0)
                    )
                    day_stats_local = _build_day_stats(df_all, start_equity_local)

                    def _pct_for_trade(row):
                        d = row["Date"]
                        base = day_stats_local.get(d).equity_before if d in day_stats_local else 0.0
                        pnl = float(pd.to_numeric(row.get("PnL", 0.0), errors="coerce") or 0.0)
                        return (pnl / base * 100.0) if base else 0.0

                    dft["pct_calc"] = dft.apply(_pct_for_trade, axis=1)

                    # ---- TABLE (header + rows in a single block so CSS applies) ----
                    rows_html = [
                        """
                        <div class="view-trades-table">
                          <div class="vt-row vt-hdr">
                            <div>Date</div>
                            <div>Symbol</div>
                            <div>Direction</div>
                            <div>PnL</div>
                            <div>%</div>
                            <div>R:R</div>
                          </div>
                        """
                    ]

                    for _, r in dft.sort_values("Date").iterrows():
                        dt = r["Date"]
                        sym = str(r.get("Symbol", "")).upper()
                        side = str(r.get("Direction", "") or r.get("Side", ""))
                        pnl = float(pd.to_numeric(r.get("PnL", 0.0), errors="coerce") or 0.0)
                        rr = float(pd.to_numeric(r.get("R Ratio", 0.0), errors="coerce") or 0.0)
                        pct = float(r["pct_calc"])

                        cls_pnl = "cal-pos" if pnl > 0 else ("cal-neg" if pnl < 0 else "cal-zero")
                        cls_pct = "cal-pos" if pct > 0 else ("cal-neg" if pct < 0 else "cal-zero")
                        cls_rr = "cal-pos" if rr > 0 else ("cal-neg" if rr < 0 else "cal-zero")

                        rows_html.append(
                            f"<div class='vt-row'>"
                            f"<div>{pd.Timestamp(dt).strftime('%b %d')}</div>"
                            f"<div>{sym}</div>"
                            f"<div>{side}</div>"
                            f"<div class='pnl {cls_pnl}'>{_fmt_money(pnl)}</div>"
                            f"<div class='pct {cls_pct}'>{_fmt_pct(pct)}</div>"
                            f"<div class='rr {cls_rr}'>{_fmt_rr(rr)}</div>"
                            f"</div>"
                        )

                    rows_html.append("</div>")  # close .view-trades-table
                    st.markdown("".join(rows_html), unsafe_allow_html=True)

                else:
                    st.info("No trades for this month.")

    st.markdown("</div>", unsafe_allow_html=True)


def _build_hover_table(day_date: date, baseline_equity: float) -> str:
    try:
        dfx = _ensure_df()
        if dfx is None or dfx.empty or "Date" not in dfx.columns:
            return ""
        dfx = dfx.copy()
        dfx["Date"] = pd.to_datetime(dfx["Date"], errors="coerce").dt.date
        rows = dfx[dfx["Date"] == day_date]
        if rows.empty:
            return ""

        html_rows = []
        html_rows.append(
            "<div class='tr head'>"
            "<div class='sym'>Symbol</div>"
            "<div class='dir'>Direction</div>"
            "<div class='pnl'>PnL</div>"
            "<div class='pct'>%</div>"
            "<div class='rr'>R:R</div>"
            "</div>"
        )
        for _, r in rows.iterrows():
            sym = str(r.get("Symbol", "")).upper()
            side = str(r.get("Direction", "") or r.get("Side", ""))
            pnl = float(pd.to_numeric(r.get("PnL", 0.0), errors="coerce") or 0.0)
            rr = float(pd.to_numeric(r.get("R Ratio", 0.0), errors="coerce") or 0.0)
            pct = (pnl / baseline_equity * 100.0) if baseline_equity else 0.0

            cls_pnl = "cal-pos" if pnl > 0 else ("cal-neg" if pnl < 0 else "cal-zero")
            cls_pct = "cal-pos" if pct > 0 else ("cal-neg" if pct < 0 else "cal-zero")
            cls_rr = "cal-pos" if rr > 0 else ("cal-neg" if rr < 0 else "cal-zero")

            html_rows.append(
                f"<div class='tr'>"
                f"<div class='sym'>{sym}</div>"
                f"<div class='dir'>{side}</div>"
                f"<div class='pnl {cls_pnl}'>{_fmt_money(pnl)}</div>"
                f"<div class='pct {cls_pct}'>{_fmt_pct(pct)}</div>"
                f"<div class='rr {cls_rr}'>{_fmt_rr(rr)}</div>"
                f"</div>"
            )

        return "<div class='hover-tip'>" + "".join(html_rows) + "</div>"
    except Exception:
        return ""


def _build_week_hover_table(week_start_date: date, baseline_equity: float) -> str:
    """
    Week tooltip: Date | Symbol | PnL | Direction | % | R:R
    % is computed using the WEEK's baseline equity so totals align with the chip.
    """
    try:
        dfx = _ensure_df()
        if dfx is None or dfx.empty or "Date" not in dfx.columns:
            return ""

        dfx = dfx.copy()
        dfx["Date"] = pd.to_datetime(dfx["Date"], errors="coerce").dt.date
        week_end_excl = (pd.Timestamp(week_start_date) + pd.Timedelta(days=7)).date()
        rows = dfx[(dfx["Date"] >= week_start_date) & (dfx["Date"] < week_end_excl)]
        if rows.empty:
            return ""

        # header
        html_rows = []
        html_rows.append(
            "<div class='tr head'>"
            "<div class='dt'>Date</div>"
            "<div class='sym'>Symbol</div>"
            "<div class='dir'>Direction</div>"
            "<div class='pnl'>PnL</div>"
            "<div class='pct'>%</div>"
            "<div class='rr'>R:R</div>"
            "</div>"
        )

        # rows (use week baseline for %)
        for _, r in rows.sort_values("Date").iterrows():
            dt = r["Date"]
            sym = str(r.get("Symbol", "")).upper()
            side = str(r.get("Direction", "") or r.get("Side", ""))
            pnl = float(pd.to_numeric(r.get("PnL", 0.0), errors="coerce") or 0.0)
            rr = float(pd.to_numeric(r.get("R Ratio", 0.0), errors="coerce") or 0.0)
            pct = (pnl / baseline_equity * 100.0) if baseline_equity else 0.0

            cls_pnl = "cal-pos" if pnl > 0 else ("cal-neg" if pnl < 0 else "cal-zero")
            cls_pct = "cal-pos" if pct > 0 else ("cal-neg" if pct < 0 else "cal-zero")
            cls_rr = "cal-pos" if rr > 0 else ("cal-neg" if rr < 0 else "cal-zero")

            html_rows.append(
                f"<div class='tr'>"
                f"<div class='dt'>{pd.Timestamp(dt).strftime('%b %d')}</div>"
                f"<div class='sym'>{sym}</div>"
                f"<div class='dir'>{side}</div>"
                f"<div class='pnl {cls_pnl}'>{_fmt_money(pnl)}</div>"
                f"<div class='pct {cls_pct}'>{_fmt_pct(pct)}</div>"
                f"<div class='rr {cls_rr}'>{_fmt_rr(rr)}</div>"
                f"</div>"
            )

        return "<div class='hover-tip total'>" + "".join(html_rows) + "</div>"
    except Exception:
        return ""


def _render_grid(month_dt: date, stats: Dict[date, DayStats]):
    # Build ONE big HTML string; rendering once keeps the CSS grid intact.
    weeks = _month_weeks(month_dt.year, month_dt.month)
    today = date.today()

    html = []
    html.append('<div class="cal-grid">')

    # column headers
    for h in [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
        "Total",
    ]:
        html.append(f'<div class="cal-colhead">{h}</div>')

    for week in weeks:
        # day cells (Mon..Sun)
        for d in week:
            in_month = d.month == month_dt.month
            classes = ["cal-cell"]
            if not in_month:
                classes.append("blank")
            if d == today:
                classes.append("today")
            ds = stats.get(d)

            if (not in_month) or ds is None:
                html.append(
                    f'<div class="{" ".join(classes)}"><div class="day-num">{d.day if in_month else ""}</div></div>'
                )
            else:
                bg, bd = _palette(ds.pnl, ds.r)
                tri = (
                    '<span class="tri-down"></span>'
                    if ds.pct < 0
                    else '<span class="tri-up"></span>'
                )

                html.append(
                    f"""
                <div class="{' '.join(classes)}">
                  <div class="day-num">{d.day}</div>
                  <div class="day-card" style="background:{bg}; border-color:{bd}">
                    <div class="money">{_fmt_money(ds.pnl)}</div>
                    <div class="pct">{tri}{_fmt_pct(ds.pct)}</div>
                    <span class="rr">{_fmt_rr(ds.r)}</span>
                    {_build_hover_table(d.date() if hasattr(d, 'date') else d, ds.equity_before)}
                  </div>
                </div>
                    """.strip()
                )

        # week summary (right-most cell)
        week_label = f"Week {d.isocalendar().week}"
        pnl_w = sum((stats.get(dd, DayStats()).pnl for dd in week))
        r_w = sum((stats.get(dd, DayStats()).r for dd in week))

        # equity baseline for the week = equity_before of first trading day in week; fallback search backward
        eq_before = None
        for dd in week:
            if dd in stats:
                eq_before = stats[dd].equity_before
                break
        if eq_before is None:
            back = week[0] - timedelta(days=1)
            hops = 31
            while eq_before is None and hops > 0:
                if back in stats:
                    eq_before = stats[back].equity_after
                back -= timedelta(days=1)
                hops -= 1
        pct_w = (pnl_w / eq_before * 100.0) if eq_before not in (None, 0) else 0.0

        bg_w, bd_w = _palette(pnl_w, r_w)
        tri_w = '<span class="tri-down"></span>' if pct_w < 0 else '<span class="tri-up"></span>'

        week_start_date = week[0]

        html.append(
            f"""
<div class="week-wrap">
  <div class="week-label">{week_label}</div>
  <div class="week-card" style="background:{bg_w}; border-color:{bd_w}">
    <div class="money">{_fmt_money(pnl_w)}</div>
    <div class="pct">{tri_w}{_fmt_pct(pct_w)}</div>
    <span class="rr">{_fmt_rr(r_w)}</span>
    {_build_week_hover_table(week_start_date, (eq_before or 0.0))}
  </div>
</div>
            """.strip()
        )

    html.append("</div>")  # .cal-grid
    st.markdown("\n".join(html), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)  # .cal-wrap


def render(*, df_view: pd.DataFrame, _date_col: str | None, month_start=None, key: str = "cal"):
    _inject_css()

    # Normalize the already-filtered global view and stash it so helpers can reuse it
    st.session_state["cal_df"] = _normalize_view(df_view, _date_col)
    df = _ensure_df()

    start_equity = float(st.session_state.get("calendar_start_equity", 100000.0))
    stats = _build_day_stats(df, start_equity)

    # current month anchor
    today = date.today()
    month_dt = st.session_state.get("cal_month", date(today.year, today.month, 1))
    st.session_state["cal_month"] = month_dt

    m_pnl, m_pct, m_r = _month_aggregates(month_dt, stats, start_equity)
    _render_header(month_dt, m_pnl, m_pct, m_r)
    _render_grid(month_dt, stats)
