import streamlit as st
import pandas as pd
from data_loader import load_data
from generator import generate_blog_post

# Page Config
st.set_page_config(
    page_title="치과 블로그 포스팅 생성기",
    page_icon="🦷",
    layout="wide"
)

# Custom CSS for Premium Design
# Apple-Style Custom CSS
st.markdown("""
<style>
/* Font & Global Reset */
@import url('https://fonts.googleapis.com/css2?family=sf-pro-display:wght@400;600&display=swap'); /* Fallback */

html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
    color: #1d1d1f;
    background-color: #f5f5f7; /* Apple Light Gray Background */
}

/* Sidebar Customization */
section[data-testid="stSidebar"] {
    background-color: #ffffff;
    border-right: 1px solid #d2d2d7;
}

/* Headings */
h1 {
    font-weight: 700;
    color: #1d1d1f;
    letter-spacing: -0.02em;
    padding-bottom: 0.5rem;
}
h2, h3 {
    font-weight: 600;
    color: #1d1d1f;
    letter-spacing: -0.01em;
}

/* Button Styling (Apple Blue) */
div.stButton > button {
    background-color: #0071e3 !important;
    color: white !important;
    border: none !important;
    border-radius: 980px !important; /* Full rounded pill */
    padding: 10px 24px !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    box-shadow: none !important;
    transition: all 0.2s ease;
}
div.stButton > button:hover {
    background-color: #0077ed !important;
    transform: scale(1.02);
}
div.stButton > button:active {
    transform: scale(0.98);
}

/* Input Fields */
div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background-color: rgba(255, 255, 255, 0.8) !important;
    border: 1px solid #d2d2d7 !important;
    border-radius: 12px !important;
    color: #1d1d1f !important;
    font-size: 15px !important;
    height: 44px !important;
}
div[data-testid="stTextInput"] input:focus, div[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within {
    border-color: #0071e3 !important;
    box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.1) !important;
}

/* Cards / Containers */
.apple-card {
    background-color: white;
    border-radius: 18px;
    padding: 30px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    margin-bottom: 25px;
    border: 1px solid rgba(255, 255, 255, 0.5);
}

/* Expander */
.streamlit-expanderHeader {
    background-color: transparent !important;
    color: #1d1d1f !important;
    font-weight: 600 !important;
    border-radius: 12px;
}

/* Success/Info Alerts */
.stSuccess {
    background-color: #eafbf0 !important;
    color: #1d1d1f !important;
    border: 1px solid #d2eadd !important;
    border-radius: 14px !important;
}
.stInfo {
    background-color: #f2f7ff !important;
    color: #1d1d1f !important;
    border: none !important;
    border-radius: 14px !important;
}

/* Streamlit specific cleanups */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

def main():
    # Header Section
    st.markdown("<h1 style='text-align: center; margin-bottom: 40px;'>🦷 치과 블로그 포스팅 생성기</h1>", unsafe_allow_html=True)

    # Load Data
    with st.spinner("데이터를 로딩해오고 있습니다..."):
        df = load_data()

    if df.empty:
        st.error("데이터를 불러오지 못했습니다. .streamlit/secrets.toml 설정을 확인해주세요.")
        return

    # Layout using columns for a centered card-like feel for inputs if needed, 
    # but sidebar is good for controls in this "app-like" feel.
    
    # Sidebar Controls
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3774/3774299.png", width=60) # Simple Icon Placeholder
        st.markdown("### 설정")
        
        # 1. Dentist Selection
        st.write("작성자 선택")
        dentists = df['DentistName'].unique().tolist()
        dentist_list = sorted([str(d) for d in dentists])
        selected_dentist = st.selectbox("치과(원장님) 선택", dentist_list, label_visibility="collapsed")
        
        st.markdown("---")
        
        # 2. Input Fields
        st.write("주제 입력")
        topic = st.text_input("주제", placeholder="예: 임플란트 수술 후 주의사항", label_visibility="collapsed")
        
        st.write("핵심 키워드")
        keyword = st.text_input("키워드", placeholder="예: 안 아픈 치과, 임플란트", label_visibility="collapsed")

        st.write("글 스타일 선택")
        style_options = {
            "기본 정보성 (Standard)": "Standard",
            "환자 스토리텔링 (Story)": "Story",
            "Q&A 질의응답 (FAQ)": "Q&A",
            "팩트체크/오해와 진실 (MythBust)": "MythBust"
        }
        selected_style_name = st.selectbox("스타일", list(style_options.keys()), label_visibility="collapsed")
        selected_style = style_options[selected_style_name]
        
        # Conditional Input for Storytelling
        context_input = ""
        if selected_style == "Story":
            st.info("💡 실제 환자 에피소드를 입력하면 더 생생한 글이 나옵니다.")
            context_input = st.text_area("환자 에피소드 (선택사항)", height=100, 
                placeholder="예: 50대 여성분, 앞니가 벌어져서 웃을 때 손으로 가리심. 라미네이트 시술 후 자신감 찾고 웃으며 귀가.")

        st.markdown("---")
        
        # 3. Generate Button
        generate_btn = st.button("글 생성하기 ✨")

    # Main Area
    if generate_btn:
        if not topic or not keyword:
            st.warning("주제와 핵심 키워드를 모두 입력해주세요!")
        else:
            with st.spinner(f"Creating content for {selected_dentist} ({selected_style_name})..."):
                # Call Gemini Logic
                generated_content, references = generate_blog_post(selected_dentist, topic, keyword, selected_style, context_input)
            
            if generated_content:
                # Result Card
                st.markdown(f"""
                <div class="apple-card">
                    <h3 style="margin-top: 0;">🎉 작성 완료</h3>
                    <p style="color: #86868b; font-size: 14px;">{selected_dentist} 원장님 스타일로 작성되었습니다.</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Layout: 2 columns (Content vs Info)
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
                    st.subheader("블로그 본문")
                    st.markdown(generated_content)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Copy Helper
                    with st.expander("📝 텍스트 복사하기 (클릭)"):
                        st.code(generated_content, language='markdown')

                with col2:
                    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
                    st.markdown("#### 💡 참고한 글")
                    if references:
                        for idx, ref in enumerate(references, 1):
                            preview = ref[:50] + "..." if len(ref) > 50 else ref
                            st.caption(f"**RefereniCE #{idx}**")
                            st.caption(preview)
                            st.markdown("---")
                    else:
                        st.caption("참고할 데이터가 부족하여 일반적인 스타일로 작성되었습니다.")
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.error("글 생성에 실패했습니다. 잠시 후 다시 시도해주세요.")
    else:
        # Empty State / Landing View
        st.markdown("""
        <div class="apple-card" style="text-align: center; padding: 50px;">
            <h2 style="color: #1d1d1f;">AI 블로그 비서에 오신 것을 환영합니다 👋</h2>
            <p style="color: #86868b; font-size: 18px;">좌측 사이드바에서 원장님을 선택하고 주제를 입력하면,<br>우리 병원만의 스타일로 블로그 글을 자동으로 작성해드립니다.</p>
        </div>
        """, unsafe_allow_html=True)

    # Debug: Hidden by default
    # with st.expander("🔍 디버그 모드"):
    #     st.write(df)



if __name__ == "__main__":
    main()
