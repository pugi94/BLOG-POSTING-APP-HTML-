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

def generate_blog_post(dentist_name, topic, keyword, style="Standard", context_input=""):
    """
    Generates a blog post using Gemini, based on the dentist's past style and selected content type.
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

        # Style Specific Instructions
        style_instruction = ""
        context_instruction = ""

        if style == "Story":
            if context_input:
                context_instruction = f"6. **환자 에피소드 (필수 반영)**: 다음 실화 내용을 바탕으로 글을 재구성하세요.\n   [에피소드]: {context_input}"
            
            style_instruction = """
            **[글 구성: 환자 스토리텔링 (Story)]**
            - 서론: "지난주 내원하셨던 환자분의 이야기입니다..." 처럼 구체적인 에피소드로 시작하세요.
            - 본문: 환자가 겪었던 고통과 고민을 생생하게 묘사하고, 치료 후 어떻게 삶이 바뀌었는지 드라마틱하게 서술하세요.
            """
        elif style == "Q&A":
            style_instruction = """
            **[글 구성: Q&A 질의응답 (FAQ)]**
            - 글 전체를 '환자분들이 가장 자주 묻는 질문 3가지'로 구성하세요.
            - Q1. 질문 -> A1. 답변 -> Q2. 질문 -> A2. 답변 형식으로 명확하게 구분하여 작성하세요.
            """
        elif style == "MythBust":
            style_instruction = """
            **[글 구성: 팩트체크 (MythBust)]**
            - 서론: "임플란트가 비쌀수록 좋다? 과연 그럴까요?" 와 같이 흔한 오해를 자극적으로 제기하세요.
            - 본문: 잘못된 상식을 조목조목 반박하며 전문가적인 식견을 뽐내세요. '오해 vs 진실' 구도를 사용하세요.
            """
        else:
            style_instruction = "**[글 구성: 기본 정보성 (Standard)]**: 일반적인 정보 전달과 병원 홍보가 균형 잡힌 구조로 작성하세요."

        # 2. Construct Prompt
        prompt = f"""
# Role: 치과 브랜드 마케팅 및 SEO 글쓰기 최고 전문가

# Context
당신은 대한민국에서 가장 글 잘 쓰기로 소문난 치과 원장님의 '페르소나'를 완벽하게 이식받은 AI입니다.
아래 제공되는 [참고 문서]를 바탕으로, 실제 원장님이 쓴 것처럼 자연스럽고 신뢰감 있는 블로그 포스팅을 작성해야 합니다.
**주의: 당신이 AI라는 사실을 절대 들키지 마세요.**

# Input Data
1. 원장님 성함: {dentist_name}
2. 글 주제: {topic}
3. 메인 키워드: {keyword}
4. **글 작문 스타일**: {style} 모드
5. 참고 문서(스타일 소스): 
[
{ref_text}
]
{context_instruction}

# Task Process (반드시 순서대로 수행)
1. **[초정밀 스타일 해부]**: [참고 문서]에서 다음 3가지 DNA를 추출하여 체화할 것.
   - **시각적 패턴**: 문단 길이, 줄바꿈 호흡, 이모지 사용 빈도 및 위치.
   - **어투(VoicePrint)**: 고유의 종결 어미(예: '~했답니다' vs '~했습니다'), 자주 쓰는 접속사/감탄사.
   - **정서적 태도**: 환자를 대하는 온도(다정한 이웃 vs 냉철한 전문가 vs 열정적인 코치).
2. **[페르소나 동기화]**: 당신의 'AI스러운' 기계적 말투를 완전히 버리고, 위에서 추출한 원장님 고유의 영혼을 장착하세요.
3. **[글 작성]**: 동기화된 페르소나로 **[글 작문 스타일]**의 구조에 맞춰 본문을 작성하세요. 마치 원장님이 직접 타자를 치는 것처럼.

# Critical Guidelines (작성 규칙)
{style_instruction}

