import streamlit as st
import google.generativeai as genai
from data_loader import load_data
import random

def configure_genai():
    """Configures the Gemini API with the key from secrets."""
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("GOOGLE_API_KEY not found in secrets.")

def get_dentist_references(dentist_name, n=3):
    """
    Fetches random past posts for a specific dentist.
    """
    df = load_data()
    if df.empty:
        return []
    
    # Filter by dentist name
    dentist_posts = df[df['DentistName'] == dentist_name]
    
    if dentist_posts.empty:
        return []
    
    # Select up to n random posts
    sample_size = min(len(dentist_posts), n)
    # We use sample to get random rows
    references = dentist_posts.sample(n=sample_size)
    
    # Convert to a list of dicts or strings
    # We'll return a list of content strings
    return references['Content'].tolist()

def generate_blog_post(dentist_name, topic, keyword):
    """
    Generates a blog post using Gemini, based on the dentist's past style.
    """
    try:
        configure_genai()
        
        # 1. Get Reference Data (RAG)
        references = get_dentist_references(dentist_name)
        
        if not references:
            st.warning(f"No past data found for {dentist_name}. Generating with generic style.")
            ref_text = "참고할 과거 데이터가 없습니다."
        else:
            # Join references with a separator
            ref_text = "\n\n---\n\n".join(references)

        # 2. Construct Prompt
        prompt = f"""
당신은 치과 마케팅 전문 블로그 글쓰기 전문가입니다.
아래 [참고 문서]는 '{dentist_name}' 원장님이 평소에 작성한 블로그 글들입니다.
이 원장님의 문체, 어조, 글의 구조, 자주 쓰는 표현 등 스타일을 완벽하게 분석하여 새로운 글을 작성해주세요.

[작성 조건]
1. 주제: {topic}
2. 핵심 키워드: {keyword} (글에 자연스럽게 5회 이상 녹여낼 것)
3. 출력 형식:
   - 제목
   - 서론 (인사말 및 문제 제기)
   - 본론 (전문적인 정보 전달, 환자 공감)
   - 결론 (요약 및 내원 유도)
   - 해시태그 (5개 이상)
4. **이미지 추천**: 글의 흐름상 이미지가 들어가면 좋은 위치에 다음 형식으로 가이드를 작성하세요.
   - 형식: (괄호 안에) [이미지: 여기에 어떤 사진을 넣으면 좋을지 구체적인 묘사]
   - 예시: [이미지: 환자가 밝게 웃으며 상담받는 모습의 정면 사진]
5. 문체: [참고 문서]의 스타일을 따르되, 너무 딱딱하지 않고 환자에게 친근감을 주도록 하세요.
6. **네이버 블로그 포맷팅 (중요)**:
   - 모바일 가독성을 최우선으로 합니다.
   - **한 줄은 20~30자 내외**로 짧게 끊어서 엔터(줄바꿈)를 넣어주세요.
   - 문장 단위가 아니라 **호흡 단위**로 줄바꿈을 자주 해야 합니다.
   - 문단 사이에는 반드시 공백 줄을 넣어 여백을 확보하세요.

[참고 문서]
{ref_text}

[작성 시작]
"""

        # 3. Call Gemini API
        # User requested 3.0 Flash. Using 'gemini-3-flash-preview'.
        model = genai.GenerativeModel('gemini-3-flash-preview')
        response = model.generate_content(prompt)
        
        return response.text, references

    except Exception as e:
        st.error(f"Generation failed: {str(e)}")
        return "", []
