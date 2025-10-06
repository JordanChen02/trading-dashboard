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
    from src.theme import BLUE, BLUE_FILL, FG, FG_MUTED, RED
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
  .cal-title {{ margin:0; font-size:18px; color:{FG}; font-weight:800; letter-spacing:.2px; }}

  /* Outline buttons (TODAY, VIEW TRADES) */
  .btn-outline {{
    background: transparent; color:{BLUE};
    border:1px solid {BLUE}; padding:6px 12px; border-radius:10px; font-weight:800;
    cursor:pointer; text-transform:uppercase;
  }}
  .btn-outline:hover {{ background:{BLUE_FILL}; }}

  /* Chevron buttons (borderless) */
  .chev-btn {{
    background: transparent; color:{FG};
    border:none; padding:6px 10px; border-radius:10px; font-weight:900; font-size:18px;
    cursor:pointer; line-height:1; transform: translateY(-2px);
  }}
  .chev-btn:hover {{ background:{BLUE_FILL}; }}

  /* Right side: chips in a single row, next to view trades */
  .cal-agg {{
    display:flex; align-items:center; gap:10px; flex-wrap:nowrap; white-space:nowrap;
  }}

  /* Plain chips (PnL and %): no background/border, keep weight */
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

  /* Filled R:R chip – color will be inlined from Python */
  .chip-rr {{
    display:inline-flex; align-items:center; gap:6px;
    padding: 6px 10px; border-radius:10px; font-weight:800;
  }}

  /* Slightly wider view trades */
  .view-btn .btn-outline {{ padding:6px 16px; min-width:140px; }}

  /* GRID */
  .cal-grid {{
    display:grid;
    grid-template-columns: repeat(8, 1fr);
    gap: 8px;
  }}

  .cal-colhead {{
    text-align:center;
    font-size:14px;            /* slightly larger than before */
    color:{{FG_MUTED}};        /* keep your muted tone */
    padding:8px;
    font-weight:800;
    text-transform:capitalize;
  }}

  .cal-cell, .week-wrap {{
    position: relative;
    min-height: 180px;         /* <-- increase height here */
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px; padding: 8px;
  }}

  .cal-cell.blank {{ background: rgba(0,0,0,0.22); }}
  .cal-cell.today {{ box-shadow: 0 0 0 1.5px {BLUE} inset; }}

  .day-num {{ position:absolute; top:6px; left:8px; font-size:14px; color:{FG_MUTED}; font-weight:700; }}

  .day-card, .week-card {{
    margin-top: 20px; padding: 10px 10px 8px; border-radius: 14px; border: 1px solid transparent; font-size:14px; text-align:center;
  }}

  /* CENTER the PnL line inside day cards */
  .day-card .money .pct {{ font-size:14px; font-weight:800; color:{FG}; margin-bottom:4px; text-align:center; }}

  /* keep % and R slightly left for compact read, unchanged */
  .pct   {{ color:{FG_MUTED}; display:flex; align-items:center; justify-content:center; gap:6px; margin-bottom:6px;}}
  .rr    {{
    display:inline-block; font-weight:800; font-size:12px; letter-spacing:.2px;
    padding: 2px 8px; border-radius: 999px; color:#d1d5db; background: rgba(255,255,255,0.06);
  }}

  .week-label {{ display:none; }}


</style>
        """,
        unsafe_allow_html=True,
    )


# ---------- data ----------
def _ensure_df() -> pd.DataFrame:
    if "journal_df" in st.session_state and isinstance(st.session_state.journal_df, pd.DataFrame):
        df = st.session_state.journal_df.copy()
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"]).dt.date
        else:
            df["Date"] = pd.NaT
        if "PnL" not in df.columns:
            df["PnL"] = 0.0
        if "R Ratio" not in df.columns:
            df["R Ratio"] = 0.0
        return df
    return pd.DataFrame(columns=["Date", "PnL", "R Ratio"])


def _fmt_money(x: float) -> str:
    return f"${x:,.2f}"


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
    c_today, c_prev, c_title, c_next, c_stats = st.columns([0.30, 0.1, 0.80, 0.9, 3.0])
    today = date.today()

    with c_today:
        if st.button("TODAY", key="cal_today"):
            st.session_state["cal_month"] = date(today.year, today.month, 1)
            st.rerun()

    with c_prev:
        if st.button("◀", key="cal_prev", help="Previous month"):
            base = st.session_state.get("cal_month", date(today.year, today.month, 1))
            prev_m = (base.replace(day=1) - timedelta(days=1)).replace(day=1)
            st.session_state["cal_month"] = prev_m
            st.rerun()

    with c_title:
        st.markdown(
            f"<h2 class='cal-title' style='text-align:center;margin:0'>{month_dt.strftime('%B %Y')}</h2>",
            unsafe_allow_html=True,
        )

    with c_next:
        if st.button("▶", key="cal_next", help="Next month"):
            base = st.session_state.get("cal_month", date(today.year, today.month, 1))
            next_m = (base.replace(day=28) + timedelta(days=7)).replace(day=1)
            st.session_state["cal_month"] = next_m
            st.rerun()

    # Right-side chips (reuse your HTML so visuals stay the same)
    with c_stats:
        st.markdown(
            f"""
            <div class="cal-agg" style="display:flex;justify-content:flex-end;align-items:center;gap:10px">
              <div class="chip-plain">{_fmt_money(sum_pnl)}</div>
              <div class="chip-plain">{'<span class="tri-down"></span>' if sum_pct < 0 else '<span class="tri-up"></span>'}{_fmt_pct(sum_pct)}</div>
              <div class="chip-rr" style="background:{rr_bg}; color:{rr_fg}; border:none;">{_fmt_rr(sum_r)}</div>
              <div class="view-btn"><button class="btn-outline">VIEW TRADES -▸</button></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
    <style>
    /* Target the very next Streamlit horizontal block after our marker */
    #{scope_id} + div [data-testid="stButton"] > button {{
    background: transparent !important;
    border: none !important;              /* 2) borderless */
    box-shadow: none !important;
    color: {BLUE} !important;             /* 3) theme text color (matches View Trades) */
    font-weight: 900;
    font-size: 18px;
    padding: 6px 10px;
    border-radius: 10px;
    line-height: 1;
    }}
    #{scope_id} + div [data-testid="stButton"] > button:hover {{
    background: {BLUE_FILL} !important;   /* subtle hover */
    }}
    /* 1) nudge title up to align with buttons */
    #{scope_id} + div h2.cal-title {{
    position: relative; top: -4px;
    }}
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)


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
<div class="{" ".join(classes)}">
  <div class="day-num">{d.day}</div>
  <div class="day-card" style="background:{bg}; border-color:{bd}">
    <div class="money">{_fmt_money(ds.pnl)}</div>
    <div class="pct">{tri}{_fmt_pct(ds.pct)}</div>
    <span class="rr">{_fmt_rr(ds.r)}</span>
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

        html.append(
            f"""
<div class="week-wrap">
  <div class="week-label">{week_label}</div>
  <div class="week-card" style="background:{bg_w}; border-color:{bd_w}">
    <div class="money">{_fmt_money(pnl_w)}</div>
    <div class="pct">{tri_w}{_fmt_pct(pct_w)}</div>
    <span class="rr">{_fmt_rr(r_w)}</span>
  </div>
</div>
            """.strip()
        )

    html.append("</div>")  # .cal-grid
    st.markdown("\n".join(html), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)  # .cal-wrap


def render(*_args, **_kwargs):
    _inject_css()

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
