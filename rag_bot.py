# (파일 상단에 이 import가 없으면 추가해주세요)
from googleapiclient.discovery import build 

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
            
            # 3. 폴더 안의 스프레드시트 검색 쿼리
            # 'parents'에 폴더ID가 있고, 파일 타입이 '스프레드시트'인 것만 찾음
            query = f"'{TARGET_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
            
            results = drive_service.files().list(q=query, fields="files(id, name)").execute()
            items = results.get('files', [])

            if not items:
                print("⚠️ 폴더 안에 스프레드시트가 없거나, 봇에게 폴더 공유가 안 되어 있습니다.")
                return

            print(f"📂 폴더에서 총 {len(items)}개의 시트 파일을 발견했습니다.")
            
            documents = []
            
            # 4. 발견된 파일들을 하나씩 열어서 읽기
            for item in items:
                file_id = item['id']
                file_name = item['name']
                
                try:
                    print(f"📖 '{file_name}' 읽는 중...")
                    # 이름을 모를 수 있으니 ID로 엽니다 (더 안전함)
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
