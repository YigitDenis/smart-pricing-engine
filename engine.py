import io
import pandas as pd
import streamlit as st
from engine import calculate_smart_pricing, clean_numeric

st.set_page_config(page_title="Smart Pricing Engine", layout="wide")

st.title("Akıllı Fiyatlandırma ve Karar Destek Paneli")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1VWZsQvYK7CyZQiogmgLiVovufr9gnwWboa3sBt17VMA/export?format=csv&gid=0"

@st.cache_data
def load_data(url):
    return pd.read_csv(url)

try:
    df = load_data(SHEET_URL)
    st.success("Veriler Google Sheets'ten başarıyla yüklendi!")

    # Sayısal dönüşümler
    df["Stok_num"] = df["Stok"].apply(clean_numeric) if "Stok" in df.columns else 0
    df["Satis_num"] = df["Satış Adeti"].apply(clean_numeric) if "Satış Adeti" in df.columns else 0

    # Gruplama
    group_cols = [col for col in ["Ürün Kodu", "Renk Kodu"] if col in df.columns]
    if not group_cols:
        group_cols = ["Ürün Adı"] if "Ürün Adı" in df.columns else []

    if group_cols:
        df_grouped = df.groupby(group_cols, as_index=False).agg({
            "Stok_num": "last",
            "Satis_num": "sum",
            "Maliyet": "first",
            "İndirimli Fiyat": "first",
            "İlk Fiyat": "first",
            "Ürün Adı": "first",
            "Renk Açıklaması": "first"
        })
        df_grouped["Stok"] = df_grouped["Stok_num"]
        df_grouped["Satış Adeti"] = df_grouped["Satis_num"]
    else:
        df_grouped = df

    # Filtre
    unique_codes = df_grouped["Ürün Kodu"].unique().tolist() if "Ürün Kodu" in df_grouped.columns else []
    selected_code = st.sidebar.selectbox("Ürün Kodu Seçin", ["Tümü"] + unique_codes)

    if selected_code != "Tümü" and "Ürün Kodu" in df_grouped.columns:
        df_filtered = df_grouped[df_grouped["Ürün Kodu"] == selected_code]
    else:
        df_filtered = df_grouped

    # Motor
    results_df = calculate_smart_pricing(df_filtered)
    results_df.index = df_filtered.index
    df_result = pd.concat([df_filtered, results_df], axis=1)

    st.subheader("Ürün Analiz ve Aksiyon Listesi")
    st.dataframe(df_result, use_container_width=True)

    # Excel İndir
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_result.to_excel(writer, index=False, sheet_name="Aksiyon_Listesi")
    
    st.download_button(
        label="📥 Tabloyu Excel Olarak İndir",
        data=output.getvalue(),
        file_name="aksiyonlar.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

except Exception as e:
    st.error(f"Hata oluştu: {e}")
