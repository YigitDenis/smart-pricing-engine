import pandas as pd
import streamlit as st
from engine import calculate_smart_pricing

st.set_page_config(
    page_title="Smart Pricing Engine", layout="wide"
)

st.title("Akıllı Fiyatlandırma ve Karar Destek Paneli")

# Google Sheets bağlantın
SHEET_URL = "https://docs.google.com/spreadsheets/d/1VWZsQvYK7CyZQiogmgLiVovufr9gnwWboa3sBt17VMA/export?format=csv&gid=0"


@st.cache_data
def load_data(url):
  return pd.read_csv(url)


try:
  df = load_data(SHEET_URL)
  st.success("Veriler Google Sheets'ten başarıyla yüklendi!")

  # Karar motorunu tüm satırlara uygulama
  results = df.apply(calculate_smart_pricing, axis=1)
  df_result = pd.concat([df, results], axis=1)

  st.subheader("Ürün Analiz ve Aksiyon Listesi")
  st.dataframe(df_result)

except Exception as e:
  st.error(f"Veri yüklenirken hata oluştu: {e}")
