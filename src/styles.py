import streamlit as st

def inject_overview_css() -> None:
    st.markdown("""
    <style>
      .pillbar{width:100%;height:18px;background:#1b2433;border-radius:999px;overflow:hidden;margin:6px 0 6px}
      .pillbar .win{height:100%;background:#2E86C1;display:inline-block}
      .pillbar .loss{height:100%;background:#212C47;display:inline-block}
    </style>
    """, unsafe_allow_html=True)

def inject_winstreak_css(brand_color: str = "#2E86C1") -> None:
    st.markdown(f"""
    <style>
      .ws-wrap {{ --brand:{brand_color}; }}
      .ws-title{{ font-weight:800; font-size:20px; margin:0 0 8px 0; }}
      .ws-row{{ display:flex; gap:28px; justify-content:space-between; }}
      .ws-col{{ flex:1; display:flex; flex-direction:column; align-items:center; }}
      .ws-main{{ display:flex; align-items:center; gap:10px; }}
      .ws-big{{ font-size:38px; font-weight:800; color:var(--brand); line-height:1; }}
      .ws-badges{{ display:flex; flex-direction:column; gap:6px; margin-left:6px; }}
      .ws-pill{{ min-width:36px; padding:2px 8px; border-radius:10px; text-align:center;
                 font-size:12px; font-weight:700; color:#cbd5e1; }}
      .ws-pill.ws-good{{ background:rgba(46,134,193,.25); border:1px solid rgba(46,134,193,.4); }}
      .ws-pill.ws-bad{{  background:rgba(202,82,82,.25);  border:1px solid rgba(202,82,82,.4); }}
      .ws-foot{{ margin-top:6px; font-size:13px; color:#cbd5e1; }}
    </style>
    """, unsafe_allow_html=True)
