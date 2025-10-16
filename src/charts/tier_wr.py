# src/charts/tier_wr.py
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.theme import AXIS_WEAK, BLUE, CARD_BG, FG, FG_MUTED, GRID_WEAK

TIERS_ORDER = ["S", "A+", "A", "A-", "B+", "B", "B-", "C"]

# -------- helpers --------


def _detect_tier_col(df: pd.DataFrame) -> str | None:
    for c in [
        "Tier",
        "tier",
        "Setup Tier",
        "setup_tier",
        "Exec Tier",
        "exec_tier",
        "grade",
        "Grade",
    ]:
        if c in df.columns:
            return c
    return None


def _detect_date_col(df: pd.DataFrame, fallback: str | None) -> str | None:
    if fallback and fallback in df.columns:
        return fallback
    for c in ["date", "Date", "timestamp", "Timestamp", "time", "Time", "closed_at", "Closed At"]:
        if c in df.columns:
            return c
    return None


def _detect_pnl_col(df: pd.DataFrame) -> str | None:
    for c in ["PnL", "pnl", "Profit", "profit", "net_pnl", "netPnl"]:
        if c in df.columns:
            return c
    return None


def _detect_r_col(df: pd.DataFrame) -> str | None:
    for c in ["R Ratio", "r_ratio", "R", "r"]:
        if c in df.columns:
            return c
    return None


def _prep(df: pd.DataFrame, date_col: str | None, tier_col: str) -> pd.DataFrame:
    g = df.copy()
    if date_col:
        g[date_col] = pd.to_datetime(g[date_col], errors="coerce")
    g[tier_col] = (
        g[tier_col]
        .astype(str)
        .str.strip()
        .str.upper()
        .str.replace("PLUS", "+")
        .str.replace("MINUS", "-")
    )
    # lock order; anything unknown goes to end as "Other"
    g["tier_norm"] = pd.Categorical(g[tier_col], categories=TIERS_ORDER, ordered=True)
    g["tier_norm"] = g["tier_norm"].astype(str).replace("nan", "Other")
    return g


# -------- figure builder --------


def _figure_wr_with_spark(
    df: pd.DataFrame, date_col: str, tier_col: str, height: int = 300
) -> go.Figure:
    # win/loss
    pnl_col = _detect_pnl_col(df)
    r_col = _detect_r_col(df)
    if pnl_col is None and r_col is None:
        raise ValueError("Need either a PnL column or an R column to compute WR and the sparkline.")

    g = _prep(df, date_col, tier_col)
    # outcome from PnL or R
    if pnl_col:
        g["win"] = pd.to_numeric(g[pnl_col], errors="coerce") > 0
    else:
        g["win"] = pd.to_numeric(g[r_col], errors="coerce") > 0

    # Win Rate by tier
    wr = (
        g.groupby("tier_norm", dropna=False)["win"]
        .agg(n="count", wr=lambda s: np.round(100.0 * s.mean(), 2))
        .reset_index()
    )
    wr = wr[wr["tier_norm"] != "nan"]
    wr = wr[wr["n"] > 0]
    if wr.empty:
        raise ValueError("No graded trades to display.")

    # numeric x positions so we can paint sparklines over each bar
    wr["x"] = range(len(wr))

    # build per-tier cumulative R time series (indexed to 0)
    if r_col is None:
        # derive R from pnl if risk column is not available; fall back to 1R per win/loss = sign
        g["R"] = np.where(g["win"], 1.0, -1.0)
    else:
        g["R"] = pd.to_numeric(g[r_col], errors="coerce")

    # aggregate by day within tier to smooth
    if date_col:
        g["_day"] = pd.to_datetime(g[date_col]).dt.normalize()
    else:
        # if we truly have no date, index by insertion order
        g["_day"] = range(len(g))

    spark = {}
    for t in wr["tier_norm"]:
        sub = g[g["tier_norm"] == t].sort_values("_day")
        if sub.empty:
            continue
        daily = sub.groupby("_day", as_index=False)["R"].sum()
        curve = daily["R"].cumsum().to_numpy(dtype=float)
        if curve.size == 0:
            continue
        # normalize to 0–1 so it sits neatly inside a small band
        if np.ptp(curve) == 0:
            norm = np.zeros_like(curve)
        else:
            norm = (curve - curve.min()) / (curve.max() - curve.min())
        spark[t] = norm

    # ---- figure
    fig = go.Figure()

    # Bars (Win Rate %)
    fig.add_trace(
        go.Bar(
            x=wr["x"],
            y=wr["wr"],
            marker=dict(color="#233244"),
            hovertemplate=(
                "Tier %{customdata[0]}<br>" "WR: %{y:.2f}%<br>" "n: %{customdata[1]}<extra></extra>"
            ),
            customdata=np.stack([wr["tier_norm"], wr["n"]], axis=1),
            name="Win Rate",
            width=0.58,
        )
    )

    # Overlay tiny sparklines centered on each bar
    for _, row in wr.iterrows():
        t = row["tier_norm"]
        if t not in spark or len(spark[t]) == 0:
            continue
        y = np.asarray(spark[t])
        # place each sparkline within a narrow vertical band (72–92% of chart)
        y = 72 + 20 * y  # scaled into [72,92] on WR axis
        # x spans a small window around the bar center
        xs = np.linspace(row["x"] - 0.24, row["x"] + 0.24, num=len(y))
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=y,
                mode="lines",
                line=dict(color=BLUE, width=2),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    # Tier labels on x
    fig.update_xaxes(
        tickmode="array",
        tickvals=wr["x"],
        ticktext=wr["tier_norm"],
        tickfont=dict(size=11, color=FG),
        showgrid=False,
        zeroline=False,
    )

    # Y axis (Win Rate %)
    fig.update_yaxes(
        title_text="Win Rate (%)",
        color=FG_MUTED,
        gridcolor=GRID_WEAK,
        zerolinecolor=AXIS_WEAK,
        range=[0, 100],  # clean scale
    )

    # End-of-bar labels: show WR% · n
    for _, r in wr.iterrows():
        fig.add_annotation(
            x=r["x"],
            y=r["wr"] + 3,
            text=f"{r['wr']:.0f}% · n={int(r['n'])}",
            showarrow=False,
            font=dict(size=10, color=FG),
            xanchor="center",
            align="center",
        )

    fig.update_layout(
        title=dict(
            text="Win Rate by Tier + Cumulative R Sparklines",
            x=0.04,
            y=0.98,
            xanchor="left",
            font=dict(size=14, color=FG),
        ),
        height=300,
        margin=dict(l=10, r=10, t=44, b=40),
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        bargap=0.18,
        showlegend=False,
    )
    return fig


# -------- public render --------


def render_tier_wr_sparkline_card(
    df: pd.DataFrame,
    date_col: str | None = "date",
    tier_col: str | None = None,
    *,
    height: int = 300,
) -> None:
    tier_col = tier_col or _detect_tier_col(df)
    date_col = _detect_date_col(df, date_col)

    if not tier_col:
        st.info("Tier chart: no Tier column found (e.g., 'Tier', 'Setup Tier').")
        return

    try:
        fig = _figure_wr_with_spark(df, date_col, tier_col, height=height)
    except ValueError as e:
        st.info(str(e))
        return

    st.plotly_chart(fig, use_container_width=True)
