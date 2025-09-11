# app.py (top of file)
import streamlit as st
# (other imports are fine above or below — imports don’t matter)

st.set_page_config(
    page_title="Trading Dashboard — MVP",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# === Header row: Title (left) + Month picker (right) + Upload (far right) ===
import pandas as pd

# default month in session (first of current month)
if "_cal_month_start" not in st.session_state:
    st.session_state["_cal_month_start"] = pd.Timestamp.today().normalize().replace(day=1)

h_left, h_month, h_upload = st.columns([12, 2, 2], gap="small")

with h_left:
    st.title("Trading Dashboard — MVP")

# ---------- MONTH PICKER (popover trigger with calendar icon) ----------
with h_month:
    st.markdown("""
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
    .month-trigger button:hover{ background: rgba(53,121,186,0.14) !important; }
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
    """, unsafe_allow_html=True)

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
            key="cal_month_input"
        )
        # normalize to first-of-month
        st.session_state["_cal_month_start"] = pd.to_datetime(_picked).normalize().replace(day=1)
        st.markdown('</div>', unsafe_allow_html=True)  # close .month-pop
    st.markdown('</div>', unsafe_allow_html=True)      # close .month-trigger

# ---------- UPLOAD (unchanged, still a popover) ----------
with h_upload:
    st.markdown("""
    <style>
    :root { --brand:#3579ba; }
    .upload-trigger button{
      background: transparent !important;
      border: 1px solid #233045 !important;
      color: #d5deed !important;
      padding: 6px 12px !important;
      border-radius: 10px !important;
      font-weight: 600;
    }
    .upload-trigger button:hover{ background: rgba(53,121,186,0.14) !important; }
    .upload-trigger button:focus{ box-shadow:none !important; outline:none !important; }
    .upload-trigger button::before{
      content:"";
      width:16px; height:16px; margin-right:8px;
      display:inline-block; background-color: var(--brand);
      -webkit-mask: url("data:image/svg+xml;utf8,\
      <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
        <path fill='black' d='M5 20h14a1 1 0 0 0 1-1v-4h-2v3H6v-3H4v4a1 1 0 0 0 1 1z'/>\
        <path fill='black' d='M12 3l5 5h-3v6h-4V8H7l5-5z'/>\
      </svg>") no-repeat center / contain;
              mask: url("data:image/svg+xml;utf8,\
      <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
        <path fill='black' d='M5 20h14a1 1 0 0 0 1-1v-4h-2v3H6v-3H4v4a1 1 0 0 0 1 1z'/>\
        <path fill='black' d='M12 3l5 5h-3v6h-4V8H7l5-5z'/>\
      </svg>") no-repeat center / contain;
    }
    .upload-pop { min-width: 640px; }
    .upload-pop [data-testid="stFileUploaderDropzone"]{
      width: 100% !important; min-width: 600px; padding-right: 200px;
    }
    </style>
    """, unsafe_allow_html=True)

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
            _sel = st.selectbox("Uploaded files", options=_names, index=_sel_ix, key="uploaded_files_select")
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

        st.markdown('</div>', unsafe_allow_html=True)  # close .upload-pop
    st.markdown('</div>', unsafe_allow_html=True)      # close .upload-trigger

st.divider()




import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path
from src.utils import ensure_journal_store, load_journal_index, create_journal, DATA_DIR
import json  # read/write sidecar metadata for notes/tags
import calendar as _cal
import plotly.graph_objects as go

# 👇 our modules
from src.io import load_trades, validate
from src.metrics import add_pnl



# ===================== SIDEBAR: Journals (UI only) =====================
ensure_journal_store()
with st.sidebar:
    # ===== Brand header =====
    BRAND = "Wavemark"  # <— change to taste

    st.markdown("""
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
    """, unsafe_allow_html=True)

    st.markdown(f'''
    <div class="brand-row">
    <div class="brand-name">{BRAND}<span class="brand-accent">.</span></div>
    <div class="brand-burger">≡</div>
    </div>
    ''', unsafe_allow_html=True)

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
        key="nav_radio"
    )
    st.session_state["nav"] = nav  # normalize key we use elsewhere

    # --- TradingView-like styling for the radio group + line icons ---
    st.markdown("""
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
    background: rgba(53,121,186,0.12);   /* brand tint */
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
    """, unsafe_allow_html=True)


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
if "_trade_notes" not in st.session_state:            # if key not present in the dict
    st.session_state["_trade_notes"] = {}             # {} creates an empty dictionary
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
        _journal_meta_path = Path(_rec["path"]).with_suffix(".meta.json")  # e.g., trades.csv -> trades.meta.json
        st.session_state["_journal_meta_path"] = str(_journal_meta_path)

        # Load once per run if present; guard with a flag
        if _journal_meta_path.exists() and not st.session_state.get("_meta_loaded"):
            try:
                with open(_journal_meta_path, "r", encoding="utf-8") as f:
                    _meta = json.load(f)  # { "notes": {idx: "..."}, "tags": {idx: "A"} }
                # merge into session stores; keys may come back as strings → cast to int
                st.session_state["_trade_notes"].update({int(k): v for k, v in _meta.get("notes", {}).items()})
                st.session_state["_trade_tags"].update({int(k): v for k, v in _meta.get("tags", {}).items()})
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
            "tags":  st.session_state.get("_trade_tags", {}),
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
    sides   = sorted(df["side"].dropna().unique().tolist())   if "side"   in df.columns else []

    sel_symbols = st.multiselect("Symbol", symbols, default=symbols if symbols else [])
    sel_sides   = st.multiselect("Side",   sides,   default=sides   if sides   else [])
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
        help="Quick grades you’ve applied to trades (A+, A, B, C)."
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
losses  = df.loc[df["pnl"] < 0, "pnl"]

profit_sum = float(profits.sum())                # ≥ 0
loss_sum   = float(losses.sum())                 # ≤ 0 or 0

profit_factor = (profit_sum / abs(loss_sum)) if loss_sum != 0 else float("inf")
avg_win       = float(profits.mean()) if len(profits) else 0.0
avg_loss      = float(losses.mean())  if len(losses)  else 0.0  # negative if any losses

# Expectancy per trade (uses avg_loss as negative)
win_rate_frac  = (win_rate / 100.0)
loss_rate_frac = 1.0 - win_rate_frac
expectancy     = win_rate_frac * avg_win + loss_rate_frac * avg_loss

# --- Equity curve + Drawdown from starting equity ---
df_ec = df.copy().reset_index(drop=True)
# use df_ec to compute trade_no, equity, peaks, etc.
df["trade_no"] = np.arange(1, len(df) + 1)
df["cum_pnl"] = df["pnl"].cumsum()
df["equity"] = start_equity + df["cum_pnl"]
df["equity_peak"] = df["equity"].cummax()
df["dd_abs"] = df["equity"] - df["equity_peak"]  # ≤ 0
df["dd_pct"] = np.where(df["equity_peak"] > 0, (df["equity"] / df["equity_peak"]) - 1.0, 0.0)

max_dd_abs = float(df["dd_abs"].min())            # most negative dollar drawdown
max_dd_pct = float(df["dd_pct"].min()) * 100.0    # most negative percent drawdown

# --- Current balance & Net PnL ---
current_balance = float(df["equity"].iloc[-1]) if len(df) else start_equity
net_pnl         = float(df["cum_pnl"].iloc[-1]) if len(df) else 0.0

