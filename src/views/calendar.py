# src/views/calendar.py
from __future__ import annotations

import calendar as _cal

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ---------- helpers ----------
def _round_rect_path(x0: float, y0: float, x1: float, y1: float, r: float) -> str:
    r = max(0.0, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    return (
        f"M{x0 + r},{y0} H{x1 - r} "
        f"Q{x1},{y0} {x1},{y0 + r} V{y1 - r} "
        f"Q{x1},{y1} {x1 - r},{y1} H{x0 + r} "
        f"Q{x0},{y1} {x0},{y1 - r} V{y0 + r} "
        f"Q{x0},{y0} {x0 + r},{y0} Z"
    )


def _controls(anchor: pd.Timestamp, min_dt, max_dt, *, key: str):
    # year bounds from data
    if (min_dt is not None) and (max_dt is not None) and pd.notna(min_dt) and pd.notna(max_dt):
        y0, y1 = int(min_dt.year), int(max_dt.year)
    else:
        y0 = y1 = int(pd.Timestamp.today().year)
    years = list(range(y0, y1 + 1))
    months = list(_cal.month_name)[1:]

    # centered & compact: [spacer][‹][Month][Year][›][spacer]
    left, right = st.columns(
        [6, 4]
    )  # tweak ratios to taste (more right = push stats farther right)

    with left:
        c_prev, c_month, c_year, c_next = st.columns([0.45, 1.2, 0.9, 0.45])
        # ... keep your prev/month/year/next widgets exactly as they are now, just under these columns ...

    with right:
        # wrap your stats HTML in a right-justified div
        st.markdown(
            """
        <div style="display:flex; justify-content:flex-end;">
        <div class="cal-stats">
            <span><span class="k">Trades</span><span class="v">{trades_ct}</span></span>
            <span><span class="k">Wins</span><span class="v">{wins_ct}</span></span>
            <span><span class="k">Profits</span><span class="v">${profits:,.2f}</span></span>
            <span><span class="k">Percent</span><span class="v">{win_pct:.2f}%</span></span>
        </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with c_prev:
        if st.button("‹", key=f"{key}_prev"):
            anchor = (anchor - pd.offsets.MonthBegin(1)).normalize().replace(day=1)

    with c_month:
        m_idx = int(anchor.month) - 1
        sel_month = st.selectbox(
            "Month", months, index=m_idx, key=f"{key}_m", label_visibility="collapsed"
        )
        if months.index(sel_month) != m_idx:
            anchor = anchor.replace(month=months.index(sel_month) + 1, day=1)

    with c_year:
        y_index = years.index(anchor.year) if anchor.year in years else len(years) - 1
        sel_year = st.selectbox(
            "Year", years, index=y_index, key=f"{key}_y", label_visibility="collapsed"
        )
        if sel_year is not None and int(sel_year) != anchor.year:
            anchor = anchor.replace(year=int(sel_year), day=1)

    with c_next:
        if st.button("›", key=f"{key}_next"):
            anchor = (anchor + pd.offsets.MonthBegin(1)).normalize().replace(day=1)

    return anchor.normalize().replace(day=1)


# ---------- main ----------
def render(
    df_view: pd.DataFrame,
    _date_col: str | None,
    month_start: pd.Timestamp,
    *,
    key: str = "cal",
):
    # guards
    if _date_col is None or _date_col not in df_view.columns or len(df_view) == 0:
        st.info("No date/timestamp column found — calendar view unavailable for this dataset.")
        return
    _dt_full = pd.to_datetime(df_view[_date_col], errors="coerce")
    if _dt_full.notna().sum() == 0:
        st.info("No parseable dates in the current dataset.")
        return
    min_dt, max_dt = _dt_full.min(), _dt_full.max()

    # palette (subtle, tight)
    panel_bg = "#0b0f19"
    border_col = "#2a3444"
    empty_fill = "#0e141f"
    empty_border = "#18202e"
    pos_fill = "rgba(34,197,94,0.22)"
    pos_border = "rgba(34,197,94,0.55)"
    neg_fill = "rgba(239,68,68,0.22)"
    neg_border = "rgba(239,68,68,0.55)"
    weekday_col = "#ffffff"
    header_total = "#cbd5e1"
    daynum_col = "#cbd5e1"
    trades_col = "#ffffff"
    pnl_green = "#86efac"
    pnl_red = "#fca5a5"
    accent_blue = "rgba(96,165,250,0.85)"

    # radii & spacing
    cell_radius = 0.05
    card_radius = 0.12
    inset = 0.02

    # compact controls + selects
    st.markdown(
        f"""
    <style>
    /* optional wrapper if you still use it elsewhere */
    .cal-card {{
        background:{panel_bg};
        border:1px solid {border_col};
        border-radius:12px;
        padding:6px 10px 2px;
    }}

    /* ARROWS: borderless + 34px */
    #cal-nav [data-testid="stButton"] > button {{
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    outline: none !important;
    color: #e5e7eb !important;
    font-size: 34px !important;     /* was 42px */
    line-height: 1 !important;
    height: 44px !important;         /* was 40px */
    min-width: 44px !important;      /* was 40px */
    border-radius: 8px !important;
    padding: 0 8px !important;
    }}
    #cal-nav [data-testid="stButton"] > button:hover,
    #cal-nav [data-testid="stButton"] > button:focus {{
    background: transparent !important;  /* was rgba(...,0.06) */
    border: 0 !important;
    box-shadow: none !important;
    outline: none !important;
    }}


    /* Month-Year label in the center */
    .cal-month-label {{
        text-align:center;
        font-weight:600;
        font-size:32px;
        letter-spacing:.3px;
        color:#e5e7eb;
        margin: 2px 0 0 0;
    }}

    /* If any selectboxes remain elsewhere, keep them compact */
    .cal-card [data-baseweb="select"] > div {{
        background:#1b2230; border-color:{border_col}; border-radius:8px;
        min-height:28px; width:max-content;
    }}
    .cal-card [data-baseweb="select"] div[role="button"] {{ padding:2px 8px; }}

    /* Stats pill (right-aligned container uses HTML wrapper in Python) */
    .cal-stats {{
        background: rgba(37,99,235,0.16);
        border: 1px solid rgba(96,165,250,0.75);
        border-radius: 12px;
        padding: 16px 20px;
        display: inline-grid;
        grid-auto-flow: column;
        gap: 20px;
        align-items: center;
        white-space: nowrap;

    }}
    .cal-stats .stat {{
        display: grid;
        grid-template-rows: auto auto; /* label above value */
        justify-items: center;
        text-align: center;
    }}
    .cal-stats .k {{ color:#93c5fd; font-size:16px; line-height:1; margin-bottom:4px; }}
    .cal-stats .v {{ color:#e5e7eb; font-weight:600; font-size:18px; line-height:1; }}
    </style>
    """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
    <style>
    /* Make arrow glyphs larger — Streamlit wraps them in a <p> inside the button */
    #cal-nav [data-testid="stButton"] > button {
    font-size: 34px !important;     /* keep 34px */
    height: 44px !important; 
    min-width: 44px !important;
    }
    #cal-nav [data-testid="stButton"] > button p {
    font-size: inherit !important;   /* was 42px */
    line-height: 1 !important;
    margin: 0 !important;
    }


    /* Add space BETWEEN each stat pair (Trades | Wins | Profits | Percent) */
    .cal-stats{ 
        gap: 26px !important;            /* spacing between the four pairs */
    }

    /* Add space WITHIN each pair: label → value (Trades 24, Wins 14, ...) */
    .cal-stats .k{ 
        margin-right: 10px !important;   /* increase if you want more */
    }
    .cal-stats .v{ 
        margin-left: 2px !important;     /* tiny extra; optional */
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # baseline anchor for this render (and persist across reruns)
    anchor = (st.session_state.get("_cal_month_start") or month_start).normalize().replace(day=1)

    # ---- Controls + Stats (same row) ----
    y0 = int(min_dt.year) if pd.notna(min_dt) else int(pd.Timestamp.today().year)
    y1 = int(max_dt.year) if pd.notna(max_dt) else y0
    years = list(range(y0, y1 + 1))
    if anchor.year not in years:
        years.append(anchor.year)
    years = sorted(set(years))

    # centered & compact: [spacer][‹][Month][Year][›][spacer]
    sL, c_prev, c_label, c_next, c_stats, sR = st.columns([0.4, 0.3, 2.0, 0.5, 6.0, 0.3])

    st.markdown("<div id='cal-nav'>", unsafe_allow_html=True)

    with c_prev:
        if st.button("‹", key=f"{key}_prev"):
            anchor = (anchor - pd.offsets.MonthBegin(1)).normalize().replace(day=1)

    with c_next:
        if st.button("›", key=f"{key}_next"):
            anchor = (anchor + pd.offsets.MonthBegin(1)).normalize().replace(day=1)

    with c_label:
        st.markdown(
            f"<div class='cal-month-label'>{anchor.strftime('%B %Y')}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # persist chosen month
    st.session_state["_cal_month_start"] = anchor

    # compute month slice for stats
    _month_start = anchor
    _month_end = (_month_start + pd.offsets.MonthEnd(1)).normalize()
    _dt_full = pd.to_datetime(df_view[_date_col], errors="coerce")
    _mask_month = (_dt_full >= _month_start) & (_dt_full <= _month_end)
    _dfm = df_view.loc[_mask_month].copy()

    # stats: trades, wins, profits, win %
    pnl_series = pd.to_numeric(_dfm.get("pnl", 0.0), errors="coerce")
    trades_ct = int(pnl_series.notna().sum())
    wins_ct = int((pnl_series > 0).sum())
    profits = float(pnl_series.sum()) if trades_ct else 0.0
    win_pct = (wins_ct / trades_ct * 100.0) if trades_ct else 0.0

    # render stats pill at the right of controls
    with c_stats:
        st.markdown(
            f"""
            <div style="display:flex; width:100%; justify-content:flex-end;">
            <div class="cal-stats">
                <span><span class="k">Trades</span><span class="v">{trades_ct}</span></span>
                <span><span class="k">Wins</span><span class="v">{wins_ct}</span></span>
                <span><span class="k">Profits</span><span class="v">${profits:,.2f}</span></span>
                <span><span class="k">Percent</span><span class="v">{win_pct:.2f}%</span></span>
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    _dfm["_day"] = pd.to_datetime(_dfm[_date_col], errors="coerce").dt.date

    _daily_stats = (
        _dfm.assign(_pnl=pd.to_numeric(_dfm.get("pnl", 0.0), errors="coerce").fillna(0.0))
        .groupby("_day")
        .agg(NetPnL=("_pnl", "sum"), Trades=("_pnl", "count"))
        .reset_index()
    )
    daily_map = {
        r["_day"]: (float(r["NetPnL"]), int(r["Trades"])) for _, r in _daily_stats.iterrows()
    }

    # geometry (Sun..Sat + Total)
    first_wd, n_days = _cal.monthrange(_month_start.year, _month_start.month)
    leading = (first_wd + 1) % 7  # Sun=0 visual start
    total_slots = leading + n_days
    rows = (total_slots + 6) // 7

    def slot_to_date(slot_idx: int):
        day_n = slot_idx - leading + 1
        if 1 <= day_n <= n_days:
            return (_month_start + pd.Timedelta(days=day_n - 1)).date()
        return None

    # weekly totals
    week_totals = []
    for r in range(rows):
        pnl_sum = 0.0
        trade_sum = 0
        for c in range(7):
            d = slot_to_date(r * 7 + c)
            if d is not None:
                p, t = daily_map.get(d, (0.0, 0))
                pnl_sum += p
                trade_sum += t
        week_totals.append((pnl_sum, trade_sum))

    # draw
    shapes, annos = [], []

    # outer rounded area (8 cols incl TOTAL)
    outer_path = _round_rect_path(-0.06, -0.80, 8.06, rows + 0.03, card_radius)
    shapes.append(
        dict(
            type="path",
            path=outer_path,
            line=dict(color=border_col, width=1.0),
            fillcolor=panel_bg,
            layer="below",
        )
    )

    # weekday header (slightly larger)
    weekday_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Total"]
    for c, label in enumerate(weekday_labels):
        annos.append(
            dict(
                x=c + 0.5,
                y=-0.28,
                xref="x",
                yref="y",
                text=f"<b>{label}</b>",
                showarrow=False,
                font=dict(size=14, color=weekday_col if c < 7 else header_total),
                xanchor="center",
                yanchor="middle",
            )
        )

    # cells
    for r in range(rows):
        for c in range(8):
            x0, x1 = c, c + 1
            y0, y1 = r, r + 1
            is_total = c == 7

            if not is_total:
                d = slot_to_date(r * 7 + c)
                fill, border = empty_fill, empty_border
                pnl_txt, pnl_col = "—", "#ffffff"
                trades_txt, day_idx = "—", ""

                if d is not None:
                    pnl_val, trade_ct = daily_map.get(d, (0.0, 0))
                    day_idx = str(d.day)
                    if trade_ct > 0:
                        if pnl_val > 0:
                            fill, border, pnl_col = pos_fill, pos_border, pnl_green
                        elif pnl_val < 0:
                            fill, border, pnl_col = neg_fill, neg_border, pnl_red
                        pnl_txt = f"${pnl_val:,.2f}".replace("$-", "-$")
                        trades_txt = f"{trade_ct} trade" if trade_ct == 1 else f"{trade_ct} trades"

                cell_path = _round_rect_path(
                    x0 + inset, y0 + inset, x1 - inset, y1 - inset, cell_radius
                )
                shapes.append(
                    dict(
                        type="path",
                        path=cell_path,
                        line=dict(color=border, width=1.0),
                        fillcolor=fill,
                        layer="below",
                    )
                )

                if d is not None:
                    annos.append(
                        dict(
                            x=x0 + 0.10,
                            y=y0 + 0.18,
                            xref="x",
                            yref="y",
                            text=day_idx,
                            showarrow=False,
                            font=dict(size=12, color=daynum_col),
                            xanchor="left",
                            yanchor="middle",
                        )
                    )
                annos.append(
                    dict(
                        x=x0 + 0.5,
                        y=y0 + 0.46,
                        xref="x",
                        yref="y",
                        text=pnl_txt,
                        showarrow=False,
                        font=dict(size=16, color=pnl_col),
                        xanchor="center",
                        yanchor="middle",
                    )
                )
                annos.append(
                    dict(
                        x=x0 + 0.5,
                        y=y0 + 0.76,
                        xref="x",
                        yref="y",
                        text=trades_txt,
                        showarrow=False,
                        font=dict(size=11, color=trades_col),
                        xanchor="center",
                        yanchor="top",
                    )
                )
            else:
                # Weekly TOTAL column — keep normal fill/color logic, but add a blue, thicker border
                pnl_sum, trade_sum = week_totals[r]

                # default neutral
                t_fill = empty_fill
                t_color = "#ffffff"

                if trade_sum > 0:
                    if pnl_sum > 0:
                        t_fill = pos_fill
                        t_color = pnl_green
                    elif pnl_sum < 0:
                        t_fill = neg_fill
                        t_color = pnl_red
                    # pnl == 0 -> neutral fill + white text

                # blue border ONLY (thicker)
                t_border = accent_blue

                tot_pnl_txt = "—" if trade_sum == 0 else f"${pnl_sum:,.2f}".replace("$-", "-$")
                tot_trd_txt = (
                    "—"
                    if trade_sum == 0
                    else (f"{trade_sum} trade" if trade_sum == 1 else f"{trade_sum} trades")
                )

                cell_path = _round_rect_path(
                    x0 + inset, y0 + inset, x1 - inset, y1 - inset, cell_radius
                )
                shapes.append(
                    dict(
                        type="path",
                        path=cell_path,
                        line=dict(color=t_border, width=1.0),  # thicker blue border
                        fillcolor=t_fill,
                        layer="below",
                    )
                )

                annos.append(
                    dict(
                        x=x0 + 0.5,
                        y=y0 + 0.46,
                        xref="x",
                        yref="y",
                        text=tot_pnl_txt,
                        showarrow=False,
                        font=dict(size=16, color=t_color),  # keep green/red/white for PnL
                        xanchor="center",
                        yanchor="middle",
                    )
                )
                annos.append(
                    dict(
                        x=x0 + 0.5,
                        y=y0 + 0.76,
                        xref="x",
                        yref="y",
                        text=tot_trd_txt,
                        showarrow=False,
                        font=dict(size=11, color=trades_col),  # trades remain white
                        xanchor="center",
                        yanchor="top",
                    )
                )

    # figure (increased row height to make cells squarer)
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=panel_bg,
        plot_bgcolor=panel_bg,
        shapes=shapes,
        annotations=annos,
        xaxis=dict(
            range=[0, 8], showgrid=False, zeroline=False, tickvals=[], ticktext=[], fixedrange=True
        ),
        yaxis=dict(
            range=[rows, -1],
            showgrid=False,
            zeroline=False,
            tickvals=[],
            ticktext=[],
            fixedrange=True,
        ),
        margin=dict(l=6, r=6, t=2, b=6),
    )
    cal_h = int(160 + rows * 160)  # <-- taller rows for “squared” look
    fig.update_layout(height=cal_h)

    st.plotly_chart(fig, use_container_width=True, key=f"{key}_{_month_start.strftime('%Y%m')}")
