from __future__ import annotations
import re
from typing import Any, Optional

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
    # crude check for K suffix as a separate token
    if re.search(r"\b[kK]\b", s):
        mult = 1000.0

    # pull the first numeric chunk
    m = _NUM_RE.search(s.replace(",", ""))
    if not m:
        return None
    try:
        val = float(m.group(0))
    except ValueError:
        return None
    return val * mult
