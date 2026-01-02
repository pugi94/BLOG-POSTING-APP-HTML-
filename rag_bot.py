# --- 2. RAG 두뇌 클래스 (멀티 시트 버전) ---
class CompanyBrain:
    def __init__(self):
        self.vector_store = None
        self.llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0)
        self.load_db()

    def load_db(self):
        """여러 개의 구글 시트 파일을 모두 읽어서 하나의 지식으로 만듭니다."""
        print("📥 통합 지식 DB 동기화 중...")
        
        # ▼▼▼ 여기에 읽고 싶은 시트 이름을 모두 적으세요 ▼▼▼
        TARGET_SPREADSHEETS = ["사내_매뉴얼_DB", "블로그_포스팅_DB", "또_다른_시트_이름"] 
        
        try:
            # 구글 시트 접속
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(GCP_KEY_DICT, scope)
            client = gspread.authorize(creds)
            
            documents = []
            
            # 파일 목록을 하나씩 돌면서 데이터 수집
            for sheet_name in TARGET_SPREADSHEETS:
                try:
                    print(f"📖 '{sheet_name}' 읽는 중...")
                    sh = client.open(sheet_name) # 파일 열기
                    
                    # 파일 안의 모든 탭(Worksheet) 읽기
                    for worksheet in sh.worksheets():
                        title = worksheet.title
                        records = worksheet.get_all_records()
                        
                        for row in records:
                            # 출처를 명확히 하기 위해 [파일명-탭이름] 형태로 저장
                            content_str = f"[{sheet_name}-{title}] " + " / ".join([f"{k}: {v}" for k, v in row.items()])
                            documents.append(Document(page_content=content_str))
                            
                except gspread.exceptions.SpreadsheetNotFound:
                    print(f"⚠️ 경고: '{sheet_name}' 파일을 찾을 수 없습니다. (공유가 되어있나요?)")
                    continue # 다음 파일로 넘어감

            # 벡터화 (임베딩)
            if documents:
                embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
                self.vector_store = FAISS.from_documents(documents, embeddings)
                print(f"✅ 총 {len(documents)}개의 문서를 학습했습니다.")
            else:
                print("⚠️ 모든 시트에 데이터가 하나도 없습니다.")

        except Exception as e:
            print(f"❌ DB 로딩 실패: {e}")

    def ask(self, query):
        if not self.vector_store:
            return "지식 DB가 비어있거나 로딩되지 않았습니다.", []
            
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 4}),
            return_source_documents=True
        )
        result = qa_chain.invoke({"query": query})
        return result["result"], result["source_documents"]
