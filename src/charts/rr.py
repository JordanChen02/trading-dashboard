# src/charts/rr.py
from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# theme colors
from src.theme import AXIS_WEAK, BG, BLUE_LIGHT

# ---------- helpers ----------


def _ensure_rr_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure df has an 'rr' column.
    If missing, create a placeholder from pnl / median(|loss|).
    """
    out = df.copy()
    if "rr" not in out.columns:
        pnl = pd.to_numeric(out.get("pnl", 0.0), errors="coerce").fillna(0.0)
        losses = pnl[pnl < 0].abs()
        risk_proxy = float(losses.median()) if len(losses) else 1.0
        out["rr"] = pnl / (risk_proxy or 1.0)
    return out


def _detect_real_dates(
    df: pd.DataFrame, date_col: Optional[str]
) -> Tuple[bool, Optional[pd.Series]]:
    """
    Return (has_real_dates, datetime_series or None).
    has_real_dates means we truly have a datetime-like column with at least one valid timestamp.
    """
    if date_col and date_col in df.columns:
        dt = pd.to_datetime(df[date_col], errors="coerce")
    elif "_date" in df.columns:
        dt = pd.to_datetime(df["_date"], errors="coerce")
    else:
        return False, None

    ok = dt.notna()
    if not ok.any():
        return False, None
    return True, dt


def _make_datetime_index(df: pd.DataFrame, dt: pd.Series) -> pd.DataFrame:
    """Attach a sorted datetime column '_date' from the given series."""
    out = df.copy()
    out = out.loc[dt.notna()].copy()
    out["_date"] = pd.to_datetime(dt.loc[dt.notna()]).astype("datetime64[ns]")
    out = out.sort_values("_date")
    return out


def _resample_last_14_timebins(
    x: pd.DatetimeIndex, y: pd.Series, rule: str
) -> Tuple[pd.Series, pd.Series]:
    """
    Resample to mean by the given pandas offset rule ('H','D','W','M'), then take the last 14 bins.
    """
    s = pd.Series(y.values, index=x)
    g = s.resample(rule).mean().dropna()
    g = g.tail(14)
    return pd.Series(g.index), pd.Series(g.values, dtype=float)


def _bin_equal_14(
    x: pd.DatetimeIndex, y: pd.Series, start: pd.Timestamp, end: pd.Timestamp
) -> Tuple[pd.Series, pd.Series]:
    """
    Build 14 equal-width bins between [start, end] and average y per bin.
    Always returns 14 values (NaNs filled with 0 so bars still render).
    """
    edges = pd.date_range(start=start, end=end, periods=15)  # 15 edges => 14 bins
    cats = pd.cut(x, bins=edges, include_lowest=True)
    g = pd.DataFrame({"rr": y.values, "bin": cats}).groupby("bin", observed=True)["rr"].mean()
    centers = pd.Series([(iv.left + (iv.right - iv.left) / 2) for iv in g.index])
    vals = g.reset_index(drop=True).fillna(0.0).astype(float)
    # ensure exactly 14
    if len(vals) < 14:
        # pad at the front with zeros/dummy centers
        pad_n = 14 - len(vals)
        if len(centers) > 1:
            span = centers.iloc[1] - centers.iloc[0]
        else:
            span = pd.Timedelta(days=1)
        pads_x = pd.Series([centers.iloc[0] - (pad_n - i) * span for i in range(pad_n)])
        pads_y = pd.Series([0.0] * pad_n, dtype=float)
        centers = pd.concat([pads_x, centers], ignore_index=True)
        vals = pd.concat([pads_y, vals], ignore_index=True)
    elif len(vals) > 14:
        centers = centers.iloc[-14:].reset_index(drop=True)
        vals = vals.iloc[-14:].reset_index(drop=True)
    return centers, vals


# ---------- main API ----------


def plot_rr(
    df_in: pd.DataFrame,  # expects: rr (optional), pnl (optional), date_col or _date (optional)
    has_date: bool,
    date_col: Optional[str] = None,
    mode: str = "D",  # one of: H, D, W, M, 3M, Y, "All" (compat)
    height: Optional[int] = None,
) -> go.Figure:
    """
    Render a 14-bar Reward:Risk chart for a given window mode.
    Bars = average R per bin.

    Y-axis bounds:
      lower = max(-3, floor(min))
      upper = ceil(max) + 2
    """
    df0 = _ensure_rr_column(df_in.copy())

    # Decide whether we truly have datetimes to resample on
    has_real_dates, dt = _detect_real_dates(df0, date_col if has_date else None)

    # If no real dates OR mode == "All": show last 14 rows on a linear x-axis
    if (not has_real_dates) or (str(mode).upper() == "ALL"):
        df0 = df0.reset_index(drop=True)
        tail14 = df0.tail(14).copy()
        x_bins = pd.Series(range(len(tail14)))  # simple linear index
        rr_vals = pd.to_numeric(tail14["rr"], errors="coerce").fillna(0.0).astype(float)
        x_is_date = False
    else:
        # We have real datetimes: build '_date' and choose window logic
        df_dt = _make_datetime_index(df0, dt)
        x = pd.to_datetime(df_dt["_date"]).astype("datetime64[ns]")
        y = pd.to_numeric(df_dt["rr"], errors="coerce").astype(float)
        last = x.max()

        m = str(mode).upper()
        if m == "H":
            xb, yb = _resample_last_14_timebins(x, y, "H")
        elif m == "D":
            xb, yb = _resample_last_14_timebins(x, y, "D")
        elif m == "W":
            xb, yb = _resample_last_14_timebins(x, y, "W")
        elif m == "M":
            xb, yb = _resample_last_14_timebins(x, y, "M")
        elif m == "3M":
            start = (last - pd.DateOffset(months=3)).normalize()
            xb, yb = _bin_equal_14(x, y, start, last)
        elif m == "Y":
            start = (last - pd.DateOffset(months=12)).normalize()
            xb, yb = _bin_equal_14(x, y, start, last)
        else:
            # fallback: last 14 days
            xb, yb = _resample_last_14_timebins(x, y, "D")

        x_bins = xb.reset_index(drop=True)
        rr_vals = yb.reset_index(drop=True)
        x_is_date = True

    # --- normalize & clamp values ---
    rr_vals = pd.to_numeric(rr_vals, errors="coerce").fillna(0.0).astype(float)
    rr_vals = rr_vals.clip(lower=-3.0)  # never below -3R

    # Y range clamp
    if len(rr_vals):
        rr_min = float(np.nanmin(rr_vals))
        rr_max = float(np.nanmax(rr_vals))
    else:
        rr_min = rr_max = 0.0
    y_min = max(-3, int(np.floor(rr_min)))  # never below -3R
    y_top = int(np.ceil(rr_max)) + 2  # headroom like your sample

    # Single theme color for all bars
    colors = [BLUE_LIGHT] * len(rr_vals)

    # --- figure ---
    fig = go.Figure()
    fig.add_bar(
        x=x_bins,
        y=rr_vals,
        marker=dict(color=colors, line=dict(width=0)),
        hovertemplate="%{y:.2f} R<extra></extra>",
    )

    fig.add_hline(y=0, line_color=AXIS_WEAK, line_width=1, opacity=0.5)

    fig.update_layout(
        height=int(height) if height else 150,
        margin=dict(l=8, r=8, t=0, b=0),
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        showlegend=False,
    )

    fig.update_yaxes(
        range=[y_min, y_top],
        gridcolor="rgba(255,255,255,0.10)",
        zeroline=False,
        ticksuffix=" R:R",
        tickformat=".0f",
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        automargin=True,
        tickmode="auto",
        nticks=7,
        type="date" if x_is_date else "linear",
    )

    return fig
