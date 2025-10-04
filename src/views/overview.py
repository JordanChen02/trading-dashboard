# src/views/overview.py
import re
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.charts.equity import plot_equity
from src.charts.long_short import render_long_short_card
from src.charts.pnl import plot_pnl
from src.components.last_trades import render_last_trades
from src.components.monthly_stats import render_monthly_stats
from src.components.winstreak import render_winstreak
from src.styles import inject_overview_css
from src.theme import BLUE


def _build_top_assets_donut_and_summary(df, max_assets: int = 5):
    """
    Returns (fig, summary_df, colors) for the Most Traded Assets donut.
      - Uses the already-filtered df (df_view)
      - Counts UNIQUE trades per symbol when a trade id column exists
      - Top N (=5), rest bucketed as 'Others'
      - Thin donut, no inner text, center label = total trades
      - Muted palette for dark theme
    summary_df columns: ['asset','trades','pct','color'] ordered by trades desc
    """
    if df is None or df.empty:
        return None, None, None

    sym_col = next(
        (
            c
            for c in ["Symbol", "symbol", "Asset", "asset", "Ticker", "ticker", "Pair", "pair"]
            if c in df.columns
        ),
        None,
    )
    if not sym_col:
        return None, None, None

    trade_id_col = next(
        (c for c in ["trade_id", "TradeID", "tradeId", "ID", "Id", "id"] if c in df.columns), None
    )

    g = df.copy()
    g[sym_col] = g[sym_col].astype(str).str.strip()

    if trade_id_col:
        counts = g.groupby(sym_col)[trade_id_col].nunique().sort_values(ascending=False)
    else:
        counts = g[sym_col].value_counts()

    if counts.empty:
        return None, None, None

    total = int(counts.sum())
    top = counts.head(max_assets)
    others = counts.iloc[max_assets:].sum()
    labels = top.index.tolist() + (["Others"] if others > 0 else [])
    values = top.values.tolist() + ([int(others)] if others > 0 else [])

    # Muted palette (last reserved for Others)
    palette = [
        "#7aa2f7",  # soft blue (primary accent)
        "#59c7d9",  # cyan-teal
        "#8b93e6",  # indigo/violet
        "#63d3a6",  # sea-green
        "#e5c07b",  # sand (one warm)
        "#ef8fa0",  # soft red (only if needed)
        "#475569",  # slate (Others)
    ]

    colors = palette[: len(labels)]
    if labels and labels[-1] == "Others":
        colors[-1] = "#7b8794"

    # Build summary table
    pct = [round(v * 100 / total, 1) for v in values]
    summary_df = pd.DataFrame(
        {
            "asset": labels,
            "trades": values,
            "pct": pct,
            "color": colors,
        }
    )

    # Thin donut + center total
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.76,  # thinner ring
            rotation=315,
            direction="clockwise",
            textinfo="none",
            sort=False,
            hovertemplate="%{label}: %{value} trades (%{percent})<extra></extra>",
            hoverlabel=dict(bgcolor="rgba(17,24,39,0.9)", font=dict(size=12, color="#E5E7EB")),
            marker=dict(colors=colors, line=dict(color="rgba(0,0,0,0.35)", width=1)),
            showlegend=False,  # legend handled by our table
        )
    )
    fig.update_layout(
        height=260,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        annotations=[
            dict(  # small label
                x=0.5,
                y=0.54,
                xref="paper",
                yref="paper",
                text="Total Trades",
                showarrow=False,
                align="center",
                font=dict(size=12, color="#9AA4B2"),
            ),
            dict(  # big number, a bit lower -> this creates vertical gap
                x=0.5,
                y=0.46,
                xref="paper",
                yref="paper",
                text=f"<b>{total}</b>",  # <b> is allowed
                showarrow=False,
                align="center",
                font=dict(size=22, color="#E5E7EB", family="inherit"),
            ),
        ],
    )
    fig.update_traces(
        hoverlabel=dict(
            bgcolor="rgba(17,24,39,0.92)",
            font=dict(size=12, color="#E5E7EB"),
        )
    )

    return fig, summary_df, colors


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

    # --- Per-card bottom spacers (px) — tune these freely
    PAD_K1 = 6  # Balance / Net Profit
    PAD_K2 = 18  # Win Rate
    PAD_K3 = 18  # Profit Factor
    PAD_K5 = 10  # Winstreak

    # ===== TOP KPI ROW (full width) =====
    k1, k2, k3, k4, k5 = st.columns([1.2, 1, 1, 1, 1], gap="small")

    # -- k1: Balance & Net Profit (side-by-side) --
    with k1:
        with st.container(border=True):
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            _net = (
                float(pd.to_numeric(df_view.get("pnl", 0.0), errors="coerce").sum())
                if df_view is not None
                else 0.0
            )
            balance_v = float(start_equity) + _net
            net_profit_v = _net
            pos = "#61D0A8"  # same green as Last Trades
            neg = "#E06B6B"  # same red as Last Trades
            net_color = pos if net_profit_v >= 0 else neg

            st.markdown(
                f"""
                <div class="kpi-pair">
                <div class="kcol">
                    <div class="k-label">Balance</div>
                    <div class="k-value" style="color:{pos};">${balance_v:,.2f}</div>
                </div>
                <div class="k-sep"></div>
                <div class="kcol">
                    <div class="k-label">Net Profit</div>
                    <div class="k-value" style="color:{net_color};">${net_profit_v:,.2f}</div>
                </div>
                </div>
                <style>
                .kpi-pair {{
                    display: flex; align-items: center; justify-content: space-evenly;
                    gap: 16px; padding: 8px 0 12px;
                }}
                .kpi-pair .kcol {{ text-align: center; min-width: 140px; }}
                .kpi-pair .k-label {{ font-size: 18px; font-weight: 600; color: #ffffff; margin-bottom: 2px; }}
                .kpi-pair .k-value {{ font-size: 32px; font-weight: 800; line-height: 1.1; }}
                .kpi-pair .k-sep {{ width: 1px; height: 102px; background: rgba(96,165,250,0.22); border-radius: 1px; }}
                @media (max-width: 900px) {{
                    .kpi-pair {{ flex-direction: column; gap: 8px; }}
                    .kpi-pair .k-sep {{ display: none; }}
                }}
                </style>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(f"<div style='height:{PAD_K1}px'></div>", unsafe_allow_html=True)

    # -- k2: Win Rate (reuse your donut) --
    with k2:
        # (copy from your existing Win Rate card)
        # START COPY of the block currently under: kpi_row1[0] -> with st.container(border=True): ...
        with st.container(border=True):
            st.markdown(
                '<div style="text-align:center; font-weight:600; margin:0 0 6px; transform: translateX(6px);">Win Rate</div>',
                unsafe_allow_html=True,
            )
            wr_pct = float(win_rate_v * 100.0)
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
                margin=dict(l=8, r=8, t=6, b=0), height=90, paper_bgcolor=panel_bg
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
            # --- Micro stats under Win Rate: Wins (left) | Losses (right) ---
            p = pd.to_numeric(df_view.get("pnl", np.nan), errors="coerce").dropna()
            wins = int((p > 0).sum())
            losses = int((p < 0).sum())
            wl_total = max(1, wins + losses)
            win_pct = (wins / wl_total) * 100.0
            loss_pct = (losses / wl_total) * 100.0

            st.markdown(
                f"""
                <div class="wr-micro">
                <span class="win">Wins&nbsp;<b>{win_pct:.1f}%</b>&nbsp;<span class="muted">({wins})</span></span>
                <span class="loss">Losses&nbsp;<b>{loss_pct:.1f}%</b>&nbsp;<span class="muted">({losses})</span></span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                """
                <style>
                .wr-micro {
                    display:flex; justify-content:space-between; align-items:baseline;
                    margin-top: 8px; font-size: 12px;
                }
                .wr-micro .muted { opacity: 0.7; font-weight: 500; }
                .wr-micro .win  { color: #9AD8C3; }   /* subtle green-ish for wins */
                .wr-micro .loss { color: #E06B6B; }   /* your loss red */
                </style>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(f"<div style='height:{PAD_K2}px'></div>", unsafe_allow_html=True)

        # END COPY

    # -- k3: Profit Factor (reuse your donut) --
    with k3:
        # (copy from your existing Profit Factor card: kpi_row2[0])
        # START COPY of the PF block...
        with st.container(border=True):
            st.markdown(
                '<div style="text-align:center; font-weight:600; margin:0 0 6px; transform: translateX(6px);">Profit Factor</div>',
                unsafe_allow_html=True,
            )
            gross_profit_v = float(pnl_v[wins_mask_v].sum())
            gross_loss_v = float(pnl_v[losses_mask_v].sum())
            pf_v = (gross_profit_v / abs(gross_loss_v)) if gross_loss_v != 0 else float("inf")
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
                margin=dict(l=8, r=8, t=6, b=0), height=90, paper_bgcolor=panel_bg, showlegend=False
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
            # --- Micro stats under Profit Factor: Avg Win (left) | Avg Loss (right) ---
            p = pd.to_numeric(df_view.get("pnl", np.nan), errors="coerce").dropna()
            avg_win = float(p[p > 0].mean()) if (p > 0).any() else 0.0
            avg_loss_abs = float((-p[p < 0]).mean()) if (p < 0).any() else 0.0  # absolute avg loss

            def _fmt_money(x: float) -> str:
                return f"${x:,.2f}"

            st.markdown(
                f"""
                <div class="pf-micro">
                <span class="left">Avg Win&nbsp;<b>{_fmt_money(avg_win)}</b></span>
                <span class="right">Avg Loss&nbsp;<b style="color:#E06B6B;">-{_fmt_money(avg_loss_abs)}</b></span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                """
                <style>
                .pf-micro {
                    display:flex; justify-content:space-between; align-items:baseline;
                    margin-top: 8px; font-size: 12px;
                }
                .pf-micro .left  { color: #D5F1E7; }  /* muted win label */
                .pf-micro .right { color: #A8B2C1; }  /* muted loss label (value itself is red) */
                </style>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(f"<div style='height:{PAD_K3}px'></div>", unsafe_allow_html=True)
        # END COPY

    # -- k4: Long vs Short (ratio pill) --
    with k4:
        with st.container(border=True):
            st.markdown(
                '<div style="text-align:center; font-weight:600; margin:0 0 8px;">Long vs Short</div>',
                unsafe_allow_html=True,
            )

            # Count longs/shorts (graceful if 'side' missing)
            if ("side" in df_view.columns) and (len(df_view) > 0):
                side = df_view["side"].astype(str).str.strip().str.lower()
                n_long = int((side == "long").sum())
                n_short = int((side == "short").sum())
                total = n_long + n_short
            else:
                n_long = n_short = total = 0

            if total == 0:
                st.caption("No long/short information in this period.")
            else:
                p_long = (n_long / total) * 100.0
                p_short = 100.0 - p_long

                # Header labels with counts
                st.markdown(
                    f"""
                    <div class="ls-head">
                    <div class="ls-left">Longs <span>{p_long:.2f}%</span> <span class="muted">({n_long})</span></div>
                    <div class="ls-right">Shorts <span>{p_short:.2f}%</span> <span class="muted">({n_short})</span></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # The pill itself
                st.markdown(
                    f"""
                    <div class="ls-pill">
                    <div class="ls-long"  style="width:{p_long:.4f}%"></div>
                    <div class="ls-short" style="width:{p_short:.4f}%"></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Local styles (kept self-contained to this card)
                st.markdown(
                    f"""
                    <style>
                    .ls-head {{
                        display:flex; justify-content:space-between; align-items:baseline;
                        margin: 2px 2px 8px 2px;
                    }}
                    .ls-head .ls-left, .ls-head .ls-right {{
                        font-size:14px; color:#E5E7EB; font-weight:600;
                    }}
                    .ls-head span {{ color:#D5DEED; }}
                    .ls-head .muted {{ color:#9AA4B2; font-weight:500; }}
                    .ls-pill {{
                        width:100%; height:12px; border-radius:999px; overflow:hidden;
                        display:flex; background:rgba(148,163,184,0.16);
                    }}
                    .ls-long  {{ background:{BLUE}; }}
                    .ls-short {{ background:%s; }}  # {{DARK}}
                    </style>
                    """,
                    unsafe_allow_html=True,
                )

    # -- k5: Winstreak (moved up here) --
    with k5:
        with st.container(border=True):
            # compute streaks (copied from your right panel)
            def _streak_stats(win_bool: pd.Series) -> tuple[int, int, int]:
                if win_bool is None or len(win_bool) == 0:
                    return 0, 0, 0
                s = pd.Series(win_bool).fillna(False).astype(bool)
                grp = (s != s.shift()).cumsum()
                run = s.groupby(grp).transform("size").where(s, 0)
                current = int(run.iloc[-1]) if s.iloc[-1] else 0
                best = int(run.max()) if len(run) else 0
                resets = int(((~s) & s.shift(1).fillna(False)).sum())
                return current, best, resets

            pnl_series = pd.to_numeric(df_view.get("pnl", 0.0), errors="coerce").fillna(0.0)
            trade_is_win = pnl_series > 0
            trades_streak, best_trades_streak, resets_trades_ct = _streak_stats(trade_is_win)
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
            st.markdown(f"<div style='height:{PAD_K5}px'></div>", unsafe_allow_html=True)

    """Renders the full Overview tab (left/right split, KPIs, equity curve tabs, daily/weekly PnL, win streak, calendar, filter button)."""

    # ======= LAYOUT FRAME: 40/60 main split (left=40%, right=60%) =======
    s_left, s_right = st.columns([1.8, 3], gap="small")  # 2:3 ≈ 40%:60%

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

        # ===== Most Traded Assets (donut + legend/table) — ABOVE Equity Curve =====
        with st.container(border=True):
            st.markdown(
                "<div style='font-weight:600; margin:2px 0 12px;'>Most Traded Assets</div>",
                unsafe_allow_html=True,
            )

            left, right = st.columns([1.2, 1], gap="large")

            with left:
                fig, summary_df, colors = _build_top_assets_donut_and_summary(df_view, max_assets=5)
                if fig is not None:
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                else:
                    st.caption("No trades to summarize.")

            with right:
                if summary_df is not None and not summary_df.empty:
                    # Build a compact HTML legend + table with color swatches
                    rows_html = []
                    for _, r in summary_df.iterrows():
                        swatch = f"<span style='display:inline-block;width:10px;height:10px;border-radius:2px;background:{r.color};margin-right:8px;'></span>"
                        rows_html.append(
                            "<tr>"
                            f"<td style='padding:8px 8px;border:none;'>{swatch}"
                            f"<span style='color:#D5DEED'>{r.asset}</span></td>"
                            f"<td style='padding:8px 8px;text-align:right;color:#E5E7EB;border:none;'>{int(r.trades)}</td>"
                            f"<td style='padding:8px 8px;text-align:right;color:#9AA4B2;border:none;'>{r.pct:.1f}%</td>"
                            "</tr>"
                        )

                    table_html = (
                        "<table style='width:100%;border-collapse:separate;border-spacing:0;"
                        "border:none;outline:none;box-shadow:none;'>"
                        "<thead>"
                        "<tr>"
                        "<th style='text-align:left;padding:6px 8px;color:#9AA4B2;font-weight:600;border:none;'>Asset</th>"
                        "<th style='text-align:right;padding:6px 8px;color:#9AA4B2;font-weight:600;border:none;'>Trades</th>"
                        "<th style='text-align:right;padding:6px 8px;color:#9AA4B2;font-weight:600;border:none;'>%</th>"
                        "</tr>"
                        "</thead>"
                        "<tbody>" + "".join(rows_html) + "</tbody>"
                        "</table>"
                    )

                    st.markdown(table_html, unsafe_allow_html=True)
                else:
                    st.empty()

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
                    '<div style="color:#d5deed; font-weight:600; letter-spacing:.2px; font-size:18px; margin:0;">Equity Curve</div>',
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
                            height=240,
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
                TITLE_TOP_PAD = 6
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
                fig_pnl = plot_pnl(df_view, date_col, mode=mode, height=180)
                st.plotly_chart(fig_pnl, use_container_width=True, key=f"ov_pnl_{mode}")

            render_long_short_card(df_view, date_col=(date_col or "date"))

    # Right side: Win Streak box
    with right_top[1]:
        with st.container(border=True):
            # top padding
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            # ---- build real Last 5 Trades from df_view ----
            d = df_view.copy()
            last5 = []
            if d is not None and len(d) > 0:
                # choose a date to sort by (prefer exit_time)
                date_cols = [
                    "exit_time",
                    "Exit Time",
                    "entry_time",
                    "Entry Time",
                    "Date",
                    "Datetime",
                    "Timestamp",
                ]
                _dcol = next((c for c in date_cols if c in d.columns), None)
                if _dcol:
                    d[_dcol] = pd.to_datetime(d[_dcol], errors="coerce")
                    d = d.dropna(subset=[_dcol]).sort_values(_dcol, ascending=False)

                # symbol & side columns (best-effort)
                sym_col = (
                    "symbol"
                    if "symbol" in d.columns
                    else ("Symbol" if "Symbol" in d.columns else None)
                )
                side_col = (
                    "side"
                    if "side" in d.columns
                    else ("Direction" if "Direction" in d.columns else None)
                )

                # R multiple: find any plausible R column; otherwise compute from pnl / risk
                risk_cols = [
                    "risk",
                    "risk_amount",
                    "risk_$",
                    "risk_usd",
                    "max_loss",
                    "planned_loss",
                ]

                def _norm_name(s: str) -> str:
                    return re.sub(r"[^a-z0-9]", "", str(s).lower())

                def _parse_r_value(v):
                    # Accept: "1.2", "1.2R", "×1.2", "1.2x", "+1.2", "−1.2", etc.
                    if pd.isna(v):
                        return np.nan
                    s = str(v)
                    s = s.replace("×", "x").replace("−", "-")  # normalize unicode
                    m = re.search(r"[-+]?\d*\.?\d+", s)
                    if not m:
                        return np.nan
                    try:
                        return float(m.group(0))
                    except Exception:
                        return np.nan

                def _find_r_column(frame: pd.DataFrame) -> str | None:
                    # Preferred normalized names
                    preferred = {
                        "r",
                        "rr",
                        "rmultiple",
                        "rmultiple",
                        "rratio",
                        "r_r",
                        "rcolonr",
                        "rmultipleactual",
                    }
                    best = None
                    best_nonnull = 0
                    for c in frame.columns:
                        n = _norm_name(c)
                        if n in preferred or n.endswith("r") or "rmultiple" in n or n == "r":
                            vals = frame[c].apply(_parse_r_value)
                            nonnull = int(vals.notna().sum())
                            if nonnull > best_nonnull:
                                best_nonnull = nonnull
                                best = c
                    return best

                _r_col = _find_r_column(d)

                def _rr(row):
                    # 1) direct column if found
                    if _r_col is not None and _r_col in d.columns:
                        val = _parse_r_value(row.get(_r_col))
                        if pd.notna(val):
                            return val
                    # 2) compute from pnl / risk-like column
                    if "pnl" in d.columns and pd.notna(row.get("pnl")):
                        for rc in risk_cols:
                            if rc in d.columns and pd.notna(row.get(rc)):
                                rv = _parse_r_value(row.get(rc))
                                if pd.notna(rv) and rv > 0:
                                    return float(row["pnl"]) / rv
                    return np.nan

                # Percent gain: prefer explicit pct columns; else derive from pnl / starting equity map (default $5k)
                pct_cols = ["pct", "return_pct", "roi", "ROI %", "pnl_pct"]
                _eq_map = st.session_state.get("starting_equity", {"__default__": 5000.0})

                def _start_equity_for_row(row):
                    acc = str(row.get("Account", "")).strip()
                    if acc and acc in _eq_map:
                        return float(_eq_map[acc])
                    return float(_eq_map.get("__default__", 5000.0))

                def _pct(row):
                    # 1) use explicit percentage if provided
                    for c in pct_cols:
                        if c in d.columns and pd.notna(row.get(c)):
                            return float(row[c])
                    # 2) derive from pnl and starting equity
                    if "pnl" in d.columns and pd.notna(row.get("pnl")):
                        eq = _start_equity_for_row(row)
                        if eq and eq > 0:
                            return (float(row["pnl"]) / eq) * 100.0
                    return np.nan

                # entry type / setup label (optional)
                setup_cols = [
                    "entry_type",
                    "Type",
                    "Setup",
                    "Setup Tier",
                    "Strategy",
                    "Tag",
                    "Label",
                    "Notes",
                ]

                def _etype(row):
                    for c in setup_cols:
                        if c in d.columns and pd.notna(row.get(c)) and str(row[c]).strip():
                            return str(row[c]).strip()
                    return ""

                for _, row in d.head(5).iterrows():
                    last5.append(
                        {
                            "symbol": (str(row.get(sym_col, "")) if sym_col else ""),
                            "side": (str(row.get(side_col, "")).upper() if side_col else ""),
                            "entry_type": _etype(row),
                            "date_from": pd.to_datetime(
                                row.get(
                                    "entry_time",
                                    row.get("Entry Time", row.get("Date", row.get(_dcol))),
                                )
                            ),
                            "date_to": pd.to_datetime(
                                row.get("exit_time", row.get("Exit Time", row.get(_dcol)))
                            ),
                            "rr": _rr(row),
                            "pct": _pct(row),
                            "pnl": (
                                float(row.get("pnl", 0.0))
                                if "pnl" in d.columns and pd.notna(row.get("pnl"))
                                else 0.0
                            ),
                        }
                    )

            render_last_trades(last5, title="Last 5 Trades", key_prefix="ov_last5")
            # -------------------------------------------------

    # --- Right column bottom: Monthly Stats (replaces Calendar) ---
    render_monthly_stats(
        df_view,
        date_col=date_col,
        years_back=2,
        title="Monthly Stats",
        key="ov_mstats",
        cell_height=95,
        total_col_width_px=120,
    )
