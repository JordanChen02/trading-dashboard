import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path
from src.utils import ensure_journal_store, load_journal_index, create_journal, DATA_DIR

# Page configuration
st.set_page_config(
    page_title="Trading Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# App header
st.title("Trading Dashboard — MVP")
st.caption("Source → Validate → Enrich → Analyze → Visualize")
st.divider()


# 👇 our modules
from src.io import load_trades, validate
from src.metrics import add_pnl

st.set_page_config(page_title="Trading Dashboard — MVP", layout="wide")
st.title("Trading Dashboard — MVP")
st.caption("Upload a CSV of trades and preview it below.")

# ===================== SIDEBAR: Journals (UI only) =====================
ensure_journal_store()
with st.sidebar:
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

# ===================== CONTROLS + KPIs =====================
st.subheader("Key Stats")

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

# --- KPI Layout ---
kc1, kc2, kc3, kc4 = st.columns(4)
kc1.metric("Total Trades", f"{total_trades}")
kc2.metric("Win Rate", f"{win_rate:.1f}%")
kc3.metric("Profit Factor", "∞" if profit_factor == float("inf") else f"{profit_factor:.2f}")
kc4.metric("Expectancy (per trade)", f"${expectancy:,.2f}")

kc5, kc6, kc7, kc8, kc9 = st.columns(5)
kc5.metric("Avg Win", f"${avg_win:,.2f}")
kc6.metric("Avg Loss", f"${avg_loss:,.2f}")
kc7.metric("Max Drawdown", f"${max_dd_abs:,.2f} ({max_dd_pct:.1f}%)")
kc8.metric("Current Balance", f"${current_balance:,.2f}")
kc9.metric("Net PnL", f"${net_pnl:,.2f}")

# ===================== CHART =====================
st.subheader("Equity Curve")
fig = px.line(
    df,
    x="trade_no",
    y="equity",
    title="Equity Curve",
    labels={"trade_no": "Trade #", "equity": "Equity ($)"},
)
# Force y-axis to start at your starting equity; add 5% headroom for readability
fig.update_yaxes(range=[start_equity, df["equity"].max() * 1.05])
st.plotly_chart(fig, use_container_width=True)
