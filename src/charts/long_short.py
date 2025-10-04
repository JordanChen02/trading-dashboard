# src/charts/long_short.py
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.theme import AXIS_WEAK, BLUE, FG, FG_MUTED, GRID_WEAK, TEAL

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
    fig.update_xaxes(title_text="Date", color=FG_MUTED, showgrid=False)
    fig.update_yaxes(
        title_text="Cumulative R", color=FG_MUTED, gridcolor=GRID_WEAK, zerolinecolor=AXIS_WEAK
    )

    fig.update_layout(
        title=dict(
            text="Long vs Short (Cumulative R)",
            x=0.04,
            xanchor="left",
            font=dict(size=14, color=FG),
        ),
        height=360,
        margin=dict(l=10, r=10, t=56, b=40),  # room for top-right legend
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            y=1.18,
            yanchor="bottom",
            x=1.0,
            xanchor="right",  # top-right, where the button used to be
            font=dict(size=10, color=FG),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig


# ---------- public render ------------------------------------------------------


def render_long_short_card(df: pd.DataFrame, date_col: str = "date") -> None:
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

    with st.container(border=True):
        fig = _fig_long_short_cum_r(df[date_col], df[side_col], r_series)
        st.plotly_chart(fig, use_container_width=True, key="ov_ls_cumr")
