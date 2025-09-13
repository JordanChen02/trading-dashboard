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
    st.markdown(f"""
    <style>
    .ws-wrap {{ --brand:{brand_color}; --pillGood:#1e3a8a; --pillBad:#6b1d1d; }}
    .ws-title{{ font-weight:800; font-size:20px; letter-spacing:.2px; margin:0 0 8px 0; }}
    .ws-row{{ display:flex; gap:28px; justify-content:space-between; }}
    .ws-col{{ flex:1; display:flex; flex-direction:column; align-items:center; }}
    .ws-main{{ display:flex; align-items:center; gap:10px; }}
    .ws-big{{ font-size:38px; font-weight:800; color:var(--brand); line-height:1; }}
    .ws-icon{{
        width:28px; height:28px; background-color:var(--brand); opacity:.95;
        -webkit-mask: url("data:image/svg+xml;utf8,\
        <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
            <path fill='black' d='M13.5 0c.9 4.4-1.8 6.8-3.6 8.6C8.1 10.4 7 12 7 14.5 7 18.1 9.9 21 13.5 21S20 18.1 20 14.5c0-3.2-1.7-5.4-3.2-6.9-.9-.9-1.7-1.6-2.1-2.7C14.1 3.5 14 1.8 13.5 0zM12 14c.5 1.8-.8 2.8-1.6 3.6-.6.6-1 1.2-1 2.2 0 1.9 1.5 3.2 3.4 3.2s3.4-1.3 3.4-3.2c0-1.5-.8-2.5-1.5-3.2-.5-.5-1-.9-1.2-1.6-.2-.6-.2-1.3-.5-2z'/>\
        </svg>") no-repeat center / contain;
                mask: url("data:image/svg+xml;utf8,\
        <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
            <path fill='black' d='M13.5 0c.9 4.4-1.8 6.8-3.6 8.6C8.1 10.4 7 12 7 14.5 7 18.1 9.9 21 13.5 21S20 18.1 20 14.5c0-3.2-1.7-5.4-3.2-6.9-.9-.9-1.7-1.6-2.1-2.7C14.1 3.5 14 1.8 13.5 0zM12 14c.5 1.8-.8 2.8-1.6 3.6-.6.6-1 1.2-1 2.2 0 1.9 1.5 3.2 3.4 3.2s3.4-1.3 3.4-3.2c0-1.5-.8-2.5-1.5-3.2-.5-.5-1-.9-1.2-1.6-.2-.6-.2-1.3-.5-2z'/>\
        </svg>") no-repeat center / contain;
    }}
    .ws-badges{{ display:flex; flex-direction:column; gap:6px; margin-left:6px; }}
    .ws-pill{{ min-width:36px; padding:2px 8px; border-radius:10px; text-align:center;
               font-size:12px; font-weight:700; color:#cbd5e1; }}
    .ws-pill.ws-good{{ background:rgba(46,134,193,.25); border:1px solid rgba(46,134,193,.4); }}
    .ws-pill.ws-bad{{  background:rgba(202,82,82,.25);  border:1px solid rgba(202,82,82,.4); }}
    .ws-foot{{ margin-top:6px; font-size:13px; color:#cbd5e1; }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="ws-wrap">
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
    """, unsafe_allow_html=True)