def render_calendar_panel(df_view: pd.DataFrame, _date_col: str | None, month_start: pd.Timestamp):
    """Render the Calendar — Daily PnL & Trade Count panel in-place (no tabs)."""

    # === Begin: moved verbatim from your `with tab_calendar:` block (minus the first 2 header lines) ===

    # Guard
    if _date_col is None or _date_col not in df_view.columns or len(df_view) == 0:
        st.info("No date/timestamp column found — calendar view unavailable for this dataset.")
        return

    _month_start = pd.to_datetime(month_start).normalize().replace(day=1)
    _month_end   = (_month_start + pd.offsets.MonthEnd(1)).normalize()


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
    _daily_map = {row["_day"]: (float(row["NetPnL"]), int(row["Trades"])) for _, row in _daily_stats.iterrows()}

    # ---- Build calendar grid meta ----
    _first_weekday, _n_days = _cal.monthrange(_month_start.year, _month_start.month)  # Mon=0..Sun=6
    _leading = _first_weekday
    _total_slots = _leading + _n_days
    _rows = (_total_slots + 6) // 7  # ceil div by 7

    # ---------- THEME TOKENS ----------
    _panel_bg    = "#0b0f19"
    _cell_bg     = "#101621"
    _grid_line   = "#2a3444"
    _txt_main    = "#e5e7eb"
    _txt_muted   = "#9ca3af"
    _pnl_pos     = "#22c55e"
    _pnl_neg     = "#ef4444"
    _pnl_zero    = _txt_main
    _dash_accent = "#1f2937"
    _total_bg    = "#0d1320"
    _total_border= "#3a4557"
    _total_hdr   = "#cbd5e1"

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

    # weekday header (adds "Total" column)
    _weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Total"]
    for c, label in enumerate(_weekday_labels):
        annos.append(dict(
            x=c + 0.5, y=-0.35, xref="x", yref="y",
            text=label, showarrow=False,
            font=dict(size=12, color=_total_hdr if label == "Total" else _txt_muted),
            xanchor="center", yanchor="middle"
        ))

    # rounded outer container (8 columns wide incl. totals)
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
    shapes.append(dict(type="path", path=path, line=dict(color=_dash_accent, width=1.5),
                       fillcolor=_panel_bg, layer="below"))

    # cells (7 day columns + 1 total column)
    for r_idx in range(_rows):
        for c_idx in range(8):
            x0, x1 = c_idx, c_idx + 1
            y0, y1 = r_idx, r_idx + 1
            is_total_col = (c_idx == 7)

            shapes.append(dict(
                type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                line=dict(color=_total_border if is_total_col else _grid_line,
                          width=1.5 if is_total_col else 1),
                fillcolor=_total_bg if is_total_col else _cell_bg,
                layer="below"
            ))

            if not is_total_col:
                slot_idx = r_idx * 7 + c_idx
                if _slot_in_month(slot_idx):
                    d = _slot_to_date(slot_idx)
                    pnl_val, trade_ct = _daily_map.get(d, (0.0, 0))

                    # day number
                    annos.append(dict(
                        x=x0 + 0.08, y=y0 + 0.15, xref="x", yref="y",
                        text=str((slot_idx - _leading + 1)),
                        showarrow=False,
                        font=dict(size=12, color=_txt_muted),
                        xanchor="left", yanchor="top"
                    ))

                    # PnL (center)
                    if trade_ct == 0:
                        pnl_txt = "—"; pnl_col = _txt_muted
                    else:
                        pnl_txt = f"${pnl_val:,.0f}"
                        pnl_col = (_pnl_pos if pnl_val > 0 else (_pnl_neg if pnl_val < 0 else _pnl_zero))
                    annos.append(dict(
                        x=x0 + 0.5, y=y0 + 0.48, xref="x", yref="y",
                        text=pnl_txt, showarrow=False,
                        font=dict(size=16, color=pnl_col),
                        xanchor="center", yanchor="middle"
                    ))

                    # trades (below center)
                    trades_txt = "—" if trade_ct == 0 else (f"{trade_ct} trade" if trade_ct == 1 else f"{trade_ct} trades")
                    annos.append(dict(
                        x=x0 + 0.5, y=y0 + 0.78, xref="x", yref="y",
                        text=trades_txt, showarrow=False,
                        font=dict(size=11, color=_txt_muted),
                        xanchor="center", yanchor="top"
                    ))
            else:
                pnl_sum, trade_sum = week_totals[r_idx]
                # totals PnL
                if trade_sum == 0:
                    tot_pnl_txt = "—"; tot_pnl_col = _txt_muted
                else:
                    tot_pnl_txt = f"${pnl_sum:,.0f}"
                    tot_pnl_col = (_pnl_pos if pnl_sum > 0 else (_pnl_neg if pnl_sum < 0 else _pnl_zero))
                annos.append(dict(
                    x=x0 + 0.5, y=y0 + 0.48, xref="x", yref="y",
                    text=tot_pnl_txt, showarrow=False,
                    font=dict(size=16, color=tot_pnl_col),
                    xanchor="center", yanchor="middle"
                ))
                # totals trades
                tot_trades_txt = "—" if trade_sum == 0 else (f"{trade_sum} trade" if trade_sum == 1 else f"{trade_sum} trades")
                annos.append(dict(
                    x=x0 + 0.5, y=y0 + 0.78, xref="x", yref="y",
                    text=tot_trades_txt, showarrow=False,
                    font=dict(size=11, color=_txt_muted),
                    xanchor="center", yanchor="top"
                ))

    # Build figure
    fig_cal = go.Figure()
    fig_cal.update_layout(
        paper_bgcolor=_panel_bg,
        plot_bgcolor=_panel_bg,
        shapes=shapes,
        annotations=annos,
        xaxis=dict(range=[0, 8], showgrid=False, zeroline=False, tickmode="array", tickvals=[], ticktext=[], fixedrange=True),
        yaxis=dict(range=[_rows, -1], showgrid=False, zeroline=False, tickvals=[], ticktext=[], fixedrange=True),
        margin=dict(l=10, r=10, t=16, b=16),
    )
    _cal_h = int(160 + _rows * 120)
    fig_cal.update_layout(height=_cal_h)
    st.session_state["_cal_height"] = _cal_h


    _title = _month_start.strftime("%B %Y")
    st.markdown(f"### {_title}")
    st.plotly_chart(fig_cal, use_container_width=True)


    # # -------- Filter from Calendar --------
    # st.markdown("#### Filter from Calendar")

    # # A) Day filter
    # col_day, col_week, col_clear = st.columns([2, 2, 1])

    # with col_day:
    #     _day_pick = st.date_input(
    #         "Pick a day",
    #         value=_month_start.to_pydatetime(),
    #         min_value=_month_start.to_pydatetime(),
    #         max_value=_month_end.to_pydatetime(),
    #         key="cal_day_input"
    #     )
    #     if st.button("Apply Day Filter", use_container_width=True):
    #         st.session_state._cal_filter = ("day", pd.to_datetime(_day_pick).date())
    #         st.toast(f"Filtered to day: {pd.to_datetime(_day_pick).date()}")
    #         st.rerun()

    # def _week_start_for_row(r_idx: int):
    #     first_slot = r_idx * 7
    #     first_date = None
    #     for c_idx in range(7):
    #         d = _slot_to_date(first_slot + c_idx)
    #         if d is not None:
    #             first_date = pd.Timestamp(d)
    #             break
    #     if first_date is None:
    #         return None
    #     return (first_date - pd.Timedelta(days=first_date.weekday())).date()

    # _week_starts = []
    # for _r in range(_rows):
    #     ws = _week_start_for_row(_r)
    #     if ws is not None:
    #         _week_starts.append(ws)

    # with col_week:
    #     _week_ix = st.selectbox(
    #         "Pick a week",
    #         options=list(range(len(_week_starts))),
    #         format_func=lambda i: f"Week of {pd.Timestamp(_week_starts[i]).strftime('%b %d')}",
    #         key="cal_week_sel"
    #     )
    #     if st.button("Apply Week Filter", use_container_width=True):
    #         ws = pd.Timestamp(_week_starts[_week_ix]).date()
    #         we = (pd.Timestamp(ws) + pd.Timedelta(days=6)).date()
    #         ws = max(ws, _month_start.date())
    #         we = min(we, _month_end.date())
    #         st.session_state._cal_filter = ("week", (ws, we))
    #         st.toast(f"Filtered to week: {ws} → {we}")
    #         st.rerun()

    # with col_clear:
    #     if st.button("Clear Filter", use_container_width=True):
    #         st.session_state._cal_filter = None
    #         st.toast("Calendar filter cleared")
    #         st.rerun()

    # # === End moved code ===