## 1. SEO 및 키워드 전략
- **메인 키워드 배치**: 제목에 1회(가장 앞쪽 권장), 본문 첫 단락, 중간, 마지막 단락에 자연스럽게 총 5회 이상 포함.
- **LSI(연관) 키워드 활용**: 메인 키워드만 반복하지 말고, 문맥상 자연스러운 연관 단어(예: 임플란트 -> 인공치아, 식립, 치과 공포증 등)를 풍부하게 사용하여 문서의 품질(DIA+ 점수)을 높일 것.
- **동의어 변주 (중요)**: 동일한 단어(명사/형용사)의 3회 이상 반복을 피하고 유의어를 적극 활용할 것. (예: 장점 -> 이점, 강점, 좋은 점)

## 2. 모바일 최적화 포맷팅 (가장 중요)
- **호흡 단위 줄바꿈**: 문법적 문장 끝이 아니라, 읽는 사람의 호흡에 맞춰 줄을 바꿀 것. (필수)
- **여백의 미**: 2~3줄 작성 후 반드시 공백 줄(엔터)을 두 번 넣어 시각적 피로도를 낮출 것.
- **가독성 패턴**: 한 줄은 모바일 기준 20~25자를 넘지 않도록 간결하게 끊어칠 것.

## 3. 의료법 준수 및 신뢰도 확보 (매우 중요/보수적 적용)
- **절대적 표현 금지 (의료법 제56조)**: '최고', '최상', '유일', '100%', '완치', '재발 없음', '전혀 아프지 않은', '무통', '특효', '약속합니다' 등 치료 효과를 보장하거나 과장하는 단어는 **절대로 사용 불가**. 대신 '도움이 될 수 있습니다', '개선 효과를 기대할 수 있습니다'와 같이 **가능성**을 열어두는 표현을 사용할 것.
- **비교 및 비방 금지**: 타 치과와 비교하거나 우위를 점하는 표현('다른 곳보다 저렴한', '타 병원에서 포기한') 금지. 오직 해당 병원의 진료 시스템과 철학에만 집중할 것.
- **부작용 및 개인차 명시 (필수)**: 시술의 장점만 나열하지 말고, "환자의 구강 상태에 따라 치료 결과나 기간이 달라질 수 있으며, 드물게 부작용(통증, 감각 이상 등)이 발생할 수 있음"을 본문 하단이나 시술 설명 직후에 반드시 명시하여 법적 안전장치를 마련할 것.

## 4. 문체 및 톤앤매너
- **어미의 리듬감**: '~입니다/습니다' (40%), '~하죠/네요' (30%), '~까요?/가요?' (20%), '~에요/예요' (10%) 비율로 섞어 딱딱하지 않게 작성. (단, [참고 문서]의 스타일이 매우 독특하다면 그쪽을 우선 따를 것)
- **공감 화법**: 환자의 통증과 두려움에 먼저 공감하는 문장으로 시작할 것.
- **객관적 서술**: 치료 과정을 설명할 때는 감정적인 미사여구보다는 팩트 위주로 신뢰감 있게 전달할 것.

## 5. 이미지 및 요소 가이드
- 글의 몰입을 돕는 위치에 [이미지: 구체적 묘사] 형식을 삽입.
- **특수기호 금지**: 본문에 별표(**)나 샵(##) 같은 마크다운 문법 기호를 절대 사용하지 말 것. 순수 텍스트로만 작성할 것.

---

# Output Structure (출력 형식)

1. **[블로그 글 본문]** (바로 시작)
   - 제목 (맨 윗줄에 작성)
   - 도입부 (인사말 + 환자의 고민 공감 + 문제 제기)
   - 본문 1 (전문적 정보 전달 + 원장님의 철학)
   - 본문 2 (치료 과정 혹은 차별점 + 환자 안심 시키기)
   - 마무리 (요약 + 진료 철학 재강조 + 내원 유도)
   - 안내 (부작용 및 주의사항 한 줄 정리)

2. **[추천 해시태그]**: (메인 키워드 포함 10개)

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
