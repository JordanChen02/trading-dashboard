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
from src.utils import create_journal, ensure_journal_store, load_journal_index
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
  [data-testid="stAppViewContainer"] .block-container {{
    padding-bottom: 200px !important;   /* adjust this value */
  }}

  /* Sidebar needs matching bottom room so it doesn’t crop */
  [data-testid="stSidebar"] > div:first-child {{
    padding-bottom: 200px !important;   /* same value as above */
  }}
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

  /* If your brand row still looks tight, you can add a small gap under it too */
  [data-testid="stSidebar"] .brand-row {
    margin-top: 10px !important;   /* optional; tweak or remove */
  }
</style>
""",
    unsafe_allow_html=True,
)


# Make theme color available to CSS as a custom property
st.markdown(f"<style>:root {{ --blue-fill: {BLUE_FILL}; }}</style>", unsafe_allow_html=True)


# default month in session (first of current month)
if "_cal_month_start" not in st.session_state:
    st.session_state["_cal_month_start"] = pd.Timestamp.today().normalize().replace(day=1)

# ========== TOP TOOLBAR (right-aligned icons) ==========
st.markdown('<div class="topbar">', unsafe_allow_html=True)


# Big spacer pushes icons to the far right
t_spacer, t_globe, t_bell, t_full, t_theme, t_profile = st.columns(
    [100, 5, 5, 5, 5, 5], gap="small"
)
with t_spacer:
    st.empty()

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
    # ===== Brand header =====
    BRAND = "Wavemark"  # <— change to taste

    st.markdown(
        """
    <style>
    .brand-row{
    display:flex; align-items:center; justify-content:space-between;
    margin: 6px 0 8px 0;
    }
    .brand-name{
    font-weight: 800; letter-spacing: .6px;
    font-size: 20px; color: #dbe5ff;
    }
    .brand-accent{ color:#3579ba; }  /* your theme blue */
    .brand-burger{
    font-weight:700; font-size: 20px; color:#3579ba; opacity:.9;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
    <div class="brand-row">
    <div class="brand-name">{BRAND}<span class="brand-accent">.</span></div>
    <div class="brand-burger">≡</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # st.markdown("## Navigation")

    # ===================== SIDEBAR: Navigation =====================
    _options = ["Dashboard", "Journal", "Accounts", "Checklist"]

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
    height: 40px;
    padding: 0 12px;
    margin: 0;                           /* no gaps between rows */
    border-radius: 10px;
    background: transparent;
    position: relative;
    left: -8px;                          /* bleed to left edge */
    width: calc(100% + 16px);            /* bleed to both edges */
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
    letter-spacing: .2px;
    }

    /* === ICONS (inline SVG, colored by --brand via CSS mask) === */

    /* Create an icon box before the label text */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label::before{
    content: "";
    width: 22px; height: 22px;
    margin-right: 10px;
    display:inline-block;
    background-color: var(--brand);      /* icon color */
    -webkit-mask-repeat: no-repeat; -webkit-mask-position: center; -webkit-mask-size: contain;
    mask-repeat: no-repeat; mask-position: center; mask-size: contain;
    opacity:.95;
    }

    /* Row order mapping: 1=Dashboard, 2=Journal, 3=Accounts  */
    /* DASHBOARD icon: grid */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:nth-of-type(1)::before{
    -webkit-mask-image: url("data:image/svg+xml;utf8,\
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
        <rect x='3' y='3' width='8' height='8' rx='2' ry='2' fill='black'/>\
        <rect x='13' y='3' width='8' height='5' rx='2' ry='2' fill='black'/>\
        <rect x='13' y='10' width='8' height='11' rx='2' ry='2' fill='black'/>\
        <rect x='3' y='13' width='8' height='8' rx='2' ry='2' fill='black'/>\
    </svg>");
            mask-image: url("data:image/svg+xml;utf8,\
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
        <rect x='3' y='3' width='8' height='8' rx='2' ry='2' fill='black'/>\
        <rect x='13' y='3' width='8' height='5' rx='2' ry='2' fill='black'/>\
        <rect x='13' y='10' width='8' height='11' rx='2' ry='2' fill='black'/>\
        <rect x='3' y='13' width='8' height='8' rx='2' ry='2' fill='black'/>\
    </svg>");
    }

    /* JOURNAL icon: pencil */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:nth-of-type(2)::before{
    -webkit-mask-image: url("data:image/svg+xml;utf8,\
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
        <path d='M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z' fill='black'/>\
        <path d='M20.71 7.04a1 1 0 0 0 0-1.42L18.37 3.3a1 1 0 0 0-1.42 0l-1.34 1.34 3.75 3.75 1.34-1.35z' fill='black'/>\
    </svg>");
            mask-image: url("data:image/svg+xml;utf8,\
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
        <path d='M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z' fill='black'/>\
        <path d='M20.71 7.04a1 1 0 0 0 0-1.42L18.37 3.3a1 1 0 0 0-1.42 0l-1.34 1.34 3.75 3.75 1.34-1.35z' fill='black'/>\
    </svg>");
    }

    /* ACCOUNTS icon: stacked cards */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:nth-of-type(3)::before{
    -webkit-mask-image: url("data:image/svg+xml;utf8,\
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
        <rect x='4' y='6' width='14' height='10' rx='2' ry='2' fill='black'/>\
        <rect x='6' y='4' width='14' height='10' rx='2' ry='2' fill='black'/>\
    </svg>");
            mask-image: url("data:image/svg+xml;utf8,\
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
        <rect x='4' y='6' width='14' height='10' rx='2' ry='2' fill='black'/>\
        <rect x='6' y='4' width='14' height='10' rx='2' ry='2' fill='black'/>\
    </svg>");
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.divider()

    st.header("Journals")

    # Load registry
    idx = load_journal_index()
    journals = idx.get("journals", [])

    # Create new journal (popover keeps UI clean)
    with st.popover("➕ New Journal"):
        jname = st.text_input("Name", placeholder="e.g., NQ, Crypto, Swings")
        if st.button("Create"):
            if not jname.strip():
                st.warning("Please enter a name.")
            else:
                rec = create_journal(jname.strip())
                st.success(f"Created '{rec['name']}'")
                st.session_state.selected_journal = rec["id"]
                st.rerun()

    # Selector (only if any exist)
    names = [j["name"] for j in journals]
    ids = [j["id"] for j in journals]
    default_ix = 0 if ids else None

    selected_name = st.selectbox(
        "Select journal",
        options=names,
        index=default_ix,
        placeholder="No journals yet",
    )
    if names:
        selected_id = ids[names.index(selected_name)]
        st.session_state.selected_journal = selected_id


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


# ===================== CONTROLS BAR (appears inline with tabs) =====================


st.markdown(
    """
<style>
  /* Make controls + tabs look like one row */
  .controls-bar { margin-bottom: 2px; }           /* shrink gap above tabs */
  div[data-baseweb="tab-list"] { margin-top: 0; } /* tabs top margin */

  /* Compact sizing */
  .jr-wrap{ width: 220px; display:inline-block; } /* ← adjust select width */
  .jr-wrap .stSelectbox{ width: 100%; }
  .jr-plus > div button{ width:40px; height:40px; padding:0; border-radius:10px; }
  .seg-btn > div button{ height:40px; }
  .date-box .stDateInput{ min-width: 210px; }
  .date-box .stDateInput input{ text-align:center; }
</style>
""",
    unsafe_allow_html=True,
)

with st.container():
    st.markdown("<div class='controls-bar'>", unsafe_allow_html=True)
    jr_col, plus_col, b7_col, b30_col, dd_col, from_col, to_col = st.columns(
        [0.32, 0.08, 0.12, 0.16, 0.22, 0.35, 0.35], gap="small"
    )

    # -------- Ensure Account column (derive if missing) --------
    if "Account" not in df.columns:
        sym = df.get("symbol", None)
        if sym is None:
            sym = df.get("Symbol", None)
        if sym is not None:
            s = sym.astype(str).str.upper()
            df["Account"] = np.select(
                [s.eq("NQ"), s.eq("BTCUSDT")],
                ["NQ", "Crypto (Prop)"],
                default="Crypto (Live)",
            )
        else:
            df["Account"] = "NQ"
    df["Account"] = (
        df["Account"]
        .astype(str)
        .str.strip()
        .replace(
            {
                "Journal: NQ": "NQ",
                "Journal: Crypto": "Crypto (Live)",
                "Journal: Crypto (Live)": "Crypto (Live)",
                "Journal: Crypto (Prop)": "Crypto (Prop)",
            }
        )
    )
    base_accounts = ["NQ", "Crypto (Prop)", "Crypto (Live)"]
    present_accounts = [a for a in base_accounts if a in df["Account"].unique().tolist()]
    st.session_state.setdefault("journal_groups", {})
    group_names = sorted(list(st.session_state["journal_groups"].keys()))
    journal_options = ["ALL"] + present_accounts + group_names

    # -------- Journal select --------
    with jr_col:
        st.markdown("<div class='jr-wrap'>", unsafe_allow_html=True)
        default_idx = (
            journal_options.index(st.session_state["global_journal_sel"])
            if st.session_state.get("global_journal_sel") in journal_options
            else 0
        )
        sel = st.selectbox(
            "Journal",
            options=journal_options,
            index=default_idx,
            key="global_journal_sel",
            label_visibility="collapsed",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # -------- ＋ group creator --------
    with plus_col:
        st.markdown("<div class='jr-plus'>", unsafe_allow_html=True)
        pop = st.popover("＋", use_container_width=True)
        with pop:
            st.markdown("**Create journal group**")
            g_name = st.text_input("Group name", placeholder="e.g., Crypto (All)")
            pick = st.multiselect(
                "Include accounts",
                options=base_accounts,
                default=["Crypto (Prop)", "Crypto (Live)"],
            )
            if st.button(
                "Save group", use_container_width=True, disabled=(not g_name.strip() or not pick)
            ):
                st.session_state["journal_groups"][g_name.strip()] = pick
                st.session_state["global_journal_sel"] = g_name.strip()
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # -------- Quick ranges + date range --------
    today = date.today()
    st.session_state.setdefault("date_from", today - timedelta(days=6))
    st.session_state.setdefault("date_to", today)

    with b7_col:
        st.markdown("<div class='seg-btn'>", unsafe_allow_html=True)
        if st.button("Recent 7 Days", use_container_width=True):
            st.session_state["date_from"] = today - timedelta(days=6)
            st.session_state["date_to"] = today
        st.markdown("</div>", unsafe_allow_html=True)

    with b30_col:
        st.markdown("<div class='seg-btn'>", unsafe_allow_html=True)
        if st.button("Recent 30 Days", use_container_width=True):
            st.session_state["date_from"] = today - timedelta(days=29)
            st.session_state["date_to"] = today
        st.markdown("</div>", unsafe_allow_html=True)

    with dd_col:
        options = {"Recent 60 Days": 59, "Recent 90 Days": 89, "Recent 120 Days": 119}
        choice = st.selectbox("Recent", list(options.keys()), index=0, label_visibility="collapsed")
        # When user changes choice, keep "to" as today and move "from" back N days:
        offs = options.get(choice, 59)
        if choice:
            st.session_state["date_from"] = today - timedelta(days=offs)
            st.session_state["date_to"] = today

    with from_col:
        st.markdown("<div class='date-box'>", unsafe_allow_html=True)
        st.session_state["date_from"] = st.date_input(
            "From", value=st.session_state["date_from"], label_visibility="collapsed"
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with to_col:
        st.markdown("<div class='date-box'>", unsafe_allow_html=True)
        st.session_state["date_to"] = st.date_input(
            "To", value=st.session_state["date_to"], label_visibility="collapsed"
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

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


# ===== CONTROL ROW (Title + Month + Filters) =====
st.markdown('<div class="controls">', unsafe_allow_html=True)
(c_left,) = st.columns([1], gap="small")
with c_left:
    st.markdown(
        "<h3 class='page-title'>Welcome, User</h3>",
        unsafe_allow_html=True,
    )


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


# ===================== TABS =====================
tab_overview, tab_perf, tab_calendar = st.tabs(["Overview", "Performance", "Calendar"])

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

# --- Timeframe selector (like the screenshot) ---
tf = st.radio(
    "Range",
    ["All", "This Week", "This Month", "This Year"],
    horizontal=True,
)

# --- Build a view DataFrame (df_view) based on the selected timeframe ---
df_view = df
if _dt_full is not None and len(df) > 0:
    today = pd.Timestamp.today().normalize()
    if tf == "This Week":
        # start of week (Mon=0). Adjust if you prefer Sun start: use .weekday() -> (weekday+1)%7
        start = today - pd.Timedelta(days=today.weekday())
        mask = _dt_full >= start
        df_view = df[mask]
    elif tf == "This Month":
        start = today.replace(day=1)
        mask = _dt_full >= start
        df_view = df[mask]
    elif tf == "This Year":
        start = today.replace(month=1, day=1)
        mask = _dt_full >= start
        df_view = df[mask]
# else: keep df_view = df (All)

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


# --- Helper: render active filters banner ---
def render_active_filters(key_suffix: str = ""):
    cal_sel = st.session_state.get("_cal_filter")
    left, mid, right = st.columns([3, 5, 2])

    # Range chip (always present)
    with left:
        st.caption(f"Range: **{tf}**")

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

# --- Render the four Overview cards for the selected timeframe ---
with tab_overview:
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


with tab_perf:
    render_active_filters("perf")
    render_performance(df_view, start_equity, _date_col, tf, win_rate_v, avg_win_v, avg_loss_v)


with tab_calendar:
    st.subheader("Trade Calendar")
    st.caption(f"Using Range: {tf}")

    # Ensure a month anchor (prefer last available date in the current view)
    if "_cal_month_start" not in st.session_state:
        if _date_col and _date_col in df_view.columns:
            _dt_tmp = pd.to_datetime(df_view[_date_col], errors="coerce").dropna()
            anchor = _dt_tmp.max() if len(_dt_tmp) else pd.Timestamp.today()
        else:
            anchor = pd.Timestamp.today()
        st.session_state["_cal_month_start"] = anchor.normalize().replace(day=1)

    # Draw the original Plotly calendar from src/views/calendar.py
    render_calendar(
        df_view=df_view,
        _date_col=_date_col,
        month_start=st.session_state["_cal_month_start"],
        key="cal",
    )

st.markdown('<div id="tail-spacer" style="height: 200px"></div>', unsafe_allow_html=True)
