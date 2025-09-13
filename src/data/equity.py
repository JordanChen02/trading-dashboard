# src/data/equity.py
from __future__ import annotations
import numpy as np
import pandas as pd

def build_equity(
    df: pd.DataFrame,
    start_equity: float,
    *,
    pnl_col: str = "pnl",
    date_col: str | None = None,
) -> pd.DataFrame:
    """
    Returns a copy of df with:
      - cum_pnl, equity, peak, dd_abs (≤0), dd_pct (≤0, percent)
      - _date (Timestamp) if date_col is provided
    """
    out = df.copy().reset_index(drop=True)

    pnl = pd.to_numeric(out.get(pnl_col, 0.0), errors="coerce").fillna(0.0)
    out["cum_pnl"] = pnl.cumsum()
    out["equity"]  = float(start_equity) + out["cum_pnl"]
    out["peak"]    = out["equity"].cummax()
    out["dd_abs"]  = out["equity"] - out["peak"]  # ≤ 0

    with np.errstate(invalid="ignore", divide="ignore"):
        out["dd_pct"] = np.where(
            out["peak"] > 0,
            (out["equity"] / out["peak"] - 1.0) * 100.0,  # percent
            0.0,
        )

    if date_col and date_col in out.columns:
        out["_date"] = pd.to_datetime(out[date_col], errors="coerce")

    return out


def resample_equity_daily(
    df: pd.DataFrame,
    start_equity: float,
    *,
    date_col: str,
    pnl_col: str = "pnl",
) -> pd.DataFrame:
    """
    Aggregate PnL to calendar days and build equity on the daily series.
    If date_col is missing/empty, falls back to build_equity on the raw df.
    """
    if date_col not in df.columns or len(df) == 0:
        return build_equity(df, start_equity, pnl_col=pnl_col, date_col=None)

    dt  = pd.to_datetime(df[date_col], errors="coerce")
    pnl = pd.to_numeric(df.get(pnl_col, 0.0), errors="coerce").fillna(0.0)

    tmp = pd.DataFrame({"_date": dt.dt.floor("D"), "pnl": pnl}).dropna(subset=["_date"])
    daily = (
        tmp.groupby("_date", as_index=False)["pnl"]
           .sum()
           .sort_values("_date")
           .reset_index(drop=True)
    )
    return build_equity(daily, start_equity, pnl_col="pnl", date_col="_date")
