# src/charts/long_short.py
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.theme import AXIS_WEAK, BLUE, CARD_BG, FG, FG_MUTED, GRID_WEAK, TEAL

# ---------- helpers ------------------------------------------------------------


def _detect_side_col(df: pd.DataFrame) -> str | None:
    for c in ["side", "Side", "position", "Position", "direction", "Direction"]:
        if c in df.columns:
            return c
    return None


def _normalize_side(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip().str.lower()
    mapping = {
        "long": "Long",
        "buy": "Long",
        "1": "Long",
        "true": "Long",
        "short": "Short",
        "sell": "Short",
        "-1": "Short",
        "false": "Short",
    }
    return s.map(mapping).fillna("Long")


def _compute_r(df: pd.DataFrame) -> pd.Series | None:
    # Prefer explicit R column if present
    for rcol in ["R Ratio", "r_ratio", "R", "r"]:
        if rcol in df.columns:
            return pd.to_numeric(df[rcol], errors="coerce")
    # Else compute from PnL / Dollars Risked
    risk_col = next(
        (
            c
            for c in [
                "Dollars Risked",
                "Dollar Risk",
                "Risk $",
                "risk_usd",
                "risk",
                "max_loss",
                "planned_loss",
            ]
            if c in df.columns
        ),
        None,
    )
    if ("pnl" in df.columns) and risk_col:
        risk = pd.to_numeric(df[risk_col], errors="coerce").replace(0, np.nan).abs()
        r = pd.to_numeric(df["pnl"], errors="coerce") / risk
        return r.replace([np.inf, -np.inf], np.nan)
    return None


# ---------- figure builder (Cumulative R only) ---------------------------------


def _fig_long_short_cum_r(
    dates: pd.Series,
    side: pd.Series,
    r_series: pd.Series,
    *,
    height: int = 360,
    top_pad: int = 56,  # top margin (acts like vertical padding)
    bottom_pad: int = 10,  # bottom margin
    title_text: str = "Long vs Short (Cumulative R)",
) -> go.Figure:
    """
    Single figure with Long vs Short **Cumulative R** curves.
    Legend is top-right; no toggle.
    """
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(dates, errors="coerce"),
            "R": pd.to_numeric(r_series, errors="coerce"),
            "side": _normalize_side(side),
        }
    ).dropna(subset=["date", "R"])

    fig = go.Figure()

    # Build cumulative R by normalized day, per side
    for label, color in [("Long", BLUE), ("Short", TEAL)]:
        sub = df[df["side"] == label].copy()
        if sub.empty:
            continue
        sub = sub.sort_values("date")
        day = sub["date"].dt.normalize()
        daily = (
            sub.assign(day=day)
            .groupby("day", as_index=False, sort=True)["R"]
            .sum()
            .rename(columns={"day": "date"})
        )
        daily["date"] = pd.to_datetime(daily["date"])
        cum = daily["R"].cumsum()

        fig.add_trace(
            go.Scatter(
                x=daily["date"],
                y=cum,
                mode="lines",
                line=dict(color=color, width=2),
                name=f"{label} Cumulative R",
                hovertemplate="%{x|%b %d, %Y}<br>" + f"{label} Cum R: " + "%{y:.2f}<extra></extra>",
            )
        )

    # Axes & layout
    # Tighten x-axis spacing but keep the title
    fig.update_xaxes(
        title_standoff=14,  # reduce title height
        tickangle=0,
        automargin=False,  # don't auto-grow bottom margin
        tickfont=dict(size=11),  # (optional) slightly smaller ticks
    )
    fig.update_yaxes(
        title_text="Cumulative R", color=FG_MUTED, gridcolor=GRID_WEAK, zerolinecolor=AXIS_WEAK
    )

    fig.update_layout(
        title=dict(
            text=title_text,
            x=0.04,
            y=1.0,
            xanchor="left",
            font=dict(size=14, color=FG),
        ),
        height=311,
        margin=dict(l=10, r=10, t=top_pad, b=48),
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        legend=dict(
            orientation="h",
            y=1.0,
            yanchor="bottom",
            x=1.0,
            xanchor="right",
            font=dict(size=10, color=FG),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig


# ---------- public render ------------------------------------------------------


def render_long_short_card(
    df: pd.DataFrame,
    date_col: str = "date",
    *,
    height: int = 480,
    top_pad: int = 56,
    bottom_pad: int = 10,
    vshift: int = 2,
    title_text: str = "Long vs Short (Cumulative R)",
) -> None:
    """
    Overview card: overlay of Long vs Short **Cumulative R** curves.
    If R cannot be computed/found, shows a short message instead.
    """
    if date_col not in df.columns:
        st.info("Long vs Short: missing date column.")
        return
    side_col = _detect_side_col(df)
    if not side_col:
        st.info("Long vs Short: no 'side'/'position' column found.")
        return

    r_series = _compute_r(df)
    if r_series is None or pd.to_numeric(r_series, errors="coerce").dropna().empty:
        st.info("Long vs Short: requires 'R' (or 'PnL' + 'Dollars Risked') to show cumulative R.")
        return

    with st.container(border=False):
        st.markdown('<div class="lsr-root"></div>', unsafe_allow_html=True)
        fig = _fig_long_short_cum_r(
            df[date_col],
            df[side_col],
            r_series,
            height=height,
            top_pad=top_pad,
            bottom_pad=bottom_pad,
            title_text=title_text,
        )
        # apply vshift as a CSS transform on the content wrapper (negative = up)
        st.markdown(
            f"<div class='lsr-content-shift' style='transform: translateY({vshift}px)'>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(fig, use_container_width=True, key="ov_ls_cumr")
        st.markdown("</div>", unsafe_allow_html=True)