def winrate_half_donut(wr: float, height: int = 110, hole: float = 0.72, half: str = "bottom"):
    """
    Horizontal half-donut (blue = wins, red = losses).
    `half`: "bottom" (default) or "top"
    """
    import plotly.graph_objects as go
    wr = max(0.0, min(1.0, float(wr)))

    # wins + losses fill one half; ghost hides the other half
    wins, losses, ghost = wr, 1.0 - wr, 1.0
    start = 270 if half.lower() == "bottom" else 90   # 180 = bottom half, 0 = top half

    fig = go.Figure(go.Pie(
        values=[wins, losses, ghost],    # keep this order
        hole=hole,
        rotation=start,                  # <- horizontal half control
        direction="clockwise",
        sort=False,                      # <- IMPORTANT so order doesn’t shuffle
        textinfo="none",
        hoverinfo="skip",
        marker=dict(
            colors=["#2E86C1", "#E57373", "rgba(0,0,0,0)"],
            line=dict(width=0),
        ),
        showlegend=False,
    ))
    fig.update_traces(domain=dict(x=[0, 1], y=[0, 1]))
    fig.update_layout(
        height=height,                   # lower height => looks wider
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
_possible_date_cols = ["date", "Date", "timestamp", "Timestamp", "time", "Time", "datetime", "Datetime", "entry_time", "exit_time"]
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
wins_mask_v   = pnl_v > 0
losses_mask_v = pnl_v < 0
bes_mask_v    = pnl_v == 0

wins_v   = int(wins_mask_v.sum())
losses_v = int(losses_mask_v.sum())
total_v  = int(len(df_view))

# Win-rate depends on your breakeven policy
if be_policy == "be excluded from win-rate":
    denom = wins_v + losses_v
    win_rate_v = wins_v / denom if denom > 0 else 0.0
elif be_policy == "count as losses":
    win_rate_v = wins_v / total_v if total_v > 0 else 0.0
else:  # "count as wins"
    win_rate_v = (wins_v + int(bes_mask_v.sum())) / total_v if total_v > 0 else 0.0

avg_win_v  = pnl_v[wins_mask_v].mean()  if wins_v   > 0 else 0.0
avg_loss_v = pnl_v[losses_mask_v].mean() if losses_v > 0 else 0.0  # negative if any losses
avg_win_loss_ratio_v = (abs(avg_win_v / avg_loss_v) if avg_loss_v != 0 else float("inf"))

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
_notes_map = st.session_state.get("_trade_notes", {})           # .get returns {} if missing
if len(_notes_map) > 0:
    # Make sure a 'note' column exists
    if "note" not in df.columns:
        df["note"] = ""
    # Update by original index keys
    for _idx, _txt in _notes_map.items():                       # .items() iterates (key, value)
        if _idx in df.index:                                    # guard against stale indices
            df.at[_idx, "note"] = _txt                          # .at is fast scalar setter
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

    # ======= LAYOUT FRAME: 40/60 main split (left=40%, right=60%) =======
    s_left, s_right = st.columns([2, 3], gap="large")  # 2:3 ≈ 40%:60%

    with s_left:
        # === Prep values used in these KPIs (Range-aware) ===
        gross_profit_v = float(pnl_v[wins_mask_v].sum())
        gross_loss_v   = float(pnl_v[losses_mask_v].sum())
        pf_v = (gross_profit_v / abs(gross_loss_v)) if gross_loss_v != 0 else float("inf")

        _side_dist_local = (
            df_view["side"].str.lower().value_counts(normalize=True)
                .reindex(["long", "short"]).fillna(0.0)
            if "side" in df_view.columns else pd.Series(dtype=float)
        )

        # === KPI GRID (2x2) ===
        kpi_row1 = st.columns([1, 1], gap="small")  # wider left card, smaller gap
        with kpi_row1[0]:
            with st.container(border=True):
                st.markdown('<div style="text-align:center; font-weight:600; margin:0 0 6px; transform: translateX(6px);">Win Rate</div>',
                            unsafe_allow_html=True)


                wr_pct = float(win_rate_v * 100.0)         # win_rate_v is 0..1
                win_color   = "#2E86C1"
                loss_color  = "#E57373"
                panel_bg    = "#0b0f19"                    # match your theme bg

                fig_win = go.Figure(go.Indicator(
                    mode="gauge",                          # no number, no needle
                    value=wr_pct,                          # where the bar would go (we’ll hide it)
                    gauge={
                        "shape": "angular",                # semicircle
                        "axis": {"range": [0, 100], "visible": False},
                        "bar": {"color": "rgba(0,0,0,0)"}, # hide the bar entirely
                        "borderwidth": 0,
                        # Two colored bands: wins then losses
                        "steps": [
                            {"range": [0, wr_pct],     "color": win_color},
                            {"range": [wr_pct, 100.0], "color": loss_color},
                        ],
                    },
                    domain={"x": [0, 1], "y": [0, 1]},
                ))

                # Size/spacing
                fig_win.update_layout(
                    margin=dict(l=8, r=8, t=6, b=0),
                    height=90,                            # bump this up/down to taste
                    paper_bgcolor=panel_bg,
                )
                # Put the % label in the middle of the visible half-donut
                fig_win.add_annotation(
                    x=0.5, y=0.10,            # center-ish of the lower half (paper coords)
                    xref="paper", yref="paper",
                    text=f"{wr_pct:.0f}%",
                    showarrow=False,
                    font=dict(size=30, color="#e5e7eb", family="Inter, system-ui, sans-serif"),
                    align="center"
                )

                st.plotly_chart(fig_win, use_container_width=True)



        with kpi_row1[1]:
            with st.container(border=True):
                st.markdown("**Avg Win / Avg Loss**")
                _aw_al = "∞" if avg_win_loss_ratio_v == float("inf") else f"{avg_win_loss_ratio_v:.2f}"
                st.metric(label="", value=_aw_al)

        kpi_row2 = st.columns(2, gap="medium")
        with kpi_row2[0]:
            with st.container(border=True):
                st.markdown("**Long vs Short**")
                if not _side_dist_local.empty:
                    fig_ls = px.pie(
                        values=_side_dist_local.values,
                        names=_side_dist_local.index.str.capitalize(),
                        hole=0.55,
                        color=_side_dist_local.index.str.capitalize(),
                        color_discrete_map={"Long": "#2E86C1", "Short": "#E57373"},
                    )
                    fig_ls.update_traces(textinfo="label+percent")
                    fig_ls.update_layout(height=180, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
                    st.plotly_chart(fig_ls, use_container_width=True)
                else:
                    st.caption("No side column found.")

        with kpi_row2[1]:
            with st.container(border=True):
                st.markdown("**Profit Factor**")
                _pf_disp = "∞" if pf_v == float("inf") else f"{pf_v:.2f}"
                st.metric(label="", value=_pf_disp)

        # === Equity Curve (bottom of s_left) — with tabs and date x-axis ===
        with st.container(border=True):
            st.markdown("""
            <style>
            /* Add a left-side caption in the same row as the tabs */
            div[data-testid="stTabs"] div[role="tablist"]::before{
            content: "Equity Curve";
            margin-right: auto;   /* keeps tabs on the right */
            color: #d5deed;
            font-weight: 600;
            letter-spacing: .2px;
            font-size:32px;        /* <-- adjust size here */
            }
            /* Tab list (container of the labels) */
            div[data-testid="stTabs"] div[role="tablist"]{
            justify-content: flex-end;
            gap: 6px;
            margin-top: 2px;
            }
            /* Individual tabs (the buttons) */
            div[data-testid="stTabs"] button[role="tab"]{
            padding: 4px 10px;
            }
            </style>
            """, unsafe_allow_html=True)


            # Build a date-indexed equity series from the current df_view (respects your sidebar Range)
            _has_date = (_date_col is not None and _date_col in df_view.columns and len(df_view) > 0)
            df_ec = df_view.copy()
            pnl_num = pd.to_numeric(df_ec["pnl"], errors="coerce").fillna(0.0)
            df_ec["cum_pnl"] = pnl_num.cumsum()
            df_ec["equity"]  = float(start_equity) + df_ec["cum_pnl"]

            if _has_date:
                _dt = pd.to_datetime(df_ec[_date_col], errors="coerce")
                df_ec = df_ec.assign(_date=_dt).sort_values("_date")
            else:
                # fallback to simple index if no date column exists
                df_ec = df_ec.reset_index(drop=True).assign(_date=pd.RangeIndex(start=0, stop=len(df_ec)))

            # Helper: filter by a trailing time window (relative to LAST visible date)
            def _slice_window(df_in: pd.DataFrame, label: str) -> pd.DataFrame:
                if not _has_date or len(df_in) == 0 or label == "All":
                    return df_in
                last_ts = pd.to_datetime(df_in["_date"].iloc[-1])
                if label == "1D":
                    start = last_ts - pd.Timedelta(days=1)
                elif label == "1W":
                    start = last_ts - pd.Timedelta(weeks=1)
                elif label == "1M":
                    start = last_ts - pd.DateOffset(months=1)
                elif label == "6M":
                    start = last_ts - pd.DateOffset(months=6)
                elif label == "1Y":
                    start = last_ts - pd.DateOffset(years=1)
                else:
                    start = df_in["_date"].min()
                return df_in[df_in["_date"] >= start]


            def _plot_equity(df_in: pd.DataFrame, *, height: int | None = None):
                import plotly.graph_objects as go

                x = df_in["_date"]
                y = pd.to_numeric(df_in["equity"], errors="coerce").astype(float)

                fig = go.Figure()

                # Invisible baseline at starting equity
                fig.add_scatter(
                    x=x,
                    y=[float(start_equity)] * len(df_in),
                    mode="lines",
                    line=dict(width=0),
                    hoverinfo="skip",
                    showlegend=False
                )

                # Equity line filled to the baseline (NOT to zero)
                fig.add_scatter(
                    x=x,
                    y=y,
                    mode="lines",
                    line=dict(width=2, color="#9ecbff"),
                    fill="tonexty",
                    fillcolor="rgba(53,121,186,0.18)",
                    hovertemplate=(
                        "%{x|%b %d, %Y}<br>Equity: $%{y:,.0f}<extra></extra>"
                        if _has_date else
                        "Trade %{x}<br>Equity: $%{y:,.0f}<extra></extra>"
                    ),
                    showlegend=False
                )

                # Height: reuse calendar height if present, else 240
                target_h = int(height) if height is not None else int(st.session_state.get("_cal_height", 240))

                # Y range anchored near starting equity with a little padding
                ymin = min(float(start_equity), float(np.nanmin(y)) if len(y) else float(start_equity))
                ymax = max(float(start_equity), float(np.nanmax(y)) if len(y) else float(start_equity))
                pad_low = max(30, (ymax - ymin) * 0.05)
                pad_high = max(30, (ymax - ymin) * 0.07)

                fig.update_layout(
                    height=target_h,
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="#0b0f19",
                    plot_bgcolor="#0b0f19",
                    showlegend=False,
                )

                if _has_date:
                    # Minimal, auto-spaced date ticks; formats change with zoom level
                    fig.update_xaxes(
                        type="date",
                        showgrid=False, zeroline=False, showspikes=False, automargin=True,
                        nticks=6,
                        tickformatstops=[
                            dict(dtickrange=[None, 1000*60*60*24*2],  value="%H:%M\n%b %d"),  # < 2 days
                            dict(dtickrange=[1000*60*60*24*2, 1000*60*60*24*14],  value="%b %d"),  # up to ~2w
                            dict(dtickrange=[1000*60*60*24*14, 1000*60*60*24*92], value="Wk %W"),  # ~2w..3m
                            dict(dtickrange=[1000*60*60*24*92,  1000*60*60*24*370], value="%b %Y"), # ~3m..1y
                            dict(dtickrange=[1000*60*60*24*370, None], value="%Y"),               # > 1y
                        ],
                    )
                else:
                    fig.update_xaxes(type="linear", showgrid=False, zeroline=False, automargin=True, nticks=6)

                fig.update_yaxes(
                    showgrid=False, zeroline=False, automargin=True,
                    tickprefix="$", separatethousands=True,
                    range=[ymin - pad_low, ymax + pad_high]
                )

                return fig


            # Tabs like your top-level tabs; default = All (first tab)
            st.markdown('<div class="eq-tabs">', unsafe_allow_html=True)
            eq_tabs = st.tabs(["All", "1D", "1W", "1M", "6M", "1Y"])

            for _label, _tab in zip(["All","1D","1W","1M","6M","1Y"], eq_tabs):
                with _tab:
                    _dfw = _slice_window(df_ec, _label)
                    if len(_dfw) == 0:
                        st.caption("No data in this window.")
                    else:
                        fig_eq = _plot_equity(_dfw, height=590)
                        st.plotly_chart(fig_eq, use_container_width=True)



    with s_right:
        # === Right column top row (split in 2) ===
        right_top = st.columns([2, 1], gap="medium")

        # Left side: Volume per Day chart
        with right_top[0]:
            with st.container(border=True):
                st.markdown("**Volume per Day (last ~20 trades)**")

                # --- Compute local _vol_per_day (independent of other sections) ---
                # 1) Determine notional per trade (qty*price, or 'notional', or |pnl| as fallback)
                _qty_cols   = [c for c in ["qty","quantity","size","contracts","amount"] if c in df_view.columns]
                _price_cols = [c for c in ["price","entry_price","avg_entry_price"] if c in df_view.columns]
                if _qty_cols and _price_cols:
                    _notional_local = (
                        pd.to_numeric(df_view[_qty_cols[0]], errors="coerce").fillna(0) *
                        pd.to_numeric(df_view[_price_cols[0]], errors="coerce").fillna(0)
                    ).abs()
                elif "notional" in df_view.columns:
                    _notional_local = pd.to_numeric(df_view["notional"], errors="coerce").fillna(0).abs()
                else:
                    _notional_local = pd.to_numeric(df_view["pnl"], errors="coerce").fillna(0).abs()

                # 2) Take the last ~20 trades within the current Range
                _last20_notional_local = _notional_local.tail(20).reset_index(drop=True)

                # 3) Group by day if we have a date column; else use simple indices
                if _date_col is not None and _date_col in df_view.columns:
                    _dt_view_local = pd.to_datetime(df_view[_date_col], errors="coerce")
                    _last20_days_local = _dt_view_local.tail(20).dt.date
                    _vol_per_day_local = (
                        pd.DataFrame({"day": _last20_days_local, "vol": _last20_notional_local})
                        .groupby("day", as_index=False)["vol"].sum()
                        .sort_values("day")
                    )
                    _x_col = "day"
                else:
                    _vol_per_day_local = pd.DataFrame(
                        {"idx": range(1, len(_last20_notional_local) + 1), "vol": _last20_notional_local}
                    )
                    _x_col = "idx"

                # 4) Build chart
                fig_vol = px.bar(_vol_per_day_local, x=_x_col, y="vol")
                fig_vol.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10))
                fig_vol.update_yaxes(tickprefix="$", separatethousands=True)
                st.plotly_chart(fig_vol, use_container_width=True)

        # Right side: Win Streak box
        with right_top[1]:
            with st.container(border=True):
                st.markdown("**Win Streak**")
                # Simple vertical metrics (avoid nested columns restriction)
                st.metric("Days 🔥", "33")
                st.metric("Trades 🔥", "19")

        # --- Right column bottom: Calendar panel ---
        with st.container(border=True):
            render_calendar_panel(df_view, _date_col, st.session_state["_cal_month_start"])


    # ======= END LAYOUT FRAME =======

    # ===================== CHARTS (card layout) =====================
    # tiny filter icon button (Material icon if supported; emoji fallback otherwise)
    _, btn_col = st.columns([8, 1], gap="small")
    with btn_col:
        clicked = False
        try:
            # Streamlit ≥ ~1.32 supports the `icon` kwarg and Material shortcodes
            clicked = st.button("Filters", key="filters_btn", icon=":material/filter_list:", use_container_width=True)
        except TypeError:
            # Older Streamlit: no `icon` kwarg → use emoji label instead
            clicked = st.button("🔎 Filters", key="filters_btn", use_container_width=True)

        if clicked:
            # For now, just nudge the user; later we can open a popover
            st.toast("Filters are in the left sidebar.")
            st.session_state["_filters_prompted"] = True

    st.subheader("Overview")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Win Rate", f"{win_rate_v*100:.1f}%")
    with c2:
        st.metric("Daily Win Rate", _daily_wr_display)
    with c3:
        st.metric("Avg Win / Avg Loss", "∞" if avg_win_loss_ratio_v == float("inf") else f"{avg_win_loss_ratio_v:.2f}")
    with c4:
        st.metric("Trade Count", f"{total_v}")

    st.divider()

    st.subheader("Charts")

    left, right = st.columns([3, 2], gap="large")

    # ===================== CHART HELPERS (assets, sides, volume & pnl windows) [timeframe-aware] =====================
    # We already computed df_view and _date_col above for the Overview cards.
    _dt_view = pd.to_datetime(df_view[_date_col], errors="coerce") if (_date_col is not None and _date_col in df_view.columns) else None

    # 1) Distribution by asset (symbol) and side (long/short)
    _symbol_dist = (
        df_view["symbol"].value_counts(normalize=True).sort_values(ascending=False)
        if "symbol" in df_view.columns else pd.Series(dtype=float)
    )
    _side_dist = (
        df_view["side"].str.lower().value_counts(normalize=True).reindex(["long", "short"]).fillna(0.0)
        if "side" in df_view.columns else pd.Series(dtype=float)
    )

    # 2) Dollar notional per trade (try qty*price, else 'notional', else |PnL|)
    _qty_cols   = [c for c in ["qty","quantity","size","contracts","amount"] if c in df_view.columns]
    _price_cols = [c for c in ["price","entry_price","avg_entry_price"] if c in df_view.columns]
    if _qty_cols and _price_cols:
        _notional = (pd.to_numeric(df_view[_qty_cols[0]], errors="coerce").fillna(0) *
                    pd.to_numeric(df_view[_price_cols[0]], errors="coerce").fillna(0)).abs()
    elif "notional" in df_view.columns:
        _notional = pd.to_numeric(df_view["notional"], errors="coerce").fillna(0).abs()
    else:
        _notional = pd.to_numeric(df_view["pnl"], errors="coerce").fillna(0).abs()  # fallback

    # 3) Windows for “last 20 trades” (by row order) in the selected timeframe
    _last20_view = df_view.tail(20).copy()
    _last20_notional = _notional.tail(20).reset_index(drop=True)
    _last20_pnl = pd.to_numeric(_last20_view["pnl"], errors="coerce").fillna(0).reset_index(drop=True)

    # 4) Volume per DAY (from last ~20 trades) in the selected timeframe
    if _dt_view is not None:
        _last20_days = _dt_view.tail(20).dt.date
        _vol_per_day = (
            pd.DataFrame({"day": _last20_days, "vol": _last20_notional})
            .groupby("day", as_index=False)["vol"].sum()
            .sort_values("day")
        )
    else:
        _vol_per_day = pd.DataFrame(
            {"day": [f"T-{i}" for i in range(len(_last20_notional),0,-1)][::-1],
            "vol": _last20_notional}
        )

    # --- Right column: Wheel charts + Bars ---
    with right:
        # Top row: two "wheel" charts (asset distribution, long vs short)
        w1, w2 = st.columns(2)
        with w1:
            st.markdown("#### Assets")
            if not _symbol_dist.empty:
                fig_sym = px.pie(
                    values=_symbol_dist.values,
                    names=_symbol_dist.index,
                    hole=0.55,
                )
                fig_sym.update_traces(textinfo="label+percent")  # <— add this
                fig_sym.update_layout(
                    height=220,
                    margin=dict(l=10, r=10, t=10, b=10),
                    showlegend=True,
                    legend=dict(orientation="v", y=0.5, x=1.05)  # vertical, right side
                )

                st.plotly_chart(fig_sym, use_container_width=True)
            else:
                st.caption("No symbol column found.")

        with w2:
            st.markdown("#### Long vs Short")
            if not _side_dist.empty:
                fig_side = px.pie(
                    values=_side_dist.values,
                    names=_side_dist.index.str.capitalize(),
                    hole=0.55,
                    color=_side_dist.index.str.capitalize(),
                    color_discrete_map={"Long": "#2E86C1", "Short": "#E57373"},  # blue / subtle red
                )
                fig_side.update_traces(textinfo="label+percent")
                fig_side.update_layout(
                    height=220,
                    margin=dict(l=10, r=10, t=10, b=10),
                    showlegend=True,
                    legend=dict(orientation="v", y=0.5, x=1.05)
                )

                st.plotly_chart(fig_side, use_container_width=True)
            else:
                st.caption("No side column found.")

        st.divider()

        # Middle card: Dollar Volume per Day (from last ~20 trades)
        with st.container():
            st.markdown("#### Volume per Day (last ~20 trades)")
            fig_vol = px.bar(
                _vol_per_day,
                x=_vol_per_day.columns[0],  # day
                y="vol",
            )
            fig_vol.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10))
            fig_vol.update_yaxes(tickprefix="$", separatethousands=True)
            st.plotly_chart(fig_vol, use_container_width=True)

        st.divider()

        # Bottom card: PnL per trade (last 20 trades) with green/red around zero
        with st.container():
            st.markdown("#### PnL (last 20 trades)")
            _pnl_df = pd.DataFrame({
                "n": range(1, len(_last20_pnl)+1),
                "pnl": _last20_pnl,
                "sign": np.where(_last20_pnl >= 0, "Win", "Loss"),
            })
            fig_pnl = px.bar(
                _pnl_df,
                x="n",
                y="pnl",
                color="sign",
                color_discrete_map={"Win": "#26a269", "Loss": "#e05252"},  # green/red
            )
            # zero line + compact styling
            fig_pnl.add_hline(y=0, line_width=1, line_dash="dot", opacity=0.6)
            fig_pnl.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
            fig_pnl.update_yaxes(tickprefix="$", separatethousands=True)
            st.plotly_chart(fig_pnl, use_container_width=True)


