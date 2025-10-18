# app.py (top of file)
import json  # read/write sidecar metadata for notes/tags
import json as _json
import re
from datetime import date, timedelta

# ---- Load saved settings (if any) and mirror into session ----
from pathlib import Path
from pathlib import Path as _Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 👇 our modules
from src.state import ensure_defaults
from src.styles import (
    inject_filters_css,
    inject_header_layout_css,
    inject_isolated_ui_css,
    inject_topbar_css,
    inject_upload_css,
)
from src.theme import BLUE_FILL
from src.utils import ensure_journal_store, load_journal_index
from src.views.account import render_account
from src.views.calendar import render as render_calendar
from src.views.checklist import render as render_checklist
from src.views.journal import render as render_journal
from src.views.overview import render_overview
from src.views.performance import render as render_performance


def require_password():
    pw = st.secrets.get("auth", {}).get("PASSWORD")
    if not pw:
        return  # no password configured → do nothing
    if not st.session_state.get("_authed"):
        st.title("Edgeboard — Sign in")
        i = st.text_input("Password", type="password")
        if st.button("Enter"):
            st.session_state["_authed"] = i == pw
        if not st.session_state.get("_authed"):
            st.stop()


require_password()


_settings_path = _Path(__file__).with_name("settings.json")
if _settings_path.exists() and "app_settings" not in st.session_state:
    try:
        _settings = _json.loads(_settings_path.read_text(encoding="utf-8"))
        st.session_state["app_settings"] = _settings
        st.session_state.setdefault(
            "starting_equity", _settings.get("starting_equity", {"__default__": 5000.0})
        )
        st.session_state.setdefault("journal_groups", _settings.get("journal_groups", {}))
        _d = _settings.get("defaults", {})
        st.session_state.setdefault("recent_select", _d.get("timeframe", "All Dates"))
        st.session_state.setdefault("global_journal_sel", _d.get("account", "ALL"))
        st.session_state.setdefault("journal_view_mode", _d.get("journal_view", "Styled"))
    except Exception:
        pass

# ------- Session defaults for topbar (set-before-widgets) -------
if "recent_select" not in st.session_state:
    st.session_state["recent_select"] = "All Dates"  # or "Year to Date (YTD)" if you prefer
if "global_journal_sel" not in st.session_state:
    st.session_state["global_journal_sel"] = "ALL"
if "date_from" not in st.session_state:
    st.session_state["date_from"] = None
if "date_to" not in st.session_state:
    st.session_state["date_to"] = None
if "starting_equity" not in st.session_state:
    st.session_state["starting_equity"] = {"__default__": 5000.0}


# ---------------------------------------------------------------
# ---- KPI inputs from df_view: Net Profit & Balance (per-account equity map) ----
def _kpi_net_and_balance(df_view):
    import streamlit as st

    if df_view is None or len(df_view) == 0:
        # No data → net = 0; balance = sum of starting_equity for any selected accounts (or default once)
        eq_map = st.session_state.get("starting_equity", {"__default__": 5000.0})
        # If no Account column, show single default equity
        base_eq = float(eq_map.get("__default__", 5000.0))
        return 0.0, base_eq

    d = df_view.copy()

    # Net Profit
    net = float(d["pnl"].sum()) if "pnl" in d.columns else 0.0

    # Starting equity per account (aggregate for ALL/group selections)
    eq_map = st.session_state.get("starting_equity", {"__default__": 5000.0})
    if "Account" in d.columns:
        present_accounts = d["Account"].astype(str).str.strip().dropna().unique().tolist()
        if not present_accounts:
            base_eq = float(eq_map.get("__default__", 5000.0))
        else:
            base_eq = 0.0
            for acc in present_accounts:
                base_eq += float(eq_map.get(acc, eq_map.get("__default__", 5000.0)))
    else:
        # No Account column → single default
        base_eq = float(eq_map.get("__default__", 5000.0))

    balance = base_eq + net
    return net, balance


# -------------------------------------------------------------------------------

# ---------- FLEXIBLE CSV/Journal normalizer ----------

