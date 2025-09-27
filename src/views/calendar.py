# src/views/calendar.py
from __future__ import annotations

import calendar as _cal

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ---------- helpers ----------
def _round_rect_path(x0: float, y0: float, x1: float, y1: float, r: float) -> str:
    """SVG path for a rounded rectangle (clockwise)."""
    r = max(0.0, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    return (
        f"M{x0 + r},{y0} "
        f"H{x1 - r} "
        f"Q{x1},{y0} {x1},{y0 + r} "
        f"V{y1 - r} "
        f"Q{x1},{y1} {x1 - r},{y1} "
        f"H{x0 + r} "
        f"Q{x0},{y1} {x0},{y1 - r} "
        f"V{y0 + r} "
        f"Q{x0},{y0} {x0 + r},{y0} Z"
    )


def _month_nav_controls(
    anchor: pd.Timestamp, min_dt: pd.Timestamp | None, max_dt: pd.Timestamp | None, *, key: str
):
    """Inline month/year dropdowns + ‹/› arrows (inside the calendar container). Returns new anchor (1st of month)."""
    # Figure year range from data (fallback to current year)
    if (min_dt is not None) and (max_dt is not None) and pd.notna(min_dt) and pd.notna(max_dt):
        y0, y1 = int(min_dt.year), int(max_dt.year)
    else:
        y0 = y1 = int(pd.Timestamp.today().year)

    years = list(range(y0, y1 + 1))
    months = list(_cal.month_name)[1:]  # 1..12

    # tight layout: [‹] [Month] [Year] [›] [spacer]
    c_prev, c_month, c_year, c_next, _ = st.columns([0.07, 0.22, 0.14, 0.07, 0.50])

    with c_prev:
        if st.button("‹", key=f"{key}_prev"):
            anchor = (anchor - pd.offsets.MonthBegin(1)).normalize().replace(day=1)

    with c_month:
        m_idx = int(anchor.month) - 1
        sel_month = st.selectbox(
            " ", months, index=m_idx, key=f"{key}_month_sel", label_visibility="collapsed"
        )
        if months.index(sel_month) != m_idx:
            anchor = anchor.normalize().replace(month=months.index(sel_month) + 1, day=1)

    with c_year:
        y_index = years.index(anchor.year) if anchor.year in years else len(years) - 1
        sel_year = st.selectbox(
            "  ", years, index=y_index, key=f"{key}_year_sel", label_visibility="collapsed"
        )
        if sel_year != anchor.year:
            anchor = anchor.normalize().replace(year=int(sel_year), day=1)

    with c_next:
        if st.button("›", key=f"{key}_next"):
            anchor = (anchor + pd.offsets.MonthBegin(1)).normalize().replace(day=1)

    return anchor.normalize().replace(day=1)


def render(
    df_view: pd.DataFrame,
    _date_col: str | None,
    month_start: pd.Timestamp,
    *,
    key: str = "cal",
):
    """Plotly calendar with rounded cells, in-card controls, and green/red fills."""
    # -------- guard + parse --------
    if _date_col is None or _date_col not in df_view.columns or len(df_view) == 0:
        st.info("No date/timestamp column found — calendar view unavailable for this dataset.")
        return

    _dt_full = pd.to_datetime(df_view[_date_col], errors="coerce")
    if _dt_full.notna().sum() == 0:
        st.info("No parseable dates in the current dataset.")
        return
    min_dt, max_dt = _dt_full.min(), _dt_full.max()

    # -------- styles (tuned darker & rounded) --------
    panel_bg = "#0b0f19"  # panel background
    border_col = "#2a3444"
    header_white = "#ffffff"
    empty_fill = "#111722"  # darker neutral for empty cells (slightly darker than before)
    empty_border = "#1c2533"

    pos_fill = "rgba(34,197,94,0.26)"  # cell bg for positive day
    pos_border = "rgba(34,197,94,0.55)"
    neg_fill = "rgba(239,68,68,0.26)"  # cell bg for negative day
    neg_border = "rgba(239,68,68,0.55)"

    pnl_green_text = "#86efac"  # lighter green number
    pnl_red_text = "#fca5a5"  # lighter red number

    daynum_muted = "#cbd5e1"  # top-left day index
    trades_white = "#ffffff"  # trade count text

    cell_radius = 0.20  # rounded corners for each day
    card_radius = 0.35  # rounded corners for whole calendar “card”

    # -------- card wrapper (CSS so controls + plot look like one card) --------
    st.markdown(
        f"""
<style>
  .cal-card {{
    background:{panel_bg};
    border:1px solid {border_col};
    border-radius:16px;
    padding:12px 12px 8px;
    margin-top: 6px;
  }}
  /* Controls alignment & compact look */
  .cal-card .stButton > button {{
    background: #1f2937; border:1px solid {border_col}; color:#e5e7eb;
    padding:4px 10px; border-radius:12px; min-width:34px; height:34px;
  }}
  .cal-card .stButton > button:hover {{ background:#263244; border-color:#3a4557; }}
  .cal-card [data-baseweb="select"] > div {{
    background:#1b2230; border-color:{border_col};
    border-radius:10px; min-height:34px;
  }}
  .cal-card [data-baseweb="select"] div[role="button"] {{ padding:4px 8px; }}
</style>
""",
        unsafe_allow_html=True,
    )

    # -------- begin card --------
    st.markdown("<div class='cal-card'>", unsafe_allow_html=True)

    # in-card controls
    anchor = month_start.normalize().replace(day=1)
    anchor = _month_nav_controls(anchor, min_dt, max_dt, key=key)
    st.session_state["_cal_month_start"] = anchor  # persist

    # slice month
    _month_start = anchor
    _month_end = (_month_start + pd.offsets.MonthEnd(1)).normalize()

    _mask_month = (_dt_full >= _month_start) & (_dt_full <= _month_end)
    _dfm = df_view.loc[_mask_month].copy()
    _dfm["_day"] = pd.to_datetime(_dfm[_date_col], errors="coerce").dt.date

    _daily_stats = (
        _dfm.assign(_pnl=pd.to_numeric(_dfm.get("pnl", 0.0), errors="coerce").fillna(0.0))
        .groupby("_day")
        .agg(NetPnL=("_pnl", "sum"), Trades=("_pnl", "count"))
        .reset_index()
    )
    _daily_map = {
        row["_day"]: (float(row["NetPnL"]), int(row["Trades"]))
        for _, row in _daily_stats.iterrows()
    }

    # geometry
    first_wd, n_days = _cal.monthrange(_month_start.year, _month_start.month)  # Mon=0..Sun=6
    # convert to Sun..Sat grid start (keep as is: our header order is Sun..Sat already)
    leading = (first_wd + 1) % 7  # shift so Sunday=0 visually
    total_slots = leading + n_days
    rows = (total_slots + 6) // 7

    def slot_to_date(slot_idx: int):
        day_n = slot_idx - leading + 1
        if 1 <= day_n <= n_days:
            return (_month_start + pd.Timedelta(days=day_n - 1)).date()
        return None

    shapes, annos = [], []

    # “whole card” rounded rectangle for the plot area (so chart corners are smooth)
    # Chart grid spans x:[0,7], y:[0,rows], but our weekday labels sit at y = -0.35, so extend a bit.
    outer_path = _round_rect_path(0 - 0.15, -0.95, 7 + 0.15, rows + 0.05, card_radius)
    shapes.append(
        dict(
            type="path",
            path=outer_path,
            line=dict(color=border_col, width=1.2),
            fillcolor=panel_bg,
            layer="below",
        )
    )

    # Header row: Sun..Sat (white + bold)
    weekday_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    for c, label in enumerate(weekday_labels):
        annos.append(
            dict(
                x=c + 0.5,
                y=-0.35,
                xref="x",
                yref="y",
                text=f"<b>{label}</b>",
                showarrow=False,
                font=dict(size=12, color=header_white),
                xanchor="center",
                yanchor="middle",
            )
        )

    # Cells: rounded rect paths + annotations
    for r in range(rows):
        for c in range(7):
            x0, x1 = c, c + 1
            y0, y1 = r, r + 1
            d = slot_to_date(r * 7 + c)

            fill = empty_fill
            border = empty_border
            pnl_txt = "—"
            pnl_color = header_white
            trades_txt = "—"
            day_idx = ""

            if d is not None:
                pnl_val, trade_ct = _daily_map.get(d, (0.0, 0))
                day_idx = str(d.day)
                if trade_ct > 0:
                    if pnl_val > 0:
                        fill, border, pnl_color = pos_fill, pos_border, pnl_green_text
                    elif pnl_val < 0:
                        fill, border, pnl_color = neg_fill, neg_border, pnl_red_text
                    pnl_txt = f"${pnl_val:,.1f}".replace("$-", "-$")
                    trades_txt = f"{trade_ct} trade" if trade_ct == 1 else f"{trade_ct} trades"

            cell_path = _round_rect_path(x0 + 0.04, y0 + 0.04, x1 - 0.04, y1 - 0.04, cell_radius)
            shapes.append(
                dict(
                    type="path",
                    path=cell_path,
                    line=dict(color=border, width=1.5),
                    fillcolor=fill,
                    layer="below",
                )
            )

            # day index (top-left)
            if d is not None:
                annos.append(
                    dict(
                        x=x0 + 0.12,
                        y=y0 + 0.20,
                        xref="x",
                        yref="y",
                        text=day_idx,
                        showarrow=False,
                        font=dict(size=12, color=daynum_muted),
                        xanchor="left",
                        yanchor="middle",
                    )
                )

            # PnL center
            annos.append(
                dict(
                    x=x0 + 0.5,
                    y=y0 + 0.48,
                    xref="x",
                    yref="y",
                    text=pnl_txt,
                    showarrow=False,
                    font=dict(size=16, color=pnl_color),
                    xanchor="center",
                    yanchor="middle",
                )
            )
            # trades (below center) — white
            annos.append(
                dict(
                    x=x0 + 0.5,
                    y=y0 + 0.78,
                    xref="x",
                    yref="y",
                    text=trades_txt,
                    showarrow=False,
                    font=dict(size=11, color=trades_white),
                    xanchor="center",
                    yanchor="top",
                )
            )

    # figure
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=panel_bg,
        plot_bgcolor=panel_bg,
        shapes=shapes,
        annotations=annos,
        xaxis=dict(
            range=[0, 7], showgrid=False, zeroline=False, tickvals=[], ticktext=[], fixedrange=True
        ),
        yaxis=dict(
            range=[rows, -1],
            showgrid=False,
            zeroline=False,
            tickvals=[],
            ticktext=[],
            fixedrange=True,
        ),
        margin=dict(l=6, r=6, t=4, b=8),
    )
    cal_h = int(120 + rows * 110)
    fig.update_layout(height=cal_h)

    st.plotly_chart(fig, use_container_width=True, key=f"{key}_{_month_start.strftime('%Y%m')}")

    # -------- end card --------
    st.markdown("</div>", unsafe_allow_html=True)