with tab_perf:
    render_active_filters("perf")
    st.subheader("Performance KPIs")
    st.caption(f"Using Range: **{tf}**")


    # --- Prepare series on df_view (timeframe-aware) ---
    pnl_tf = pd.to_numeric(df_view["pnl"], errors="coerce").fillna(0.0)
    wins_m = pnl_tf > 0
    loss_m = pnl_tf < 0
    be_m   = pnl_tf == 0

    gross_profit = float(pnl_tf[wins_m].sum())
    gross_loss   = float(pnl_tf[loss_m].sum())   # negative or 0
    net_profit   = float(pnl_tf.sum())

    largest_win  = float(pnl_tf[wins_m].max()) if wins_m.any() else 0.0
    largest_loss = float(pnl_tf[loss_m].min()) if loss_m.any() else 0.0  # most negative

    win_count    = int(wins_m.sum())
    loss_count   = int(loss_m.sum())
    be_count     = int(be_m.sum())
    total_count  = int(len(pnl_tf))

    # Win/Loss count ratio (avoid div by zero)
    wl_count_ratio = (win_count / loss_count) if loss_count > 0 else float("inf")

    # Profit Factor in timeframe
    pf_tf = (gross_profit / abs(gross_loss)) if gross_loss != 0 else float("inf")

    # Commission (if present)
    _fee_cols = [c for c in ["commission","fee","fees","commissions"] if c in df_view.columns]
    commission_paid = float(pd.to_numeric(df_view[_fee_cols[0]], errors="coerce").fillna(0.0).sum()) if _fee_cols else 0.0

    # --- Timeframe-aware risk KPIs ---
    # Equity over df_view so DD and balance match the selected Range
    dfv_perf = df_view.copy().reset_index(drop=True)
    dfv_perf["trade_no"] = np.arange(1, len(dfv_perf) + 1)
    dfv_perf["cum_pnl"]  = pd.to_numeric(dfv_perf["pnl"], errors="coerce").fillna(0).cumsum()
    dfv_perf["equity"]   = start_equity + dfv_perf["cum_pnl"]
    dfv_perf["peak"]     = dfv_perf["equity"].cummax()

    max_dd_abs_tf = float((dfv_perf["equity"] - dfv_perf["peak"]).min()) if len(dfv_perf) else 0.0  # ≤ 0
    max_dd_pct_tf = float(((dfv_perf["equity"] / dfv_perf["peak"]) - 1.0).min() * 100.0) if len(dfv_perf) and (dfv_perf["peak"] > 0).any() else 0.0
    current_balance_tf = float(dfv_perf["equity"].iloc[-1]) if len(dfv_perf) else start_equity

    # Expectancy per trade within the selected Range (reuse win_rate_v / avg_win_v / avg_loss_v from Overview calc)
    win_rate_frac_v  = float(win_rate_v)  # win_rate_v is already in [0..1]
    loss_rate_frac_v = 1.0 - win_rate_frac_v
    expectancy_v     = (win_rate_frac_v * float(avg_win_v)) + (loss_rate_frac_v * float(avg_loss_v))

    # --- KPI row ---
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Gross Profit", f"${gross_profit:,.2f}")
    k2.metric("Gross Loss", f"${gross_loss:,.2f}")
    k3.metric("Net Profit", f"${net_profit:,.2f}")
    k4.metric("Profit Factor", "∞" if pf_tf == float("inf") else f"{pf_tf:.2f}")

    k5, k6, k7, k8 = st.columns(4)
    k5.metric("Largest Win", f"${largest_win:,.2f}")
    k6.metric("Largest Loss", f"${largest_loss:,.2f}")
    k7.metric("Win/Loss (count)", "∞" if wl_count_ratio == float("inf") else f"{wl_count_ratio:.2f}")
    k8.metric("Commission Paid", f"${commission_paid:,.2f}")

    k9, k10, k11 = st.columns(3)
    k9.metric("Max Drawdown % (Range)", f"{max_dd_pct_tf:.2f}%")
    k10.metric("Current Balance (Range)", f"${current_balance_tf:,.2f}")
    k11.metric("Expectancy / Trade", f"${expectancy_v:,.2f}")
    # --- Additional Risk KPIs (timeframe-aware) ---
    _p_tf = pd.to_numeric(df_view["pnl"], errors="coerce").fillna(0.0)
    _eq = start_equity + _p_tf.cumsum()
    _peak = _eq.cummax()
    _dd_abs_series = _eq - _peak  # ≤ 0 in $
    _dd_pct_series = np.where(_peak > 0, (_eq / _peak) - 1.0, 0.0)

    def _longest_run(mask: np.ndarray) -> int:
        longest = cur = 0
        for v in mask:
            if v:
                cur += 1
                if cur > longest:
                    longest = cur
            else:
                cur = 0
        return int(longest)

    _max_dd_abs_usd = float(_dd_abs_series.min()) if len(_dd_abs_series) else 0.0  # negative or 0
    _max_dd_duration_trades = _longest_run(_dd_pct_series < 0) if len(_dd_pct_series) else 0
    _longest_losing_streak = _longest_run(_p_tf.values < 0) if len(_p_tf) else 0

    r1, r2, r3 = st.columns(3)
    r1.metric("Max DD ($)", f"${_max_dd_abs_usd:,.0f}")
    r2.metric("Max DD Duration", f"{_max_dd_duration_trades} trades")
    r3.metric("Longest Losing Streak", f"{_longest_losing_streak} trades")

    st.divider()

    # -------- Daily Net PnL (timeframe-aware) --------
    st.markdown("#### Daily Net PnL")
    if _date_col is not None and _date_col in df_view.columns and len(df_view) > 0:
        _d = pd.to_datetime(df_view[_date_col], errors="coerce")
        _daily = (
            pd.DataFrame({
                "day": _d.dt.date,
                "pnl": pd.to_numeric(df_view["pnl"], errors="coerce").fillna(0.0),
            })
            .groupby("day", as_index=False)["pnl"].sum()
            .sort_values("day")
        )

        fig_daily = px.bar(
            _daily,
            x="day",
            y="pnl",
            title=None,
            labels={"day": "Day", "pnl": "Net PnL ($)"},
        )
        # zero line + compact styling
        fig_daily.add_hline(y=0, line_width=1, line_dash="dot", opacity=0.6)
        fig_daily.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
        fig_daily.update_yaxes(tickprefix="$", separatethousands=True)
        st.plotly_chart(fig_daily, use_container_width=True)
    else:
        st.caption("No date/timestamp column found — Daily Net PnL is unavailable for this dataset.")

    st.divider()

    # -------- Export filtered trades --------
    st.markdown("#### Export")
    _export_df = df_view.copy()
    # Optional: reorder common columns if present
    _preferred_cols = [c for c in ["datetime","date","timestamp","symbol","side","qty","price","pnl","commission","fees","tag","note"] if c in _export_df.columns]
    _export_df = _export_df[_preferred_cols + [c for c in _export_df.columns if c not in _preferred_cols]]

    _fname_tf = tf.lower().replace(" ", "_")  # all / this_week / this_month / this_year
    _fname = f"trades_filtered_{_fname_tf}.csv"

    _csv = _export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⤓ Download filtered trades (CSV)",
        data=_csv,
        file_name=_fname,
        mime="text/csv",
        use_container_width=True,
    )
    # -------- Notes (per trade) — Journal QoL --------