_ALIAS_MAP = {
    # ids
    "id": "trade_id",
    "tradeID": "trade_id",
    "Trade #": "trade_id",  # <-- Journal
    "Symbol": "symbol",
    "Ticker": "symbol",
    "Asset": "symbol",
    # times
    "time": "entry_time",
    "timestamp": "entry_time",
    "Timestamp": "entry_time",
    "Date": "entry_time",  # <-- Journal (we’ll backfill exit_time from this if missing)
    "Datetime": "entry_time",
    "Entry Time": "entry_time",  # <-- Journal
    "Entry Time (Local)": "entry_time",
    "Exit Time": "exit_time",  # <-- Journal
    "Exit Time (Local)": "exit_time",
    # prices
    "entry": "entry_price",
    "Entry Price": "entry_price",
    "exit": "exit_price",
    "Exit Price": "exit_price",
    # qty / fees
    "quantity": "qty",
    "size": "qty",
    "amount": "qty",
    "fee": "fees",
    # side
    "direction": "side",
    "Direction": "side",  # <-- Journal
    # pnl
    "PnL": "pnl",  # <-- Journal
    "PNL": "pnl",
    "profit": "pnl",
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    # Map aliases if present
    for old, new in _ALIAS_MAP.items():
        if old in out.columns and new not in out.columns:
            out.rename(columns={old: new}, inplace=True)
    return out


def normalize_trades(
    raw: pd.DataFrame, *, account_label: str | None = None
) -> tuple[pd.DataFrame, list[str]]:
    issues: list[str] = []
    if raw is None or raw.empty:
        return pd.DataFrame(), ["Empty file"]

    df = _normalize_columns(raw)

    # Required “identity” fields
    required_base = ["trade_id", "symbol", "side", "entry_time", "exit_time"]
    for c in required_base:
        if c not in df.columns:
            df[c] = np.nan
            issues.append(f"Missing required column '{c}'")

    # Coerce types
    for c in ["entry_time", "exit_time"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    for c in ["entry_price", "exit_price", "qty", "fees", "pnl"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Backfill exit_time from entry_time if missing/empty (Journal often has only a single Date)
    if "exit_time" not in df.columns:
        df["exit_time"] = df.get("entry_time")
    else:
        _et = pd.to_datetime(df["exit_time"], errors="coerce")
        df.loc[_et.isna(), "exit_time"] = df.get("entry_time")

    # If trade_id still missing, use a stable row index as a fallback (prevents drops)
    if "trade_id" not in df.columns:
        df["trade_id"] = np.arange(1, len(df) + 1)

    # Side normalization
    if "side" in df.columns:
        side_map = {
            "buy": "long",
            "long": "long",
            "l": "long",
            "sell": "short",
            "short": "short",
            "s": "short",
        }
        df["side"] = df["side"].astype(str).str.strip().str.lower().map(side_map)
    else:
        df["side"] = np.nan

    # Fees default
    if "fees" not in df.columns:
        df["fees"] = 0.0
    df["fees"] = df["fees"].fillna(0.0)

    # If PNL missing but we have components, compute it
    has_components = all(col in df.columns for col in ["entry_price", "exit_price", "qty"])
    if "pnl" not in df.columns and has_components:
        df["pnl"] = (df["exit_price"] - df["entry_price"]) * df["qty"]
        # sign for short
        df.loc[df["side"] == "short", "pnl"] *= -1
        df["pnl"] = df["pnl"] - df["fees"]
    # If pnl exists, keep it; we do NOT require qty/prices then
    if "pnl" not in df.columns:
        issues.append("No 'pnl' and missing price/qty components → cannot compute PNL")

    # Drop rows that lack the absolute minimum identity fields
    base_ok = (
        df["trade_id"].notna()
        & df["symbol"].notna()
        & df["side"].isin(["long", "short"])
        & df["entry_time"].notna()
        & df["exit_time"].notna()
    )
    # Also require either pnl, or all components (guard when 'pnl' is missing)
    _pnl = pd.to_numeric(df.get("pnl"), errors="coerce")
    pnl_or_components = _pnl.notna() | (
        df.get("entry_price", pd.Series(index=df.index, dtype="float64")).notna()
        & df.get("exit_price", pd.Series(index=df.index, dtype="float64")).notna()
        & df.get("qty", pd.Series(index=df.index, dtype="float64")).notna()
    )

    keep = base_ok & pnl_or_components
    dropped = (~keep).sum()
    if dropped:
        issues.append(f"Dropped {int(dropped)} rows that failed minimal checks")

    df = df.loc[keep].copy()

    # Ensure Account label
    if "Account" not in df.columns:
        df["Account"] = account_label or "Journal"
    else:
        df["Account"] = (
            df["Account"].astype(str).str.strip().replace("", account_label or "Journal")
        )

    # Nice standard helpers for downstream charts
    # Prefer a single working date column _date
    if "entry_time" in df.columns:
        df["_date"] = pd.to_datetime(df["entry_time"], errors="coerce")
    elif "exit_time" in df.columns:
        df["_date"] = pd.to_datetime(df["exit_time"], errors="coerce")

    return df, issues


ensure_defaults()

st.set_page_config(
    page_title="Trading Dashboard — MVP",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_header_layout_css()
inject_filters_css()
inject_isolated_ui_css()
inject_topbar_css()
inject_upload_css()


st.markdown(
    """
<style>
/* Remove Streamlit's top header/toolbar */
[data-testid="stHeader"]  { height: 0; visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

/* Pull main content to the very top (robust selector) */
[data-testid="stAppViewContainer"] .block-container { padding-top: 0 !important; }
/* Hide sidebar collapse "hamburger" button */
[data-testid="stSidebarCollapse"] {
  display: none !important;
}

</style>
""",
    unsafe_allow_html=True,
)


st.markdown(
    """
<style>
  /* Kill the 96px top padding on the main content container */
  [data-testid="stAppViewContainer"] .block-container{
    padding-top: 0 !important;   /* or 8px if you want a tiny buffer */
  }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<style>
  /* Remove top margin that headings (and some components) add at the page start */
  [data-testid="stAppViewContainer"] .block-container > *:first-child {
    margin-top: 0 !important;
    padding-top: 0 !important;
  }
  /* Belt & suspenders: common heading tags + your custom title class */
  [data-testid="stAppViewContainer"] .block-container h1,
  [data-testid="stAppViewContainer"] .block-container h2,
  [data-testid="stAppViewContainer"] .block-container h3,
  .page-title {
    margin-top: 0 !important;
  }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<style>
  /* FINAL OVERRIDES (place at very end of app.py) */

  /* Hide Streamlit chrome */
  [data-testid="stHeader"]  { height: 0 !important; visibility: hidden !important; }
  [data-testid="stToolbar"] { display: none !important; }

  /* Remove all top padding/margins from the main container */
  [data-testid="stAppViewContainer"],
  [data-testid="stAppViewContainer"] .block-container {
    padding-top: 0 !important;
    margin-top: 0 !important;
  }

  /* Kill any top margins headings/components try to add */
  [data-testid="stAppViewContainer"] .block-container > *:first-child {
    margin-top: 0 !important;
    padding-top: 0 !important;
  }
  [data-testid="stAppViewContainer"] .block-container h1,
  [data-testid="stAppViewContainer"] .block-container h2,
  [data-testid="stAppViewContainer"] .block-container h3,
  .page-title {
    margin-top: 0 !important;
  }

  /* Micro-lift just the first row without affecting page height (no bottom clipping) */
  :root { --lift: 8px; }  /* tweak 8–16px to taste */
  [data-testid="stAppViewContainer"] .block-container > *:first-child{
    margin-top: calc(-32 * var(--lift)) !important;  /* ← use negative margin instead of transform */
    transform: none !important;                     /* ← kill the old transform */
    position: relative; 
    z-index: 1;                                     /* keep it clickable above neighbors */
  }
  /* Match the sidebar to that lift so its top aligns */
  [data-testid="stSidebar"] > div:first-child {
    padding-top: var(--lift) !important;
  }


</style>
""",
    unsafe_allow_html=True,
)


st.markdown(
    f"""
<style>
/* Base: make sidebar transitions smooth */
[data-testid="stSidebar"] {{ transition: all .18s ease; }}
    
/* Expanded look (optional explicit sizing) */
{'''
[data-testid="stSidebar"]{
  transform: none !important;
  width: 18rem !important;
  min-width: 18rem !important;
  visibility: visible !important;
}
''' if st.session_state.get('sb_open', True) else '' }
</style>
""",
    unsafe_allow_html=True,
)
st.markdown(
    """
<style>
  /* Sidebar top offset to align with the main topbar.
     Increase/decrease this value to match your current main margin tweak. */
  [data-testid="stSidebar"] > div:first-child {
    padding-top: 10px !important;   /* ← adjust this number */
  }


</style>
""",
    unsafe_allow_html=True,
)


# Make theme color available to CSS as a custom property
st.markdown(f"<style>:root {{ --blue-fill: {BLUE_FILL}; }}</style>", unsafe_allow_html=True)

st.markdown(
    """
<style>
/* Nudge the two selects down so they align with the icon row */
.topbar .tb-select { margin-top: 6px !important; }

/* Compact rounded selects to match your icon height */
.topbar .tb-select [data-baseweb="select"] > div {
  min-height: 36px; height: 36px; border-radius: 10px;
}
.topbar .tb-select [data-baseweb="select"] input { height: 36px; }
.topbar .tb-select .stSelectbox div[data-baseweb="select"] span { line-height: 36px; }
.topbar .tb-select .stSelectbox label { display: none !important; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<style>
:root{
  --tb-accent: var(--blue-fill);
  --tb-range-width: 520px;   /* adjust here; now it will actually apply */
  --tb-range-height: 40px; 
}

/* Range pill sizing & shape */
.topbar [data-testid="stDateInput"]{
  width: var(--tb-range-width) !important;
  display: inline-block !important;
}
.topbar [data-testid="stDateInput"] > div {
  border-radius: 10px !important;     /* match dropdowns */
  overflow: hidden;                   /* keep corners crisp */
}
.topbar [data-testid="stDateInput"] > div > div{
  background: #0f1728;
  border: 1px solid #1f2a3a;
  border-radius: 10px !important;     /* enforce consistent roundness */
  min-height: 60px; height: 60px;
  padding: 0 10px 0 34px;
  display: flex; align-items: center;
}
.topbar [data-testid="stDateInput"] > div > div:hover{ background:#152138; }


</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<style>
:root{ --tb-range-height: 0px; } /* change to 36/40/44/48 to taste */

/* Make the actual BaseWeb input box respect our height */
.topbar [data-testid="stDateInput"] div[data-baseweb="input"],
.topbar [data-testid="stDateInput"] > div > div {
  min-height: var(--tb-range-height) !important;
  height: var(--tb-range-height) !important;
  display: flex !important;
  align-items: center !important;
  box-sizing: border-box !important;

  /* keep your look consistent with dropdowns */
  background: #0f1728 !important;
  border: 1px solid #1f2a3a !important;
  border-radius: 10px !important;
  padding: 0 10px 0 34px !important;
}

/* Round the outer wrapper as well so corners match perfectly */
.topbar [data-testid="stDateInput"] > div {
  border-radius: 10px !important;
  overflow: hidden !important;
}

/* Keep overlay aligned with the same height */
.tb-overlay{
  position:relative; height:0;
  margin-top: calc(-1 * var(--tb-range-height)) !important;
  pointer-events:none;
}

/* (unchanged) icon + label styling */
.tb-ico, .tb-ico svg { color:#3AA4EB !important; fill:#3AA4EB !important; }
.tb-text { color:#e5e7eb; font-weight:400; font-size:16px; letter-spacing:.1px; }
</style>
""",
    unsafe_allow_html=True,
)

# st.markdown(
#     """
# <style>
# /* Hide the native date text completely so it can't ghost-underlap the overlay */
# .topbar [data-testid="stDateInput"]:has(+ .topbar-range .tb-overlay) input{ color:transparent !important; caret-color:transparent !important; text-shadow:none !important; font-size:0 !important; }
# .topbar .topbar-range [data-testid="stDateInput"] svg{ display:none !important; }
# </style>

# """,
#     unsafe_allow_html=True,
# )

st.markdown(
    """
<style>
:root{ --tb-range-height: 40px; }  /* keep this global var if you like */

.topbar .topbar-range [data-testid="stDateInput"] div[data-baseweb="input"]{
  min-height: var(--tb-range-height) !important;
  height:      var(--tb-range-height) !important;
  display:flex !important; align-items:center !important; box-sizing:border-box !important;
  background:#0f1728 !important; border:1px solid #1f2a3a !important; border-radius:10px !important;
  padding:0 10px 0 34px !important;
}
.topbar .topbar-range [data-testid="stDateInput"] > div{ border-radius:10px !important; overflow:hidden !important; }

.topbar .topbar-range .tb-overlay{
  position:relative; height:0; margin-top: calc(-1 * var(--tb-range-height)) !important; pointer-events:none;
}
.topbar .topbar-range .tb-ico, 
.topbar .topbar-range .tb-ico svg{ color:#3AA4EB !important; fill:#3AA4EB !important; }
.topbar .topbar-range .tb-text{ color:#e5e7eb; font-weight:500; font-size:16px; letter-spacing:.1px; }
</style>

""",
    unsafe_allow_html=True,
)


# ------ Ensure Journal session is initialized (provides journal_df & accounts_options) ------
try:
    from src.views.journal import _init_session_state as _journal_bootstrap

    _journal_bootstrap()  # populates st.session_state.journal_df and st.session_state.accounts_options
except Exception as _e:
    # Safe fallback: if Journal module changes, just continue
    pass

# ---- Global timeframe state (defaults to YTD) + handlers used by topbar ----

_today = date.today()
st.session_state.setdefault("date_from", date(_today.year, 1, 1))  # YTD start
st.session_state.setdefault("date_to", _today)


RECENT_OPTIONS = [
    "Year to Date (YTD)",
    "All Dates",
    "Recent 7 Days",
    "Recent 30 Days",
    "Recent 60 Days",
    "Recent 90 Days",
]


def _apply_range(label: str):
    """Update date_from/date_to in session based on a label."""
    today = date.today()

    if label == "Year to Date (YTD)":
        st.session_state["date_from"] = date(today.year, 1, 1)
        st.session_state["date_to"] = today
        return

    if label == "All Dates":
        # Turn OFF date filtering entirely
        st.session_state["date_from"] = None
        st.session_state["date_to"] = None
        return

    if label.startswith("Recent "):
        n = int(label.split()[1])  # "Recent 60 Days" -> 60
        st.session_state["date_from"] = today - timedelta(days=n - 1)
        st.session_state["date_to"] = today
        return


def _on_recent_change():
    label = st.session_state.get("recent_select", "All Dates")
    _apply_range(label)  # this just sets date_from/date_to


def _default_range_from_preset():
    """Return (from, to) based on session preset, or saved custom range."""
    d_from = st.session_state.get("date_from")
    d_to = st.session_state.get("date_to")
    if d_from and d_to:
        return d_from, d_to

    preset = st.session_state.get("recent_select", "All Dates")
    today = date.today()
    if "Year to Date" in preset:
        return date(today.year, 1, 1), today
    if "Recent 7" in preset:
        return today - timedelta(days=6), today
    if "Recent 30" in preset:
        return today - timedelta(days=29), today

    # All Dates → fall back to bounds if you track them
    _min_bound = st.session_state.get("_data_min", today)
    _max_bound = st.session_state.get("_data_max", today)
    return _min_bound, _max_bound


# Journal page can overwrite these; we keep safe defaults here.
st.session_state.setdefault("accounts_options", ["NQ", "Crypto (Live)", "Crypto (Prop)"])
st.session_state.setdefault(
    "journal_groups",
    {
        "NQ": ["NQ"],
        "Crypto (Live)": ["Crypto (Live)"],
        "Crypto (Prop)": ["Crypto (Prop)"],
    },
)

# default month in session (first of current month)
if "_cal_month_start" not in st.session_state:
    st.session_state["_cal_month_start"] = pd.Timestamp.today().normalize().replace(day=1)

# ---- journal account/groups defaults (so topbar never crashes) ----
# Pull the account list from Journal if present; otherwise use sane defaults.
st.session_state.setdefault("accounts_options", ["NQ", "Crypto (Live)", "Crypto (Prop)"])

# Minimal groups (can be expanded later). This prevents KeyError.
st.session_state.setdefault(
    "journal_groups",
    {
        "NQ": ["NQ"],
        "Crypto (Live)": ["Crypto (Live)"],
        "Crypto (Prop)": ["Crypto (Prop)"],
    },
)


# ===================== SIDEBAR: Journals (UI only) =====================
ensure_journal_store()
with st.sidebar:
    st.image("assets/edgeboard_blue.png", use_container_width=True)

    st.markdown(
        """
    <style>
    /* Logo container: edge-to-edge (matches your nav row bleed) */
    [data-testid="stSidebar"] .stImage {
    margin: 6px -12px 12px;            /* bleed left/right to align with nav pills */
    width: calc(100%);
    padding: -10px 12px -14px;
    margin: -92px -12px -36px;
    border-bottom: 1px solid #202b3b;
    }

    /* Image tweaks */
    [data-testid="stSidebar"] .stImage img {
    display: block;
    margin: 0 auto;
    max-width: 100px;                  /* adjust to taste */
    width: 100%;
    height: auto;
    filter: drop-shadow(0 2px 6px rgba(0,0,0,.25));  /* optional */
    border-radius: 8px;                                   /* optional */
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # ===================== SIDEBAR: Navigation =====================
    _options = ["Dashboard", "Performance", "Calendar", "Journal", "Account", "Checklist"]

    # Ensure a default exactly once
    if "nav" not in st.session_state:
        st.session_state["nav"] = "Dashboard"

    # Radio is the single source of truth for nav
    nav = st.radio(
        "Go to:",
        _options,
        key="nav",  # <-- binds to st.session_state["nav"]
        label_visibility="collapsed",
    )
    # DO NOT set st.session_state["nav"] = nav anywhere else

    # --- TradingView-like styling for the radio group + line icons ---
    st.markdown(
        """
    <style>
    :root { --brand:#3579ba; }   /* theme blue you chose */

    /* Let rows go edge-to-edge (reduce padding) */
    [data-testid="stSidebar"] > div:first-child {
    padding-left: 8px !important;
    padding-right: 8px !important;
    }

    /* Make each radio label a full-bleed row (NO circles, flat list) */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
    display: flex;
    align-items: center;
    height: 60px;
    padding: 0 12px 0 20px;   /* top right bottom left */
    margin: 0;                           /* no gaps between rows */
    border-radius: 10px;
    background: transparent;
    position: relative;
    left: 0px;                          /* bleed to left edge */
    width: calc(100% + 62px);            /* bleed to both edges */
    border-bottom: 1px solid #202b3b;    /* thin separator */
    }

    /* Remove the circular radio indicator */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:first-child {
    display: none !important;
    }

    /* Hover: subtle lighten */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {
    background: var(--blue-fill);
    }


    /* Active row: filled bg */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[aria-checked="true"],
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[data-checked="true"] {
    background: #0e1a33 !important;
    }

    /* Remove the separator on the last item */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:last-of-type {
    border-bottom: none;
    }

    /* Text polish */
    [data-testid="stSidebar"] .stRadio label p {
    color: #d5deed !important;
    font-weight: 600 !important;
    font-size: 1.1rem !important; 
    letter-spacing: 1px;
    }

    /* === ICONS (inline SVG, colored by --brand via CSS mask) === */

    /* Create an icon box before the label text */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label::before{
    content: "";
    width: 26px; height: 26px;
    margin-right: 10px;
    display:inline-block;
    background-color: var(--brand);      /* icon color */
    -webkit-mask-repeat: no-repeat; -webkit-mask-position: center; -webkit-mask-size: contain;
    mask-repeat: no-repeat; mask-position: center; mask-size: contain;
    opacity:.95;
    }

    /* Row order mapping: 1=Dashboard, 2=Performance, 3=Calendar, 4=Journal, 5=Account, 6=Checklist */

    /* DASHBOARD icon: grid */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:nth-of-type(1)::before {
    -webkit-mask-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect x='3' y='3' width='8' height='8' rx='2' ry='2' fill='black'/><rect x='13' y='3' width='8' height='5' rx='2' ry='2' fill='black'/><rect x='13' y='10' width='8' height='11' rx='2' ry='2' fill='black'/><rect x='3' y='13' width='8' height='8' rx='2' ry='2' fill='black'/></svg>");
            mask-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect x='3' y='3' width='8' height='8' rx='2' ry='2' fill='black'/><rect x='13' y='3' width='8' height='5' rx='2' ry='2' fill='black'/><rect x='13' y='10' width='8' height='11' rx='2' ry='2' fill='black'/><rect x='3' y='13' width='8' height='8' rx='2' ry='2' fill='black'/></svg>");
    }

    /* PERFORMANCE icon: bar chart */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:nth-of-type(2)::before {
    -webkit-mask-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M3 3h2v18H3V3zm7 6h2v12h-2V9zm7-4h2v16h-2V5z' fill='black'/></svg>");
            mask-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M3 3h2v18H3V3zm7 6h2v12h-2V9zm7-4h2v16h-2V5z' fill='black'/></svg>");
    }

    /* CALENDAR icon */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:nth-of-type(3)::before {
    -webkit-mask-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M19 4h-1V2h-2v2H8V2H6v2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V9h14v11z' fill='black'/></svg>");
            mask-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M19 4h-1V2h-2v2H8V2H6v2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V9h14v11z' fill='black'/></svg>");
    }

    /* JOURNAL icon: pencil */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:nth-of-type(4)::before {
    -webkit-mask-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z' fill='black'/><path d='M20.71 7.04a1 1 0 0 0 0-1.42L18.37 3.3a1 1 0 0 0-1.42 0l-1.34 1.34 3.75 3.75 1.34-1.35z' fill='black'/></svg>");
            mask-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z' fill='black'/><path d='M20.71 7.04a1 1 0 0 0 0-1.42L18.37 3.3a1 1 0 0 0-1.42 0l-1.34 1.34 3.75 3.75 1.34-1.35z' fill='black'/></svg>");
    }

    /* ACCOUNT icon: user */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:nth-of-type(5)::before {
    -webkit-mask-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8V22h19.2v-2.8c0-3.2-6.4-4.8-9.6-4.8z' fill='black'/></svg>");
            mask-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8V22h19.2v-2.8c0-3.2-6.4-4.8-9.6-4.8z' fill='black'/></svg>");
    }

    /* CHECKLIST icon: simple checkmark */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:nth-of-type(6)::before {
    -webkit-mask-image: url("data:image/svg+xml;utf8,\
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'>\
    <path d='M5 13l4 4L19 7'/>\
    </svg>");
            mask-image: url("data:image/svg+xml;utf8,\
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'>\
    <path d='M5 13l4 4L19 7'/>\
    </svg>");
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
    <style>
    :root{ --tb-accent: var(--blue-fill); }

    /* Style the actual Streamlit date input like a pill */
    :root{
    --tb-range-height: 44px;    /* ← set the height you want here (36px, 40px, 44px, etc.) */
    }

    .topbar [data-testid="stDateInput"] > div > div{
    background:#0f1728; border:1px solid #1f2a3a; border-radius:10px;
    min-height: var(--tb-range-height) !important;
    height:      var(--tb-range-height) !important;
    padding: 0 10px 0 34px; display:flex; align-items:center;
    }
    .topbar [data-testid="stDateInput"] > div > div:hover{ background:#152138; }


    /* Pull the overlay up by exactly the same height */
    .tb-overlay{
    position:relative; height:0;
    margin-top: calc(-1 * var(--tb-range-height));  /* keep overlay perfectly aligned */
    pointer-events:none;
    }
    .tb-overlay .inner{
    position:absolute; inset:0; display:flex; align-items:center; gap:10px; padding:0 12px;
    }

    /* Icon + text */
    .tb-ico{ width:18px; height:18px; min-width:16px; margin-left:7px; color:#3AA4EB; fill:#3AA4EB; }
    .tb-text{ color:#e5e7eb; font-weight:600; font-size:13px; letter-spacing:.1px; }
    .tb-text { word-spacing: 6px !important; }

    /* Text size / weight */
    .tb-text{
    font-size: 16px !important;   /* ← change size here */
    font-weight: 500 !important;  /* 400–700 */
    position: relative;
    top: 4px;                      /* ← nudge text up/down (+/- px) */
    }
    /* Round the BaseWeb datepicker popup to match */
    [data-baseweb="datepicker"]{ border-radius:12px; border:1px solid #223045; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.divider()


# ===================== MAIN: Journal Session Only =====================

# Pull from in-memory Journal only (no CSV)
df = st.session_state.get("journal_df", pd.DataFrame()).copy()

# Normalize just like before (maps Journal column names)
df, _j_issues = normalize_trades(df, account_label="Journal")

# Ensure pnl column exists (prevents KeyError when journal is empty)
if "pnl" not in df.columns:
    df["pnl"] = 0.0

# Safety: ensure Account column
if "Account" not in df.columns:
    df["Account"] = "Journal"


# --- Detect a usable date column ONCE and compute bounds for "All Dates" ---
_possible_date_cols = [
    "date",
    "Date",
    "entry_time",
    "Entry Time",
    "Entry Time (Local)",
    "exit_time",
    "Exit Time",
    "timestamp",
    "Timestamp",
    "datetime",
    "Datetime",
]
_date_col_for_bounds = next((c for c in _possible_date_cols if c in df.columns), None)

st.session_state["_date_col"] = _date_col_for_bounds

if _date_col_for_bounds is not None and len(df):
    _dt_full_bounds = pd.to_datetime(df[_date_col_for_bounds], errors="coerce")
    if not _dt_full_bounds.empty:
        st.session_state["_data_min"] = _dt_full_bounds.min().date()
        st.session_state["_data_max"] = _dt_full_bounds.max().date()
        # If "All Dates" was selected before we knew bounds, apply now
        if st.session_state.get("recent_select") == "All Dates":
            _apply_range("All Dates")

# --- Build Account options for the topbar (Journal + CSV + Groups) ---
_prev_opts = tuple(st.session_state.get("journal_options", []))

# 1) Accounts defined by journal.py (preferred source of truth)
journal_accounts = list(
    dict.fromkeys(
        [str(x).strip() for x in st.session_state.get("accounts_options", []) if str(x).strip()]
    )
)

# 2) Accounts present in the current Journal dataframe (ensures we capture real data labels)
present_journal_accounts = []
_jdf = st.session_state.get("journal_df", pd.DataFrame())
if "Account" in _jdf.columns and len(_jdf):
    present_journal_accounts = sorted(
        _jdf["Account"].astype(str).str.strip().dropna().unique().tolist()
    )

# 3) Accounts present in the combined df (journal + uploads)
present_all_accounts = []
if "Account" in df.columns and len(df):
    present_all_accounts = sorted(df["Account"].astype(str).str.strip().dropna().unique().tolist())

# 4) Named groups
group_names = list(st.session_state.get("journal_groups", {}).keys())

# Merge and de-dup: ALL + groups + journal.py list + journal_df present + combined present
combo = ["ALL"] + group_names + journal_accounts + present_journal_accounts + present_all_accounts
new_opts = list(dict.fromkeys(combo))

st.session_state["journal_options"] = new_opts

# If options changed since first render, re-run once so the topbar shows them
if tuple(new_opts) != _prev_opts:
    st.rerun()

# ========== TOP TOOLBAR (title spacer | timeframe | account | icons) ==========
st.markdown('<div class="topbar">', unsafe_allow_html=True)

t_spacer, t_tf, t_range, t_acct, t_globe, t_bell, t_full, t_theme, t_profile = st.columns(
    [50, 10, 15, 14, 5, 5, 5, 5, 5], gap="small"
)

with t_spacer:
    st.empty()

# -- Timeframe (compact select) --
with t_tf:
    # ⬇️ vertical nudge (px) for the Timeframe select
    TOPBAR_TIMEFRAME_SHIFT = 10  # adjust to taste
    st.markdown(f"<div style='height:{TOPBAR_TIMEFRAME_SHIFT}px'></div>", unsafe_allow_html=True)

    st.markdown("<div class='tb tb-select'>", unsafe_allow_html=True)

    # ---- Timeframe select (single source of truth + UI mirror) ----
    if "recent_select" not in st.session_state:
        st.session_state["recent_select"] = "All Dates"

    RECENT_OPTIONS = [
        "Year to Date (YTD)",
        "All Dates",
        "Recent 7 Days",
        "Recent 30 Days",
        "Recent 60 Days",
        "Recent 90 Days",
    ]

    def _on_recent_change():
        # Normal path: widget key is 'recent_select'
        label = st.session_state.get("recent_select", "All Dates")
        _apply_range(label)

    def _on_recent_ui_change():
        # Mirror path (when current state is 'Custom Range')
        st.session_state["recent_select"] = st.session_state["recent_select_ui"]
        _apply_range(st.session_state["recent_select"])

    current = st.session_state.get("recent_select", "All Dates")

    if current in RECENT_OPTIONS:
        # Render the real widget bound to the real key (NO value/index passed)
        st.selectbox(
            "Timeframe",
            RECENT_OPTIONS,
            key="recent_select",
            on_change=_on_recent_change,
            label_visibility="collapsed",
        )
    else:
        # State is something like 'Custom Range' (not in options).
        # Render a *separate* UI widget to avoid the warning, then sync to state.
        if "recent_select_ui" not in st.session_state:
            st.session_state["recent_select_ui"] = "All Dates"

        st.selectbox(
            "Timeframe",
            RECENT_OPTIONS,
            key="recent_select_ui",  # different key → no conflict
            on_change=_on_recent_ui_change,
            label_visibility="collapsed",
        )

    st.markdown("</div>", unsafe_allow_html=True)

# --- TOPBAR: Custom Date Range ---------------------------------------------
with t_range:
    # vertical alignment with other dropdowns
    TOPBAR_RANGE_SHIFT = 0
    st.markdown(f"<div style='height:{TOPBAR_RANGE_SHIFT}px'></div>", unsafe_allow_html=True)

    # === NEW: define all variables the widget needs ===
    from datetime import date as _date

    _RANGE_KEY = "topbar_range"

    # Bounds for the picker; fall back safely if dataset bounds aren’t set yet
    _min_bound = st.session_state.get("_data_min", _date(_date.today().year, 1, 1))
    _max_bound = st.session_state.get("_data_max", _date.today())

    # What should show today in the picker (uses your helper)
    cur_from, cur_to = _default_range_from_preset()

    # stage machine: 0 = idle, 1 = user has clicked the "from" date (one pick)
    st.session_state.setdefault("_range_stage", 0)
    st.session_state.setdefault("_last_range_value", None)

    def _on_range_change():
        v = st.session_state.get(_RANGE_KEY)

        # First selection (FROM) → just arm; no apply yet, no rerun needed.
        if st.session_state.get("_range_stage", 0) == 0:
            st.session_state["_range_stage"] = 1
            return

        # Second selection (TO) → apply and reset stage (Streamlit will rerun automatically).
        st.session_state["_range_stage"] = 0
        if isinstance(v, tuple) and len(v) == 2:
            st.session_state["date_from"], st.session_state["date_to"] = v
            st.session_state["recent_select"] = "Custom Range"
            # no st.rerun() here — Streamlit reruns once automatically after the callback

    # pill width
    RANGE_WIDTH_PX = 800
    st.markdown(
        f"<style>:root{{ --tb-range-width:{RANGE_WIDTH_PX}px }}</style>",
        unsafe_allow_html=True,
    )

    # Clamp the default shown in the picker to its allowed bounds
    cf, ct = cur_from, cur_to
    if cf < _min_bound:
        cf = _min_bound
    if ct > _max_bound:
        ct = _max_bound
    # If the clamped range inverted (e.g., YTD starts before min), show full bounds
    if cf > ct:
        cf, ct = _min_bound, _max_bound

    # The actual date widget (unchanged behavior)
    st.date_input(
        label="Date range",
        value=(cf, ct),
        min_value=_min_bound,
        max_value=_max_bound,
        format="YYYY-MM-DD",
        label_visibility="collapsed",
        key=_RANGE_KEY,
        on_change=_on_range_change,
    )

    # # === Overlay label that visually replaces the input text (keeps clicks working) ===
    # d1 = st.session_state.get("date_from") or cur_from
    # d2 = st.session_state.get("date_to") or cur_to
    # label_txt = f"{d1:%Y-%m-%d}  \u2192  {d2:%Y-%m-%d}"  # note the spaces around the arrow

    # st.markdown(
    #     f"""
    #     <div class="tb-overlay" style="width:{RANGE_WIDTH_PX}px">
    #       <div class="inner">
    #         <span class="tb-ico">
    #           <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
    #             <path d="M7 2a1 1 0 0 1 1 1v1h8V3a1 1 0 1 1 2 0v1h1.5A2.5 2.5 0 0 1 22 6.5v13A2.5 2.5 0 0 1 19.5 22h-15A2.5 2.5 0 0 1 2 19.5v-13A2.5 2.5 0 0 1 4.5 4H6V3a1 1 0 1 1 2 0v1Zm12.5 6H4.5a.5.5 0 0 0-.5.5v10a.5.5 0 0 0 .5.5h15a.5.5 0 0 0 .5-.5v-10a.5.5 0 0 0-.5-.5ZM8 7H6v1a1 1 0 0 0 2 0V7Zm10 0h-2v1a1 1 0 1 0 2 0V7Z"/>
    #           </svg>
    #         </span>
    #         <span class="tb-text">{label_txt}</span>
    #       </div>
    #     </div>
    #     """,
    #     unsafe_allow_html=True,
    # )
    # st.markdown("</div>", unsafe_allow_html=True)  # ← add (closes .topbar-range)
# --- END TOPBAR: Custom Date Range -----------------------------------------


# -- Account (NOW after options were built) --
with t_acct:
    # ⬇️ vertical nudge (px) for the Account select
    TOPBAR_ACCOUNT_SHIFT = 10  # adjust to taste
    st.markdown(f"<div style='height:{TOPBAR_ACCOUNT_SHIFT}px'></div>", unsafe_allow_html=True)

    st.markdown("<div class='tb tb-select'>", unsafe_allow_html=True)
    _acct_options = st.session_state.get("journal_options", ["ALL"])
    _current = st.session_state.get("global_journal_sel", None)
    _acct_idx = _acct_options.index(_current) if (_current in _acct_options) else 0
    st.selectbox(
        "Account",
        _acct_options,
        index=_acct_idx,
        key="global_journal_sel",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)


# -- Icons (unchanged) --
with t_globe:
    st.markdown('<span class="tb"></span>', unsafe_allow_html=True)
    try:
        st.button("", key="btn_globe", icon=":material/language:")
    except TypeError:
        st.button("🌐", key="btn_globe")

with t_bell:
    st.markdown('<span class="tb"></span>', unsafe_allow_html=True)
    try:
        st.button("", key="btn_bell", icon=":material/notifications:")
    except TypeError:
        st.button("🔔", key="btn_bell")

with t_full:
    st.markdown('<span class="tb"></span>', unsafe_allow_html=True)
    try:
        st.button("", key="btn_full", icon=":material/fullscreen:")
    except TypeError:
        st.button("⛶", key="btn_full")

with t_theme:
    st.markdown('<span class="tb"></span>', unsafe_allow_html=True)
    try:
        st.button("", key="btn_theme", icon=":material/light_mode:")
    except TypeError:
        st.button("☼", key="btn_theme")

with t_profile:
    st.markdown('<span class="tb"></span>', unsafe_allow_html=True)
    try:
        pp = st.popover("", icon=":material/account_circle:")
    except TypeError:
        pp = st.popover("🙂")
    with pp:
        st.markdown('<div class="profile-pop">', unsafe_allow_html=True)

        st.subheader("Account")
        col_p1, col_p2 = st.columns([1, 3])
        with col_p1:
            st.image(
                "https://upload.wikimedia.org/wikipedia/commons/7/7c/Profile_avatar_placeholder_large.png?20150327203541",
                width=180,
            )
        with col_p2:
            st.caption("Signed in as")
            st.write("**squintz**")
            if st.button("Settings ⚙️", use_container_width=True):
                st.toast("Settings (placeholder)")

        st.divider()
        st.subheader("Data")
        inject_upload_css()
        st.markdown('<div class="upload-pop">', unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)  # close .upload-pop
        st.markdown("</div>", unsafe_allow_html=True)  # close .profile-pop
# ====================================================================

# --- Ensure both 'symbol' and 'Symbol' exist before any page uses df ---
if "symbol" in df.columns and "Symbol" not in df.columns:
    df["Symbol"] = df["symbol"]
elif "Symbol" in df.columns and "symbol" not in df.columns:
    df["symbol"] = df["Symbol"]

# ---- Router: open Journal page if selected ----
if st.session_state.get("nav", "Dashboard") == "Journal":
    render_journal(df)  # df is already loaded/validated above
    st.stop()  # prevent Dashboard tabs from rendering
elif st.session_state["nav"] == "Checklist":
    render_checklist(df)
    st.stop()

# In-session notes store: maps original df index -> note text
if "_trade_notes" not in st.session_state:  # if key not present in the dict
    st.session_state["_trade_notes"] = {}  # {} creates an empty dictionary
# In-session tags store: maps original df index -> tag (e.g., "A+", "A", "B", "C")
if "_trade_tags" not in st.session_state:
    st.session_state["_trade_tags"] = {}

# Determine journal meta sidecar path (if current source is a journal) and load it once
source_label = "journal: session"  # added placeholder since we removed CSV logic

_journal_meta_path = None
sel_id = st.session_state.get("selected_journal")
if isinstance(source_label, str) and source_label.startswith("journal:") and sel_id:
    idx = load_journal_index()
    _rec = next((j for j in idx.get("journals", []) if j["id"] == sel_id), None)
    if _rec:
        _journal_meta_path = Path(_rec["path"]).with_suffix(
            ".meta.json"
        )  # e.g., trades.csv -> trades.meta.json
        st.session_state["_journal_meta_path"] = str(_journal_meta_path)

        # Load once per run if present; guard with a flag
        if _journal_meta_path.exists() and not st.session_state.get("_meta_loaded"):
            try:
                with open(_journal_meta_path, "r", encoding="utf-8") as f:
                    _meta = json.load(f)  # { "notes": {idx: "..."}, "tags": {idx: "A"} }
                # merge into session stores; keys may come back as strings → cast to int
                st.session_state["_trade_notes"].update(
                    {int(k): v for k, v in _meta.get("notes", {}).items()}
                )
                st.session_state["_trade_tags"].update(
                    {int(k): v for k, v in _meta.get("tags", {}).items()}
                )
                st.session_state["_meta_loaded"] = True
                st.toast("Loaded journal notes/tags from disk")
            except Exception as e:
                st.warning(f"Couldn't read journal metadata: {e}")


def _persist_journal_meta():
    """Write session notes/tags to sidecar JSON if a journal is selected."""
    _mp = st.session_state.get("_journal_meta_path")
    if not _mp:
        return  # uploads (non-journal) won't persist
    try:
        payload = {
            "notes": st.session_state.get("_trade_notes", {}),
            "tags": st.session_state.get("_trade_tags", {}),
        }
        with open(_mp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        st.toast("Journal notes/tags saved")
    except Exception as e:
        st.warning(f"Couldn't save journal metadata: {e}")


def _norm_ac(s: str) -> str:
    # lowercase + strip all non [a-z0-9] to make 'NQ (Live)' match 'nq live'
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())


sel = st.session_state.get("global_journal_sel", "ALL")
if sel != "ALL":
    if sel in st.session_state.get("journal_groups", {}):
        targets = st.session_state["journal_groups"][sel]
        mask = df["Account"].astype(str).isin(targets)
        df = df.loc[mask].copy()
    else:
        target_norm = _norm_ac(sel)
        acc_norm = df["Account"].astype(str).map(_norm_ac)
        df = df.loc[acc_norm == target_norm].copy()
# else: ALL → no filter

# Date filter (re-use the same detected column we used for bounds)
date_col = st.session_state.get("_date_col")
dfrom = st.session_state.get("date_from", None)
dto = st.session_state.get("date_to", None)

# Keep a copy of the full merged frame for “equity at window start” math
df_all = df.copy()

# If All Dates is selected → both are None → skip filtering entirely
if date_col is not None and date_col in df.columns and not (dfrom is None and dto is None):
    dtser = pd.to_datetime(df[date_col], errors="coerce")
    mask = pd.Series(True, index=df.index)
    if dfrom is not None:
        mask &= dtser >= pd.to_datetime(dfrom)
    if dto is not None:
        mask &= dtser <= pd.to_datetime(dto)
    df = df.loc[mask].copy()


# ===================== RUNTIME SETTINGS (no UI) =====================
# Defaults for now; we'll move breakeven policy into Filters later
be_policy = st.session_state.get("be_policy", "be excluded from win-rate")

# --- Compute equity AT the start of the selected window, per Account settings ---
acct_eq_map = st.session_state.get("acct_equity", {})  # set on Account page
default_base = float(st.session_state.get("default_equity_base", 5000.0))

# Use the pre-slice frame for account selection (df_all was created just before the date filter)
if "Account" in df_all.columns and len(df_all):
    sel_accounts = df_all["Account"].astype(str).str.strip().dropna().unique().tolist()
else:
    sel_accounts = []

# Sum starting equity for the selected accounts (fallback to default if none)
base_eq = (
    sum(float(acct_eq_map.get(acc, default_base)) for acc in sel_accounts)
    if sel_accounts
    else float(default_base)
)

# Add PnL accrued BEFORE the current window start (anchor equity at window start)
pnl_col = "pnl" if "pnl" in df_all.columns else ("PnL" if "PnL" in df_all.columns else None)
prior_sum = 0.0
if (
    (pnl_col is not None)
    and (dfrom is not None)
    and (date_col is not None)
    and (date_col in df_all.columns)
):
    dt_all = pd.to_datetime(df_all[date_col], errors="coerce")
    mask_prior = dt_all < pd.to_datetime(dfrom)
    if sel_accounts and "Account" in df_all.columns:
        mask_prior &= df_all["Account"].astype(str).isin(sel_accounts)
    prior_sum = pd.to_numeric(df_all.loc[mask_prior, pnl_col], errors="coerce").fillna(0.0).sum()

# Final: equity at the beginning of the window
start_equity = float(base_eq + prior_sum)


# --- Win-rate components depending on breakeven policy ---
is_win = df["pnl"] > 0
is_loss = df["pnl"] < 0
is_be = df["pnl"] == 0

total_trades = len(df)

if be_policy == "be excluded from win-rate":
    denom = (is_win | is_loss).sum()  # exclude 0 PnL
    wins = is_win.sum()
    win_rate = (wins / denom * 100.0) if denom > 0 else 0.0
elif be_policy == "count as losses":
    wins = is_win.sum()
    win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
else:  # "count as wins"
    wins = (is_win | is_be).sum()
    win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0

# --- Basic KPIs ---
profits = df.loc[df["pnl"] > 0, "pnl"]
losses = df.loc[df["pnl"] < 0, "pnl"]

profit_sum = float(profits.sum())  # ≥ 0
loss_sum = float(losses.sum())  # ≤ 0 or 0

profit_factor = (profit_sum / abs(loss_sum)) if loss_sum != 0 else float("inf")
avg_win = float(profits.mean()) if len(profits) else 0.0
avg_loss = float(losses.mean()) if len(losses) else 0.0  # negative if any losses

# Expectancy per trade (uses avg_loss as negative)
win_rate_frac = win_rate / 100.0
loss_rate_frac = 1.0 - win_rate_frac
expectancy = win_rate_frac * avg_win + loss_rate_frac * avg_loss

# --- Equity curve + Drawdown from starting equity ---
df_ec = df.copy().reset_index(drop=True)
# use df_ec to compute trade_no, equity, peaks, etc.
df["trade_no"] = np.arange(1, len(df) + 1)
df["cum_pnl"] = df["pnl"].cumsum()
df["equity"] = start_equity + df["cum_pnl"]
df["equity_peak"] = df["equity"].cummax()
df["dd_abs"] = df["equity"] - df["equity_peak"]  # ≤ 0
df["dd_pct"] = np.where(df["equity_peak"] > 0, (df["equity"] / df["equity_peak"]) - 1.0, 0.0)

max_dd_abs = float(df["dd_abs"].min())  # most negative dollar drawdown
max_dd_pct = float(df["dd_pct"].min()) * 100.0  # most negative percent drawdown

# --- Current balance & Net PnL ---
current_balance = float(df["equity"].iloc[-1]) if len(df) else start_equity
net_pnl = float(df["cum_pnl"].iloc[-1]) if len(df) else 0.0


def winrate_half_donut(wr: float, height: int = 110, hole: float = 0.72, half: str = "bottom"):
    """
    Horizontal half-donut (blue = wins, red = losses).
    `half`: "bottom" (default) or "top"
    """

    wr = max(0.0, min(1.0, float(wr)))

    # wins + losses fill one half; ghost hides the other half
    wins, losses, ghost = wr, 1.0 - wr, 1.0
    start = 270 if half.lower() == "bottom" else 90  # 180 = bottom half, 0 = top half

    fig = go.Figure(
        go.Pie(
            values=[wins, losses, ghost],  # keep this order
            hole=hole,
            rotation=start,  # <- horizontal half control
            direction="clockwise",
            sort=False,  # <- IMPORTANT so order doesn’t shuffle
            textinfo="none",
            hoverinfo="skip",
            marker=dict(
                colors=["#2E86C1", "#E57373", "rgba(0,0,0,0)"],
                line=dict(width=0),
            ),
            showlegend=False,
        )
    )
    fig.update_traces(domain=dict(x=[0, 1], y=[0, 1]))
    fig.update_layout(
        height=height,  # lower height => looks wider
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


# ===================== OVERVIEW KPI CARDS (Timeframe-aware) =====================
# Try to detect a date column once so we can filter by timeframe
_possible_date_cols = [
    "date",
    "Date",
    "timestamp",
    "Timestamp",
    "time",
    "Time",
    "datetime",
    "Datetime",
    "entry_time",
    "exit_time",
]
_date_col = next((c for c in _possible_date_cols if c in df.columns), None)
_dt_full = pd.to_datetime(df[_date_col], errors="coerce") if _date_col is not None else None

# Use the already-filtered df (journal + date_from/to) as the view
df_view = df.copy()

# --- Apply TOPBAR date_from/date_to (if set) to df_view ---
_raw_from = st.session_state.get("date_from", None)
_raw_to = st.session_state.get("date_to", None)

if _date_col is not None and _date_col in df_view.columns and len(df_view) > 0:
    _dates_series = pd.to_datetime(df_view[_date_col], errors="coerce").dt.date
    if _raw_from is not None:
        df_view = df_view[_dates_series >= _raw_from]
    if _raw_to is not None:
        df_view = df_view[_dates_series <= _raw_to]
# --- end apply date range ---

# Nice label for the current range (from the date inputs)
_raw_from = st.session_state.get("date_from", None)
_raw_to = st.session_state.get("date_to", None)

if _raw_from is None and _raw_to is None:
    tf_display = "All Dates"
elif _raw_from is None:
    tf_display = f"… → {pd.to_datetime(_raw_to):%b %d, %Y}"
elif _raw_to is None:
    tf_display = f"{pd.to_datetime(_raw_from):%b %d, %Y} → …"
else:
    tf_display = f"{pd.to_datetime(_raw_from):%b %d, %Y} → {pd.to_datetime(_raw_to):%b %d, %Y}"


# -------- Apply Calendar selection (optional) to df_view --------
# We’ll store the calendar selection in st.session_state._cal_filter
#   - ("day", date)
#   - ("week", (start_date, end_date))
cal_sel = st.session_state.get("_cal_filter")
if cal_sel is not None and _date_col is not None and _date_col in df.columns and len(df_view) > 0:
    _dates_series = pd.to_datetime(df_view[_date_col], errors="coerce").dt.date
    mode, payload = cal_sel
    if mode == "day":
        _day = payload  # datetime.date
        df_view = df_view[_dates_series == _day]
    elif mode == "week":
        _ws, _we = payload  # (datetime.date, datetime.date)
        df_view = df_view[(_dates_series >= _ws) & (_dates_series <= _we)]

# --- Recompute KPI ingredients for the view ---
pnl_v = pd.to_numeric(df_view["pnl"], errors="coerce").fillna(0.0)
wins_mask_v = pnl_v > 0
losses_mask_v = pnl_v < 0
bes_mask_v = pnl_v == 0

wins_v = int(wins_mask_v.sum())
losses_v = int(losses_mask_v.sum())
total_v = int(len(df_view))

# Win-rate depends on your breakeven policy
if be_policy == "be excluded from win-rate":
    denom = wins_v + losses_v
    win_rate_v = wins_v / denom if denom > 0 else 0.0
elif be_policy == "count as losses":
    win_rate_v = wins_v / total_v if total_v > 0 else 0.0
else:  # "count as wins"
    win_rate_v = (wins_v + int(bes_mask_v.sum())) / total_v if total_v > 0 else 0.0

avg_win_v = pnl_v[wins_mask_v].mean() if wins_v > 0 else 0.0
avg_loss_v = pnl_v[losses_mask_v].mean() if losses_v > 0 else 0.0  # negative if any losses
avg_win_loss_ratio_v = abs(avg_win_v / avg_loss_v) if avg_loss_v != 0 else float("inf")

# Daily Win Rate inside the selected timeframe (if a date column exists)
_daily_wr_display = "—%"
if _date_col is not None and total_v > 0:
    _d_view = pd.to_datetime(df_view[_date_col], errors="coerce")
    _tmpv = pd.DataFrame({"pnl": pnl_v, "_day": _d_view.dt.date})
    _daily_pnl_v = _tmpv.groupby("_day")["pnl"].sum()
    if len(_daily_pnl_v) > 0:
        _daily_wr_v = float((_daily_pnl_v > 0).mean() * 100.0)
        _daily_wr_display = f"{_daily_wr_v:.1f}%"

# --- Symbol compatibility (some charts expect 'Symbol', some use 'symbol') ---
if "symbol" in df.columns and "Symbol" not in df.columns:
    df["Symbol"] = df["symbol"]
elif "Symbol" in df.columns and "symbol" not in df.columns:
    df["symbol"] = df["Symbol"]

# Clean empty strings → NaN so groupbys don’t show 'nan' label
if "symbol" in df.columns:
    df["symbol"] = df["symbol"].astype(str).str.strip().replace({"": np.nan})
if "Symbol" in df.columns:
    df["Symbol"] = df["Symbol"].astype(str).str.strip().replace({"": np.nan})

# ===================== ROUTER: MAIN VIEWS =====================
if st.session_state["nav"] == "Dashboard":
    render_overview(
        df_view,
        start_equity,
        _date_col,
        st.session_state["_cal_month_start"],
        win_rate_v,
        avg_win_loss_ratio_v,
        avg_win_v,
        avg_loss_v,
        pnl_v,
        wins_mask_v,
        losses_mask_v,
    )

elif st.session_state["nav"] == "Performance":
    render_performance(
        df_view,
        start_equity,
        _date_col,
        tf_display,
        win_rate_v,
        avg_win_v,
        avg_loss_v,
    )


elif st.session_state["nav"] == "Calendar":
    render_calendar(
        df_view=df_view,
        _date_col=_date_col,
        month_start=st.session_state["_cal_month_start"],
        key="cal",
    )

elif st.session_state["nav"] == "Journal":
    render_journal(df)

elif st.session_state["nav"] == "Account":
    render_account()

elif st.session_state["nav"] == "Checklist":
    render_checklist(df)


# --- Helper: render active filters banner ---
def render_active_filters(key_suffix: str = ""):
    cal_sel = st.session_state.get("_cal_filter")
    left, mid, right = st.columns([3, 5, 2])

    # Range chip (always present)
    with left:
        st.caption(f"Range: **{tf_display}**")

    # Calendar filter status (optional)
    with mid:
        if cal_sel:
            mode, payload = cal_sel
            if mode == "day":
                st.caption(f"Calendar filter: **{payload}**")  # YYYY-MM-DD
            else:
                ws, we = payload
                st.caption(f"Calendar filter: **{ws} → {we}**")
        else:
            st.caption("Calendar filter: **none**")


# Apply in-session notes to df/df_view so the 'note' column reflects saved edits
_notes_map = st.session_state.get("_trade_notes", {})  # .get returns {} if missing
if len(_notes_map) > 0:
    # Make sure a 'note' column exists
    if "note" not in df.columns:
        df["note"] = ""
    # Update by original index keys
    for _idx, _txt in _notes_map.items():  # .items() iterates (key, value)
        if _idx in df.index:  # guard against stale indices
            df.at[_idx, "note"] = _txt  # .at is fast scalar setter
    # Recompute df_view from df with the same mask (cheap & safe)
    df_view = df.loc[df_view.index]

# Apply in-session tags to df/df_view so the 'tag' column reflects saved edits
_tags_map = st.session_state.get("_trade_tags", {})
if len(_tags_map) > 0:
    if "tag" not in df.columns:
        df["tag"] = ""
    for _idx, _tg in _tags_map.items():
        if _idx in df.index:
            df.at[_idx, "tag"] = _tg
    df_view = df.loc[df_view.index]
