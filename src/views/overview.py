# src/views/overview.py
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import src.views.calendar_panel as cal_view
from src.charts.equity import plot_equity
from src.charts.pnl import plot_pnl
from src.components.winstreak import render_winstreak
from src.styles import inject_overview_css
from src.theme import BLUE  # to pass the brand color


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
                if not _has_date or len(df_in) == 0 or label == "All":
                    return df_in
                last_ts = pd.to_datetime(df_in["_date"].iloc[-1])
                if label == "1D":
                    start = last_ts - pd.Timedelta(days=1)
                elif label == "1W":
                    start = last_ts - pd.Timedelta(weeks=1)
                elif label == "1M":
                    start = last_ts - pd.DateOffset(months=1)
                elif label == "6M":
                    start = last_ts - pd.DateOffset(months=6)
                elif label == "1Y":
                    start = last_ts - pd.DateOffset(years=1)
                else:
                    start = df_in["_date"].min()
                return df_in[df_in["_date"] >= start]

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
                            height=590,
                        )
                        # Use a unique key prefix so it won't collide with other tabs
                        st.plotly_chart(
                            fig_eq, use_container_width=True, key=f"ov_eq_curve_{_label}"
                        )

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
                # (temporary placeholders; wire real values later)
                days_streak = 9
                trades_streak = 19
                best_days_streak = 21
                resets_days_count = 1
                best_trades_streak = 19
                resets_trades_ct = 7

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
