from __future__ import annotations
import pandas as pd

def add_pnl(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-trade PnL and return a new DataFrame (non-mutating)."""
    out = df.copy()
    sign = out["side"].map({"long": 1, "short": -1})
    out["pnl"] = (out["exit_price"] - out["entry_price"]) * out["qty"] * sign - out["fees"]
    return out
