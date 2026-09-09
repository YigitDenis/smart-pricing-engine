import pandas as pd
import streamlit as st

st.set_page_config(page_title="Smart Pricing Engine", layout="wide")
st.title("Akıllı Fiyatlandırma ve Karar Destek Paneli")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1VWZsQvYK7CyZQiogmgLiVovufr9gnwWboa3sBt17VMA/export?format=csv&gid=0"

@st.cache_data(ttl=3600)
def load_data(url):
    return pd.read_csv(url)

try:
    df = load_data(SHEET_URL)
    st.success("Veri Google Sheets'ten başarıyla çekildi!")
    
    # Ham veriyi direkt göstererek CPU'yu koruyoruz
    st.dataframe(df.head(100), use_container_width=True)

except Exception as e:
    st.error(f"Hata: {e}")
