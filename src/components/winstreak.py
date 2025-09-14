from src.styles import inject_winstreak_css
import streamlit as st

def render_winstreak(
    *,
    days_streak: int,
    trades_streak: int,
    best_days_streak: int,
    resets_days_count: int,
    best_trades_streak: int,
    resets_trades_ct: int,
    title: str = "Winstreak",
    brand_color: str = "#2E86C1",
) -> None:
    # make sure CSS classes exist
    
    inject_winstreak_css()
    

    # render the card (CSS only lives in styles.py)
    st.markdown(
        f"""
        <div class="ws-wrap" style="--brand:{brand_color};">
          <div class="ws-title">{title}</div>
          <div class="ws-row">
            <div class="ws-col">
              <div class="ws-main">
                <span class="ws-big">{days_streak}</span>
                <span class="ws-icon"></span>
                <span class="ws-badges">
                  <span class="ws-pill ws-good">{best_days_streak}</span>
                  <span class="ws-pill ws-bad">{resets_days_count}</span>
                </span>
              </div>
              <div class="ws-foot">Days</div>
            </div>
            <div class="ws-col">
              <div class="ws-main">
                <span class="ws-big">{trades_streak}</span>
                <span class="ws-icon"></span>
                <span class="ws-badges">
                  <span class="ws-pill ws-good">{best_trades_streak}</span>
                  <span class="ws-pill ws-bad">{resets_trades_ct}</span>
                </span>
              </div>
              <div class="ws-foot">Trades</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
