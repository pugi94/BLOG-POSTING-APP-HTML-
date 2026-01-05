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
        self.llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)
        self.load_db()

    def load_db(self):
        """특정 폴더 안에 있는 모든 구글 시트 파일을 읽어서 지식으로 만듭니다."""
        print("📥 통합 지식 DB 동기화 중...")
        
        # ▼▼▼ 여기에 복사한 폴더 ID를 넣으세요 ▼▼▼
        TARGET_FOLDER_ID = "1_sddYuhDRy1plDrCyA8GtKItQqVj4ULf" 
        
        try:
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(GCP_KEY_DICT, scope)
            client = gspread.authorize(creds)
            drive_service = build('drive', 'v3', credentials=creds)
            
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
                    # print(f"📖 '{file_name}' 읽는 중...") # 로그가 너무 많으면 주석 처리
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
            return "아직 지식 DB가 준비되지 않았어요. 잠시 후 다시 시도해주세요!", []
            
        prompt_template = """
        당신은 회사의 유능하고 친절한 AI 비서입니다.
        아래 [회사의 지식]을 참고해서 질문에 답변해 주세요.
        
        규칙:
        1. [회사의 지식]에 있는 내용이라면, 그 내용을 바탕으로 상세하게 답변하세요.
        2. [회사의 지식]과 관련 없는 일상적인 대화(인사, 농담 등)라면, 당신의 AI 능력을 발휘해 자연스럽고 재치 있게 대화하세요.
        3. 모르는 내용은 솔직하게 모른다고 하고, 지어내지 마세요.
        4. 답변은 항상 친절한 존댓말로 해주세요.

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

# ⭐ [핵심 수정] 두뇌를 전역 캐시에 저장합니다 (모든 스레드 공유)
@st.cache_resource
def get_brain():
    return CompanyBrain()

# 두뇌 로딩 (이제 brain 변수는 어디서든 접근 가능)
brain = get_brain()

# --- 3. 슬랙 봇 로직 ---
app = App(token=SLACK_BOT_TOKEN)

@app.message(".*")
def handle_message(message, say):
    query = message['text']
    
    # 로딩 중 메시지 (선택 사항)
    # say(f"🔍...", thread_ts=message['ts'])
    
    try:
        # ⭐ [수정됨] st.session_state 대신 전역 brain 변수 사용
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

st.title("🤖 사내 지식 봇 컨트롤러")
st.info("이 화면이 켜져 있으면 봇이 작동합니다.")

# DB 업데이트 버튼
if st.button("🔄 지식 DB 업데이트"):
    brain.load_db() # 전역 brain 객체를 바로 업데이트
    st.success("최신 데이터를 반영했습니다!")

if 'bot_thread' not in st.session_state:
    bot_thread = threading.Thread(target=run_slack_bot, daemon=True)
    bot_thread.start()
    st.session_state.bot_thread = bot_thread
