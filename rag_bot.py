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
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import threading

# --- 1. 클라우드 환경 설정 (Secrets에서 키 가져오기) ---
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
        self.llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0)
        self.load_db()

    def load_db(self):
        """특정 폴더 안에 있는 모든 구글 시트 파일을 읽어서 지식으로 만듭니다."""
        print("📥 통합 지식 DB 동기화 중...")
        
        # ▼▼▼ 여기에 복사한 폴더 ID를 넣으세요 ▼▼▼
        TARGET_FOLDER_ID = "1_sddYuhDRy1plDrCyA8GtKItQqVj4ULf" 
        
        try:
            # 1. 인증 및 권한 설정
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(GCP_KEY_DICT, scope)
            client = gspread.authorize(creds)
            
            # 2. 구글 드라이브 API 연결 (폴더 검색용)
            drive_service = build('drive', 'v3', credentials=creds)
            
            # 3. 폴더 안의 스프레드시트 검색
            query = f"'{TARGET_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
            results = drive_service.files().list(q=query, fields="files(id, name)").execute()
            items = results.get('files', [])

            if not items:
                print("⚠️ 폴더 안에 스프레드시트가 없거나, 봇에게 폴더 공유가 안 되어 있습니다.")
                # (빈 벡터 스토어라도 만들지 않으면 에러가 날 수 있으므로 여기서 return)
                return

            print(f"📂 폴더에서 총 {len(items)}개의 시트 파일을 발견했습니다.")
            
            documents = []
            
            # 4. 발견된 파일들을 하나씩 열어서 읽기
            for item in items:
                file_id = item['id']
                file_name = item['name']
                
                try:
                    print(f"📖 '{file_name}' 읽는 중...")
                    # 이름을 모를 수 있으니 ID로 엽니다
                    sh = client.open_by_key(file_id) 
                    
                    for worksheet in sh.worksheets():
                        title = worksheet.title
                        records = worksheet.get_all_records()
                        
                        for row in records:
                            # [파일명-탭이름] 내용...
                            content_str = f"[{file_name}-{title}] " + " / ".join([f"{k}: {v}" for k, v in row.items()])
                            documents.append(Document(page_content=content_str))
                            
                except Exception as e:
                    print(f"⚠️ '{file_name}' 읽기 실패: {e}")
                    continue

            # 5. 벡터화 (임베딩)
            if documents:
                embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
                self.vector_store = FAISS.from_documents(documents, embeddings)
                print(f"✅ 총 {len(documents)}개의 문서를 학습했습니다.")
            else:
                print("⚠️ 읽어온 데이터가 없습니다.")

        except Exception as e:
            print(f"❌ DB 로딩 실패: {e}")

    def ask(self, query):
        if not self.vector_store:
            return "지식 DB가 비어있거나 로딩되지 않았습니다. (폴더 ID / 공유 권한 확인)", []
            
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 4}),
            return_source_documents=True
        )
        result = qa_chain.invoke({"query": query})
        return result["result"], result["source_documents"]

# 전역 두뇌 생성
if 'brain' not in st.session_state:
    st.session_state.brain = CompanyBrain()

# --- 3. 슬랙 봇 로직 ---
app = App(token=SLACK_BOT_TOKEN)

@app.message(".*")
def handle_message(message, say):
    query = message['text']
    say(f"🔍 *'{query}'* 관련 내용을 찾는 중입니다...", thread_ts=message['ts'])
    
    try:
        answer, sources = st.session_state.brain.ask(query)
        
        # 출처 깔끔하게 정리
        source_text = ""
        for i, doc in enumerate(sources):
            preview = doc.page_content[:60].replace("\n", " ")
            source_text += f"\n> {i+1}. {preview}..."
            
        say(
            text=f"📋 *답변:*\n{answer}\n\n📚 *참고 데이터:*{source_text}",
            thread_ts=message['ts']
        )
    except Exception as e:
        say(f"❌ 처리 중 에러 발생: {e}", thread_ts=message['ts'])

# --- 4. 메인 실행 ---
def run_slack_bot():
    try:
        handler = SocketModeHandler(app, SLACK_APP_TOKEN)
        handler.start()
    except Exception as e:
        print(f"봇 실행 에러: {e}")

st.title("🤖 사내 지식 봇 컨트롤러")
st.info("Running 상태면 봇이 작동 중입니다.")

if st.button("🔄 지식 DB 업데이트"):
    st.session_state.brain.load_db()
    st.success("최신 데이터를 반영했습니다!")

if 'bot_thread' not in st.session_state:
    bot_thread = threading.Thread(target=run_slack_bot, daemon=True)
    bot_thread.start()
    st.session_state.bot_thread = bot_thread
