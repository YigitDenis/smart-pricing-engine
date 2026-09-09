import io
import pandas as pd
import streamlit as st
from engine import calculate_smart_pricing, clean_numeric

st.set_page_config(page_title="Smart Pricing Engine", layout="wide")

st.title("Akıllı Fiyatlandırma ve Karar Destek Paneli")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1VWZsQvYK7CyZQiogmgLiVovufr9gnwWboa3sBt17VMA/export?format=csv&gid=0"

@st.cache_data(ttl=600)
def load_data(url):
    return pd.read_csv(url)

try:
    df = load_data(SHEET_URL)
    st.success("Veriler başarıyla yüklendi!")

    # Hafta sütununu kaldır (Kümüle görünüm)
    if "Hafta" in df.columns:
        df = df.drop(columns=["Hafta"])

    # Sayısal sütunları güvenli dönüştür
    df["Stok"] = df["Stok"].apply(clean_numeric) if "Stok" in df.columns else 0
    df["Satış Adeti"] = df["Satış Adeti"].apply(clean_numeric) if "Satış Adeti" in df.columns else 0
    df["Maliyet"] = df["Maliyet"].apply(clean_numeric) if "Maliyet" in df.columns else 0
    df["İndirimli Fiyat"] = df["İndirimli Fiyat"].apply(clean_numeric) if "İndirimli Fiyat" in df.columns else 0

    # Basit ve hızlı kümüle gruplama (Çökme riskini önler)
    group_col = "Ürün Kodu" if "Ürün Kodu" in df.columns else ("Ürün Adı" if "Ürün Adı" in df.columns else None)

    if group_col:
        df_grouped = df.groupby(group_col, as_index=False).agg({
            "Stok": "last",
            "Satış Adeti": "sum",
            "Maliyet": "first",
            "İndirimli Fiyat": "first",
            "İlk Fiyat": "first" if "İlk Fiyat" in df.columns else "first",
            "Ürün Adı": "first" if "Ürün Adı" in df.columns else "first",
            "Renk Açıklaması": "first" if "Renk Açıklaması" in df.columns else "first"
        })
    else:
        df_grouped = df

    # Sol Menü: Ürün Kodu Filtresi
    st.sidebar.subheader("Filtreleme Paneli")
    if group_col and group_col in df_grouped.columns:
        unique_codes = df_grouped[group_col].dropna().unique().tolist()
        selected_code = st.sidebar.selectbox("Ürün Kodu Seçin", ["Tümü"] + unique_codes)
        
        if selected_code != "Tümü":
            df_filtered = df_grouped[df_grouped[group_col] == selected_code]
        else:
            df_filtered = df_grouped
    else:
        df_filtered = df_grouped

    # Karar motorunu çalıştır
    results_df = calculate_smart_pricing(df_filtered)
    results_df = results_df.reset_index(drop=True)
    df_filtered = df_filtered.reset_index(drop=True)
    
    df_result = pd.concat([df_filtered, results_df], axis=1)

    # Dashboard Özet Kartları
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Toplam Çeşit", len(df_result))
    col2.metric("Toplam Stok", int(df_result["Stok"].sum()) if "Stok" in df_result.columns else 0)
    col3.metric("Toplam Satış", int(df_result["Satış Adeti"].sum()) if "Satış Adeti" in df_result.columns else 0)
    alarm_count = len(df_result[df_result["Aciliyet"].str.contains("Kırmızı Alarm", na=False)]) if "Aciliyet" in df_result.columns else 0
    col4.metric("Kırmızı Alarm", alarm_count)

    st.markdown("---")
    st.subheader("Ürün Analiz ve Aksiyon Listesi (Kümüle)")
    st.dataframe(df_result, use_container_width=True)

    # Excel İndir
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_result.to_excel(writer, index=False, sheet_name="Aksiyon_Listesi")
    
    st.download_button(
        label="📥 Tabloyu Excel Olarak İndir",
        data=output.getvalue(),
        file_name="akilli_fiyatlandirma_kumule.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

except Exception as e:
    st.error(f"Hata oluştu: {e}")
