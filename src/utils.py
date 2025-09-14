from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# ===== Number parsing =====
_NUM_RE = re.compile(r"[-+]?[\d,.]*\.?\d+(?:[eE][-+]?\d+)?")


def to_number(x: Any) -> Optional[float]:
    """
    Convert messy strings like '4.51 K USDT', '100.00 USDT', '24.7%', '$1,234.56'
    into floats. Returns None if it can't parse.
    Rules:
      - removes currency/unit text (USDT, USD, $, %)
      - handles commas
      - handles 'K'/'k' multiplier (x1000) when appears as a separate token
    """
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)

    s = str(x).strip()
    if not s:
        return None

    mult = 1.0
    if re.search(r"\b[kK]\b", s):
        mult = 1000.0

    m = _NUM_RE.search(s.replace(",", ""))
    if not m:
        return None
    try:
        val = float(m.group(0))
    except ValueError:
        return None
    return val * mult


# ===== Journal storage (minimal scaffold only) =====

# Folder: data/journals/
DATA_DIR = Path("data/journals")
# Registry file: data/journals/index.json
INDEX_PATH = DATA_DIR / "index.json"


def ensure_journal_store() -> None:
    """
    Ensure the journals folder and index file exist.
    Creates:
      - data/journals/ (directory)
      - data/journals/index.json with {"journals": []} if missing
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not INDEX_PATH.exists():
        INDEX_PATH.write_text(json.dumps({"journals": []}, indent=2))


def load_journal_index() -> dict:
    """
    Return the current journals registry as a dict.
    Call ensure_journal_store() first so files exist.
    """
    ensure_journal_store()
    return json.loads(INDEX_PATH.read_text())


def save_journal_index(idx: dict) -> None:
    """
    Overwrite the journals registry with the provided dict.
    """
    INDEX_PATH.write_text(json.dumps(idx, indent=2))


def _slugify(name: str) -> str:
    """Turn 'My Journal Name' into 'my-journal-name'."""
    s = re.sub(r"[^A-Za-z0-9_-]+", "-", name.strip()).strip("-").lower()
    return s or f"journal-{int(datetime.now().timestamp())}"


# Minimal native one-row-per-trade schema header
_NATIVE_HEADER = (
    "trade_id,symbol,side,entry_time,exit_time,entry_price,exit_price,qty,fees,session,notes\n"
)


def create_journal(name: str) -> dict:
    """
    Create an empty journal CSV (native schema) and register it in index.json.
    If it already exists in the index, return the existing record.
    """
    ensure_journal_store()
    idx = load_journal_index()

    jid = _slugify(name)
    csv_path = DATA_DIR / f"{jid}.csv"

    if not csv_path.exists():
        csv_path.write_text(_NATIVE_HEADER)

    existing = next((j for j in idx["journals"] if j["id"] == jid), None)
    if existing:
        return existing

    record = {
        "id": jid,
        "name": name,
        "path": str(csv_path),
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    idx["journals"].append(record)
    save_journal_index(idx)
    return record
