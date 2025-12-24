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
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif;
    }
    
    /* Header Styling */
    h1 {
        color: #2c3e50;
        font-weight: 700;
        padding-bottom: 1rem;
        border-bottom: 2px solid #eee;
    }
    
    /* Button Styling */
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #4CAF50 0%, #45a049 100%);
        color: white;
        border: none;
        padding: 0.8rem;
        border-radius: 10px;
        font-weight: bold;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(0,0,0,0.15);
    }
    
    /* Card/Container Styling */
    .css-1r6slb0, .stMarkdown {
        border-radius: 10px;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa;
        border-right: 1px solid #eee;
    }
    
    /* Success Message */
    .stSuccess {
        background-color: #d4edda;
        color: #155724;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    st.title("🦷 치과 블로그 포스팅 AI 생성기")
    st.markdown("원장님의 과거 글 스타일을 분석하여 새로운 블로그 글을 작성해드립니다.")

    # Load Data
    with st.spinner("데이터를 불러오는 중..."):
        df = load_data()

    if df.empty:
        st.error("데이터를 불러오지 못했습니다. .streamlit/secrets.toml 설정을 확인해주세요.")
        return

    # Sidebar
    with st.sidebar:
        st.header("📝 설정 입력")
        
        # 1. Dentist Selection
        # Ensure all values are strings to avoid TypeError during sort
        dentists = df['DentistName'].unique().tolist()
        dentist_list = sorted([str(d) for d in dentists])
        selected_dentist = st.selectbox("치과(원장님) 선택", dentist_list)
        
        # 2. Input Fields
        topic = st.text_input("작성할 주제", placeholder="예: 임플란트 수술 후 주의사항")
        keyword = st.text_input("핵심 키워드", placeholder="예: 안 아픈 치과, 임플란트")
        
        st.markdown("---")
        
        # 3. Generate Button
        generate_btn = st.button("포스팅 생성하기 ✨")

    # Main Area
    if generate_btn:
        if not topic or not keyword:
            st.warning("주제와 핵심 키워드를 모두 입력해주세요!")
        else:
            with st.spinner(f"'{selected_dentist}' 원장님의 스타일을 분석하여 글을 작성 중입니다... 🤖"):
                # Call Gemini Logic
                generated_content, references = generate_blog_post(selected_dentist, topic, keyword)
            
            if generated_content:
                st.success("작성 완료! 🎉")
                
                # Layout: 2 columns (Content vs Info)
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.subheader("📄 생성된 블로그 글")
                    st.markdown(generated_content)
                    
                    # Copy Helper (Streamlit doesn't have direct copy-to-clipboard yet, using code block or text area)
                    st.markdown("### 복사하기")
                    st.code(generated_content, language='markdown')

                with col2:
                    st.info("💡 스타일에 참고한 과거 글")
                    if references:
                        for idx, ref in enumerate(references, 1):
                            # Truncate for display
                            preview = ref[:50] + "..." if len(ref) > 50 else ref
                            with st.expander(f"참고글 #{idx}"):
                                st.write(preview)
                    else:
                        st.write("참고할 데이터가 부족하여 일반적인 스타일로 작성되었습니다.")
            else:
                st.error("글 생성에 실패했습니다. 잠시 후 다시 시도해주세요.")
    
    # Debug: Show Raw Data
    with st.expander("🔍 원본 데이터 확인 (디버깅용)"):
        st.write("전체 데이터:", df)
        
        # Check for numeric values in DentistName
        if 'DentistName' in df.columns:
            # Convert to numeric, errors='coerce' turns non-numbers to NaN
            numeric_rows = df[pd.to_numeric(df['DentistName'], errors='coerce').notnull()]
            if not numeric_rows.empty:
                st.warning(f"⚠️ '치과명(DentistName)' 컬럼에 숫자로 된 데이터가 {len(numeric_rows)}건 발견되었습니다.")
                st.write("숫자로 된 데이터 예시:", numeric_rows)



if __name__ == "__main__":
    main()
