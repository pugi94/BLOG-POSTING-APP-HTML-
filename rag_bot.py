import streamlit as st
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document
from langchain.chains import RetrievalQA
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import threading

# --- 1. 클라우드 환경 설정 (Secrets에서 키 가져오기) ---
# Streamlit Secrets에서 키를 못 찾으면 에러 메시지를 띄움
if "GOOGLE_API_KEY" in st.secrets:
    os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]
    SLACK_BOT_TOKEN = st.secrets["SLACK_BOT_TOKEN"]
    SLACK_APP_TOKEN = st.secrets["SLACK_APP_TOKEN"]
    # JSON 키는 문자열로 저장되어 있으므로 다시 딕셔너리로 변환
    GCP_KEY_DICT = json.loads(st.secrets["gcp_service_account"]["json_key"], strict=False)
else:
    st.error("🚨 Secrets 설정이 필요합니다! (Step 2를 확인하세요)")
    st.stop()

# --- 2. RAG 두뇌 클래스 ---
class CompanyBrain:
    def __init__(self):
        self.vector_store = None
        # 요약은 정확해야 하니 temperature=0 (창의성 낮춤)
        self.llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0) 
        self.load_db()

    def load_db(self):
        """구글 시트의 모든 탭을 읽어서 지식으로 만듭니다."""
        print("📥 지식 DB 동기화 중...")
        
        try:
            # 구글 시트 접속
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(GCP_KEY_DICT, scope)
            client = gspread.authorize(creds)
            
            # 🚨 시트 이름이 다르면 여기서 에러납니다! 꼭 확인하세요.
            sh = client.open("사내_매뉴얼_DB") 
            
            documents = []
            
            # 모든 탭(Worksheet)을 돌면서 데이터 수집
            for worksheet in sh.worksheets():
                title = worksheet.title
                records = worksheet.get_all_records()
                
                for row in records:
                    # 데이터 합치기: [시트이름] 내용...
                    content_str = f"[{title}] " + " / ".join([f"{k}: {v}" for k, v in row.items()])
                    documents.append(Document(page_content=content_str))
                    
            # 벡터화 (임베딩)
            if documents:
                embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
                self.vector_store = FAISS.from_documents(documents, embeddings)
                print(f"✅ 총 {len(documents)}개의 문서를 학습했습니다.")
            else:
                print("⚠️ 시트에 데이터가 하나도 없습니다.")

        except Exception as e:
            print(f"❌ DB 로딩 실패: {e}")

    def ask(self, query):
        if not self.vector_store:
            return "지식 DB가 비어있거나 로딩되지 않았습니다. (시트 권한/이름 확인 필요)", []
            
        # 검색 + 요약 답변 생성
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 4}), # 관련 문서 4개 참조
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
            # 내용이 너무 길면 60자로 자름
            preview = doc.page_content[:60].replace("\n", " ")
            source_text += f"\n> {i+1}. {preview}..."
            
        say(
            text=f"📋 *답변:*\n{answer}\n\n📚 *참고 데이터:*{source_text}",
            thread_ts=message['ts']
        )
    except Exception as e:
        say(f"❌ 처리 중 에러 발생: {e}", thread_ts=message['ts'])

# --- 4. 메인 실행 (Streamlit + Slack Bot) ---
def run_slack_bot():
    try:
        handler = SocketModeHandler(app, SLACK_APP_TOKEN)
        handler.start()
    except Exception as e:
        print(f"봇 실행 에러: {e}")

st.title("🤖 사내 지식 봇 컨트롤러")
st.info("이 페이지가 'Running' 상태면 슬랙봇도 살아있습니다.")

if st.button("🔄 지식 DB 업데이트 (시트 수정 후 클릭)"):
    st.session_state.brain.load_db()
    st.success("최신 데이터를 반영했습니다!")

# 슬랙봇을 백그라운드에서 실행
if 'bot_thread' not in st.session_state:
    bot_thread = threading.Thread(target=run_slack_bot, daemon=True)
    bot_thread.start()
    st.session_state.bot_thread = bot_thread
    st.write("✅ 슬랙봇이 백그라운드에서 실행 중입니다.")