st.markdown("#### Notes (per trade)")
if len(df_view) == 0:
    st.caption("No rows to annotate.")
else:
    # Build human-friendly chooser; preserve original indices
    _dv = df_view.copy()
    _date_lbl = None
    if _date_col is not None and _date_col in _dv.columns:
        _date_lbl = pd.to_datetime(_dv[_date_col], errors="coerce").dt.strftime("%Y-%m-%d")
    else:
        _date_lbl = pd.Series(["—"] * len(_dv), index=_dv.index)

    _sym_lbl  = _dv["symbol"].astype(str) if "symbol" in _dv.columns else pd.Series(["—"] * len(_dv), index=_dv.index)
    _side_lbl = _dv["side"].astype(str)   if "side"   in _dv.columns else pd.Series(["—"] * len(_dv), index=_dv.index)
    _pnl_lbl  = pd.to_numeric(_dv["pnl"], errors="coerce").fillna(0.0)

    _options = []
    for _i in _dv.index:  # original index label
        _label = f"[{_i}] {_date_lbl.loc[_i]} · {_sym_lbl.loc[_i]} · {_side_lbl.loc[_i]} · ${_pnl_lbl.loc[_i]:,.0f}"
        _options.append((_label, _i))

    _labels = [t[0] for t in _options]
    _values = [t[1] for t in _options]

    _sel = st.selectbox(
        "Pick a trade to annotate",
        options=list(range(len(_labels))),
        format_func=lambda k: _labels[k],
        key="note_sel_idx",
    )
    _sel_index = _values[_sel]

    _prefill = st.session_state["_trade_notes"].get(_sel_index, "")
    if _prefill == "" and "note" in df.columns:
        _prefill = str(df.loc[_sel_index, "note"]) if pd.notna(df.loc[_sel_index, "note"]) else ""

    _note_txt = st.text_area(
        "Note",
        value=_prefill,
        height=100,
        placeholder="What did you see or learn on this trade? Execution, context, emotions, setup quality…"
    )

    cols = st.columns([1,1,6])
    with cols[0]:
        if st.button("💾 Save note", use_container_width=True):
            st.session_state["_trade_notes"][_sel_index] = _note_txt
            _persist_journal_meta()  # persist for journals
            st.toast(f"Note saved for trade index [{_sel_index}]")
            st.rerun()
    with cols[1]:
        if st.button("🗑️ Clear note", use_container_width=True):
            st.session_state["_trade_notes"].pop(_sel_index, None)
            _persist_journal_meta()  # persist for journals
            st.toast(f"Note cleared for [{_sel_index}]")
            st.rerun()

    st.markdown("#### Quick Tags")
    _tag_options = ["A+", "A", "B", "C"]
    _current_tag = st.session_state["_trade_tags"].get(
        _sel_index, df.loc[_sel_index, "tag"] if "tag" in df.columns else ""
    )
    _tag_choice = st.radio(
        "Select a tag for this trade",
        options=_tag_options + ["(clear)"],
        index=(_tag_options + ["(clear)"]).index(_current_tag) if _current_tag in (_tag_options + ["(clear)"]) else len(_tag_options),
        horizontal=True
    )

    tcols = st.columns([1,1,6])
    with tcols[0]:
        if st.button("🏷️ Save tag", use_container_width=True):
            if _tag_choice == "(clear)":
                st.session_state["_trade_tags"].pop(_sel_index, None)
                if "tag" in df.columns:
                    df.at[_sel_index, "tag"] = ""
            else:
                st.session_state["_trade_tags"][_sel_index] = _tag_choice
                if "tag" not in df.columns:
                    df["tag"] = ""
                df.at[_sel_index, "tag"] = _tag_choice
            _persist_journal_meta()  # persist for journals
            st.toast(f"Tag saved for trade index [{_sel_index}]")
            st.rerun()
    with tcols[1]:
        if st.button("🗑️ Clear tag", use_container_width=True):
            st.session_state["_trade_tags"].pop(_sel_index, None)
            if "tag" in df.columns:
                df.at[_sel_index, "tag"] = ""
            _persist_journal_meta()  # persist for journals
            st.toast(f"Tag cleared for [{_sel_index}]")
            st.rerun()

