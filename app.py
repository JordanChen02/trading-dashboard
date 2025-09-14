# app.py (top of file)
import calendar as _cal
import json  # read/write sidecar metadata for notes/tags
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 👇 our modules
from src.io import load_trades, validate
from src.metrics import add_pnl
from src.state import ensure_defaults
from src.styles import inject_filters_css, inject_upload_css
from src.theme import BLUE_FILL
from src.utils import create_journal, ensure_journal_store, load_journal_index
from src.views.overview import render_overview
from src.views.performance import render as render_performance

# (other imports are fine above or below — imports don’t matter)


ensure_defaults()

st.set_page_config(
    page_title="Trading Dashboard — MVP",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Make theme color available to CSS as a custom property
st.markdown(f"<style>:root{{--blue-fill:{BLUE_FILL};}}</style>", unsafe_allow_html=True)


# default month in session (first of current month)
if "_cal_month_start" not in st.session_state:
    st.session_state["_cal_month_start"] = pd.Timestamp.today().normalize().replace(day=1)

h_left, h_month, h_upload, h_filters = st.columns([12, 2, 2, 2], gap="small")

with h_left:
    st.title("Trading Dashboard — MVP")

# ---------- MONTH PICKER (popover trigger with calendar icon) ----------
with h_month:
    st.markdown(
        """
    <style>
    :root { --brand:#3579ba; }
    .month-trigger button{
      background: transparent !important;
      border: 1px solid #233045 !important;
      color: #d5deed !important;
      padding: 6px 12px !important;
      border-radius: 10px !important;
      font-weight: 600;
    }
    .month-trigger button:hover{ background: var(--blue-fill) !important; }
    .month-trigger button:focus{ box-shadow:none !important; outline:none !important; }
    .month-trigger button::before{
      content:"";
      width:16px; height:16px; margin-right:8px;
      display:inline-block; background-color: var(--brand);
      -webkit-mask: url("data:image/svg+xml;utf8,\
      <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
        <path fill='black' d='M7 2v2H5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2V2h-2v2H9V2H7zm12 7H5v10h14V9z'/>\
      </svg>") no-repeat center / contain;
              mask: url("data:image/svg+xml;utf8,\
      <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
        <path fill='black' d='M7 2v2H5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2V2h-2v2H9V2H7zm12 7H5v10h14V9z'/>\
      </svg>") no-repeat center / contain;
    }
    .month-pop { min-width: 360px; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Build a label like: "Sep 1, 2025 - Sep 30, 2025"
    _ms = pd.Timestamp(st.session_state["_cal_month_start"]).normalize().replace(day=1)
    _me = (_ms + pd.offsets.MonthEnd(1)).normalize()

    def _fmt(ts: pd.Timestamp) -> str:
        # Avoid %-d vs %#d OS differences: format day via attribute
        return f"{ts.strftime('%b')} {ts.day}, {ts.year}"

    _lbl = f"{_fmt(_ms)} - {_fmt(_me)}"

    st.markdown('<div class="month-trigger">', unsafe_allow_html=True)
    mp = st.popover(_lbl, use_container_width=False)
    with mp:
        st.markdown('<div class="month-pop">', unsafe_allow_html=True)
        _picked = st.date_input(
            "Pick month",
            value=st.session_state["_cal_month_start"].to_pydatetime(),
            format="YYYY-MM-DD",
            key="cal_month_input",
        )
        # normalize to first-of-month
        st.session_state["_cal_month_start"] = pd.to_datetime(_picked).normalize().replace(day=1)
        st.markdown("</div>", unsafe_allow_html=True)  # close .month-pop
    st.markdown("</div>", unsafe_allow_html=True)  # close .month-trigger

# ---------- UPLOAD (unchanged, still a popover) ----------
with h_upload:
    inject_upload_css()

    st.markdown('<div class="upload-trigger">', unsafe_allow_html=True)
    up = st.popover("Upload", use_container_width=False)
    with up:
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
    st.markdown("</div>", unsafe_allow_html=True)  # close .upload-trigger


# ---------- FILTERS TRIGGER (popover; sits next to Upload) ----------
with h_filters:
    inject_filters_css()

    st.markdown('<div class="filters-trigger">', unsafe_allow_html=True)
    fp = st.popover("Filters", use_container_width=False)
    with fp:
        st.markdown('<div class="filters-pop">', unsafe_allow_html=True)

        st.caption("Filters live in the left sidebar. Quick actions:")
        colA, colB = st.columns(2, gap="small")

        with colA:
            if st.button("Open Sidebar", use_container_width=True):
                st.toast("Filters are in the left sidebar (expanded).")

        with colB:
            if st.button("Clear Calendar Filter", use_container_width=True):
                st.session_state._cal_filter = None
                st.toast("Calendar filter cleared")
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)  # close .filters-pop
    st.markdown("</div>", unsafe_allow_html=True)  # close .filters-trigger


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

    # Keep selected tab in session; default to Dashboard
    _current = st.session_state.get("nav", "Dashboard")
    _options = ["Dashboard", "Journal", "Accounts"]

    # Render as a radio but style it as a flat list (no circles, full-bleed rows)
    nav = st.radio(
        "Go to:",
        _options,
        index=_options.index(_current),
        label_visibility="collapsed",
        key="nav_radio",
    )
    st.session_state["nav"] = nav  # normalize key we use elsewhere

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
            with open(rec["path"], "rb") as f:
                df = load_trades(f)

# If we still don't have data, bail out gently
if df is None:
    st.info("Use the ☰ menu (top-right) to upload a CSV, or create/select a journal.")
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


# ===================== FILTERS (render after df exists) =====================
# Recreate the sidebar expander now that df is available
with st.sidebar.expander("Filters", expanded=True):
    symbols = sorted(df["symbol"].dropna().unique().tolist()) if "symbol" in df.columns else []
    sides = sorted(df["side"].dropna().unique().tolist()) if "side" in df.columns else []

    sel_symbols = st.multiselect("Symbol", symbols, default=symbols if symbols else [])
    sel_sides = st.multiselect("Side", sides, default=sides if sides else [])
    # --- Tag filter (A+/A/B/C) ---
    # We gather possible tags from the DataFrame if present, plus any in-session tags.
    _tags_present = set()
    if "tag" in df.columns:
        _tags_present |= set(
            df["tag"].dropna().astype(str).str.strip().tolist()
        )  # |= is set-union assignment

    _tags_present |= set(st.session_state.get("_trade_tags", {}).values())

    # Keep only known tag grades in a nice order
    _known_order = ["A+", "A", "B", "C"]
    tag_options = [t for t in _known_order if t in _tags_present]

    sel_tags = st.multiselect(
        "Tag",
        options=tag_options,
        default=tag_options if tag_options else [],
        help="Quick grades you’ve applied to trades (A+, A, B, C).",
    )

# Apply filters
df_filtered = df.copy()
if "symbol" in df_filtered.columns and sel_symbols:
    df_filtered = df_filtered[df_filtered["symbol"].isin(sel_symbols)]
if "side" in df_filtered.columns and sel_sides:
    df_filtered = df_filtered[df_filtered["side"].isin(sel_sides)]
if "tag" in df_filtered.columns and sel_tags:
    df_filtered = df_filtered[df_filtered["tag"].isin(sel_tags)]

if df_filtered.empty:
    st.info("No rows match the current filters. Adjust filters in the sidebar.")
    st.stop()

# From here on, keep your existing code but make it operate on the filtered data:
df = df_filtered

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
    import plotly.graph_objects as go

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

    # Clear button (only useful if a filter exists)
    with right:
        if cal_sel:
            if st.button("Clear", key=f"clear_cal_filter_{key_suffix}", use_container_width=True):
                st.session_state._cal_filter = None
                st.toast("Calendar filter cleared")
                st.rerun()


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
    import calendar as _cal

    import plotly.graph_objects as go

    st.subheader("Calendar — Daily PnL & Trade Count")
    st.caption(f"Using Range: **{tf}**")

    # Guard
    if _date_col is None or _date_col not in df_view.columns or len(df_view) == 0:
        st.info("No date/timestamp column found — calendar view unavailable for this dataset.")
    else:
        # ---- Month selector (defaults to current month) ----
        _today = pd.Timestamp.today().normalize()
        _default_month = _today.replace(day=1)
        _picked = st.date_input(
            "Select a month", value=_default_month.to_pydatetime(), format="YYYY-MM-DD"
        )
        _picked = pd.to_datetime(_picked)
        _month_start = _picked.replace(day=1)
        _month_end = (_month_start + pd.offsets.MonthEnd(1)).normalize()

        # ---- Aggregate df_view by day for the selected month ----
        _dt = pd.to_datetime(df_view[_date_col], errors="coerce")
        _mask_month = (_dt >= _month_start) & (_dt <= _month_end)
        _dfm = df_view.loc[_mask_month].copy()
        _dfm["_day"] = pd.to_datetime(_dfm[_date_col], errors="coerce").dt.date

        _daily_stats = (
            _dfm.assign(_pnl=pd.to_numeric(_dfm["pnl"], errors="coerce").fillna(0.0))
            .groupby("_day")
            .agg(NetPnL=("_pnl", "sum"), Trades=("pnl", "count"))
            .reset_index()
        )
        _daily_map = {
            row["_day"]: (float(row["NetPnL"]), int(row["Trades"]))
            for _, row in _daily_stats.iterrows()
        }

        # ---- Build calendar grid meta ----
        _first_weekday, _n_days = _cal.monthrange(
            _month_start.year, _month_start.month
        )  # Mon=0..Sun=6
        _leading = _first_weekday
        _total_slots = _leading + _n_days
        _rows = (_total_slots + 6) // 7  # ceil div by 7

        # ---------- THEME TOKENS ----------
        _panel_bg = "#0b0f19"  # page/panel bg
        _cell_bg = "#101621"  # day cell background
        _grid_line = "#2a3444"  # subtle grid lines
        _txt_main = "#e5e7eb"  # main text
        _txt_muted = "#9ca3af"  # muted text
        _pnl_pos = "#22c55e"  # green
        _pnl_neg = "#ef4444"  # red
        _pnl_zero = _txt_main  # neutral
        _dash_accent = "#1f2937"  # outer frame border
        _total_bg = "#0d1320"  # TOTAL column bg
        _total_border = "#3a4557"  # TOTAL column border
        _total_hdr = "#cbd5e1"  # TOTAL header color

        # ---------- HELPERS ----------
        def _slot_in_month(slot_idx: int) -> bool:
            day_n = slot_idx - _leading + 1
            return 1 <= day_n <= _n_days

        def _slot_to_date(slot_idx: int):
            day_n = slot_idx - _leading + 1
            if 1 <= day_n <= _n_days:
                return (_month_start + pd.Timedelta(days=day_n - 1)).date()
            return None

        # Precompute weekly totals (row-wise)
        week_totals = []
        for r_idx in range(_rows):
            start_slot = r_idx * 7
            pnl_sum = 0.0
            trade_sum = 0
            for c_idx in range(7):
                slot_idx = start_slot + c_idx
                d = _slot_to_date(slot_idx)
                if d is not None:
                    p, t = _daily_map.get(d, (0.0, 0))
                    pnl_sum += float(p)
                    trade_sum += int(t)
            week_totals.append((pnl_sum, trade_sum))

        # ---------- DRAW GRID ----------
        shapes, annos = [], []

        # weekday header row (above grid) — include "Total" column
        _weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Total"]
        for c, label in enumerate(_weekday_labels):
            annos.append(
                dict(
                    x=c + 0.5,
                    y=-0.35,
                    xref="x",
                    yref="y",
                    text=label,
                    showarrow=False,
                    font=dict(size=12, color=_total_hdr if label == "Total" else _txt_muted),
                    xanchor="center",
                    yanchor="middle",
                )
            )

        # rounded outer container (now 8 columns wide to include totals)
        total_w, total_h = 8, _rows
        _corner_r = 0.35
        path = (
            f"M{_corner_r},-1 H{total_w - _corner_r} "
            f"Q{total_w},-1 {total_w},{-1 + _corner_r} "
            f"V{total_h - _corner_r} "
            f"Q{total_w},{total_h} {total_w - _corner_r},{total_h} "
            f"H{_corner_r} "
            f"Q0,{total_h} 0,{total_h - _corner_r} "
            f"V{-1 + _corner_r} "
            f"Q0,-1 {_corner_r},-1 Z"
        )
        shapes.append(
            dict(
                type="path",
                path=path,
                line=dict(color=_dash_accent, width=1.5),
                fillcolor=_panel_bg,
                layer="below",
            )
        )

        # cells (7 day columns + 1 total column)
        for r_idx in range(_rows):
            for c_idx in range(8):
                x0, x1 = c_idx, c_idx + 1
                y0, y1 = r_idx, r_idx + 1

                # TOTAL column styled differently
                is_total_col = c_idx == 7
                shapes.append(
                    dict(
                        type="rect",
                        x0=x0,
                        x1=x1,
                        y0=y0,
                        y1=y1,
                        line=dict(
                            color=_total_border if is_total_col else _grid_line,
                            width=1.5 if is_total_col else 1,
                        ),
                        fillcolor=_total_bg if is_total_col else _cell_bg,
                        layer="below",
                    )
                )

                # day columns (0..6)
                if not is_total_col:
                    slot_idx = r_idx * 7 + c_idx
                    if _slot_in_month(slot_idx):
                        d = _slot_to_date(slot_idx)
                        pnl_val, trade_ct = _daily_map.get(d, (0.0, 0))

                        # --- day number (TOP-LEFT) ---
                        annos.append(
                            dict(
                                x=x0 + 0.08,
                                y=y0 + 0.15,
                                xref="x",
                                yref="y",
                                text=str((slot_idx - _leading + 1)),
                                showarrow=False,
                                font=dict(size=12, color=_txt_muted),
                                xanchor="left",
                                yanchor="top",
                            )
                        )

                        # --- PnL (CENTER, larger) ---
                        if trade_ct == 0:
                            pnl_txt = "—"
                            pnl_col = _txt_muted
                        else:
                            pnl_txt = f"${pnl_val:,.0f}"
                            pnl_col = (
                                _pnl_pos
                                if pnl_val > 0
                                else (_pnl_neg if pnl_val < 0 else _pnl_zero)
                            )
                        annos.append(
                            dict(
                                x=x0 + 0.5,
                                y=y0 + 0.48,
                                xref="x",
                                yref="y",
                                text=pnl_txt,
                                showarrow=False,
                                font=dict(size=20, color=pnl_col),
                                xanchor="center",
                                yanchor="middle",
                            )
                        )

                        # --- trades (BELOW center) ---
                        trades_txt = (
                            "—"
                            if trade_ct == 0
                            else (f"{trade_ct} trade" if trade_ct == 1 else f"{trade_ct} trades")
                        )
                        annos.append(
                            dict(
                                x=x0 + 0.5,
                                y=y0 + 0.78,
                                xref="x",
                                yref="y",
                                text=trades_txt,
                                showarrow=False,
                                font=dict(size=11, color=_txt_muted),
                                xanchor="center",
                                yanchor="top",
                            )
                        )

                # totals column (c_idx == 7)
                else:
                    pnl_sum, trade_sum = week_totals[r_idx]
                    # PnL total (center)
                    if trade_sum == 0:
                        tot_pnl_txt = "—"
                        tot_pnl_col = _txt_muted
                    else:
                        tot_pnl_txt = f"${pnl_sum:,.0f}"
                        tot_pnl_col = (
                            _pnl_pos if pnl_sum > 0 else (_pnl_neg if pnl_sum < 0 else _pnl_zero)
                        )
                    annos.append(
                        dict(
                            x=x0 + 0.5,
                            y=y0 + 0.48,
                            xref="x",
                            yref="y",
                            text=tot_pnl_txt,
                            showarrow=False,
                            font=dict(size=16, color=tot_pnl_col),
                            xanchor="center",
                            yanchor="middle",
                        )
                    )
                    # Trades total (below center)
                    tot_trades_txt = (
                        "—"
                        if trade_sum == 0
                        else (f"{trade_sum} trade" if trade_sum == 1 else f"{trade_sum} trades")
                    )
                    annos.append(
                        dict(
                            x=x0 + 0.5,
                            y=y0 + 0.78,
                            xref="x",
                            yref="y",
                            text=tot_trades_txt,
                            showarrow=False,
                            font=dict(size=11, color=_txt_muted),
                            xanchor="center",
                            yanchor="top",
                        )
                    )

        # ---------- BUILD FIGURE ----------
        fig_cal = go.Figure()
        fig_cal.update_layout(
            paper_bgcolor=_panel_bg,
            plot_bgcolor=_panel_bg,
            shapes=shapes,
            annotations=annos,
            xaxis=dict(
                range=[0, 8],  # 7 days + 1 TOTAL column
                showgrid=False,
                zeroline=False,
                tickmode="array",
                tickvals=[],
                ticktext=[],
                fixedrange=True,
            ),
            yaxis=dict(
                range=[_rows, -1],  # leave -1 for header row
                showgrid=False,
                zeroline=False,
                tickvals=[],
                ticktext=[],
                fixedrange=True,
            ),
            margin=dict(l=10, r=10, t=10, b=16),
        )
        # Save the computed height for other panels (e.g., Equity Curve)
        _cal_h = 160 + _rows * 120
        fig_cal.update_layout(height=_cal_h)
        st.session_state["_cal_height"] = int(_cal_h)

        # Month title
        _title = _month_start.strftime("%B %Y")
        st.markdown(f"### {_title}")
        st.plotly_chart(fig_cal, use_container_width=True)
        st.caption("Green = positive PnL, red = negative. Rightmost column shows weekly totals.")

        # -------- Filter from Calendar --------
        st.markdown("#### Filter from Calendar")

        # A) Day filter (within the selected month)
        col_day, col_week, col_clear = st.columns([2, 2, 1])

        with col_day:
            _day_pick = st.date_input(
                "Pick a day",
                value=_month_start.to_pydatetime(),
                min_value=_month_start.to_pydatetime(),
                max_value=_month_end.to_pydatetime(),
                key="cal_day_input",
            )
            if st.button("Apply Day Filter", use_container_width=True):
                st.session_state._cal_filter = ("day", pd.to_datetime(_day_pick).date())
                st.toast(f"Filtered to day: {pd.to_datetime(_day_pick).date()}")
                st.rerun()

        # Helper to compute the Monday start of each visible week-row
        def _week_start_for_row(r_idx: int):
            first_slot = r_idx * 7
            # find the first in-month date in that row
            first_date = None
            for c_idx in range(7):
                d = _slot_to_date(first_slot + c_idx)
                if d is not None:
                    first_date = pd.Timestamp(d)
                    break
            if first_date is None:
                return None
            # normalize to Monday (weekday: Monday=0)
            return (first_date - pd.Timedelta(days=first_date.weekday())).date()

        # Build week options from visible rows
        _week_starts = []
        for _r in range(_rows):
            ws = _week_start_for_row(_r)
            if ws is not None:
                _week_starts.append(ws)

        with col_week:
            _week_ix = st.selectbox(
                "Pick a week",
                options=list(range(len(_week_starts))),
                format_func=lambda i: f"Week of {pd.Timestamp(_week_starts[i]).strftime('%b %d')}",
                key="cal_week_sel",
            )
            if st.button("Apply Week Filter", use_container_width=True):
                ws = pd.Timestamp(_week_starts[_week_ix]).date()
                we = (pd.Timestamp(ws) + pd.Timedelta(days=6)).date()
                # Clamp to the displayed month window
                ws = max(ws, _month_start.date())
                we = min(we, _month_end.date())
                st.session_state._cal_filter = ("week", (ws, we))
                st.toast(f"Filtered to week: {ws} → {we}")
                st.rerun()

        with col_clear:
            if st.button("Clear Filter", use_container_width=True):
                st.session_state._cal_filter = None
                st.toast("Calendar filter cleared")
                st.rerun()

st.divider()
st.subheader("Preview (first 50 rows)")
st.dataframe(df.head(50), use_container_width=True)
