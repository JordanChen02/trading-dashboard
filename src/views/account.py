# src/views/account.py
from __future__ import annotations

import streamlit as st

# Theme fallbacks (so this file works even if theme.py isn't present)
try:
    from src.theme import BLUE, CARD_BG
except Exception:
    BLUE = "#3AA4EB"
    CARD_BG = "#0f1829"

RED = "#E06B6B"
FG = "#E5E7EB"
FG_MUTED = "#9AA4B2"


# ----------------------------- CSS -----------------------------
def _inject_css():
    st.markdown(
        f"""
<style>
/* center the entire page into a middle column feel */
.account-scope * {{ box-sizing: border-box; }}

/* Card shells */
.account-card {{
  background: {CARD_BG};
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  padding: 16px;
}}

/* Section titles */
.section-title {{
  font-weight: 700;
  color: {FG};
  margin-bottom: 6px;
}}

/* Inputs: light outline so they pop on dark BG */
.account-scope [data-testid="stTextInput"] input,
.account-scope [data-testid="stNumberInput"] input,
.account-scope [data-testid="stSelectbox"] > div,
.account-scope [data-testid="stMultiSelect"] > div,
.account-scope textarea {{
  background-color: rgba(255,255,255,0.03) !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  border-radius: 10px !important;
}}

/* Buttons — blue outline + blue text (like Checklist / Journal) */
.account-scope [data-testid="stButton"] > button,
.account-scope [data-testid="stFormSubmitButton"] > button {{
  border: 1px solid {BLUE} !important;
  color: {BLUE} !important;
  background: transparent !important;
  box-shadow: none !important;
}}

/* Danger buttons (Delete etc.) */
.account-scope [data-testid="stButton"] .stTooltipHoverTarget > button {{
  border: 1px solid {RED} !important;
  color: {RED} !important;
  background: transparent !important;
  box-shadow: none !important;
}}
</style>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------- STATE -----------------------------
def _ensure_state():
    st.session_state.setdefault("acct_username", "")
    st.session_state.setdefault("acct_password", "")

    # Starting equity map by account
    st.session_state.setdefault(
        "acct_starting_equity",
        {"Crypto (Live)": 5000.0, "Crypto (Prop)": 5000.0, "NQ": 5000.0},
    )
    st.session_state.setdefault("acct_default_equity", 5000.0)

    # Groups
    st.session_state.setdefault("acct_groups", {"Crypto ALL": ["Crypto (Live)", "Crypto (Prop)"]})

    # Preferences
    st.session_state.setdefault("acct_timezone", "(UTC -4) New York")


# ----------------------------- SECTIONS -----------------------------
def _tab_profile():
    with st.container():
        st.markdown('<div class="account-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Profile</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.session_state.acct_username = st.text_input(
                "Username", value=st.session_state.acct_username
            )
        with c2:
            st.session_state.acct_password = st.text_input(
                "Password", value=st.session_state.acct_password, type="password"
            )

        st.markdown("")
        st.button("Save Profile", key="btn_save_profile")
        st.markdown("</div>", unsafe_allow_html=True)


def _tab_starting_equity():
    with st.container():
        st.markdown('<div class="account-card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-title">Starting Equity (per Account)</div>', unsafe_allow_html=True
        )

        # Simple editor-like form (no dataframe)
        for acct in list(st.session_state.acct_starting_equity.keys()):
            col1, col2 = st.columns([3, 2])
            with col1:
                st.text_input(
                    "Account",
                    value=acct,
                    key=f"se_name_{acct}",
                    disabled=True,
                    label_visibility="collapsed",
                )
            with col2:
                st.session_state.acct_starting_equity[acct] = st.number_input(
                    f"Starting Equity for {acct}",
                    value=float(st.session_state.acct_starting_equity[acct]),
                    step=100.0,
                    format="%.2f",
                    key=f"se_val_{acct}",
                    label_visibility="collapsed",
                )

        st.markdown("---")
        cdef, cbtn = st.columns([2, 1])
        with cdef:
            st.session_state.acct_default_equity = st.number_input(
                "Default Starting Equity ($) for accounts not listed",
                value=float(st.session_state.acct_default_equity),
                step=100.0,
                format="%.2f",
            )
        with cbtn:
            st.button("Save Starting Equity", key="btn_save_equity")
        st.markdown("</div>", unsafe_allow_html=True)


def _tab_groups():
    with st.container():
        st.markdown('<div class="account-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Group Options</div>', unsafe_allow_html=True)

        st.caption(
            "Create groups that appear in the Journal Account selector (e.g., Crypto ALL → Crypto (Live), Crypto (Prop))."
        )
        gname = st.text_input("Group name", placeholder="e.g., Crypto ALL")
        gmembers = st.multiselect(
            "Group members",
            options=["Crypto (Live)", "Crypto (Prop)", "NQ"],
        )

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Add / Update Group", key="btn_add_group") and gname.strip():
                st.session_state.acct_groups[gname.strip()] = list(gmembers)
        with c2:
            del_pick = st.selectbox(
                "Delete group", options=["(pick)"] + list(st.session_state.acct_groups.keys())
            )
            if st.button("Delete", key="btn_del_group") and del_pick and del_pick != "(pick)":
                st.session_state.acct_groups.pop(del_pick, None)

        st.markdown("---")
        st.markdown("**Existing groups**")
        for g, members in st.session_state.acct_groups.items():
            st.write(f"- **{g}** — {', '.join(members) if members else '—'}")
        st.markdown("</div>", unsafe_allow_html=True)


def _tab_preferences():
    with st.container():
        st.markdown('<div class="account-card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-title">Defaults & Preferences</div>', unsafe_allow_html=True
        )

        tz_options = [
            "UTC",
            "(UTC -4) New York",
            "(UTC -7) Los Angeles",
            "(UTC +0) London",
            "(UTC +1) Berlin",
            "(UTC +8) Singapore",
            "(UTC +9) Tokyo",
            "(UTC +10) Sydney",
        ]
        st.session_state.acct_timezone = st.selectbox(
            "Timezone",
            options=tz_options,
            index=(
                tz_options.index(st.session_state.acct_timezone)
                if st.session_state.acct_timezone in tz_options
                else 1
            ),
        )

        st.button("Save Defaults", key="btn_save_defaults")
        st.caption("Changes persist to settings.json and update the running session.")
        st.markdown("</div>", unsafe_allow_html=True)


def _tab_guide():
    # No caption/header per your request — just the content
    with st.container():
        st.markdown('<div class="account-card">', unsafe_allow_html=True)

        st.markdown("### Dashboard")
        st.write(
            "- **Win Rate / Profit Factor half-donuts**: quick view of % wins and the ratio of gross profit to gross loss. "
            "Profit Factor > 1 means profitable overall.\n"
            "- **Long vs Short**: share of trades taken long vs short.\n"
            "- **Most Traded Assets**: counts by symbol.\n"
            "- **Daily PnL**: bar chart of profit or loss by day.\n"
            "- **Equity Curve**: running total of PnL over time.\n"
            "- **Last 5 Trades**: recent outcomes with quick tags.\n"
            "- **Calendar heatmap**: month grid showing activity and PnL."
        )

        st.markdown("### Performance")
        st.write(
            "- **Underwater (Drawdown %)**: shows equity dips from prior peaks. Useful for risk control and regime shifts.\n"
            "- **Cumulative R**: total Risk-units (R) earned over time.\n"
            "- **Rolling Metrics**: moving-window win-rate and expectancy so you can see trends smoothing out noise.\n"
            "- **Expectancy / Trade**: average R you expect per trade; positive expectancy with consistent risk sizing is key.\n"
            "- **Sigma Bands** (if enabled on charts): standard-deviation envelopes around a rolling mean; points outside "
            "bands indicate unusually strong/weak outcomes that may revert."
        )

        st.markdown("### Calendar")
        st.write(
            "Browse your trades by day. Use it to spot clusters of activity, streaks, or days to avoid."
        )

        st.markdown("### Journal")
        st.write(
            "- **New Entry** opens a pop-out form. Fill in times, symbol, risk, PnL, and add confirmations.\n"
            "- **Styled View** shows a read-only, color-coded table with tags; toggle off for an editable grid.\n"
            "- **Delete selected** lets you mark rows and confirm deletion in a modal.\n"
            "- **Load from Checklist** pulls your current checklist/confluences into the new entry’s confirmations.\n"
            "- **Filters** at the top (account, dates, direction, etc.) update the table and KPIs below."
        )

        st.markdown("</div>", unsafe_allow_html=True)


# ----------------------------- MAIN -----------------------------
def render_account(*_args, **_kwargs) -> None:
    _ensure_state()
    _inject_css()

    # Center layout: [0.2, 0.6, 0.2]
    _, mid, _ = st.columns([0.2, 0.6, 0.2])
    with mid:
        st.markdown('<div class="account-scope">', unsafe_allow_html=True)

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