# ======= BELOW ARE SIBLINGS OF NOTES (dedented one level), STILL INSIDE with tab_perf: =======

st.divider()
st.subheader("Breakdown")

def _group_metrics(group_df: pd.DataFrame) -> pd.Series:
    _p = pd.to_numeric(group_df["pnl"], errors="coerce").fillna(0.0)
    _wins = (_p > 0)
    _loss = (_p < 0)
    _be   = (_p == 0)
    _w = int(_wins.sum()); _l = int(_loss.sum()); _b = int(_be.sum())
    _tot = int(len(_p))

    # win-rate with your breakeven policy
    if be_policy == "be excluded from win-rate":
        denom = _w + _l
        wr = (_w / denom) * 100.0 if denom > 0 else 0.0
    elif be_policy == "count as losses":
        wr = (_w / _tot) * 100.0 if _tot > 0 else 0.0
    else:  # count as wins
        wr = ((_w + _b) / _tot) * 100.0 if _tot > 0 else 0.0

    gp = float(_p[_wins].sum())
    gl = float(_p[_loss].sum())
    pf = (gp / abs(gl)) if gl != 0 else float("inf")
    avg_w = float(_p[_wins].mean()) if _w > 0 else 0.0
    avg_l = float(_p[_loss].mean()) if _l > 0 else 0.0
    aw_al = (abs(avg_w / avg_l) if avg_l != 0 else float("inf"))

    return pd.Series({
        "Trades": _tot,
        "Win Rate %": round(wr, 1),
        "PF": (float("inf") if pf == float("inf") else round(pf, 2)),
        "Net PnL": round(float(_p.sum()), 2),
        "Avg Win/Loss": ("∞" if aw_al == float("inf") else round(aw_al, 2)),
    })

# Per-Symbol
if "symbol" in df_view.columns:
    sym_tbl = df_view.groupby("symbol", dropna=True).apply(_group_metrics).reset_index().sort_values("Net PnL", ascending=False)
    st.markdown("**Per Symbol**")
    st.dataframe(sym_tbl, use_container_width=True)
else:
    st.caption("No `symbol` column found for per-symbol breakdown.")

st.divider()

# Per-Side
if "side" in df_view.columns:
    side_tbl = df_view.assign(_side=df_view["side"].str.lower()).groupby("_side", dropna=True).apply(_group_metrics).reset_index()
    side_tbl["_side"] = side_tbl["_side"].str.capitalize()
    side_tbl = side_tbl.rename(columns={"_side": "Side"}).sort_values("Net PnL", ascending=False)
    st.markdown("**Per Side**")
    st.dataframe(side_tbl, use_container_width=True)
else:
    st.caption("No `side` column found for per-side breakdown.")

# -------- One-click Summary Report (Markdown + JSON) --------
st.divider()
st.markdown("#### Summary Report (current Range)")

# Gather quick stats from df_view
_p = pd.to_numeric(df_view["pnl"], errors="coerce").fillna(0.0)
_total = int(len(_p))
_wr = ( (_p > 0).mean() * 100.0 ) if _total > 0 else 0.0
_gp = float(_p[_p > 0].sum()); _gl = float(_p[_p < 0].sum()); _np = float(_p.sum())
_pf = ( _gp / abs(_gl) ) if _gl != 0 else float("inf")

