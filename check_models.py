import google.generativeai as genai
import streamlit as st
import os

# Load secrets directly or handle if not present (assuming we run this in the env where secrets are or we might need to parse toml manually if running as script)
# easier to just parse the toml file manually for this script since streamlits secrets management works best inside streamlit app
import toml

try:
    with open(".streamlit/secrets.toml", "r", encoding="utf-8") as f:
        secrets = toml.load(f)
        api_key = secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        
        print("Listing available models...")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
except Exception as e:
    print(f"Error: {e}")
