# src/views/account.py
from __future__ import annotations

import streamlit as st

# Theme fallbacks
try:
    from src.theme import BLUE, CARD_BG, FG
except Exception:
    BLUE = "#3AA4EB"
    CARD_BG = "#0f1829"
    FG = "#E5E7EB"


# ---------- CSS ----------
def _inject_css() -> None:
    st.markdown(
        f"""
<style>
.acc-root * {{ box-sizing: border-box; }}


.acc-title {{ font-weight: 700; color: {FG}; margin-bottom: 6px; }}

/* Inputs & dropdowns — match New Entry popout */
.acc-card [data-testid="stTextInput"] input,
.acc-card [data-testid="stNumberInput"] input,
.acc-card [data-testid="stSelectbox"] > div,
.acc-card [data-testid="stMultiSelect"] > div,
.acc-card textarea {{
  background-color: rgba(2,8,23,0.25) !important;
  border: 1px solid rgba(148,163,184,0.28) !important;
  border-radius: 10px !important;
  outline: none !important;
}}
/* BaseWeb focus-within ring */
.acc-card [data-baseweb="input"]:focus-within,
.acc-card [data-baseweb="select"]:focus-within,
.acc-card [data-testid="stTextInput"] input:focus,
.acc-card [data-testid="stNumberInput"] input:focus,
.acc-card textarea:focus {{
  border-color: {BLUE} !important;
  box-shadow: 0 0 0 2px rgba(58,164,235,0.20) !important;
}}

/* Blue-outline buttons (match Checklist/Journal) */
[data-testid="stButton"] > button,
[data-testid="stFormSubmitButton"] > button {{
  border: 1px solid {BLUE} !important;
  color: {BLUE} !important;
  background: transparent !important;
  box-shadow: none !important;
  border-radius: 10px !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )


# ---------- session defaults ----------
def _ensure_state() -> None:
    st.session_state.setdefault("accounts_options", ["Crypto (Live)", "Crypto (Prop)", "NQ"])
    st.session_state.setdefault(
        "acct_equity", {k: 5000.0 for k in st.session_state.accounts_options}
    )
    st.session_state.setdefault("default_equity_base", 5000.0)
    st.session_state.setdefault("acct_groups", {"Crypto ALL": ["Crypto (Live)", "Crypto (Prop)"]})
    st.session_state.setdefault("tz_pref", "UTC")


# ---------- tabs ----------
def _tab_profile() -> None:
    st.markdown('<div class="acc-title">Profile</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.text_input(
            "Username", value=st.session_state.get("profile_username", ""), key="profile_username"
        )
    with c2:
        st.text_input(
            "Password",
            type="password",
            value=st.session_state.get("profile_password", ""),
            key="profile_password",
        )

    st.write("")
    st.button("Save Profile", key="btn_save_profile")
    st.markdown("</div>", unsafe_allow_html=True)  # /acc-card

    st.markdown("</div>", unsafe_allow_html=True)  # /acc-panel


def _tab_starting_equity() -> None:
    st.markdown('<div class="acc-panel">', unsafe_allow_html=True)

    st.markdown('<div class="acc-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="acc-title">Starting Equity (per Account)</div>', unsafe_allow_html=True
    )

    # Per-account equity inputs — widgets own eq_<acct> keys
    for acct in st.session_state.accounts_options:
        key = f"eq_{acct}"
        if key not in st.session_state:
            st.session_state[key] = float(
                st.session_state.acct_equity.get(acct, st.session_state.default_equity_base)
            )
        val = st.number_input(acct, step=100.0, format="%.2f", key=key)
        st.session_state.acct_equity[acct] = float(val)

    st.write("")
    # Default equity — widget owns "default_equity" key
    if "default_equity" not in st.session_state:
        st.session_state["default_equity"] = float(st.session_state.default_equity_base)
    st.number_input(
        "Default Starting Equity ($) for accounts not listed",
        step=100.0,
        format="%.2f",
        key="default_equity",
    )
    st.session_state.default_equity_base = float(st.session_state["default_equity"])

    st.write("")
    if st.button("Save Starting Equity", key="btn_save_equity"):
        st.toast("Starting equity saved ✓")

    st.markdown("</div>", unsafe_allow_html=True)  # /acc-card
    st.markdown("</div>", unsafe_allow_html=True)  # /acc-panel


def _tab_groups() -> None:
    st.markdown('<div class="acc-panel">', unsafe_allow_html=True)

    st.markdown('<div class="acc-card">', unsafe_allow_html=True)
    st.markdown('<div class="acc-title">Group Options</div>', unsafe_allow_html=True)

    g1, g2 = st.columns([1, 1])
    with g1:
        group_name = st.text_input("Group name", placeholder="e.g., Crypto ALL", key="grp_name")
    with g2:
        members = st.multiselect(
            "Group members",
            options=st.session_state.accounts_options,
            default=[],
            key="grp_members",
        )

    if st.button("Add / Update Group", key="btn_group_add") and group_name.strip():
        st.session_state.acct_groups[group_name.strip()] = members[:]
        st.toast("Group saved ✓")

    st.write("")
    st.markdown("**Existing groups**")
    for name, mem in list(st.session_state.acct_groups.items()):
        r1, r2 = st.columns([4, 1])
        with r1:
            st.write(f"- **{name}** — {', '.join(mem) if mem else '—'}")
        with r2:
            if st.button("Delete", key=f"del_{name}"):
                st.session_state.acct_groups.pop(name, None)
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)  # /acc-card
    st.markdown("</div>", unsafe_allow_html=True)  # /acc-panel


def _tab_preferences() -> None:
    st.markdown('<div class="acc-panel">', unsafe_allow_html=True)

    st.markdown('<div class="acc-card">', unsafe_allow_html=True)
    st.markdown('<div class="acc-title">Defaults & Preferences</div>', unsafe_allow_html=True)

    tz_options = [
        "UTC",
        "(UTC -8) Los Angeles",
        "(UTC -7) Denver",
        "(UTC -6) Chicago",
        "(UTC -5) New York",
        "(UTC  0) London",
        "(UTC +1) Berlin",
        "(UTC +5:30) India",
        "(UTC +8) Singapore",
        "(UTC +9) Tokyo",
        "(UTC +10) Sydney",
    ]
    idx = (
        tz_options.index(st.session_state.get("tz_pref", "UTC"))
        if st.session_state.get("tz_pref", "UTC") in tz_options
        else 0
    )
    st.selectbox("Timezone", options=tz_options, index=idx, key="tz_pref")

    st.write("")
    st.button("Save Defaults", key="btn_save_prefs")

    st.markdown("</div>", unsafe_allow_html=True)  # /acc-card
    st.markdown("</div>", unsafe_allow_html=True)  # /acc-panel


def _tab_guide() -> None:
    st.markdown('<div class="acc-panel">', unsafe_allow_html=True)

    st.markdown('<div class="acc-card">', unsafe_allow_html=True)
    # No extra caption; direct content
    st.markdown(
        """
### Dashboard  
- **Win Rate / Profit Factor / Winstreak**: headline KPIs for the selected date range and account filter.  
- **Most Traded Assets**: donut with trade counts per symbol; use it to spot concentration.  
- **Daily PnL**: bars by day; clusters of red/green reveal streaks and session bias.  
- **Long vs Short (Cumulative R)**: running total of R split by side; widening gap shows drift.  
- **Equity Curve**: balance trend; sudden drops flag risk spikes.  
- **Month Grid**: calendar-style monthly PnL; quick scan for hot/cold months.

### Performance  
- **Underwater (Drawdown %)**: depth of peak-to-trough losses; shallow & quick recoveries are healthy.  
- **Cumulative R**: total performance independent of position size; flat lines indicate churn.  
- **Rolling Metrics**: windowed stats over time.  
  - *Rolling Win %*: moving win rate; smooths noise to show regime change.  
  - *Expectancy / Trade*: average R you expect per trade; positive expectancy with consistent risk sizing is key.  
  - *Sigma Bands* (if enabled): standard-deviation envelopes around a rolling mean; points outside bands are unusually strong/weak and often revert.  
- **Profit by Symbol**: bars of total PnL per asset to reveal which tickers carry you.  
- **PnL per Trade (Histogram)**: distribution of trade outcomes; long right tail is ideal.

### Calendar  
A monthly grid of trades; click a day to review context. Great for spotting weekday/session patterns.

### Journal  
- **Styled view**: read-only table with colored tags.  
- **+ New Entry**: opens a wide popout.  
- **Load from Checklist**: pulls your current checklist selections as confirmations.  
- **Delete selected**: multi-select rows in the editable view, then delete via a confirmation popout.  
- **Filters**: top bar for account, date range, session, symbol, tier, etc.
""",
        unsafe_allow_html=True,
    )


# ---------- entry ----------
def render_account(*_args, **_kwargs) -> None:
    _ensure_state()
    _inject_css()

    # Center page: [0.2, 0.6, 0.2]
    _, mid, _ = st.columns([0.2, 0.6, 0.2])
    with mid:
        st.markdown('<div class="acc-root">', unsafe_allow_html=True)

        tabs = st.tabs(["Profile", "Starting Equity", "Group Options", "Preferences", "Guide"])

        with tabs[0]:
            _tab_profile()
        with tabs[1]:
            _tab_starting_equity()
        with tabs[2]:
            _tab_groups()
        with tabs[3]:
            _tab_preferences()
        with tabs[4]:
            _tab_guide()

        st.markdown("</div>", unsafe_allow_html=True)