_best = float(_p.max()) if _total > 0 else 0.0
_worst = float(_p.min()) if _total > 0 else 0.0

# Time-aware drawdown for this Range (reusing approach from Performance risk KPIs)
_eq = start_equity + _p.cumsum()
_peak = _eq.cummax()
_dd_pct_series = np.where(_peak > 0, (_eq / _peak) - 1.0, 0.0) * 100.0
_max_dd_pct_report = float(_dd_pct_series.min()) if _total > 0 else 0.0

# Top symbols by Net PnL (if symbol column present)
_top_sym_lines = []
if "symbol" in df_view.columns:
    _by_sym = (
        df_view.assign(_p=_p)
            .groupby("symbol", dropna=True)["_p"]
            .sum()
            .sort_values(ascending=False)
            .head(3)
    )
    for s, v in _by_sym.items():
        _top_sym_lines.append(f"- {s}: ${v:,.0f}")
else:
    _top_sym_lines.append("- (no symbol column)")

# Last 3 notes (if any and if note column exists)
_note_lines = []
if "note" in df_view.columns:
    _notes_nonempty = df_view.loc[df_view["note"].astype(str).str.strip() != ""]
    if len(_notes_nonempty) > 0:
        _last_notes = _notes_nonempty.tail(3)[["note"]].astype(str)["note"].tolist()
        for n in _last_notes:
            _note_lines.append(f"- {n[:200]}")
    else:
        _note_lines.append("- (no notes in current Range)")
else:
    _note_lines.append("- (no note column)")

# Tag mix (if any tags present)
_tag_lines = []
if "tag" in df_view.columns:
    _tag_counts = (
        df_view["tag"].astype(str).str.strip()
        .replace("", np.nan)
        .dropna()
        .value_counts()
        .reindex(["A+","A","B","C"])
        .fillna(0)
        .astype(int)
    )
    if _tag_counts.sum() > 0:
        for tg, ct in _tag_counts.items():
            _tag_lines.append(f"- {tg}: {ct}")
    else:
        _tag_lines.append("- (no tags in current Range)")
else:
    _tag_lines.append("- (no tag column)")

# Build markdown
_report_md = f"""# Trading Summary — {tf}

**Range:** {tf}  
**Trades:** {_total}  
**Win Rate:** {_wr:.1f}%  
**Net Profit:** ${_np:,.0f}  
**Profit Factor:** {"∞" if _pf == float("inf") else f"{_pf:.2f}"}  
**Max Drawdown (Range):** {_max_dd_pct_report:.2f}%

## Top Symbols
{chr(10).join(_top_sym_lines)}

## Best / Worst Trade
- Best: ${_best:,.0f}  
- Worst: ${_worst:,.0f}

## Tag Mix
{chr(10).join(_tag_lines)}

## Recent Notes
{chr(10).join(_note_lines)}
"""

st.code(_report_md, language="markdown")

from datetime import datetime as _dt
_fname_rep = f"summary_{tf.lower().replace(' ','_')}_{_dt.now().strftime('%Y%m%d_%H%M%S')}.md"
st.download_button(
    "⬇️ Download Summary (Markdown)",
    data=_report_md.encode("utf-8"),
    file_name=_fname_rep,
    mime="text/markdown",
    use_container_width=True
)

# ---- JSON Summary (machine-readable) ----
def _parse_money(s: str) -> float:
    s = s.replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except Exception:
        return 0.0

_top_symbols_json = []
for line in _top_sym_lines:
    line = line.strip().lstrip("-").strip()
    if ": " in line:
        sym, val = line.split(": ", 1)
        _top_symbols_json.append({"symbol": sym, "net_pnl": _parse_money(val)})

_tag_mix_json = {}
for line in _tag_lines:
    line = line.strip().lstrip("-").strip()
    if ": " in line:
        tg, ct = line.split(": ", 1)
        try:
            _tag_mix_json[tg] = int(ct)
        except Exception:
            pass

_json_payload = {
    "range": tf,
    "generated_at": _dt.now().isoformat(timespec="seconds"),
    "trades": {
        "count": _total,
        "win_rate_pct": round(_wr, 2),
        "gross_profit": round(_gp, 2),
        "gross_loss": round(_gl, 2),
        "net_profit": round(_np, 2),
        "profit_factor": (None if _pf == float("inf") else round(_pf, 4)),
        "best_trade": round(_best, 2),
        "worst_trade": round(_worst, 2)
    },
    "risk": {
        "max_drawdown_pct": round(_max_dd_pct_report, 2)
    },
    "top_symbols": _top_symbols_json,
    "tag_mix": _tag_mix_json,
    "recent_notes": [n.lstrip("- ").strip() for n in _note_lines]
}

st.code(json.dumps(_json_payload, ensure_ascii=False, indent=2), language="json")

_fname_json = f"summary_{tf.lower().replace(' ','_')}_{_dt.now().strftime('%Y%m%d_%H%M%S')}.json"
st.download_button(
    "⬇️ Download Summary (JSON)",
    data=json.dumps(_json_payload, ensure_ascii=False, indent=2).encode("utf-8"),
    file_name=_fname_json,
    mime="application/json",
    use_container_width=True
)

# -------- Underwater (Drawdown %) [timeframe-aware] --------
st.divider()
st.markdown("#### Underwater (Drawdown %)")

# Build equity from df_view so this respects Range + Calendar filter
_p = pd.to_numeric(df_view["pnl"], errors="coerce").fillna(0.0)
_dfu = df_view.copy().reset_index(drop=True)
_dfu["trade_no"] = np.arange(1, len(_dfu) + 1)
_dfu["cum_pnl"]  = _p.cumsum()
_dfu["equity"]   = start_equity + _dfu["cum_pnl"]
_dfu["peak"]     = _dfu["equity"].cummax()
_dfu["dd_pct"]   = np.where(_dfu["peak"] > 0, (_dfu["equity"] / _dfu["peak"]) - 1.0, 0.0) * 100.0  # ≤ 0

# Current DD badge (uses last row)
_current_dd_pct = float(_dfu["dd_pct"].iloc[-1])  # last drawdown % (negative or 0)
_current_dd_abs = float((_dfu["equity"] - _dfu["peak"]).iloc[-1])  # last DD in $ (≤ 0)
st.caption(f"Current DD: **{_current_dd_pct:.2f}%**  (${_current_dd_abs:,.0f})")

