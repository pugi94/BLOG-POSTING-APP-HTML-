import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import toml

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

def benchmark():
    print("Loading secrets...")
    try:
        with open(".streamlit/secrets.toml", "r", encoding="utf-8") as f:
            secrets = toml.load(f)
            creds_dict = secrets["gcp_service_account"]
    except Exception as e:
        print(f"Error loading secrets: {e}")
        return

    print("Authenticating...")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    client = gspread.authorize(creds)

    print("Opening spreadsheet...")
    spreadsheet = client.open("블로그 포스팅 DB")
    sheet = spreadsheet.sheet1

    print("Benchmarking get_all_records()...")
    start_time = time.time()
    data = sheet.get_all_records()
    end_time = time.time()
    
    print(f"Time taken: {end_time - start_time:.4f} seconds")
    print(f"Number of records: {len(data)}")

    print("-" * 20)
    
    print("Benchmarking get_all_values()...")
    start_time = time.time()
    data_values = sheet.get_all_values()
    end_time = time.time()
    print(f"Time taken: {end_time - start_time:.4f} seconds")
    print(f"Number of rows (including header): {len(data_values)}")

if __name__ == "__main__":
    benchmark()
