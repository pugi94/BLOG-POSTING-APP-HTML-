import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Scope for Google Sheets and Drive API
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_data(ttl=3600)
def load_data():
    """
    Loads data from the Google Sheet 'Rawdata'.
    Uses credentials stored in streamlit.secrets.
    Returns:
        pd.DataFrame: DataFrame containing blog post data with standardized columns.
    """
    # 1. Check if secrets are available
    if "gcp_service_account" not in st.secrets:
        st.error("GCP credentials not found in .streamlit/secrets.toml")
        return pd.DataFrame()

    try:
        # 2. Authenticate
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        client = gspread.authorize(creds)

        # 3. Open Spreadsheet
        # Requires the "블로그 포스팅 DB" sheet to be shared with the service account email
        spreadsheet = client.open("블로그 포스팅 DB")
        sheet = spreadsheet.sheet1  # Access the first worksheet

        # 4. Get all records
        # Use get_all_values() instead of get_all_records() for better performance and robustness
        data = sheet.get_all_values()
        
        if not data:
            return pd.DataFrame()

        # 5. Create DataFrame (First row is header)
        headers = data.pop(0)
        df = pd.DataFrame(data, columns=headers)

        # 6. Rename columns for internal consistency (Korean -> English)
        # Expected: [날짜, 치과명, 주제, 파일위치, 기존링크, 글본문]
        column_map = {
            "날짜": "Date",
            "치과명": "DentistName",
            "주제": "Topic",
            "파일 위치": "FilePath",
            "기존 링크": "Link",
            "글 본문": "Content"
        }
        df.rename(columns=column_map, inplace=True)

        # Force 'DentistName' to be string to avoid PyArrow/Streamlit errors with mixed types (int/str)
        if 'DentistName' in df.columns:
            df['DentistName'] = df['DentistName'].astype(str)

        return df

    except gspread.exceptions.SpreadsheetNotFound:
        st.error("Spreadsheet 'Rawdata' not found. Please check the name and permissions.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

if __name__ == "__main__":
    # Local verification block
    # Note: Will only work if secrets.toml is set up correctly
    print("Attempting to load data...")
    try:
        df_result = load_data()
        if not df_result.empty:
            print(f"Success! Loaded {len(df_result)} rows.")
            print("Columns:", df_result.columns.tolist())
            print(df_result.head(2))
        else:
            print("Failed to load data or data is empty.")
    except Exception as e:
        print(f"Execution failed: {e}")
