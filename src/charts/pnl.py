from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go

BLUE = "#2E86C1"


def plot_pnl(
    df_view: pd.DataFrame, date_col: Optional[str], *, mode: str = "Daily", height: int = 250
) -> go.Figure:
    panel_bg = "#0b0f19"
    pos_color = BLUE
    neg_color = BLUE
    bar_line = "rgba(255,255,255,0.12)"
    dcol = (
        date_col
        if (date_col and date_col in df_view.columns)
        else next(
            (
                c
                for c in [
                    "_date",
                    "date",
                    "datetime",
                    "timestamp",
                    "time",
                    "entry_time",
                    "exit_time",
                ]
                if c in df_view.columns
            ),
            None,
        )
    )
    pnl_col = (
        "pnl" if "pnl" in df_view.columns else ("net_pnl" if "net_pnl" in df_view.columns else None)
    )

    fig = go.Figure()
    fig.update_layout(
        height=height,
        margin=dict(l=16, r=16, t=8, b=10),
        paper_bgcolor=panel_bg,
        plot_bgcolor=panel_bg,
        showlegend=False,
    )
    if not dcol or not pnl_col or df_view.empty:
        return fig

    _dt = pd.to_datetime(df_view[dcol], errors="coerce")
    _pnl = pd.to_numeric(df_view[pnl_col], errors="coerce").fillna(0.0)
    tmp = pd.DataFrame({"_date": _dt, "pnl": _pnl}).dropna(subset=["_date"])
    if tmp.empty:
        return fig

    if mode == "Weekly":
        day = tmp["_date"].dt.floor("D")
        wk = day.to_frame().assign(pnl=tmp["pnl"]).set_index("_date")["pnl"].resample("W-SUN").sum()
        widx = pd.date_range(end=wk.index.max(), periods=8, freq="W-SUN")
        agg = wk.reindex(widx, fill_value=0.0).reset_index()
        agg.columns = ["x", "pnl"]
        tickvals = agg["x"]
        ticktext = [d.strftime("%m/%d/%Y") for d in tickvals]
    else:
        day = tmp["_date"].dt.floor("D")
        daily = day.to_frame().assign(pnl=tmp["pnl"]).groupby("_date", as_index=False)["pnl"].sum()
        last_day = pd.to_datetime(daily["_date"].max())
        idx = pd.date_range(end=last_day, periods=14, freq="D")
        agg = daily.set_index("_date").reindex(idx, fill_value=0.0).rename_axis("x").reset_index()
        tickvals = agg["x"][::2]
        ticktext = [d.strftime("%m/%d/%Y") for d in tickvals]

    x_vals = agg["x"]
    y_vals = agg["pnl"]
    fig.add_bar(
        x=x_vals,
        y=y_vals,
        marker=dict(
            color=[pos_color if v >= 0 else neg_color for v in y_vals],
            line=dict(color=bar_line, width=1),
        ),
        hovertemplate="%{x|%b %d, %Y}<br>PNL: $%{y:,.2f}<extra></extra>",
    )
    fig.add_hline(y=0, line_width=1, line_color="rgba(255,255,255,0.25)")
    fig.update_yaxes(
        zeroline=False,
        showgrid=True,
        gridcolor="rgba(255,255,255,0.06)",
        tickprefix="$",
        separatethousands=True,
    )
    fig.update_xaxes(
        showgrid=False, tickangle=-35, tickmode="array", tickvals=tickvals, ticktext=ticktext
    )
    return fig
