# app.py (top of file)
import streamlit as st
# (other imports are fine above or below — imports don’t matter)

st.set_page_config(
    page_title="Trading Dashboard — MVP",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ONLY AFTER page_config:
st.title("Trading Dashboard — MVP")
st.caption("Source → Validate → Enrich → Analyze → Visualize")
st.caption("Upload a CSV of trades and preview it below.")
st.divider()

import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path
from src.utils import ensure_journal_store, load_journal_index, create_journal, DATA_DIR

# 👇 our modules
from src.io import load_trades, validate
from src.metrics import add_pnl



# ===================== SIDEBAR: Journals (UI only) =====================
ensure_journal_store()
with st.sidebar:
    # --- Navigation (static for now) ---
    st.markdown("## Navigation")
    nav = st.radio("Go to:", ["Dashboard", "Journal", "Accounts"], index=0, label_visibility="collapsed")
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
file = st.file_uploader("Upload CSV", type=["csv"])

df = None
source_label = ""

if file is not None:
    source_label = "uploaded file"
    try:
        df = load_trades(file)
    except Exception as e:
        st.error(f"Could not read that file: {e}")
        st.stop()
else:
    # Fallback: load the currently selected journal (if any)
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
    st.info("Upload a CSV or create/select a journal to begin.")
    st.stop()

st.caption(f"Data source: **{source_label}**")
st.toast(f"✅ Loaded {len(df)} trades from {source_label}")

# ===================== PIPELINE: Validate → PnL → Preview =====================
issues = validate(df)
if issues:
    st.error("We found issues in your CSV:")
    for i, msg in enumerate(issues, start=1):
        st.write(f"{i}. {msg}")
    st.stop()

df = add_pnl(df)

st.subheader("Preview (first 50 rows)")
st.dataframe(df.head(50), use_container_width=True)

# ===================== FILTERS (render after df exists) =====================
# Recreate the sidebar expander now that df is available
with st.sidebar.expander("Filters", expanded=True):
    symbols = sorted(df["symbol"].dropna().unique().tolist()) if "symbol" in df.columns else []
    sides   = sorted(df["side"].dropna().unique().tolist())   if "side"   in df.columns else []

    sel_symbols = st.multiselect("Symbol", symbols, default=symbols if symbols else [])
    sel_sides   = st.multiselect("Side",   sides,   default=sides   if sides   else [])

# Apply filters
df_filtered = df.copy()
if "symbol" in df_filtered.columns and sel_symbols:
    df_filtered = df_filtered[df_filtered["symbol"].isin(sel_symbols)]
if "side" in df_filtered.columns and sel_sides:
    df_filtered = df_filtered[df_filtered["side"].isin(sel_sides)]

if df_filtered.empty:
    st.info("No rows match the current filters. Adjust filters in the sidebar.")
    st.stop()

# From here on, keep your existing code but make it operate on the filtered data:
df = df_filtered

# ===================== CONTROLS + KPIs =====================
st.subheader("Controls")

# Breakeven handling for win-rate
be_policy = st.radio(
    "Breakeven trades (PnL = 0) should…",
    ["be excluded from win-rate", "count as losses", "count as wins"],
    help="This only affects win-rate. Totals and sums still include breakeven PnL."
)

# Starting equity for equity curve + Max DD%
start_equity = st.number_input(
    "Starting equity ($)", min_value=0.0, value=5000.0, step=100.0,
    help="Used to anchor the equity curve and compute Max Drawdown %."
)

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
df = df.copy().reset_index(drop=True)
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

# ===================== OVERVIEW KPI CARDS =====================
# Daily Win Rate (days with net positive PnL / total trading days), if a date-like column exists
_daily_wr_display = "—%"  # default placeholder
_possible_date_cols = ["date", "Date", "timestamp", "Timestamp", "time", "Time", "datetime", "Datetime", "entry_time", "exit_time"]
_date_col = next((c for c in _possible_date_cols if c in df.columns), None)
try:
    if _date_col is not None:
        _d = pd.to_datetime(df[_date_col], errors="coerce")
        _tmp = df.copy()
        _tmp["_day"] = _d.dt.date
        _daily_pnl = _tmp.groupby("_day")["pnl"].sum()
        if len(_daily_pnl) > 0:
            _daily_wr = float((_daily_pnl > 0).mean() * 100.0)
            _daily_wr_display = f"{_daily_wr:.1f}%"
except Exception:
    # keep placeholder if conversion fails
    pass

# Avg Win / Avg Loss ratio (absolute, avoids negative sign on losses)
avg_win_loss_ratio = (abs(avg_win / avg_loss) if avg_loss != 0 else float("inf"))

st.subheader("Overview")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Win Rate", f"{win_rate:.1f}%")
with c2:
    st.metric("Daily Win Rate", _daily_wr_display)
with c3:
    st.metric("Avg Win / Avg Loss", "∞" if avg_win_loss_ratio == float("inf") else f"{avg_win_loss_ratio:.2f}")
with c4:
    st.metric("Trade Count", f"{total_trades}")


# --- MORE KPIs (details) ---
with st.expander("More KPIs (details)", expanded=False):
    kc1, kc2, kc3, kc4 = st.columns(4)
    kc1.metric("Total Trades", f"{total_trades}")
    kc2.metric("Win Rate", f"{win_rate:.1f}%")
    kc3.metric("Profit Factor", "∞" if profit_factor == float("inf") else f"{profit_factor:.2f}")
    kc4.metric("Expectancy (per trade)", f"${expectancy:,.2f}")

    kd1, kd2, kd3, kd4, kd5 = st.columns(5)
    kd1.metric("Avg Win", f"${avg_win:,.2f}")
    kd2.metric("Avg Loss", f"${avg_loss:,.2f}")
    kd3.metric("Max Drawdown", f"${max_dd_abs:,.2f} ({max_dd_pct:.1f}%)")
    kd4.metric("Current Balance", f"${current_balance:,.2f}")
    kd5.metric("Net PnL", f"${net_pnl:,.2f}")



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



st.subheader("Charts")

left, right = st.columns([3, 2], gap="large")

# ===================== CHART HELPERS (assets, sides, volume & pnl windows) =====================
# Detect a date-like column we can use for daily grouping
_possible_date_cols = ["date", "Date", "timestamp", "Timestamp", "time", "Time", "datetime", "Datetime", "entry_time", "exit_time"]
_date_col = next((c for c in _possible_date_cols if c in df.columns), None)
_dt = pd.to_datetime(df[_date_col], errors="coerce") if _date_col is not None else None

# 1) Distribution by asset (symbol) and side (long/short)
_symbol_dist = (
    df["symbol"].value_counts(normalize=True).sort_values(ascending=False)
    if "symbol" in df.columns else pd.Series(dtype=float)
)
_side_dist = (
    df["side"].str.lower().value_counts(normalize=True).reindex(["long", "short"]).fillna(0.0)
    if "side" in df.columns else pd.Series(dtype=float)
)

# 2) Dollar notional per trade (best-effort):
# Try common field names; otherwise fall back to abs(PnL) as a rough proxy
_qty_cols   = [c for c in ["qty","quantity","size","contracts","amount"] if c in df.columns]
_price_cols = [c for c in ["price","entry_price","avg_entry_price"] if c in df.columns]
if _qty_cols and _price_cols:
    _notional = (pd.to_numeric(df[_qty_cols[0]], errors="coerce").fillna(0) *
                 pd.to_numeric(df[_price_cols[0]], errors="coerce").fillna(0)).abs()
elif "notional" in df.columns:
    _notional = pd.to_numeric(df["notional"], errors="coerce").fillna(0).abs()
else:
    _notional = df["pnl"].abs()  # fallback

# 3) Windows for “last 20 trades” (by row order)
_last20 = df.tail(20).copy()
_last20_notional = _notional.tail(20).reset_index(drop=True)
_last20_pnl = pd.to_numeric(_last20["pnl"], errors="coerce").fillna(0).reset_index(drop=True)

# 4) Volume per DAY (from last 20 trades)
if _dt is not None:
    _last20_days = _dt.tail(20).dt.date
    _vol_per_day = (
        pd.DataFrame({"day": _last20_days, "vol": _last20_notional})
        .groupby("day", as_index=False)["vol"].sum()
        .sort_values("day")
    )
else:
    # No date column → make a simple index label instead
    _vol_per_day = pd.DataFrame({"day": [f"T-{i}" for i in range(len(_last20_notional),0,-1)][::-1],
                                 "vol": _last20_notional})


# --- Left card: Equity Curve (smaller, minimal title) ---
with left:
    with st.container():
        st.markdown("#### Equity Curve")
        fig = px.line(
            df,
            x="trade_no",
            y="equity",
            title=None,  # keep it minimal like your reference
            labels={"trade_no": "Trade #", "equity": "Equity ($)"},
        )
        ymax = max(start_equity, float(df["equity"].max()) * 1.05)
        fig.update_yaxes(range=[start_equity, ymax])
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

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
                hole=0.55,  # donut look
            )
            fig_sym.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
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
            )
            fig_side.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
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
        st.plotly_chart(fig_pnl, use_container_width=True)
