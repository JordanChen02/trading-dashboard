from __future__ import annotations

from typing import List

import pandas as pd

from .utils import to_number

# Our normalized, 1-row-per-trade schema
REQUIRED_COLS = [
    "trade_id",
    "symbol",
    "side",
    "entry_time",
    "exit_time",
    "entry_price",
    "exit_price",
    "qty",
    "fees",
    "session",
    "notes",
]


def load_trades(file_or_path) -> pd.DataFrame:
    """
    Load trades from a CSV path or file-like object and normalize into our schema.
    Supports:
      A) native 1-row-per-trade schema (columns in REQUIRED_COLS), or
      B) TradingView strategy tester export (2 rows per trade, with Type = Entry/Exit).
    """
    raw = pd.read_csv(file_or_path)
    raw.columns = [c.strip() for c in raw.columns]  # keep case for detection
    lower_cols = {c.lower(): c for c in raw.columns}

    # Detect TradingView export by presence of common columns
    is_tv = all(k in lower_cols for k in ["type", "date/time", "price"]) and (
        "trade #" in lower_cols or "trade no" in lower_cols or "trade" in lower_cols
    )

    if is_tv:
        df = _from_tradingview(raw)
    else:
        # Assume native schema, just normalize types/casing
        df = raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]
        missing = [c for c in REQUIRED_COLS if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        # parse datetimes
        for c in ["entry_time", "exit_time"]:
            df[c] = pd.to_datetime(df[c], errors="coerce")
        # numerics
        for c in ["entry_price", "exit_price", "qty", "fees"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        # sides
        df["side"] = df["side"].astype(str).str.strip().str.lower()
        return df

    return df


def validate(df: pd.DataFrame) -> List[str]:
    """Return a list of human-readable issues. Empty list means valid."""
    issues: List[str] = []

    # Ensure required columns exist
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        issues.append(f"Missing required columns: {missing}")
        return issues

    # Null checks
    for c in REQUIRED_COLS:
        if df[c].isna().any():
            issues.append(f"Null values in column '{c}'")

    # Side domain
    bad_side = ~df["side"].isin(["long", "short"])
    if bad_side.any():
        issues.append(f"Invalid 'side' values at rows: {list(df.index[bad_side])[:5]}...")

    # Time order
    bad_time = df["exit_time"] < df["entry_time"]
    if bad_time.any():
        issues.append(f"exit_time < entry_time at rows: {list(df.index[bad_time])[:5]}...")

    # Numeric sanity
    if (df["entry_price"] <= 0).any() or (df["exit_price"] <= 0).any():
        issues.append("entry_price/exit_price must be > 0")
    if (df["qty"] <= 0).any():
        issues.append("qty must be > 0")
    if (df["fees"] < 0).any():
        issues.append("fees must be >= 0")

    return issues


def _from_tradingview(tv: pd.DataFrame) -> pd.DataFrame:
    """
    Convert TradingView strategy tester CSV (2 rows per trade: Entry/Exit)
    into our 1-row-per-trade schema.
    Expected columns (names vary by export locale/theme):
      - 'Trade #' or similar
      - 'Type'  (Entry/Exit)
      - 'Date/Time'
      - 'Signal'
      - 'Price'
      - 'Position size'
      - 'Net P&L'
      - 'Run-up'
      - 'Drawdown'
      - 'Cumulative P&L'
    """
    # Build a lowercase->original map and helpers
    orig = {c.lower(): c for c in tv.columns}

    def col(name: str) -> str:
        return orig[name]

    # Normalize essential columns to a canonical set
    # Choose the first matching key present
    trade_key = next(k for k in ["trade #", "trade no", "trade"] if k in orig)
    tv = tv.rename(
        columns={
            col(trade_key): "trade_id",
            col("type"): "type",
            col("date/time"): "datetime",
            col("price"): "price",
        }
    )

    if "signal" in orig:
        tv = tv.rename(columns={col("signal"): "signal"})
    if "position size" in orig:
        tv = tv.rename(columns={col("position size"): "position_size"})
    if "net p&l" in orig:
        tv = tv.rename(columns={col("net p&l"): "net_pnl"})
    if "run-up" in orig:
        tv = tv.rename(columns={col("run-up"): "run_up"})
    if "drawdown" in orig:
        tv = tv.rename(columns={col("drawdown"): "drawdown"})
    if "cumulative p&l" in orig:
        tv = tv.rename(columns={col("cumulative p&l"): "cum_pnl"})
    if "symbol" in orig:
        tv = tv.rename(columns={col("symbol"): "symbol"})

    # Parse types
    tv["type"] = tv["type"].astype(str).str.strip().str.title()  # 'Entry'/'Exit'
    tv["datetime"] = pd.to_datetime(tv["datetime"], format="%b %d, %Y %H:%M", errors="coerce")

    # Try to get side: explicit symbol/side column rarely exists; infer from Signal if needed
    if "side" in tv.columns:
        side_series = tv["side"].astype(str).str.lower()
    else:
        # infer from 'signal' text: contains 'short' or 'long'
        side_series = (
            tv.get("signal", pd.Series(index=tv.index, dtype="object")).astype(str).str.lower()
        )
        side_series = side_series.where(
            side_series.str.contains("short") | side_series.str.contains("long"), other=""
        )
    # fallback: fill later per-trade
    tv["side_inferred"] = side_series

    # Numeric parsing for price/size and optional metrics
    tv["price_num"] = tv["price"].apply(to_number)
    if "position_size" in tv.columns:
        tv["qty_num"] = tv["position_size"].apply(to_number)
    else:
        tv["qty_num"] = None

    # Split entry/exit
    entries = tv[tv["type"] == "Entry"].copy()
    exits = tv[tv["type"] == "Exit"].copy()

    # Use first non-empty value per trade for side (prefer 'side_inferred' from signal)
    entries["side"] = entries["side_inferred"].replace("", pd.NA)
    exits["side"] = exits["side_inferred"].replace("", pd.NA)

    # Build 1-row-per-trade
    left = entries.set_index("trade_id")
    right = exits.set_index("trade_id")

    out = pd.DataFrame(index=sorted(set(left.index) | set(right.index)))
    out.index.name = "trade_id"

    out["symbol"] = left.get("symbol") or right.get("symbol")
    # Fill side preference: entry side, else exit side
    out["side"] = left.get("side")
    out["side"] = out["side"].fillna(right.get("side"))
    out["side"] = out["side"].astype(str).str.strip().str.lower().replace({"": pd.NA})
    # normalize to long/short words if signal only gave that
    out["side"] = out["side"].map(
        lambda s: (
            "short"
            if isinstance(s, str) and "short" in s
            else ("long" if isinstance(s, str) and "long" in s else pd.NA)
        )
    )

    out["entry_time"] = left["datetime"]
    out["exit_time"] = right["datetime"]
    out["entry_price"] = left["price_num"]
    out["exit_price"] = right["price_num"]

    # Quantity: take entry qty if present
    out["qty"] = left.get("qty_num")
    # Fees are not present in TV export; default to 0
    out["fees"] = 0.0

    # Optional fields we’ll keep in notes for now
    # (you can expose these later in charts/KPIs)
    out["session"] = ""  # can derive later

    # Create a basic notes string combining signal/metrics if present
    def _mk_notes(idx):
        s_entry = entries.set_index("trade_id").get("signal")
        s_exit = exits.set_index("trade_id").get("signal")
        parts = []
        if s_entry is not None and idx in s_entry.index and pd.notna(s_entry.loc[idx]):
            parts.append(f"entry:{s_entry.loc[idx]}")
        if s_exit is not None and idx in s_exit.index and pd.notna(s_exit.loc[idx]):
            parts.append(f"exit:{s_exit.loc[idx]}")
        return "; ".join(parts) if parts else ""

    out["notes"] = [_mk_notes(i) for i in out.index]

    # Reset index back to a column and re-order
    out = out.reset_index()

    # Final normalize & type coercions
    out["symbol"] = out["symbol"].astype(str).str.upper()
    out["side"] = out["side"].fillna("long")  # default if inference failed
    out["entry_time"] = pd.to_datetime(out["entry_time"], errors="coerce")
    out["exit_time"] = pd.to_datetime(out["exit_time"], errors="coerce")
    for c in ["entry_price", "exit_price", "qty", "fees"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    # Ensure all required columns exist
    for c in REQUIRED_COLS:
        if c not in out.columns:
            out[c] = "" if c in ("session", "notes", "symbol", "side") else pd.NA

    # order columns
    out = out[REQUIRED_COLS]
    return out