if len(_dfu) > 0:
    # Extra fields for hover
    _dfu["dd_abs"] = _dfu["equity"] - _dfu["peak"]  # drawdown in $ (≤ 0)
    if _date_col is not None and _date_col in df_view.columns:
        _dfu["_date"] = pd.to_datetime(df_view[_date_col], errors="coerce").dt.strftime("%Y-%m-%d")
    else:
        _dfu["_date"] = ""

    # Range-aware chips
    _max_dd_pct_chip = float(_dfu["dd_pct"].min())
    _current_dd_pct_chip = float(_dfu["dd_pct"].iloc[-1])

    _idx_min_chip = int(_dfu["dd_pct"].idxmin())
    _recovered_chip = (_dfu.loc[_idx_min_chip + 1:, "dd_pct"] >= -1e-9).any()

    c_max, c_cur, c_rec = st.columns(3)
    with c_max: st.caption(f"**Max DD**: { _max_dd_pct_chip:.2f}%")
    with c_cur: st.caption(f"**Current DD**: { _current_dd_pct_chip:.2f}%")
    with c_rec: st.caption(f"**Recovered**: {'Yes ✅' if _recovered_chip else 'No ❌'}")

    fig_dd = px.area(
        _dfu,
        x="trade_no",
        y="dd_pct",
        title=None,
        labels={"trade_no": "Trade #", "dd_pct": "Drawdown (%)"},
        custom_data=["dd_abs", "equity", "peak", "_date"]
    )
    fig_dd.update_traces(
        hovertemplate=(
            "Trade #%{x}<br>"
            "Date: %{customdata[3]}<br>"
            "Drawdown: %{y:.2f}%<br>"
            "DD ($): $%{customdata[0]:,.0f}<br>"
            "Equity: $%{customdata[1]:,.0f}<br>"
            "Peak: $%{customdata[2]:,.0f}<extra></extra>"
        ),
        showlegend=False
    )
    min_dd = float(_dfu["dd_pct"].min()) if len(_dfu) else 0.0
    y_floor = min(-1.0, min_dd * 1.10)
    fig_dd.update_yaxes(range=[y_floor, 0], ticksuffix="%", separatethousands=True)
    fig_dd.add_hline(y=0, line_width=1, line_dash="dot", opacity=0.6)
    fig_dd.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10))

    _show_vline = st.checkbox("Show Max DD vertical line", value=True, key="uw_show_maxdd_vline")
    _show_persistent = st.checkbox("Show Max DD label", value=True, key="uw_show_maxdd_label")

    _idx_min = int(_dfu["dd_pct"].idxmin())
    _x_trade = int(_dfu.loc[_idx_min, "trade_no"])
    _y_ddpct = float(_dfu.loc[_idx_min, "dd_pct"])
    _dd_abs_v = float(_dfu.loc[_idx_min, "dd_abs"])
    _date_str = str(_dfu.loc[_idx_min, "_date"]) if "_date" in _dfu.columns else ""

    _pre_slice = _dfu.loc[:_idx_min]
    _peak_idx  = int(_pre_slice["equity"].idxmax())
    _since_peak_trades = int(_x_trade - int(_dfu.loc[_peak_idx, "trade_no"]))

    _recover_slice = _dfu.loc[_idx_min + 1:, "dd_pct"]
    _recovered_mask = _recover_slice >= -1e-9
    _recover_idx = _recovered_mask.index[_recovered_mask.argmax()] if _recovered_mask.any() else None
    if _recover_idx is not None:
        _trades_to_recover = int(_dfu.loc[_recover_idx, "trade_no"] - _x_trade)
        _recover_msg = f"Recovered from Max DD in **{_trades_to_recover} trades**."
    else:
        _recover_msg = "Not yet recovered from Max DD."

    fig_dd.add_scatter(
        x=[_x_trade], y=[_y_ddpct],
        mode="markers",
        marker=dict(size=8, color="#ef4444"),
        name="Max DD",
        hovertemplate=(
            "Trade #%{x}<br>"
            "Date: " + (_date_str if _date_str else "%{x}") + "<br>"
            "Drawdown: %{y:.2f}%<br>"
            f"Since peak: {_since_peak_trades} trades"
            "<extra>Max DD point</extra>"
        )
    )

    if _show_persistent:
        fig_dd.add_annotation(
            x=_x_trade, y=_y_ddpct,
            text=f"Max DD { _y_ddpct:.2f}% (${'{:,.0f}'.format(_dd_abs_v)})",
            showarrow=True, arrowhead=2,
            ax=0, ay=-40,
            bgcolor="rgba(16,22,33,0.7)",
            bordercolor="#2a3444",
            font=dict(size=11, color="#e5e7eb")
        )
    if _show_vline:
        fig_dd.add_vline(
            x=_x_trade,
            line_width=1,
            line_dash="dash",
            line_color="#ef4444",
            opacity=0.6
        )

    st.plotly_chart(fig_dd, use_container_width=True)
    st.caption(_recover_msg)
else:
    st.caption("No rows available in the current Range to compute drawdown.")


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
            "Select a month",
            value=_default_month.to_pydatetime(),
            format="YYYY-MM-DD"
        )
        _picked = pd.to_datetime(_picked)
        _month_start = _picked.replace(day=1)
        _month_end   = (_month_start + pd.offsets.MonthEnd(1)).normalize()

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
        _daily_map = {row["_day"]: (float(row["NetPnL"]), int(row["Trades"])) for _, row in _daily_stats.iterrows()}

        # ---- Build calendar grid meta ----
        _first_weekday, _n_days = _cal.monthrange(_month_start.year, _month_start.month)  # Mon=0..Sun=6
        _leading = _first_weekday
        _total_slots = _leading + _n_days
        _rows = (_total_slots + 6) // 7  # ceil div by 7

        # ---------- THEME TOKENS ----------
        _panel_bg    = "#0b0f19"   # page/panel bg
        _cell_bg     = "#101621"   # day cell background
        _grid_line   = "#2a3444"   # subtle grid lines
        _txt_main    = "#e5e7eb"   # main text
        _txt_muted   = "#9ca3af"   # muted text
        _pnl_pos     = "#22c55e"   # green
        _pnl_neg     = "#ef4444"   # red
        _pnl_zero    = _txt_main   # neutral
        _dash_accent = "#1f2937"   # outer frame border
        _total_bg    = "#0d1320"   # TOTAL column bg
        _total_border= "#3a4557"   # TOTAL column border
        _total_hdr   = "#cbd5e1"   # TOTAL header color

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
            annos.append(dict(
                x=c + 0.5, y=-0.35, xref="x", yref="y",
                text=label, showarrow=False,
                font=dict(size=12, color=_total_hdr if label == "Total" else _txt_muted),
                xanchor="center", yanchor="middle"
            ))

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
        shapes.append(dict(
            type="path", path=path,
            line=dict(color=_dash_accent, width=1.5),
            fillcolor=_panel_bg, layer="below"
        ))

        # cells (7 day columns + 1 total column)
        for r_idx in range(_rows):
            for c_idx in range(8):
                x0, x1 = c_idx, c_idx + 1
                y0, y1 = r_idx, r_idx + 1

                # TOTAL column styled differently
                is_total_col = (c_idx == 7)
                shapes.append(dict(
                    type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                    line=dict(color=_total_border if is_total_col else _grid_line,
                              width=1.5 if is_total_col else 1),
                    fillcolor=_total_bg if is_total_col else _cell_bg,
                    layer="below"
                ))

                # day columns (0..6)
                if not is_total_col:
                    slot_idx = r_idx * 7 + c_idx
                    if _slot_in_month(slot_idx):
                        d = _slot_to_date(slot_idx)
                        pnl_val, trade_ct = _daily_map.get(d, (0.0, 0))

                        # --- day number (TOP-LEFT) ---
                        annos.append(dict(
                            x=x0 + 0.08, y=y0 + 0.15, xref="x", yref="y",
                            text=str((slot_idx - _leading + 1)),
                            showarrow=False,
                            font=dict(size=12, color=_txt_muted),
                            xanchor="left", yanchor="top"
                        ))

                        # --- PnL (CENTER, larger) ---
                        if trade_ct == 0:
                            pnl_txt = "—"
                            pnl_col = _txt_muted
                        else:
                            pnl_txt = f"${pnl_val:,.0f}"
                            pnl_col = (_pnl_pos if pnl_val > 0 else (_pnl_neg if pnl_val < 0 else _pnl_zero))
                        annos.append(dict(
                            x=x0 + 0.5, y=y0 + 0.48, xref="x", yref="y",
                            text=pnl_txt, showarrow=False,
                            font=dict(size=16, color=pnl_col),
                            xanchor="center", yanchor="middle"
                        ))

                        # --- trades (BELOW center) ---
                        trades_txt = "—" if trade_ct == 0 else (f"{trade_ct} trade" if trade_ct == 1 else f"{trade_ct} trades")
                        annos.append(dict(
                            x=x0 + 0.5, y=y0 + 0.78, xref="x", yref="y",
                            text=trades_txt, showarrow=False,
                            font=dict(size=11, color=_txt_muted),
                            xanchor="center", yanchor="top"
                        ))

                # totals column (c_idx == 7)
                else:
                    pnl_sum, trade_sum = week_totals[r_idx]
                    # PnL total (center)
                    if trade_sum == 0:
                        tot_pnl_txt = "—"
                        tot_pnl_col = _txt_muted
                    else:
                        tot_pnl_txt = f"${pnl_sum:,.0f}"
                        tot_pnl_col = (_pnl_pos if pnl_sum > 0 else (_pnl_neg if pnl_sum < 0 else _pnl_zero))
                    annos.append(dict(
                        x=x0 + 0.5, y=y0 + 0.48, xref="x", yref="y",
                        text=tot_pnl_txt, showarrow=False,
                        font=dict(size=16, color=tot_pnl_col),
                        xanchor="center", yanchor="middle"
                    ))
                    # Trades total (below center)
                    tot_trades_txt = "—" if trade_sum == 0 else (f"{trade_sum} trade" if trade_sum == 1 else f"{trade_sum} trades")
                    annos.append(dict(
                        x=x0 + 0.5, y=y0 + 0.78, xref="x", yref="y",
                        text=tot_trades_txt, showarrow=False,
                        font=dict(size=11, color=_txt_muted),
                        xanchor="center", yanchor="top"
                    ))

        # ---------- BUILD FIGURE ----------
        fig_cal = go.Figure()
        fig_cal.update_layout(
            paper_bgcolor=_panel_bg,
            plot_bgcolor=_panel_bg,
            shapes=shapes,
            annotations=annos,
            xaxis=dict(
                range=[0, 8],  # 7 days + 1 TOTAL column
                showgrid=False, zeroline=False,
                tickmode="array", tickvals=[], ticktext=[], fixedrange=True
            ),
            yaxis=dict(
                range=[_rows, -1],  # leave -1 for header row
                showgrid=False, zeroline=False,
                tickvals=[], ticktext=[], fixedrange=True
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
                key="cal_day_input"
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
                key="cal_week_sel"
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
