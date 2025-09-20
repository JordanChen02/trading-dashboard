# src/views/overview.py
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import src.views.calendar_panel as cal_view
from src.charts.equity import plot_equity
from src.charts.pnl import plot_pnl
from src.charts.rr import plot_rr
from src.components.winstreak import render_winstreak
from src.styles import inject_overview_css
from src.theme import BLUE


def render_overview(
    df_view: pd.DataFrame,
    start_equity: float,
    date_col: Optional[str],
    month_start: pd.Timestamp,
    win_rate_v: float,
    avg_win_loss_ratio_v: float,
    avg_win_v: float,
    avg_loss_v: float,
    pnl_v: pd.Series,
    wins_mask_v: pd.Series,
    losses_mask_v: pd.Series,
) -> None:

    inject_overview_css()

    """Renders the full Overview tab (left/right split, KPIs, equity curve tabs, daily/weekly PnL, win streak, calendar, filter button)."""

    # ======= LAYOUT FRAME: 40/60 main split (left=40%, right=60%) =======
    s_left, s_right = st.columns([2, 3], gap="small")  # 2:3 ≈ 40%:60%

    with s_left:
        # === Prep values used in these KPIs (Range-aware) ===
        gross_profit_v = float(pnl_v[wins_mask_v].sum())
        gross_loss_v = float(pnl_v[losses_mask_v].sum())
        pf_v = (gross_profit_v / abs(gross_loss_v)) if gross_loss_v != 0 else float("inf")

        _side_dist_local = (
            df_view["side"]
            .str.lower()
            .value_counts(normalize=True)
            .reindex(["long", "short"])
            .fillna(0.0)
            if "side" in df_view.columns
            else pd.Series(dtype=float)
        )
        # Expectancy / Trade (in $)
        expectancy_v = float(win_rate_v) * float(avg_win_v) + (1.0 - float(win_rate_v)) * float(
            avg_loss_v
        )

        # === KPI GRID (2x2) ===
        kpi_row1 = st.columns([1, 1], gap="small")
        with kpi_row1[0]:
            with st.container(border=True):
                st.markdown(
                    '<div style="text-align:center; font-weight:600; margin:0 0 6px; transform: translateX(6px);">Win Rate</div>',
                    unsafe_allow_html=True,
                )

                wr_pct = float(win_rate_v * 100.0)  # win_rate_v is 0..1
                win_color = "#2E86C1"
                loss_color = "#212C47"
                panel_bg = "#0b0f19"

                fig_win = go.Figure(
                    go.Indicator(
                        mode="gauge",
                        value=wr_pct,
                        gauge={
                            "shape": "angular",
                            "axis": {"range": [0, 100], "visible": False},
                            "bar": {"color": "rgba(0,0,0,0)"},
                            "borderwidth": 0,
                            "steps": [
                                {"range": [0, wr_pct], "color": win_color},
                                {"range": [wr_pct, 100.0], "color": loss_color},
                            ],
                        },
                        domain={"x": [0, 1], "y": [0, 1]},
                    )
                )
                fig_win.update_layout(
                    margin=dict(l=8, r=8, t=6, b=0),
                    height=90,
                    paper_bgcolor=panel_bg,
                )
                fig_win.add_annotation(
                    x=0.5,
                    y=0.10,
                    xref="paper",
                    yref="paper",
                    text=f"{wr_pct:.0f}%",
                    showarrow=False,
                    font=dict(size=30, color="#e5e7eb", family="Inter, system-ui, sans-serif"),
                    align="center",
                )
                st.plotly_chart(fig_win, use_container_width=True)

        with kpi_row1[1]:
            with st.container(border=True):
                st.markdown('<div class="kpi-pack">', unsafe_allow_html=True)

                _aw_al_num = (
                    "∞" if avg_win_loss_ratio_v == float("inf") else f"{avg_win_loss_ratio_v:.2f}"
                )
                st.markdown(
                    f"""
                    <div class="kpi-center">
                      <div class="kpi-number">{_aw_al_num}</div>
                      <div class="kpi-label">Avg Win / Avg Loss</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # --- Blue/Red ratio pill (Avg Win vs Avg Loss) ---
                _aw = float(max(avg_win_v, 0.0))
                _al = float(abs(avg_loss_v))
                _total = _aw + _al
                _blue_pct = 50.0 if _total <= 0 else (_aw / _total) * 100.0
                _red_pct = 100.0 - _blue_pct

                st.markdown(
                    f"""
                    <div class="pillbar" style="margin-top:6px;">
                      <div class="win"  style="width:{_blue_pct:.2f}%"></div>
                      <div class="loss" style="width:{_red_pct:.2f}%"></div>
                    </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # --- KPI row 2 (Profit Factor left, Long vs Short right) ---
        kpi_row2 = st.columns([1, 1], gap="small")

        # LEFT: Profit Factor — half donut
        with kpi_row2[0]:
            with st.container(border=True):
                st.markdown(
                    '<div style="text-align:center; font-weight:600; margin:0 0 6px; transform: translateX(6px);">'
                    "Profit Factor</div>",
                    unsafe_allow_html=True,
                )

                pf_display = "∞" if pf_v == float("inf") else f"{pf_v:.2f}"
                max_pf = 4.0
                pf_clamped = max(0.0, min(float(pf_v if pf_v != float("inf") else max_pf), max_pf))
                pct = (pf_clamped / max_pf) * 100.0

                panel_bg = "#0b0f19"
                fill_col = "#2E86C1"
                rest_col = "#212C47"

                fig_pf = go.Figure(
                    go.Indicator(
                        mode="gauge",
                        value=pct,
                        gauge={
                            "shape": "angular",
                            "axis": {"range": [0, 100], "visible": False},
                            "bar": {"color": "rgba(0,0,0,0)"},
                            "borderwidth": 0,
                            "steps": [
                                {"range": [0, pct], "color": fill_col},
                                {"range": [pct, 100.0], "color": rest_col},
                            ],
                        },
                        domain={"x": [0, 1], "y": [0, 1]},
                    )
                )
                fig_pf.update_layout(
                    margin=dict(l=8, r=8, t=6, b=0),
                    height=90,
                    paper_bgcolor=panel_bg,
                    showlegend=False,
                )
                fig_pf.add_annotation(
                    x=0.5,
                    y=0.10,
                    xref="paper",
                    yref="paper",
                    text=pf_display,
                    showarrow=False,
                    font=dict(size=28, color="#e5e7eb", family="Inter, system-ui, sans-serif"),
                    align="center",
                )
                st.plotly_chart(fig_pf, use_container_width=True)

        # RIGHT: Expectancy / Trade — compact KPI
        with kpi_row2[1]:
            with st.container(border=True):
                st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
                st.markdown(
                    '<div style="text-align:center; font-weight:600; margin:0 0 10px; transform: translateX(6px);">'
                    "Expectancy / Trade</div>",
                    unsafe_allow_html=True,
                )
                big = f"${expectancy_v:,.2f}"
                # --- Clean zero-centered pill bar for Expectancy ---

                # symmetric cap (so the bar is centered at 0)
                denom = max(abs(float(avg_win_v)), abs(float(avg_loss_v)), 1e-9)
                cap = max(denom * 2.0, 1.0)  # widen/narrow the bar range as you like
                v = float(expectancy_v)
                target_e = 8.0  # $ target

                # map value -> [0,1] position (0.5 is zero)
                def to_pos(val: float) -> float:
                    return (val + cap) / (2 * cap)

                x0 = 0.08  # left padding
                x1 = 0.92  # right padding
                mid = (x0 + x1) / 2.0
                y0, y1 = 0.40, 0.60  # pill thickness

                rail = "#212C47"
                pos_col = "#2E86C1"
                neg_col = "#9B2C2C"

                x_val = x0 + (x1 - x0) * to_pos(v)
                x_tgt = x0 + (x1 - x0) * to_pos(target_e)

                fig_e = go.Figure()
                # background rail
                fig_e.add_shape(
                    type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=rail, line=dict(width=0)
                )
                # filled segment from center→value
                if v >= 0:
                    fig_e.add_shape(
                        type="rect",
                        x0=mid,
                        x1=x_val,
                        y0=y0,
                        y1=y1,
                        fillcolor=pos_col,
                        line=dict(width=0),
                    )
                else:
                    fig_e.add_shape(
                        type="rect",
                        x0=x_val,
                        x1=mid,
                        y0=y0,
                        y1=y1,
                        fillcolor=neg_col,
                        line=dict(width=0),
                    )
                # zero tick (subtle)
                fig_e.add_shape(
                    type="line",
                    x0=mid,
                    x1=mid,
                    y0=y0 - 0.08,
                    y1=y1 + 0.08,
                    line=dict(color="rgba(229,231,235,0.25)", width=1),
                )
                # target marker
                fig_e.add_shape(
                    type="line",
                    x0=x_tgt,
                    x1=x_tgt,
                    y0=y0 - 0.14,
                    y1=y1 + 0.14,
                    line=dict(color="rgba(229,231,235,0.9)", width=2),
                )

                # hover (optional): show value on hover anywhere on the pill
                fig_e.add_trace(
                    go.Scatter(
                        x=[x_val],
                        y=[(y0 + y1) / 2],
                        mode="markers",
                        marker=dict(size=0.1, color="rgba(0,0,0,0)"),
                        hovertemplate=f"Expectancy: ${v:,.2f}<extra></extra>",
                    )
                )

                fig_e.update_xaxes(visible=False, range=[0, 1], fixedrange=True)
                fig_e.update_yaxes(visible=False, range=[0, 1], fixedrange=True)
                fig_e.update_layout(
                    margin=dict(l=8, r=8, t=2, b=2),
                    height=56,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_e, use_container_width=True)

                st.markdown(
                    f"<div style='font-size:36px; font-weight:700; text-align:center; margin:2px 0 16px;'>{big}</div>",
                    unsafe_allow_html=True,
                )

        # === Equity Curve (bottom of s_left) — with tabs and date x-axis ===
        with st.container(border=True):

            _has_date = date_col is not None and date_col in df_view.columns and len(df_view) > 0
            df_ec = df_view.copy()
            pnl_num = pd.to_numeric(df_ec["pnl"], errors="coerce").fillna(0.0)
            df_ec["cum_pnl"] = pnl_num.cumsum()
            df_ec["equity"] = float(start_equity) + df_ec["cum_pnl"]

            if _has_date:
                _dt = pd.to_datetime(df_ec[date_col], errors="coerce")
                df_ec = df_ec.assign(_date=_dt).sort_values("_date")
            else:
                df_ec = df_ec.reset_index(drop=True).assign(
                    _date=pd.RangeIndex(start=0, stop=len(df_ec))
                )

            def _slice_window(df_in: pd.DataFrame, label: str) -> pd.DataFrame:
                # Expect df_in has a datetime-like column "_date" already sorted ascending.
                if not _has_date or len(df_in) == 0 or label == "All":
                    return df_in

                x = pd.to_datetime(df_in["_date"], errors="coerce")
                last_ts = x.iloc[-1]
                last_day = last_ts.normalize()

                if label == "1D":
                    # Only trades on the latest calendar day
                    mask = x.dt.normalize() == last_day
                elif label == "1W":
                    # Last 7 calendar days (today + previous 6)
                    cutoff = last_day - pd.Timedelta(days=6)
                    mask = x.dt.normalize() >= cutoff
                elif label == "1M":
                    # Last 30 calendar days
                    cutoff = last_day - pd.Timedelta(days=29)
                    mask = x.dt.normalize() >= cutoff
                elif label == "6M":
                    # Last ~6 months; use 183 days to avoid month-length edge cases
                    cutoff = last_day - pd.Timedelta(days=183)
                    mask = x.dt.normalize() >= cutoff
                elif label == "1Y":
                    # Last 365 calendar days (if only 3 months exist, you'll just see those 3 months)
                    cutoff = last_day - pd.Timedelta(days=364)
                    mask = x.dt.normalize() >= cutoff
                else:
                    mask = slice(None)

                out = df_in.loc[mask]
                # Ensure the chart never ends up blank
                return out if len(out) else df_in.tail(1)

            st.markdown('<div class="eq-tabs">', unsafe_allow_html=True)

            hdr_l, hdr_r = st.columns([1, 3], gap="small")
            with hdr_l:
                st.markdown(
                    '<div style="color:#d5deed; font-weight:600; letter-spacing:.2px; font-size:32px; margin:0;">Equity Curve</div>',
                    unsafe_allow_html=True,
                )
            with hdr_r:
                st.empty()

            eq_tabs = st.tabs(["All", "1D", "1W", "1M", "6M", "1Y"])

            for _label, _tab in zip(["All", "1D", "1W", "1M", "6M", "1Y"], eq_tabs):
                with _tab:
                    _dfw = _slice_window(df_ec, _label)
                    if len(_dfw) == 0:
                        st.caption("No data in this window.")
                    else:
                        fig_eq = plot_equity(
                            _dfw,
                            start_equity=start_equity,
                            has_date=_has_date,
                            height=360,
                        )
                        # Use a unique key prefix so it won't collide with other tabs
                        st.plotly_chart(
                            fig_eq, use_container_width=True, key=f"ov_eq_curve_{_label}"
                        )

        with st.container(border=True):
            st.markdown(
                '<div style="font-weight:600; margin:0 0 8px; transform: translateX(6px);">Reward:Risk</div>',
                unsafe_allow_html=True,
            )

            _has_date = (date_col is not None) and (date_col in df_view.columns)
            rr_df = df_view.copy()

            # x-axis
            if _has_date:
                rr_df["_date"] = pd.to_datetime(rr_df[date_col], errors="coerce")
                rr_df = rr_df.loc[rr_df["_date"].notna()].sort_values("_date")
            else:
                rr_df["_date"] = np.arange(len(rr_df))

            # Placeholder RR (until you have a real rr column)
            if "rr" not in rr_df.columns:
                pnl_num = pd.to_numeric(rr_df.get("pnl", 0.0), errors="coerce").fillna(0.0)
                losses = pnl_num[pnl_num < 0].abs()
                risk_proxy = float(losses.median()) if len(losses) else 1.0
                rr_df["rr"] = pnl_num / (risk_proxy or 1.0)

            def _slice_window_rr(df_in: pd.DataFrame, label: str) -> pd.DataFrame:
                if not _has_date or len(df_in) == 0 or label == "All":
                    return df_in
                x = pd.to_datetime(df_in["_date"], errors="coerce")
                last = x.max().normalize()
                if label == "1D":
                    mask = x.dt.normalize() == last
                elif label == "1W":
                    mask = x.dt.normalize() >= last - pd.Timedelta(days=6)
                elif label == "1M":
                    mask = x.dt.normalize() >= last - pd.Timedelta(days=29)
                elif label == "6M":
                    mask = x.dt.normalize() >= last - pd.Timedelta(days=183)
                elif label == "1Y":
                    mask = x.dt.normalize() >= last - pd.Timedelta(days=364)
                else:
                    mask = slice(None)
                out = df_in.loc[mask]
                return out if len(out) else df_in.tail(1)

            tabs = st.tabs(["All", "1D", "1W", "1M", "6M", "1Y"])
            for lab, tab in zip(["All", "1D", "1W", "1M", "6M", "1Y"], tabs):
                with tab:
                    df_show = _slice_window_rr(rr_df, lab)
                    fig_rr = plot_rr(df_show[["_date", "rr"]], has_date=_has_date, height=150)
                    st.plotly_chart(fig_rr, use_container_width=True, key=f"rr_chart_{lab}")

        # === Right column top row (split in 2) ===
        with s_right:
            st.markdown("<div style='margin-bottom:-12px'></div>", unsafe_allow_html=True)
            right_top = st.columns([1.5, 1], gap="small")

            # ----- Left side: Daily / Weekly PnL (inside bordered card) -----
            with right_top[0]:
                with st.container(border=True):
                    # Header spacing knobs
                    TITLE_TOP_PAD = 10
                    CTRL_TOP_PAD = 4

                    # ROW 1: Title (left) | Segmented control (right)
                    r1l, r1r = st.columns([3, 1], gap="small")
                    with r1l:
                        st.markdown(
                            f"<div style='height:{TITLE_TOP_PAD}px'></div>", unsafe_allow_html=True
                        )
                        current_mode = st.session_state.get("_dpnl_mode", "Daily")
                        st.markdown(
                            "<div style='font-size:28px; font-weight:600; margin:0'>"
                            f"{current_mode} PnL</div>",
                            unsafe_allow_html=True,
                        )
                    with r1r:
                        st.markdown(
                            f"<div style='height:{CTRL_TOP_PAD}px'></div>", unsafe_allow_html=True
                        )
                        mode = st.segmented_control(
                            options=["Daily", "Weekly"], default=current_mode, label=""
                        )
                        st.session_state["_dpnl_mode"] = mode

                    # tighten gap between header and chart
                    st.markdown("<div style='margin-bottom:-12px'></div>", unsafe_allow_html=True)

                    # ---- Chart ----
                    mode = st.session_state.get("_dpnl_mode", "Daily")  # safety fallback
                    fig_pnl = plot_pnl(df_view, date_col, mode=mode, height=250)
                    st.plotly_chart(fig_pnl, use_container_width=True, key=f"ov_pnl_{mode}")

            # --- Right column bottom: Calendar panel ---
            with st.container(border=True):
                cal_view.render_calendar_panel(df_view, date_col, month_start, key="cal_overview")

        # Right side: Win Streak box
        with right_top[1]:
            with st.container(border=True):
                # ---- compute real streaks ----
                def _streak_stats(win_bool: pd.Series) -> tuple[int, int, int]:
                    """Return (current_win_streak, best_win_streak, resets_count)."""
                    if win_bool is None or len(win_bool) == 0:
                        return 0, 0, 0
                    s = pd.Series(win_bool).fillna(False).astype(bool)
                    grp = (s != s.shift()).cumsum()  # group consecutive equal values
                    run = (
                        s.groupby(grp).transform("size").where(s, 0)
                    )  # size of current win-run per row
                    current = int(run.iloc[-1]) if s.iloc[-1] else 0
                    best = int(run.max()) if len(run) else 0
                    resets = int(((~s) & s.shift(1).fillna(False)).sum())  # count win→loss breaks
                    return current, best, resets

                # trades streaks (row-level wins)
                pnl_series = (
                    pd.to_numeric(df_view["pnl"], errors="coerce").fillna(0.0)
                    if "pnl" in df_view.columns
                    else pd.Series(dtype=float)
                )
                trade_is_win = pnl_series > 0
                trades_streak, best_trades_streak, resets_trades_ct = _streak_stats(trade_is_win)

                # days streaks (net PnL by day)
                if date_col and (date_col in df_view.columns) and len(df_view) > 0:
                    dates = pd.to_datetime(df_view[date_col], errors="coerce")
                    daily_net = pnl_series.groupby(dates.dt.date).sum()
                    day_is_win = daily_net > 0
                    days_streak, best_days_streak, resets_days_count = _streak_stats(day_is_win)
                else:
                    days_streak = best_days_streak = resets_days_count = 0

                render_winstreak(
                    days_streak=days_streak,
                    trades_streak=trades_streak,
                    best_days_streak=best_days_streak,
                    resets_days_count=resets_days_count,
                    best_trades_streak=best_trades_streak,
                    resets_trades_ct=resets_trades_ct,
                    title="Winstreak",
                    brand_color=BLUE,
                )

                # keep the small spacing tweak you had before
                st.markdown("<div style='margin-bottom:-32px'></div>", unsafe_allow_html=True)

            # # --- Avg Setup Score (always show; N/A until journal populates it) ---
            # with st.container(border=True):
            #     st.markdown(
            #         '<div style="text-align:center; font-weight:600; margin:0 0 6px; transform: translateX(6px);">'
            #         "Avg Setup Score</div>",
            #         unsafe_allow_html=True,
            #     )

            #     if "setup_score_pct" in df_view.columns:
            #         try:
            #             _avg_score = float(
            #                 pd.to_numeric(df_view["setup_score_pct"], errors="coerce").mean()
            #             )
            #         except Exception:
            #             _avg_score = float("nan")
            #         if pd.notna(_avg_score):
            #             st.markdown(
            #                 f"<div style='font-size:32px; font-weight:700; text-align:center;'>{_avg_score:.1f}%</div>",
            #                 unsafe_allow_html=True,
            #             )
            #         else:
            #             st.markdown(
            #                 "<div style='font-size:14px; text-align:center; opacity:.8;'>N/A</div>",
            #                 unsafe_allow_html=True,
            #             )
            #     else:
            #         st.markdown(
            #             "<div style='font-size:14px; text-align:center; opacity:.8;'>N/A</div>",
            #             unsafe_allow_html=True,
            #         )

            # --- normalized strategy scores used by the radar/value list ---
            # 1) Win Rate → 0..100
            try:
                wr_score = max(0.0, min(100.0, float(win_rate_v) * 100.0))
            except Exception:
                wr_score = 0.0

            # 2) Payoff Ratio (Avg Win / |Avg Loss|), cap at 3.0 => 100
            try:
                payoff_raw = float(avg_win_loss_ratio_v)
                if payoff_raw == float("inf") or pd.isna(payoff_raw):
                    payoff_raw = 3.0
            except Exception:
                payoff_raw = 0.0
            payoff_cap = 3.0
            payoff_score = max(0.0, min(100.0, (payoff_raw / payoff_cap) * 100.0))

            # 3) Expectancy (normalized by larger of |avg win| or |avg loss|)
            try:
                exp_val = float(win_rate_v) * float(avg_win_v) + (1.0 - float(win_rate_v)) * float(
                    avg_loss_v
                )
            except Exception:
                exp_val = 0.0
            denom = max(abs(float(avg_win_v)), abs(float(avg_loss_v)), 1e-9)
            exp_norm_score = max(0.0, min(100.0, (exp_val / denom) * 100.0))

            # 4) Drawdown (inverted): score = 100 * (1 - min(1, |maxDD| / cap))
            try:
                pnl_series = pd.to_numeric(df_view["pnl"], errors="coerce").fillna(0.0)
                equity = float(start_equity) + pnl_series.cumsum()
                dd_pct = (equity / equity.cummax()) - 1.0  # negative values
                max_dd_abs = float(abs(dd_pct.min())) if len(dd_pct) else 0.0
            except Exception:
                max_dd_abs = 0.0
            dd_cap = 0.30  # 30% cap; tweak to taste
            dd_score = 100.0 * (1.0 - min(1.0, max_dd_abs / dd_cap))

            # --- Strategy Radar (normalized, orthogonal set) ---
            with st.container(border=True):
                st.markdown(
                    "<div style='text-align:center; font-weight:600; margin:0 0 6px;'>"
                    "Strategy Values <span style='opacity:.6'>(Normalized Scores)</span>"
                    "</div>",
                    unsafe_allow_html=True,
                )

                left_vals, right_chart = st.columns([1.1, 2.2], gap="small")

                with left_vals:
                    st.write(f"**Win Rate:** {wr_score:,.0f}%")
                    st.write(f"**Payoff Ratio:** {payoff_score:,.0f}%")
                    st.write(f"**Expectancy (norm):** {exp_norm_score:,.0f}%")
                    st.write(f"**Drawdown (inv):** {dd_score:,.0f}%")

                with right_chart:
                    fig = go.Figure(
                        go.Scatterpolar(
                            r=[wr_score, payoff_score, exp_norm_score, dd_score],
                            theta=[
                                "Win Rate",
                                "Payoff Ratio",
                                "Expectancy (norm)",
                                "Drawdown (inv)",
                            ],
                            fill="toself",
                            mode="lines+markers",
                            hovertemplate="%{theta}: %{r:.0f}%<extra></extra>",
                            line=dict(width=2),
                            marker=dict(size=5),
                        )
                    )
                    fig.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        margin=dict(l=6, r=6, t=6, b=6),
                        showlegend=False,
                        height=180,
                        polar=dict(
                            bgcolor="rgba(0,0,0,0)",
                            gridshape="linear",  # polygon grid (diamond/square)
                            angularaxis=dict(
                                rotation=90,  # "+" orientation (diamond polygon)
                                showticklabels=False,
                                ticks="",
                                gridcolor="rgba(255,255,255,0.3)",
                                linecolor="rgba(255,255,255,0.12)",
                            ),
                            radialaxis=dict(
                                range=[0, 100],
                                showticklabels=False,
                                ticks="",
                                gridcolor="rgba(255,255,255,0.2)",
                                linecolor="rgba(255,255,255,0.12)",
                            ),
                        ),
                    )
                    st.plotly_chart(fig, use_container_width=True)

    # ======= END LAYOUT FRAME =======
