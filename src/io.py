from __future__ import annotations
import pandas as pd

REQUIRED_COLS = [
    "trade_id", "symbol", "side",
    "entry_time", "exit_time",
    "entry_price", "exit_price",
    "qty", "fees", "session", "notes"
]

def load_trades(file_or_path) -> pd.DataFrame:
    """
    Load trades from a CSV path or file-like object.
    - Parses datetimes
    - Normalizes column names
    - Normalizes 'side' to {'long','short'}
    """
    df = pd.read_csv(file_or_path)

    # normalize column names
    df.columns = [c.strip().lower() for c in df.columns]

    # ensure required columns exist (we'll do full validate() separately)
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # parse datetimes
    for c in ["entry_time", "exit_time"]:
        df[c] = pd.to_datetime(df[c], errors="coerce")

    # numeric coercions (safe)
    num_cols = ["entry_price", "exit_price", "qty", "fees"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # normalize 'side'
    df["side"] = df["side"].astype(str).str.strip().str.lower()
    df["side"] = df["side"].map({"long": "long", "short": "short"})

    return df


def validate(df: pd.DataFrame) -> list[str]:
    """
    Return a list of human-readable issues. Empty list means 'valid'.
    """
    issues: list[str] = []

    # 1) required columns present
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        issues.append(f"Missing required columns: {missing}")
        return issues  # can't continue deeper checks

    # 2) null checks
    for c in REQUIRED_COLS:
        if df[c].isna().any():
            issues.append(f"Null values in column '{c}'")

    # 3) side values
    bad_side = ~df["side"].isin(["long", "short"])
    if bad_side.any():
        issues.append(f"Invalid 'side' values at rows: {list(df.index[bad_side])[:5]}...")

    # 4) time order
    bad_time = df["exit_time"] < df["entry_time"]
    if bad_time.any():
        issues.append(f"exit_time < entry_time at rows: {list(df.index[bad_time])[:5]}...")

    # 5) numeric sanity
    if (df["entry_price"] <= 0).any() or (df["exit_price"] <= 0).any():
        issues.append("entry_price/exit_price must be > 0")
    if (df["qty"] <= 0).any():
        issues.append("qty must be > 0")
    if (df["fees"] < 0).any():
        issues.append("fees must be >= 0")

    return issues
