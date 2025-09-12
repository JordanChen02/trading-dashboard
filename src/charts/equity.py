# src/charts/equity.py
from typing import Optional
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def plot_equity(
    df_in: pd.DataFrame,
    start_equity: float,
    has_date: bool,
    height: Optional[int] = None,
) -> go.Figure:
    """
    Plots equity with a fixed baseline at start_equity.
    Colors above baseline light; below baseline dark.
    Expects df_in['_date'] and df_in['equity'] columns.
    """
    # X/Y
    x = df_in["_date"]
    y = pd.to_numeric(df_in["equity"], errors="coerce").astype(float)

    fig = go.Figure()

    # 1) Invisible baseline at starting equity
    base = float(start_equity)
    fig.add_scatter(
        x=x,
        y=[base] * len(df_in),
        mode="lines",
        line=dict(width=0),
        hoverinfo="skip",
        showlegend=False,
    )

    # 2) Split series relative to fixed baseline
    y_above = [v if (v is not None and v >= base) else None for v in y]
    y_below = [v if (v is not None and v <  base) else None for v in y]

    # Common hover template
    _ht = (
        "%{x|%b %d, %Y}<br>Equity: $%{y:,.0f}<extra></extra>"
        if has_date else
        "Trade %{x}<br>Equity: $%{y:,.0f}<extra></extra>"
    )

    # 3) ABOVE segment (fills back to baseline trace)
    fig.add_scatter(
        x=x, y=[base] * len(x),
        mode="lines",
        line=dict(width=0),
        hoverinfo="skip",
        showlegend=False,
    )
    fig.add_scatter(
        x=x, y=y_above,
        mode="lines",
        line=dict(width=2, color="#9ecbff"),
        fill="tonexty",
        fillcolor="rgba(53,121,186,0.18)",
        hovertemplate=_ht,
        showlegend=False,
    )

    # 4) BELOW segment (dark line/fill, also fills to baseline)
    fig.add_scatter(
        x=x, y=[base] * len(x),
        mode="lines",
        line=dict(width=0),
        hoverinfo="skip",
        showlegend=False,
    )
    fig.add_scatter(
        x=x, y=y_below,
        mode="lines",
        line=dict(width=2, color="#212C47"),
        fill="tonexty",
        fillcolor="rgba(33,44,71,0.55)",  # #212C47 at ~55% alpha
        hovertemplate=_ht,
        showlegend=False,
    )

    # 5) Layout & axes
    target_h = int(height) if height is not None else int(st.session_state.get("_cal_height", 240))

    ymin = min(base, float(np.nanmin(y)) if len(y) else base)
    ymax = max(base, float(np.nanmax(y)) if len(y) else base)
    pad_low  = max(30, (ymax - ymin) * 0.05)
    pad_high = max(30, (ymax - ymin) * 0.07)

    fig.update_layout(
        height=target_h,
        margin=dict(l=8, r=8, t=0, b=0),
        paper_bgcolor="#0b0f19",
        plot_bgcolor="#0b0f19",
        showlegend=False,
    )

    if has_date:
        # Build ~7 day ticks from the x that you already plotted
        dt_index = pd.to_datetime(x, errors="coerce")
        unique_days = pd.Series(dt_index).dt.floor("D").unique()
        step = max(1, len(unique_days) // 7)  # target ~7 ticks
        tick_vals = unique_days[::step]

        fig.update_xaxes(
            type="date",
            showgrid=False, zeroline=False, showspikes=False, automargin=True,
            tickmode="array",
            tickvals=tick_vals,
            tickformat="%b %d",       # e.g., Sep 11
            ticklabelstandoff=2,      # tighten label spacing
            ticklen=4,                # short tick marks
        )

        # Shift left edge a bit so the first tick sits under the curve
        xmin = dt_index.min()
        xmax = dt_index.max()
        if pd.notna(xmin) and pd.notna(xmax):
            xmin_shifted = xmin - pd.Timedelta(days=5)
            fig.update_xaxes(range=[xmin_shifted, xmax])
    else:
        fig.update_xaxes(
            type="linear",
            showgrid=False, zeroline=False, automargin=True,
            nticks=6,
        )

    fig.update_yaxes(
        showgrid=False, zeroline=False, automargin=True,
        tickprefix="$", separatethousands=True,
        range=[ymin - pad_low, ymax + pad_high],
    )

    return fig
