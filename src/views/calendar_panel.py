# src/views/calendar_panel.py
import calendar as _cal

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_calendar_panel(
    df_view: pd.DataFrame,
    _date_col: str | None,
    month_start: pd.Timestamp,
    *,
    key: str = "cal",
):
    """Render the Calendar — Daily PnL & Trade Count panel in-place (no tabs)."""

    # === Begin: moved verbatim from your `with tab_calendar:` block (minus the first 2 header lines) ===

    # Guard
    if _date_col is None or _date_col not in df_view.columns or len(df_view) == 0:
        st.info("No date/timestamp column found — calendar view unavailable for this dataset.")
        return

    _month_start = pd.to_datetime(month_start).normalize().replace(day=1)
    _month_end = (_month_start + pd.offsets.MonthEnd(1)).normalize()

    # ---- Aggregate df_view by day for the selected month ----
    _dt = pd.to_datetime(df_view[_date_col], errors="coerce")
    _mask_month = (_dt >= _month_start) & (_dt <= _month_end)
    _dfm = df_view.loc[_mask_month].copy()
    _dfm["_day"] = pd.to_datetime(_dfm[_date_col], errors="coerce").dt.date

    _daily_stats = (
        _dfm.assign(_pnl=pd.to_numeric(_dfm["pnl"], errors="coerce").fillna(0.0))
        .groupby("_day")
        .agg(NetPnL=("_pnl", "sum"), Trades=("pnl", "count"))
        .reset_index()
    )
    _daily_map = {
        row["_day"]: (float(row["NetPnL"]), int(row["Trades"]))
        for _, row in _daily_stats.iterrows()
    }

    # ---- Build calendar grid meta ----
    _first_weekday, _n_days = _cal.monthrange(_month_start.year, _month_start.month)  # Mon=0..Sun=6
    _leading = _first_weekday
    _total_slots = _leading + _n_days
    _rows = (_total_slots + 6) // 7  # ceil div by 7

    # ---------- THEME TOKENS ----------
    _panel_bg = "#0b0f19"
    _cell_bg = "#101621"
    _grid_line = "#2a3444"
    _txt_main = "#e5e7eb"
    _txt_muted = "#9ca3af"
    _pnl_pos = "#22c55e"
    _pnl_neg = "#ef4444"
    _pnl_zero = _txt_main
    _dash_accent = "#1f2937"
    _total_bg = "#0d1320"
    _total_border = "#3a4557"
    _total_hdr = "#cbd5e1"

    def _slot_in_month(slot_idx: int) -> bool:
        day_n = slot_idx - _leading + 1
        return 1 <= day_n <= _n_days

    def _slot_to_date(slot_idx: int):
        day_n = slot_idx - _leading + 1
        if 1 <= day_n <= _n_days:
            return (_month_start + pd.Timedelta(days=day_n - 1)).date()
        return None

    # Precompute weekly totals (row-wise)
    week_totals = []
    for r_idx in range(_rows):
        start_slot = r_idx * 7
        pnl_sum = 0.0
        trade_sum = 0
        for c_idx in range(7):
            slot_idx = start_slot + c_idx
            d = _slot_to_date(slot_idx)
            if d is not None:
                p, t = _daily_map.get(d, (0.0, 0))
                pnl_sum += float(p)
                trade_sum += int(t)
        week_totals.append((pnl_sum, trade_sum))

    # ---------- DRAW GRID ----------
    shapes, annos = [], []

    # weekday header (adds "Total" column)
    _weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Total"]
    for c, label in enumerate(_weekday_labels):
        annos.append(
            dict(
                x=c + 0.5,
                y=-0.35,
                xref="x",
                yref="y",
                text=label,
                showarrow=False,
                font=dict(size=12, color=_total_hdr if label == "Total" else _txt_muted),
                xanchor="center",
                yanchor="middle",
            )
        )

    # rounded outer container (8 columns wide incl. totals)
    total_w, total_h = 8, _rows
    _corner_r = 0.35
    path = (
        f"M{_corner_r},-1 H{total_w - _corner_r} "
        f"Q{total_w},-1 {total_w},{-1 + _corner_r} "
        f"V{total_h - _corner_r} "
        f"Q{total_w},{total_h} {total_w - _corner_r},{total_h} "
        f"H{_corner_r} "
        f"Q0,{total_h} 0,{total_h - _corner_r} "
        f"V{-1 + _corner_r} "
        f"Q0,-1 {_corner_r},-1 Z"
    )
    shapes.append(
        dict(
            type="path",
            path=path,
            line=dict(color=_dash_accent, width=1.5),
            fillcolor=_panel_bg,
            layer="below",
        )
    )

    # cells (7 day columns + 1 total column)
    for r_idx in range(_rows):
        for c_idx in range(8):
            x0, x1 = c_idx, c_idx + 1
            y0, y1 = r_idx, r_idx + 1
            is_total_col = c_idx == 7

            shapes.append(
                dict(
                    type="rect",
                    x0=x0,
                    x1=x1,
                    y0=y0,
                    y1=y1,
                    line=dict(
                        color=_total_border if is_total_col else _grid_line,
                        width=1.5 if is_total_col else 1,
                    ),
                    fillcolor=_total_bg if is_total_col else _cell_bg,
                    layer="below",
                )
            )

            if not is_total_col:
                slot_idx = r_idx * 7 + c_idx
                if _slot_in_month(slot_idx):
                    d = _slot_to_date(slot_idx)
                    pnl_val, trade_ct = _daily_map.get(d, (0.0, 0))

                    # day number
                    annos.append(
                        dict(
                            x=x0 + 0.08,
                            y=y0 + 0.15,
                            xref="x",
                            yref="y",
                            text=str((slot_idx - _leading + 1)),
                            showarrow=False,
                            font=dict(size=12, color=_txt_muted),
                            xanchor="left",
                            yanchor="top",
                        )
                    )

                    # PnL (center)
                    if trade_ct == 0:
                        pnl_txt = "—"
                        pnl_col = _txt_muted
                    else:
                        pnl_txt = f"${pnl_val:,.0f}"
                        pnl_col = (
                            _pnl_pos if pnl_val > 0 else (_pnl_neg if pnl_val < 0 else _pnl_zero)
                        )
                    annos.append(
                        dict(
                            x=x0 + 0.5,
                            y=y0 + 0.48,
                            xref="x",
                            yref="y",
                            text=pnl_txt,
                            showarrow=False,
                            font=dict(size=16, color=pnl_col),
                            xanchor="center",
                            yanchor="middle",
                        )
                    )

                    # trades (below center)
                    trades_txt = (
                        "—"
                        if trade_ct == 0
                        else (f"{trade_ct} trade" if trade_ct == 1 else f"{trade_ct} trades")
                    )
                    annos.append(
                        dict(
                            x=x0 + 0.5,
                            y=y0 + 0.78,
                            xref="x",
                            yref="y",
                            text=trades_txt,
                            showarrow=False,
                            font=dict(size=11, color=_txt_muted),
                            xanchor="center",
                            yanchor="top",
                        )
                    )
            else:
                pnl_sum, trade_sum = week_totals[r_idx]
                # totals PnL
                if trade_sum == 0:
                    tot_pnl_txt = "—"
                    tot_pnl_col = _txt_muted
                else:
                    tot_pnl_txt = f"${pnl_sum:,.0f}"
                    tot_pnl_col = (
                        _pnl_pos if pnl_sum > 0 else (_pnl_neg if pnl_sum < 0 else _pnl_zero)
                    )
                annos.append(
                    dict(
                        x=x0 + 0.5,
                        y=y0 + 0.48,
                        xref="x",
                        yref="y",
                        text=tot_pnl_txt,
                        showarrow=False,
                        font=dict(size=16, color=tot_pnl_col),
                        xanchor="center",
                        yanchor="middle",
                    )
                )
                # totals trades
                tot_trades_txt = (
                    "—"
                    if trade_sum == 0
                    else (f"{trade_sum} trade" if trade_sum == 1 else f"{trade_sum} trades")
                )
                annos.append(
                    dict(
                        x=x0 + 0.5,
                        y=y0 + 0.78,
                        xref="x",
                        yref="y",
                        text=tot_trades_txt,
                        showarrow=False,
                        font=dict(size=11, color=_txt_muted),
                        xanchor="center",
                        yanchor="top",
                    )
                )

    # Build figure
    fig_cal = go.Figure()
    fig_cal.update_layout(
        paper_bgcolor=_panel_bg,
        plot_bgcolor=_panel_bg,
        shapes=shapes,
        annotations=annos,
        xaxis=dict(
            range=[0, 8],
            showgrid=False,
            zeroline=False,
            tickmode="array",
            tickvals=[],
            ticktext=[],
            fixedrange=True,
        ),
        yaxis=dict(
            range=[_rows, -1],
            showgrid=False,
            zeroline=False,
            tickvals=[],
            ticktext=[],
            fixedrange=True,
        ),
        margin=dict(l=10, r=10, t=16, b=16),
    )
    _cal_h = int(160 + _rows * 120)
    fig_cal.update_layout(height=_cal_h)
    st.session_state["_cal_height"] = _cal_h

    _title = _month_start.strftime("%B %Y")
    st.markdown(f"### {_title}")
    st.plotly_chart(fig_cal, use_container_width=True, key=f"{key}_{month_start.strftime('%Y%m')}")
