# src/charts/tier_wr.py
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.theme import AXIS_WEAK, CARD_BG, FG, FG_MUTED, GRID_WEAK

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


def figure_tier_wr(
    df: pd.DataFrame,
    date_col: str | None = "date",
    tier_col: str | None = None,
    *,
    height: int = 300,
) -> go.Figure:
    tier_col = tier_col or _detect_tier_col(df)
    date_col = _detect_date_col(df, date_col)
    if not tier_col:
        # empty figure w/ title so the card renders consistently
        fig = go.Figure()
        fig.update_layout(
            title=dict(
                text="Win Rate by Tier", x=0.04, xanchor="left", font=dict(size=14, color=FG)
            ),
            height=height,
            margin=dict(l=10, r=10, t=28, b=36),
            paper_bgcolor=CARD_BG,
            plot_bgcolor=CARD_BG,
        )
        return fig

    # Prep
    g = _prep(df, date_col, tier_col)

    # Outcome from PnL or R
    pnl_col = _detect_pnl_col(g)
    r_col = _detect_r_col(g)
    if pnl_col:
        g["win"] = pd.to_numeric(g[pnl_col], errors="coerce") > 0
    elif r_col:
        g["win"] = pd.to_numeric(g[r_col], errors="coerce") > 0
    else:
        # Fall back to signless if neither exists (treat missing as loss)
        g["win"] = False

    # Win rate by ordered tier
    wr = (
        g.groupby("tier_norm", dropna=False)["win"]
        .agg(n="count", wr=lambda s: np.round(100.0 * s.mean(), 2))
        .reset_index()
    )
    wr = wr[(wr["tier_norm"] != "nan") & (wr["n"] > 0)]
    wr["tier_norm"] = pd.Categorical(wr["tier_norm"], TIERS_ORDER, ordered=True)
    wr = wr.sort_values("tier_norm").reset_index(drop=True)

    # Colors from Journal (match your table chips)
    tier_colors = {
        "S": "#14b8a6",
        "A+": "#a78bfa",
        "A": "#a78bfa",
        "A-": "#a78bfa",
        "B+": "#1e97e7",
        "B": "#1e97e7",
        "B-": "#1e97e7",
        "C": "#41ce2f",
    }
    bar_colors = [tier_colors.get(t, "#233244") for t in wr["tier_norm"].astype(str)]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=wr["tier_norm"].astype(str),
            y=wr["wr"],
            marker=dict(color=bar_colors, line=dict(width=0)),
            opacity=0.95,
            width=0.58,
            hovertemplate="Tier %{x}<br>WR: %{y:.2f}%<br>n: %{customdata}<extra></extra>",
            customdata=wr["n"],
            name="Win Rate",
        )
    )

    # End-of-bar labels (WR% · n) — safe at 100%
    for _, r in wr.iterrows():
        y_val = float(r["wr"])
        fig.add_annotation(
            x=str(r["tier_norm"]),
            y=y_val,  # anchor at bar top
            yanchor="bottom",  # place text just above the bar
            yshift=2,  # tiny gap
            text=f"{y_val:.0f}% · n={int(r['n'])}",
            showarrow=False,
            font=dict(size=10, color=FG),
            xanchor="center",
            align="center",
        )

    # Axes
    fig.update_xaxes(
        title_text=None,
        tickfont=dict(size=11, color=FG),
        showgrid=False,
        zeroline=False,
    )
    # Y-axis (add headroom)
    y_top = max(100.0, wr["wr"].max() + 4)  # 4% buffer above tallest bar
    fig.update_yaxes(
        title_text="Win Rate (%)",
        range=[0, y_top],
        color=FG_MUTED,
        gridcolor=GRID_WEAK,
        zerolinecolor=AXIS_WEAK,
    )

    # Layout — add more space below title
    fig.update_layout(
        title=dict(text="Win Rate by Tier", x=0.04, xanchor="left", font=dict(size=14, color=FG)),
        height=height,
        margin=dict(l=10, r=10, t=36, b=36),  # t previously 28
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        bargap=0.18,
        showlegend=False,
    )
    return fig
