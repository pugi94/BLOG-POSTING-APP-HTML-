import streamlit as st
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import threading

# --- 1. 클라우드 환경 설정 ---
if "GOOGLE_API_KEY" in st.secrets:
    os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]
    SLACK_BOT_TOKEN = st.secrets["SLACK_BOT_TOKEN"]
    SLACK_APP_TOKEN = st.secrets["SLACK_APP_TOKEN"]
    GCP_KEY_DICT = json.loads(st.secrets["gcp_service_account"]["json_key"], strict=False)
else:
    st.error("🚨 Secrets 설정이 필요합니다!")
    st.stop()

# --- 2. RAG 두뇌 클래스 ---
class CompanyBrain:
    def __init__(self):
        self.vector_store = None
        # ⚠️ 3.0을 쓰면 에러가 납니다! 현재 API에서 가장 안정적인 최신 버전은 1.5입니다.
        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
        self.load_db()

    def load_db(self):
        """특정 폴더 안에 있는 모든 구글 시트 파일을 읽어서 지식으로 만듭니다."""
        print("📥 그룹디 지식 DB 동기화 중...")
        
        # ▼▼▼ 지정하신 폴더 ID 유지 ▼▼▼
        TARGET_FOLDER_ID = "1_sddYuhDRy1plDrCyA8GtKItQqVj4ULf" 
        
        try:
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(GCP_KEY_DICT, scope)
            client = gspread.authorize(creds)
            drive_service = build('drive', 'v3', credentials=creds)
            
            # 폴더 내 시트 검색
            query = f"'{TARGET_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
            results = drive_service.files().list(q=query, fields="files(id, name)").execute()
            items = results.get('files', [])

            if not items:
                print("⚠️ 폴더 안에 시트가 없습니다.")
                return

            documents = []
            for item in items:
                file_id = item['id']
                file_name = item['name']
                try:
                    # print(f"📖 '{file_name}' 읽는 중...") 
                    sh = client.open_by_key(file_id) 
                    for worksheet in sh.worksheets():
                        title = worksheet.title
                        records = worksheet.get_all_records()
                        for row in records:
                            content_str = f"[{file_name}-{title}] " + " / ".join([f"{k}: {v}" for k, v in row.items()])
                            documents.append(Document(page_content=content_str))
                except Exception:
                    continue

            if documents:
                embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
                self.vector_store = FAISS.from_documents(documents, embeddings)
                print(f"✅ 총 {len(documents)}개의 문서를 학습했습니다.")
            else:
                print("⚠️ 데이터 없음")

        except Exception as e:
            print(f"❌ DB 로딩 실패: {e}")

    def ask(self, query):
        if not self.vector_store:
            return "아직 그룹디 지식 DB가 준비되지 않았어요. 잠시 후 다시 시도해주세요!", []
            
        # ⭐ [수정됨] 그룹디(GroupD) 전용 페르소나 적용
        prompt_template = """
        당신은 '그룹디(GroupD)'의 유능하고 센스 있는 AI 비서입니다.
        아래 [회사의 지식]을 참고해서 질문에 답변해 주세요.
        
        [행동 지침]:
        1. 질문이 [회사의 지식]에 있는 업무 내용이라면, 정확하고 전문적으로 답변하세요.
        2. 질문이 "안녕", "고마워", "너 누구야?" 같은 일상 대화라면, 문서에 없더라도 친절하고 재치 있게 대화하세요. 
           (예: "안녕하세요! 그룹디의 든든한 AI 비서입니다. 무엇을 도와드릴까요?")
        3. 문서에 없는 내용을 억지로 지어내지 마세요. 모르면 솔직하게 모른다고 하고 담당자에게 문의하라고 안내하세요.
        4. 답변은 항상 '해요체'(존댓말)로 정중하고 친절하게 하세요.

        [회사의 지식]:
        {context}

        [사용자 질문]:
        {question}

        [답변]:
        """
        PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])

        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 4}),
            return_source_documents=True,
            chain_type_kwargs={"prompt": PROMPT}
        )
        
        result = qa_chain.invoke({"query": query})
        return result["result"], result["source_documents"]

# ⭐ [핵심] 두뇌를 전역 캐시에 저장 (슬랙 봇 접속 오류 해결)
@st.cache_resource
def get_brain():
    return CompanyBrain()

# 두뇌 로딩
brain = get_brain()

# --- 3. 슬랙 봇 로직 ---
app = App(token=SLACK_BOT_TOKEN)

@app.message(".*")
def handle_message(message, say):
    query = message['text']
    
    # 로딩 중 메시지 (필요시 주석 해제)
    # say(f"🔍 '{query}' 확인 중...", thread_ts=message['ts'])
    
    try:
        answer, sources = brain.ask(query)
        
        source_text = ""
        # 출처가 있을 때만 표시
        if sources: 
            source_text = "\n\n📚 *참고 문서:*"
            for i, doc in enumerate(sources):
                preview = doc.page_content[:60].replace("\n", " ")
                source_text += f"\n> {i+1}. {preview}..."
            
        say(
            text=f"{answer}{source_text}",
            thread_ts=message['ts']
        )
    except Exception as e:
        say(f"❌ 에러 발생: {e}", thread_ts=message['ts'])

# --- 4. 메인 실행 ---
def run_slack_bot():
    try:
        handler = SocketModeHandler(app, SLACK_APP_TOKEN)
        handler.start()
    except Exception as e:
        print(f"봇 실행 에러: {e}")

st.title("🤖 그룹디(GroupD) 지식 봇 컨트롤러")
st.info("이 화면이 켜져 있으면 봇이 작동합니다.")

# DB 업데이트 버튼
if st.button("🔄 지식 DB 업데이트"):
    brain.load_db() 
    st.success("최신 데이터를 반영했습니다!")

if 'bot_thread' not in st.session_state:
    bot_thread = threading.Thread(target=run_slack_bot, daemon=True)
    bot_thread.start()
    st.session_state.bot_thread = bot_thread
