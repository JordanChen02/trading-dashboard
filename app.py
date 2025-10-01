# app.py (top of file)
import json  # read/write sidecar metadata for notes/tags
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 👇 our modules
from src.io import load_trades, validate
from src.metrics import add_pnl
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
from src.views.calendar import render as render_calendar
from src.views.checklist import render as render_checklist
from src.views.journal import render as render_journal
from src.views.overview import render_overview
from src.views.performance import render as render_performance

# (other imports are fine above or below — imports don’t matter)


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
  :root { --lift: 200px; }  /* tweak 8–16px to taste */
  [data-testid="stAppViewContainer"] .block-container > *:first-child {
    transform: translateY(calc(-1 * var(--lift)));
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
    """
<style>
  /* Add extra scroll space so bottom isn’t clipped */
  [data-testid="stAppViewContainer"] .block-container {
    padding-bottom: 200px !important;   /* adjust this value */
  }

  /* Sidebar needs matching bottom room so it doesn’t crop */
  [data-testid="stSidebar"] > div:first-child {
    padding-bottom: 200px !important;   /* same value as above */
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

# ---- Global timeframe state (defaults to YTD) + handlers used by topbar ----

_today = date.today()
st.session_state.setdefault("date_from", date(_today.year, 1, 1))  # YTD start
st.session_state.setdefault("date_to", _today)
st.session_state.setdefault("recent_select", "Year to Date (YTD)")

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
    lo = st.session_state.get("_data_min", today)
    hi = st.session_state.get("_data_max", today)

    if label == "Year to Date (YTD)":
        st.session_state["date_from"] = date(today.year, 1, 1)
        st.session_state["date_to"] = today
        return

    if label == "All Dates":
        st.session_state["date_from"] = lo
        st.session_state["date_to"] = hi
        return

    if label.startswith("Recent "):
        n = int(label.split()[1])  # "Recent 60 Days" -> 60
        st.session_state["date_from"] = today - timedelta(days=n - 1)
        st.session_state["date_to"] = today
        return


def _on_recent_change():
    _apply_range(st.session_state.get("recent_select") or "Year to Date (YTD)")


# Seed account options so the topbar has something useful on first render
st.session_state.setdefault("journal_options", ["ALL", "NQ", "Crypto (Live)"])
st.session_state.setdefault("global_journal_sel", "ALL")

# default month in session (first of current month)
if "_cal_month_start" not in st.session_state:
    st.session_state["_cal_month_start"] = pd.Timestamp.today().normalize().replace(day=1)


# ========== TOP TOOLBAR (title spacer | timeframe | account | icons) ==========
st.markdown('<div class="topbar">', unsafe_allow_html=True)

t_spacer, t_tf, t_acct, t_globe, t_bell, t_full, t_theme, t_profile = st.columns(
    [70, 12, 16, 5, 5, 5, 5, 5], gap="small"
)

with t_spacer:
    st.empty()


# -- Timeframe (compact select) --
with t_tf:
    st.markdown("<div class='tb tb-select'>", unsafe_allow_html=True)
    # show current selection; if missing, default to YTD
    _idx = (
        RECENT_OPTIONS.index(st.session_state["recent_select"])
        if st.session_state.get("recent_select") in RECENT_OPTIONS
        else 0
    )
    st.selectbox(
        "Timeframe",
        RECENT_OPTIONS,
        index=_idx,
        key="recent_select",
        on_change=_on_recent_change,
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

# -- Account (populated after DF load; we show whatever is in session now) --
with t_acct:
    st.markdown("<div class='tb tb-select'>", unsafe_allow_html=True)
    _acct_options = st.session_state.get("journal_options", ["ALL"])
    _acct_idx = (
        _acct_options.index(st.session_state["global_journal_sel"])
        if st.session_state.get("global_journal_sel") in _acct_options
        else 0
    )
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

        if "_uploaded_files" not in st.session_state:
            st.session_state["_uploaded_files"] = {}

        _newfile = st.file_uploader("Browse file", type=["csv"], key="file_menu")
        if _newfile is not None:
            st.session_state["_uploaded_files"][_newfile.name] = _newfile.read()
            st.toast(f"Saved '{_newfile.name}'")
            st.session_state["_selected_upload"] = _newfile.name

        if st.session_state["_uploaded_files"]:
            _names = list(st.session_state["_uploaded_files"].keys())
            _sel_ix = _names.index(st.session_state.get("_selected_upload", _names[0]))
            _sel = st.selectbox(
                "Uploaded files", options=_names, index=_sel_ix, key="uploaded_files_select"
            )
            st.session_state["_selected_upload"] = _sel

            if st.button("Use this file", use_container_width=True):
                import io

                file = io.BytesIO(st.session_state["_uploaded_files"][_sel])
                file.name = _sel
                st.session_state["_menu_file_obj"] = file
                st.toast(f"Using '{_sel}' as current dataset")
                st.rerun()
        else:
            st.caption("No uploads yet.")

        st.markdown("</div>", unsafe_allow_html=True)  # close .upload-pop
        st.markdown("</div>", unsafe_allow_html=True)  # close .profile-pop


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

    st.divider()

# ===================== MAIN: Upload OR Journal Fallback =====================
df = None
source_label = ""

# 1) If user picked a file from the burger/popover, use it
_menu_file = st.session_state.get("_menu_file_obj")

if _menu_file is not None:
    source_label = f"uploaded: {getattr(_menu_file, 'name', 'file.csv')}"
    try:
        _menu_file.seek(0)
        df = load_trades(_menu_file)
    except Exception as e:
        st.error(f"Could not read that file: {e}")
        st.stop()
else:
    # 2) Otherwise fallback to currently selected journal (if any)
    sel_id = st.session_state.get("selected_journal")
    if sel_id:
        idx = load_journal_index()
        rec = next((j for j in idx.get("journals", []) if j["id"] == sel_id), None)
        if rec and Path(rec["path"]).exists():
            source_label = f"journal: {rec['name']}"
            # ---- read file in a way that tolerates empty CSVs ----
            with open(rec["path"], "rb") as f:
                _bytes = f.read()

            # If empty file → show an empty Journal page instead of erroring
            if not _bytes.strip():
                empty_cols = [
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
                df = pd.DataFrame(columns=empty_cols)

            else:
                import io

                try:
                    df = load_trades(io.BytesIO(_bytes))
                except Exception as e:
                    st.warning(f"Journal file couldn’t be parsed ({e}). Opening Journal.")
                    empty_cols = [
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
                    df = pd.DataFrame(columns=empty_cols)

# 3) Final safety: ensure df is always defined
if df is None:
    df = pd.DataFrame(
        columns=[
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
    )
    source_label = "empty"


# If we still don't have data, bail out gently
if df is None:
    st.info("Use the profile menu (top-right) to upload a CSV, or create/select a journal.")
    st.stop()


# st.caption(f"Data source: **{source_label}**")
st.toast(f"✅ Loaded {len(df)} trades from {source_label}")

# ===================== PIPELINE: Validate → PnL → Preview =====================
issues = validate(df)
if issues:
    st.error("We found issues in your CSV:")
    for i, msg in enumerate(issues, start=1):
        st.write(f"{i}. {msg}")
    st.stop()

df = add_pnl(df)

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

if _date_col_for_bounds is not None and len(df):
    _dt_full_bounds = pd.to_datetime(df[_date_col_for_bounds], errors="coerce")
    if not _dt_full_bounds.empty:
        st.session_state["_data_min"] = _dt_full_bounds.min().date()
        st.session_state["_data_max"] = _dt_full_bounds.max().date()
        # If "All Dates" was selected before we knew bounds, apply now
        if st.session_state.get("recent_select") == "All Dates":
            _apply_range("All Dates")

# --- Build Account options for the topbar (kept in session so topbar can render early) ---
_prev_opts = tuple(st.session_state.get("journal_options", []))
_acc_series = None
for _c in ("Account", "account"):
    if _c in df.columns:
        _acc_series = df[_c]
        break

if _acc_series is not None and len(_acc_series):
    _present = sorted(set(_acc_series.astype(str).str.strip()))
    _groups = sorted(list(st.session_state.get("journal_groups", {}).keys()))
    _new_opts = ["ALL"] + _present + _groups
else:
    _new_opts = ["ALL", "NQ", "Crypto (Live)"]

st.session_state["journal_options"] = _new_opts

# If options changed since first render, re-run once so the topbar shows them
if tuple(_new_opts) != _prev_opts:
    st.rerun()


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


# --- Compute data bounds for "All Dates" ---
# Pick a date column you already use later:
_date_col = "date" if "date" in df.columns else ("Date" if "Date" in df.columns else None)
if _date_col is not None and len(df):
    _dt_full = pd.to_datetime(df[_date_col], errors="coerce")
    if not _dt_full.empty:
        st.session_state["_data_min"] = _dt_full.min().date()
        st.session_state["_data_max"] = _dt_full.max().date()

# If user picked "All Dates", apply it now that we know true bounds
if st.session_state.get("recent_select") == "All Dates":
    _apply_range("All Dates")

# --- Build Account options for the topbar (kept in session so topbar can render early) ---
acc_series = df.get("Account")
if acc_series is not None:
    present = sorted(set(acc_series.astype(str).str.strip()))
    groups = sorted(list(st.session_state.get("journal_groups", {}).keys()))
    st.session_state["journal_options"] = ["ALL"] + present + groups
else:
    st.session_state["journal_options"] = ["ALL"]


# -------- Apply journal + date filters to df (global) --------
sel = st.session_state.get("global_journal_sel", "ALL")
if sel == "ALL":
    df = df.copy()
elif sel in st.session_state["journal_groups"]:
    df = df[df["Account"].isin(st.session_state["journal_groups"][sel])].copy()
else:
    df = df[df["Account"].astype(str).str.strip() == sel].copy()

# Date filter (if your df has a date column)
date_col = "date" if "date" in df.columns else ("Date" if "Date" in df.columns else None)
if date_col is not None:
    dfrom, dto = pd.to_datetime(st.session_state["date_from"]), pd.to_datetime(
        st.session_state["date_to"]
    )
    mask = (pd.to_datetime(df[date_col]) >= dfrom) & (pd.to_datetime(df[date_col]) <= dto)
    df = df[mask].copy()


# ===================== RUNTIME SETTINGS (no UI) =====================
# Defaults for now; we'll move breakeven policy into Filters later
be_policy = st.session_state.get("be_policy", "be excluded from win-rate")
start_equity = float(st.session_state.get("start_equity", 5000.0))

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

# Nice label for the current range (from the date inputs)
dfrom, dto = pd.to_datetime(st.session_state["date_from"]), pd.to_datetime(
    st.session_state["date_to"]
)
tf_display = f"{dfrom:%b %d, %Y} → {dto:%b %d, %Y}"

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
    st.subheader("Account")
    st.info("Account settings page (placeholder)")

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


st.markdown('<div id="tail-spacer" style="height: 200px"></div>', unsafe_allow_html=True)
