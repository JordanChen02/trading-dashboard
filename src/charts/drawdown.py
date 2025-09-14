# src/charts/drawdown.py
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def plot_underwater(
    df_view: pd.DataFrame,
    start_equity: float,
    date_col: Optional[str] = None,
    *,
    show_vline: bool = True,
    show_label: bool = True,
    height: Optional[int] = None,
) -> Tuple[go.Figure, Dict[str, Any]]:
    """
    Build an 'underwater' drawdown chart from a filtered view (respects current Range/Calendar filters).

    Returns (fig, stats) where stats contains:
      - current_dd_pct (float)
      - current_dd_abs (float, $)
      - max_dd_pct (float)
      - recovered (bool)
      - recover_msg (str)
    """
    h = int(height) if height is not None else 220

    # Guard: empty
    if df_view is None or len(df_view) == 0:
        fig_empty = go.Figure().update_layout(
            height=h,
            paper_bgcolor="#0b0f19",
            plot_bgcolor="#0b0f19",
            margin=dict(l=10, r=10, t=10, b=10),
        )
        return fig_empty, {
            "current_dd_pct": 0.0,
            "current_dd_abs": 0.0,
            "max_dd_pct": 0.0,
            "recovered": True,
            "recover_msg": "No rows available in the current Range to compute drawdown.",
        }

    # ---------- Compute drawdown frame ----------
    _p = pd.to_numeric(df_view["pnl"], errors="coerce").fillna(0.0)
    _dfu = df_view.copy().reset_index(drop=True)
    _dfu["trade_no"] = np.arange(1, len(_dfu) + 1)
    _dfu["cum_pnl"] = _p.cumsum()
    _dfu["equity"] = float(start_equity) + _dfu["cum_pnl"]
    _dfu["peak"] = _dfu["equity"].cummax()
    _dfu["dd_pct"] = (
        np.where(_dfu["peak"] > 0, (_dfu["equity"] / _dfu["peak"]) - 1.0, 0.0) * 100.0
    )  # ≤ 0
    _dfu["dd_abs"] = _dfu["equity"] - _dfu["peak"]  # ≤ 0

    if date_col is not None and date_col in df_view.columns:
        _dfu["_date"] = pd.to_datetime(df_view[date_col], errors="coerce").dt.strftime("%Y-%m-%d")
    else:
        _dfu["_date"] = ""

    # Stats (current & max)
    current_dd_pct = float(_dfu["dd_pct"].iloc[-1])
    current_dd_abs = float(_dfu["dd_abs"].iloc[-1])
    max_dd_pct = float(_dfu["dd_pct"].min())
    _idx_min = int(_dfu["dd_pct"].idxmin())
    _x_trade = int(_dfu.loc[_idx_min, "trade_no"])
    _y_ddpct = float(_dfu.loc[_idx_min, "dd_pct"])
    _dd_abs_v = float(_dfu.loc[_idx_min, "dd_abs"])
    _date_str = str(_dfu.loc[_idx_min, "_date"]) if "_date" in _dfu.columns else ""

    _pre_slice = _dfu.loc[:_idx_min]
    _peak_idx = int(_pre_slice["equity"].idxmax())
    _since_peak_trades = int(_x_trade - int(_dfu.loc[_peak_idx, "trade_no"]))

    _recover_slice = _dfu.loc[_idx_min + 1 :, "dd_pct"]
    _recovered_mask = _recover_slice >= -1e-9
    _recover_idx = (
        _recovered_mask.index[_recovered_mask.argmax()] if _recovered_mask.any() else None
    )
    if _recover_idx is not None:
        _trades_to_recover = int(_dfu.loc[_recover_idx, "trade_no"] - _x_trade)
        recover_msg = f"Recovered from Max DD in **{_trades_to_recover} trades**."
        recovered = True
    else:
        recover_msg = "Not yet recovered from Max DD."
        recovered = False

    # ---------- Figure ----------
    fig_dd = px.area(
        _dfu,
        x="trade_no",
        y="dd_pct",
        title=None,
        labels={"trade_no": "Trade #", "dd_pct": "Drawdown (%)"},
        custom_data=["dd_abs", "equity", "peak", "_date"],
    )
    fig_dd.update_traces(
        hovertemplate=(
            "Trade #%{x}<br>"
            "Date: %{customdata[3]}<br>"
            "Drawdown: %{y:.2f}%<br>"
            "DD ($): $%{customdata[0]:,.0f}<br>"
            "Equity: $%{customdata[1]:,.0f}<br>"
            "Peak: $%{customdata[2]:,.0f}<extra></extra>"
        ),
        showlegend=False,
    )

    min_dd = float(_dfu["dd_pct"].min()) if len(_dfu) else 0.0
    y_floor = min(-1.0, min_dd * 1.10)

    fig_dd.update_yaxes(range=[y_floor, 0], ticksuffix="%", separatethousands=True)
    fig_dd.add_hline(y=0, line_width=1, line_dash="dot", opacity=0.6)
    fig_dd.update_layout(
        height=h,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="#0b0f19",
        plot_bgcolor="#0b0f19",
    )

    # Max DD point marker
    fig_dd.add_scatter(
        x=[_x_trade],
        y=[_y_ddpct],
        mode="markers",
        marker=dict(size=8, color="#ef4444"),
        name="Max DD",
        hovertemplate=(
            "Trade #%{x}<br>"
            "Date: " + (_date_str if _date_str else "%{x}") + "<br>"
            "Drawdown: %{y:.2f}%<br>"
            f"Since peak: {_since_peak_trades} trades"
            "<extra>Max DD point</extra>"
        ),
    )

    if show_label:
        fig_dd.add_annotation(
            x=_x_trade,
            y=_y_ddpct,
            text=f"Max DD { _y_ddpct:.2f}% (${'{:,.0f}'.format(_dd_abs_v)})",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-40,
            bgcolor="rgba(16,22,33,0.7)",
            bordercolor="#2a3444",
            font=dict(size=11, color="#e5e7eb"),
        )
    if show_vline:
        fig_dd.add_vline(
            x=_x_trade, line_width=1, line_dash="dash", line_color="#ef4444", opacity=0.6
        )

    stats = dict(
        current_dd_pct=current_dd_pct,
        current_dd_abs=current_dd_abs,
        max_dd_pct=max_dd_pct,
        recovered=recovered,
        recover_msg=recover_msg,
    )
    return fig_dd, stats
