# src/views/overview.py
import re
from textwrap import dedent
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.charts.long_short import render_long_short_card
from src.charts.pnl import plot_pnl
from src.components.last_trades import render_last_trades
from src.components.monthly_stats import render_monthly_stats
from src.components.winstreak import render_winstreak
from src.styles import inject_overview_css, inject_ui_title_css
from src.theme import BLUE, CARD_BG, DARK

GREEN = "#61D0A8"
RED = "#E06B6B"
TEAL = "#3FA096"


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
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
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


def _annotate_donut_title(fig, text, y=1.10):
    # y>1.0 draws the title above the half-donut; raise/lower with y
    fig.add_annotation(
        x=0.5,
        y=y,
        xref="paper",
        yref="paper",
        text=f"<b>{text}</b>",
        showarrow=False,
        font=dict(size=14, color="#E5E7EB"),
        align="center",
    )


def _annotate_donut_sides(
    fig, left_label_html, right_label_html, x_left=0.12, y_left=0.60, x_right=0.88, y_right=0.60
):
    # Left
    fig.add_annotation(
        x=x_left,
        y=y_left,
        xref="paper",
        yref="paper",
        text=left_label_html,
        showarrow=False,
        align="left",
    )
    # Right
    fig.add_annotation(
        x=x_right,
        y=y_right,
        xref="paper",
        yref="paper",
        text=right_label_html,
        showarrow=False,
        align="right",
    )


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
    inject_ui_title_css()

    st.markdown(
        """
        <style>
        /* tighten the page's top padding just for this view */
        div[data-testid="stAppViewContainer"] .main > div.block-container {
            padding-top: -8px !important;      /* adjust to taste */
        }
        /* kill any extra top margin on the first block */
        div[data-testid="stAppViewContainer"] .main .block-container > div:first-child {
            margin-top: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <style>
        /* ============ FILLED CARDS: consistent rounding + spacing ============ */
        /* Balance | Net Profit */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kpi-pair) {{
            background: {CARD_BG} !important;
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 12px !important;
            padding: 0px !important;
            transform: translateY(0px);   /* tweak verticality */
            min-height: 130px;             /* tweak card height */
            overflow: hidden;              /* keep inner edges clean */
        }}
        
        /* Win Rate */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .wr-root) {{
        background: {CARD_BG} !important;
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px !important;
        padding: 1px !important;
        overflow: hidden;
        }}

        /* Profit Factor */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .pf-root) {{
        background: {CARD_BG} !important;
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px !important;
        padding: 1px !important;
        overflow: hidden;
        }}

        /* Long vs Short */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ls-card) {{
            background: {CARD_BG} !important;
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 16px !important;
            padding: 10px !important;
            transform: translateY(0px);
            min-height: 145px;
            overflow: hidden;
        }}

        /* Winstreak */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ws-wrap) {{
            background: {CARD_BG} !important;
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 12px !important;
            padding: 12px !important;
            transform: translateY(0px);
            min-height: 140px;
            overflow: hidden;
        }}

        /* Most Traded Assets */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .mta-root) {{
          background: {CARD_BG} !important;
          border: 1px solid rgba(255,255,255,0.06);
          border-radius: 12px !important;
          padding: 12px !important;
          transform: translateY(-19px);     /* ⬆︎ negative = up, positive = down */
          min-height: 350px;              /* card height */
          overflow: hidden;
        }}

        /* Last 5 Trades */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .last5-root) {{
          background: {CARD_BG} !important;
          border: 1px solid rgba(255,255,255,0.06);
          border-radius: 12px !important;
          padding: 24px !important;
          transform: translateY(-35px);
          min-height: 340px;
          overflow: hidden;
        }}
 
        .last5-title{{
            font-weight:700;
            font-size:14px;
            margin:0;
            transform: translateY(-10px); /* tweak: negative = higher, positive = lower */
        }}

        /* Daily PnL */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .pnl-root) {{
          background: {CARD_BG} !important;
          border: 1px solid rgba(255,255,255,0.06);
          border-radius: 12px !important;
          padding: 12px !important;
          transform: translateY(-35px);
          min-height: 280px;
          overflow: hidden;
        }}
        /* Make Plotly canvases respect the card rounding */
        [data-testid="stPlotlyChart"] > div:first-child {{
            border-radius: 12px; overflow: hidden;
        }}
        /* Equity Curve */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .eq-root) {{
          background: {CARD_BG} !important;
          border: 1px solid rgba(255,255,255,0.06);
          border-radius: 12px !important;
          padding: 12px !important;
          transform: translateY(-20px);
          min-height: 392px;
          overflow: hidden;
        }}
        
        /* Unified chart/card title style */
        .chart-title {{
        margin: 0 0 2px 18px;      /* tight, like your other cards */
        font-size: 14px;        /* match */
        font-weight: 700;       /* match */
        line-height: 1.25;
        color: var(--fg, #E5E7EB);
        }}

        /* Long vs Short card — mirror equity card shell */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .lsr-root) {{
        background: {CARD_BG} !important;
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px !important;
        padding: 12px !important;
        /* keep ticks safe if the next row sits close */
        overflow: visible;
        /* if you pull the equity card up with translateY, mirror that here */
        transform: translateY(-34px);
        }}


        
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .wr-root) [data-testid="stPlotlyChart"],
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .pf-root) [data-testid="stPlotlyChart"]{{
        margin: 0 !important;
        }}
        /* Shift Monthly Stats card up slightly */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ms-root) {{
        transform: translateY(-66px);  /* tweak this value as you like */
        }}

        </style>
        """,
        unsafe_allow_html=True,
    )

    # --- Per-card bottom spacers (px) — tune these freely
    PAD_K1 = 6  # Balance / Net Profit
    PAD_K5 = 10  # Winstreak

    # ===== TOP KPI ROW (full width) =====
    k1, k2, k3, k4, k5 = st.columns([1.2, 1, 1, 1, 1], gap="small")

    # -- k1: Balance & Net Profit (side-by-side) --
    with k1:
        with st.container(border=False):
            st.markdown('<div class="ov-fill-marker"></div>', unsafe_allow_html=True)
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
                <div class="kpi-inner">
                <div class="kcol">
                    <div class="k-label">Balance</div>
                    <div class="k-value" style="color:{pos};">${balance_v:,.2f}</div>
                </div>
                </div>
                <div class="k-sep"></div>
                <div class="kpi-inner">
                <div class="kcol">
                    <div class="k-label">Net Profit</div>
                    <div class="k-value" style="color:{net_color};">${net_profit_v:,.2f}</div>
                </div>
                </div>
                </div>
                <style>
                .kpi-pair {{
                    display: flex; align-items: center; justify-content: space-evenly;
                    gap: 16px; padding: 8px 0 12px;
                }}
                .kpi-pair .kpi-inner {{ transform: translateY(-12px); }} /* content up/down only */
                .kpi-pair .kcol {{ text-align: center; min-width: 140px; }}
                .kpi-pair .k-label {{ font-size: 18px; font-weight: 600; color: #ffffff; margin-bottom: 2px; }}
                .kpi-pair .k-value {{ font-size: 32px; font-weight: 800; line-height: 1.1; }}
                .kpi-pair .k-sep {{ width: 1px; height: 102px; background: rgba(96,165,250,0.22); border-radius: 1px;  transform: translateY(-10px);}}
                @media (max-width: 900px) {{
                    .kpi-pair {{ flex-direction: column; gap: 8px; }}
                    .kpi-pair .k-sep {{ display: none; }}
                }}
                </style>
                <style>
                /* Optional per-card min-heights to align rows */
                div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kpi-pair)  {{ min-height: 140px; }}
                div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ls-card)   {{ min-height: 150px; }}
                div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ws-wrap)   {{ min-height: 120px; }}
                div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .mta-root)  {{ min-height: 340px; }}
                </style>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(f"<div style='height:{PAD_K1}px'></div>", unsafe_allow_html=True)

    with k2:
        with st.container(border=False):
            # ---- Win Rate donut ----
            wr_pct = float(win_rate_v * 100.0)
            win_color = "#2E86C1"
            loss_color = "#212C47"
            panel_bg = CARD_BG

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
                    domain={"x": [0, 1], "y": [0, 0.86]},
                )
            )
            # ---- INSIDE-donut title + left/right stacks ----
            # compute wins/losses from the filtered view
            p = pd.to_numeric(df_view.get("pnl", np.nan), errors="coerce").dropna()
            wins = int((p > 0).sum())
            losses = int((p < 0).sum())
            wl_tot = max(1, wins + losses)
            win_pct_real = (wins / wl_tot) * 100.0
            loss_pct_real = (losses / wl_tot) * 100.0

            # two-line hover (uses your palette)
            hover_html = (
                f"<span style='font-weight:700; color:#dbe4ee'>Wins </span>"
                f"<span style='font-weight:700; color:{GREEN}'>{win_pct_real:.1f}% ({wins})</span><br>"
                f"<span style='font-weight:700; color:#dbe4ee'>Losses </span>"
                f"<span style='font-weight:700; color:{RED}'>{loss_pct_real:.1f}% ({losses})</span>"
                "<extra></extra>"
            )

            # overlay: invisible pie to capture hover anywhere on the donut
            fig_win.add_trace(
                go.Pie(
                    values=[wr_pct, 100.0 - wr_pct],
                    hole=0.76,  # similar ring thickness
                    sort=False,
                    textinfo="none",
                    hovertemplate=hover_html,
                    hoverlabel=dict(
                        bgcolor="rgba(11,15,25,.95)",
                        bordercolor="#223045",
                        font_size=14,
                        font_family="Inter, system-ui, sans-serif",
                        font_color="#dbe4ee",
                    ),
                    marker=dict(colors=["rgba(0,0,0,0)", "rgba(0,0,0,0)"]),  # fully transparent
                    showlegend=False,
                    domain={"x": [0, 1], "y": [0, 0.86]},  # same vertical domain as your indicator
                )
            )

            fig_win.update_layout(
                hoverlabel=dict(bgcolor="rgba(11,15,25,.95)", bordercolor="#223045", font_size=14)
            )

            fig_win.update_layout(
                hoverlabel=dict(
                    bgcolor="rgba(11,15,25,.95)",  # dark tooltip bg
                    bordercolor="#223045",
                    font_size=14,  # slightly larger than default
                    font_family="Inter, system-ui, sans-serif",
                    font_color="#dbe4ee",  # base text color (per-line colors come from spans)
                )
            )

            fig_win.update_layout(
                margin=dict(l=8, r=8, t=34, b=4),
                height=136,
                paper_bgcolor=panel_bg,
                plot_bgcolor=panel_bg,
            )

            # center big number
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

            # title inside chart
            _annotate_donut_title(fig_win, "Win Rate", y=1.24)

            st.markdown('<div class="wr-root"></div>', unsafe_allow_html=True)
            st.plotly_chart(fig_win, use_container_width=True)

    with k3:
        with st.container(border=False):
            # ---- Profit Factor donut ----
            gross_profit_v = float(pnl_v[wins_mask_v].sum())
            gross_loss_v = float(pnl_v[losses_mask_v].sum())
            pf_v = (gross_profit_v / abs(gross_loss_v)) if gross_loss_v != 0 else float("inf")
            max_pf = 4.0
            pf_clamped = max(0.0, min(float(pf_v if pf_v != float("inf") else max_pf), max_pf))
            pct = (pf_clamped / max_pf) * 100.0

            panel_bg = CARD_BG
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
                    domain={"x": [0, 1], "y": [0, 0.86]},
                )
            )
            fig_pf.update_layout(
                margin=dict(l=8, r=8, t=34, b=4),
                height=136,
                paper_bgcolor=panel_bg,
                plot_bgcolor=panel_bg,
            )

            # center big PF value
            pf_display = "∞" if pf_v == float("inf") else f"{pf_v:.2f}"
            fig_pf.add_annotation(
                x=0.5,
                y=0.10,
                xref="paper",
                yref="paper",
                text=pf_display,
                showarrow=False,
                font=dict(size=30, color="#e5e7eb", family="Inter, system-ui, sans-serif"),
                align="center",
            )

            # ---- INSIDE-donut title + left/right stacks ----
            p = pd.to_numeric(df_view.get("pnl", np.nan), errors="coerce").dropna()
            # derive gross profit/loss for Profit Factor hover (uses the same df_view used for PF)
            p = pd.to_numeric(df_view.get("pnl", np.nan), errors="coerce").dropna()
            gross_profit = float(p[p > 0].sum())
            gross_loss = float(-p[p < 0].sum())  # positive number

            _annotate_donut_title(fig_pf, "Profit Factor", y=1.24)

            # two-line hover (same colors as elsewhere)
            hover_html_pf = (
                "<span style='font-weight:700; color:#dbe4ee'>Gross Profit </span>"
                f"<span style='font-weight:700; color:{GREEN}'>${gross_profit:,.0f}</span><br>"
                "<span style='font-weight:700; color:#dbe4ee'>Gross Loss </span>"
                f"<span style='font-weight:700; color:{RED}'>${gross_loss:,.0f}</span>"
                "<extra></extra>"
            )

            # overlay an invisible pie on the PF donut so hover shows both lines
            fig_pf.add_trace(
                go.Pie(
                    values=[50, 50],  # any split; trace is only for hover
                    hole=0.76,  # match your indicator ring thickness
                    sort=False,
                    textinfo="none",
                    hovertemplate=hover_html_pf,
                    hoverlabel=dict(
                        bgcolor="rgba(11,15,25,.95)",
                        bordercolor="#223045",
                        font_size=14,
                        font_family="Inter, system-ui, sans-serif",
                        font_color="#dbe4ee",
                    ),
                    marker=dict(colors=["rgba(0,0,0,0)", "rgba(0,0,0,0)"]),  # fully transparent
                    showlegend=False,
                    domain={"x": [0, 1], "y": [0, 0.86]},  # match your indicator’s domain
                )
            )

            st.markdown('<div class="pf-root"></div>', unsafe_allow_html=True)
            st.plotly_chart(fig_pf, use_container_width=True)

    # -- k4: Long vs Short (ratio pill) --
    with k4:
        with st.container(border=False):
            # ---- Long vs Short (title + text + pill move together) ----

            # 3 simple knobs:
            LS_CARD_SHIFT = 32  # moves the entire block down (title + text + pill)
            LS_LEFT_SHIFT = 18  # nudges Longs text right (+) / left (-)
            LS_RIGHT_SHIFT = 18  # nudges Shorts text left (+) / right (-)

            # Count longs/shorts (same logic you already had)
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

                st.markdown(
                    dedent(
                        f"""
                            <div class="ls-card" style="margin-top:{LS_CARD_SHIFT}px">
                            <div class="ls-inner">
                            <div class="ui-title center">Long vs Short</div>

                            <div class="ls-wrap">
                            <div class="ls-row ls-labels">
                                <div class="col left">Longs</div>
                                <div class="col right">Shorts</div>
                            </div>

                            <div class="ls-row ls-values">
                                <div class="col left"><b style="color:{GREEN}">{p_long:.2f}%</b> <span class="muted"><b style="color:{GREEN}">({n_long})</span></div>
                                <div class="col right"><b style="color:{RED}">{p_short:.2f}%</b> <span class="muted"><b style="color:{RED}">({n_short})</span></div>
                            </div>

                            <div class="ls-pill">
                                <div class="ls-long"  style="width:{p_long:.4f}%"></div>
                                <div class="ls-short" style="width:{p_short:.4f}%"></div>
                            </div>
                            </div>
                            </div>  
                            </div>
                            """
                    ),
                    unsafe_allow_html=True,
                )

                st.markdown(
                    dedent(
                        f"""
                        <style>
                        .ls-card {{ width:100%; }}
                        .ls-card .ls-inner {{ transform: translateY(-16px); }}  /* raise/lower content only */
                        .ls-title {{ text-align:center; font-weight:600; font-size:14px; color:#E5E7EB; margin:0 0 8px 0; }}
                        .ls-wrap {{ width:100%; }}
                        .ls-card .ui-title {{
                            font-size: 14px;      /* smaller like other titles */
                            font-weight: 700;     /* heavier */
                            margin: 0 0 16px 0;    /* a bit of space below */
                            text-align: center;
                            color: #E5E7EB;
                        }}
                        /* Center the two text rows; pill remains full width below */
                        .ls-row {{
                        display:grid; grid-template-columns:1fr 1fr; align-items:baseline;
                        max-width:78%; margin:0 auto 6px;
                        }}
                        .ls-row .col.left  {{ text-align:left;  transform:translateX({LS_LEFT_SHIFT}px);  }}
                        .ls-row .col.right {{ text-align:right; transform:translateX(-{LS_RIGHT_SHIFT}px); }}

                        .ls-labels {{ font-size:13px; font-weight:600; color:#E5E7EB; }}
                        .ls-values {{ font-size:13px; }}
                        .ls-values b {{ font-weight:700; color:#D5DEED; }}
                        .ls-values .muted {{ color:#9AA4B2; font-weight:500; }}

                        .ls-pill {{
                        width:95%; height:16px; border-radius:200px; overflow:hidden;
                        display:flex; background:rgba(148,163,184,0.16); margin:0 auto;
                        }}
                        .ls-long  {{ background:{BLUE}; }}
                        .ls-short {{ background:{DARK}; }}
                        </style>
                        
                        """
                    ),
                    unsafe_allow_html=True,
                )

    # -- k5: Winstreak (moved up here) --
    with k5:
        with st.container(border=False):
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
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

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
        with st.container(border=False):
            MTA_TITLE_XSHIFT_PX = 19  # ⬅︎ adjust this to move the title right (+) / left (−)
            st.markdown(
                f"<div class='mta-root' style='font-weight:700; margin:10px 0 4px; margin-left:{MTA_TITLE_XSHIFT_PX}px;'>Most Traded Assets</div>",
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

        # === Equity Curve — title + Streamlit segmented control, height=282 ===
        with st.container(border=False):
            st.markdown('<div class="eq-root"></div>', unsafe_allow_html=True)

            # Header row: title (left) + segmented control (right)
            h1, h2 = st.columns([1, 0.26], vertical_alignment="center")
            with h1:
                # match other chart titles (size 14, weight 700)
                st.markdown('<div class="chart-title">Equity Curve</div>', unsafe_allow_html=True)

            with h2:
                mode = st.segmented_control(
                    label="",
                    options=["PnL", "R:R"],
                    default="PnL",
                    label_visibility="collapsed",
                    key="eq_mode_segmented",
                )

            # -------- data prep (unchanged) --------
            _has_date = date_col is not None and date_col in df_view.columns and len(df_view) > 0
            dfe = df_view.copy()
            pnl_col = "pnl" if "pnl" in dfe.columns else "PnL"
            pnl_num = pd.to_numeric(dfe.get(pnl_col, 0.0), errors="coerce").fillna(0.0)

            if _has_date:
                _dt = pd.to_datetime(dfe[date_col], errors="coerce")
                dfe = dfe.assign(_date=_dt).dropna(subset=["_date"]).sort_values("_date")
            else:
                dfe = dfe.reset_index(drop=True).assign(_date=pd.RangeIndex(start=0, stop=len(dfe)))

            dfe["cum_pnl"] = pnl_num.loc[dfe.index].cumsum()
            dfe["equity"] = float(start_equity) + dfe["cum_pnl"]

            def _find_r(frame):
                for c in ["R Ratio", "R", "r", "rr", "R Multiple", "r_ratio", "R:R"]:
                    if c in frame.columns:
                        return c
                return None

            rc = _find_r(dfe)
            r_vals = (
                pd.to_numeric(dfe[rc], errors="coerce").fillna(0.0)
                if rc
                else np.where(pnl_num.loc[dfe.index] > 0, 1.0, -1.0)
            )
            dfe["cum_r"] = pd.Series(r_vals).cumsum()

            # -------- figure (only height changed previously) --------
            EQ_HEIGHT = 282
            LEFT_M, RIGHT_M, TOP_M, BOT_M = 66, 10, 6, 4  # keep y-title visible & padding tight

            fig = go.Figure()
            if mode == "PnL":
                # baseline for fill (Starting Equity)
                fig.add_trace(
                    go.Scatter(
                        x=dfe["_date"],
                        y=np.full(len(dfe), float(start_equity)),
                        mode="lines",
                        line=dict(width=0),
                        hoverinfo="skip",
                        showlegend=False,
                        name="Baseline",
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=dfe["_date"],
                        y=dfe["equity"],
                        mode="lines",
                        line=dict(width=2, color="#9ec1ff"),
                        fill="tonexty",
                        fillcolor="rgba(158,193,255,0.15)",
                        name="Balance",
                    )
                )
                y_title = "PnL"
            else:
                fig.add_trace(
                    go.Scatter(
                        x=dfe["_date"],
                        y=dfe["cum_r"],
                        mode="lines",
                        line=dict(width=2, color="#64d4c3"),
                        name="Cumulative R",
                    )
                )
                y_title = "R:R"

            fig.update_layout(
                height=EQ_HEIGHT,
                paper_bgcolor=CARD_BG,
                plot_bgcolor=CARD_BG,
                margin=dict(l=LEFT_M, r=RIGHT_M, t=TOP_M, b=BOT_M),
                showlegend=False,
                uirevision="eq_static",  # prevents margin reflow on toggle
            )
            fig.update_xaxes(tickangle=0, tickformat="%b %d")
            fig.update_yaxes(title_text=y_title, title_standoff=24, automargin=False)

            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # === Right column top row (split in 2) ===
    with s_right:
        st.markdown("<div style='margin-bottom:-12px'></div>", unsafe_allow_html=True)
        right_top = st.columns([1.5, 1], gap="small")

        # ----- Left side: Daily PnL(inside bordered card) -----
        with right_top[0]:
            with st.container(border=False):
                st.markdown('<div class="pnl-root"></div>', unsafe_allow_html=True)

                # ---- Chart ----
                PNL_HEIGHT = 310
                PNL_TOP_PAD = 11
                PNL_BOTTOM_PAD = 10
                PNL_VSHIFT = 0
                mode = "Daily"

                # Build the figure as usual
                fig_pnl = plot_pnl(df_view, (date_col or "date"), mode=mode, height=PNL_HEIGHT)

                # Card styling / margins
                fig_pnl.update_layout(
                    paper_bgcolor=CARD_BG,
                    plot_bgcolor=CARD_BG,
                    margin=dict(
                        l=8,
                        r=8,
                        t=26 + PNL_TOP_PAD - PNL_VSHIFT,
                        b=8 + PNL_BOTTOM_PAD + PNL_VSHIFT,
                    ),
                )

                # --- Make x truly datetime & clear categorical ticks ---
                for i, tr in enumerate(fig_pnl.data):
                    if getattr(tr, "type", None) == "bar" and hasattr(tr, "x"):
                        try:
                            x_dt = pd.to_datetime(list(tr.x), errors="coerce")
                            fig_pnl.data[i].x = x_dt
                        except Exception:
                            pass

                # Remove any ticktext/tickvals set by plot_pnl so our formatter applies
                fig_pnl.update_xaxes(ticktext=None, tickvals=None)

            # --- Decide if we actually have bars to size the x-range ---
            _has_bars = any(
                getattr(tr, "type", None) == "bar" and hasattr(tr, "x") and len(tr.x) > 0
                for tr in fig_pnl.data
            )

            if _has_bars:
                xs = pd.to_datetime(fig_pnl.data[0].x, errors="coerce")
                start_range = xs.min() - pd.Timedelta(days=1)
                end_range = xs.max() - pd.Timedelta(days=1)

                fig_pnl.update_xaxes(
                    type="date",
                    tickformat="%b %d",
                    hoverformat="%b %d, %Y",
                    tickangle=0,
                    range=[start_range, end_range],
                )
            else:
                # No data: keep date axis style but don’t set a range
                fig_pnl.update_xaxes(
                    type="date",
                    tickformat="%b %d",
                    hoverformat="%b %d, %Y",
                    tickangle=0,
                )
                # Friendly placeholder
                fig_pnl.add_annotation(
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    text="<b>No PnL data in this range</b>",
                    showarrow=False,
                    font=dict(size=12, color="#9AA4B2"),
                )

            # y-axis label
            fig_pnl.update_yaxes(title_text="PnL")

            # Title inside chart
            fig_pnl.add_annotation(
                x=-0.09,
                y=1.17,
                xref="paper",
                yref="paper",
                text="<b>Daily PnL</b>",
                showarrow=False,
                align="left",
                font=dict(size=14, color="#E5E7EB"),
            )

            st.plotly_chart(fig_pnl, use_container_width=True)

            # === Long vs Short — Cumulative R (matches Equity Curve card layout) ===
            row_cumr = st.container(border=False)
            with row_cumr:
                # same border/rounding hook as Equity (own class)
                st.markdown('<div class="lsr-root"></div>', unsafe_allow_html=True)

                # figure (rendered by the chart helper)
                render_long_short_card(
                    df_view,
                    date_col=(date_col or "date"),
                    height=317,  # same as Equity Curve
                    top_pad=10,  # tight top (title is in header)
                    bottom_pad=28,  # safe bottom so ticks never clip
                    vshift=0,
                    title_text="Long vs Short — Cumulative R",  # title handled by header row
                )

    with right_top[1]:
        with st.container(border=False):
            # top padding
            st.markdown('<div class="last5-root"></div>', unsafe_allow_html=True)

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

            # put this inside the same container as Last 5 Trades
            st.markdown('<div class="last5-title">Last 5 Trades</div>', unsafe_allow_html=True)
            render_last_trades(last5, title="", key_prefix="ov_last5")
            # -------------------------------------------------

    CARD_BG_DARK = "#0f1422"
    # --- Right column bottom: Monthly Stats (replaces Calendar) ---
    render_monthly_stats(
        df_view,
        date_col=date_col,
        years_back=2,
        title="Monthly Stats",
        key="ov_mstats",
        cell_height=95,
        total_col_width_px=120,
        card_bg=CARD_BG,
        card_bg_dark=CARD_BG_DARK,
    )
