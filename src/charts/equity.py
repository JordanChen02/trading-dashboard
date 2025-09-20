# src/charts/equity.py
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.theme import AXIS_WEAK, BG, BLUE_LIGHT  # <- theme tokens


def plot_equity(
    df_in: pd.DataFrame,
    start_equity: float,
    has_date: bool,
    height: Optional[int] = None,
) -> go.Figure:
    """
    Simple equity curve:
      • single line (no area fills)
      • dashed reference line at start_equity
      • y-axis auto-ranges to true min/max (with small padding)
      • date ticks ~7 labels when dates are present
    Expects df_in['_date'] and df_in['equity'].
    """
    # X/Y
    x = df_in["_date"]
    y_raw = pd.to_numeric(df_in["equity"], errors="coerce").astype(float)
    # gentle smoothing; bump window to 5 or 7 if you want more
    SMOOTH_WIN = 6
    y = pd.Series(y_raw).rolling(window=SMOOTH_WIN, min_periods=1, center=True).mean().to_numpy()

    # Hover
    _ht = (
        "%{x|%b %d, %Y}<br>Equity: $%{y:,.0f}<extra></extra>"
        if has_date
        else "Trade %{x}<br>Equity: $%{y:,.0f}<extra></extra>"
    )

    fig = go.Figure()

    # Reference baseline at starting equity
    fig.add_hline(
        y=float(start_equity),
        line_width=1,
        line_dash="dot",
        line_color=AXIS_WEAK,
        opacity=0.5,
    )

    # Invisible baseline at the data floor (so fill goes only down to min equity)
    y_floor = float(np.nanmin(y)) if len(y) else float(start_equity)
    fig.add_scatter(
        x=x,
        y=[y_floor] * len(x),
        mode="lines",
        line=dict(width=0),
        hoverinfo="skip",
        showlegend=False,
    )

    # Filled equity curve (fill between this and the baseline added just above)
    fig.add_scatter(
        x=x,
        y=y,
        mode="lines",
        line=dict(width=2, color=BLUE_LIGHT),
        line_shape="linear",  # smooth look comes from rolling mean, not spline
        fill="tonexty",
        fillcolor="rgba(46,134,193,0.18)",
        hovertemplate=_ht,
        showlegend=False,
        connectgaps=False,
    )

    # Y range from data (pad a touch)
    if len(y):
        ymin = float(np.nanmin(y))
        ymax = float(np.nanmax(y))
    else:
        ymin = ymax = float(start_equity)
    span = max(1.0, ymax - ymin)
    pad_low = max(20.0, span * 0.05)
    pad_high = max(20.0, span * 0.07)
    fig.update_yaxes(range=[ymin - pad_low, ymax + pad_high])

    # Layout
    target_h = int(height) if height is not None else int(st.session_state.get("_cal_height", 240))
    fig.update_layout(
        height=target_h,
        margin=dict(l=8, r=8, t=0, b=0),
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        showlegend=False,
    )
    fig.update_yaxes(tickformat="$,.0f")

    # X axis (date vs linear)
    if has_date:
        dt = pd.to_datetime(x, errors="coerce").dropna()
        if len(dt) == 0:
            fig.update_xaxes(type="date", showgrid=False, zeroline=False, automargin=True)
        else:
            min_dt = pd.to_datetime(dt.min())
            max_dt = pd.to_datetime(dt.max())

            # --- knobs ---
            SHIFT_DAYS = 8  # ← move labels this many days to the right
            N_LABELS = 7  # ← how many date labels to show

            # Keep the chart range EXACTLY on your data (curve doesn't move)
            fig.update_xaxes(type="date", range=[min_dt, max_dt])

            # Build tick positions starting a bit later, ending at the last data day
            start_for_ticks = (min_dt + pd.Timedelta(days=SHIFT_DAYS)).floor("D")
            tick_vals = pd.date_range(start=start_for_ticks, end=max_dt, periods=N_LABELS)

            fig.update_xaxes(
                showgrid=False,
                zeroline=False,
                showspikes=False,
                automargin=True,
                tickmode="array",
                tickvals=tick_vals,
                tickformat="%b %d",
                ticklabelstandoff=-25,  # ↓ smaller gap under axis
                ticklen=2,  # shorter tick marks
            )
    else:
        fig.update_xaxes(type="linear", showgrid=False, zeroline=False, automargin=True, nticks=6)

    return fig
