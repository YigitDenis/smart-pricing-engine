import io
import pandas as pd
import streamlit as st
from engine import calculate_smart_pricing, clean_numeric

st.set_page_config(page_title="Smart Pricing Engine", layout="wide")

st.title("Akıllı Fiyatlandırma ve Karar Destek Paneli")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1VWZsQvYK7CyZQiogmgLiVovufr9gnwWboa3sBt17VMA/export?format=csv&gid=0"

@st.cache_data(ttl=3600)
def load_and_aggregate_data(url):
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    
    if "Hafta" in df.columns:
        df = df.drop(columns=["Hafta"])

    if "Stok" in df.columns:
        df["Stok_num"] = clean_numeric(df["Stok"])
    else:
        df["Stok_num"] = 0.0

    if "Satış Adeti" in df.columns:
        df["Satis_num"] = clean_numeric(df["Satış Adeti"])
    else:
        df["Satis_num"] = 0.0

    group_col = "Ürün Kodu" if "Ürün Kodu" in df.columns else "Ürün Adı"

    if group_col in df.columns:
        agg_rules = {"Stok_num": "last", "Satis_num": "sum"}
        for col in ["Ürün Adı", "Maliyet", "İndirimli Fiyat", "İlk Fiyat", "Renk Açıklaması", "ANAKATEGORİ Açıklama", "GMROI", "SMM", "PSF DEĞERİ"]:
            if col in df.columns:
                agg_rules[col] = "first"
                
        df_grouped = df.groupby(group_col, as_index=False).agg(agg_rules)
        df_grouped["Stok"] = df_grouped["Stok_num"]
        df_grouped["Satış Adeti"] = df_grouped["Satis_num"]
    else:
        df_grouped = df

    if "Maliyet" in df_grouped.columns:
        df_grouped["Maliyet"] = clean_numeric(df_grouped["Maliyet"])
    if "İndirimli Fiyat" in df_grouped.columns:
        df_grouped["İndirimli Fiyat"] = clean_numeric(df_grouped["İndirimli Fiyat"])
        
    return df_grouped

try:
    df_grouped = load_and_aggregate_data(SHEET_URL)
    st.success("Veriler başarıyla yüklendi!")

    # Sol Menü Filtre
    st.sidebar.subheader("Filtreleme Paneli")
    group_col = "Ürün Kodu" if "Ürün Kodu" in df_grouped.columns else "Ürün Adı"

    if group_col in df_grouped.columns:
        unique_codes = df_grouped[group_col].dropna().unique().tolist()
        selected_code = st.sidebar.selectbox("Ürün Kodu Seçin", ["Tümü"] + unique_codes)
        
        if selected_code != "Tümü":
            df_filtered = df_grouped[df_grouped[group_col] == selected_code]
        else:
            df_filtered = df_grouped
    else:
        df_filtered = df_grouped

    # Motoru çalıştır ve sonuçları bağımsız sütunlar olarak al
    results_df = calculate_smart_pricing(df_filtered)
    
    # İndeksleri sıfırlayıp yan yana (kolon kolon) birleştir
    df_filtered = df_filtered.reset_index(drop=True)
    results_df = results_df.reset_index(drop=True)
    
    df_result = pd.concat([df_filtered, results_df], axis=1)

    # Dashboard Metrikleri
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Toplam Çeşit", len(df_result))
    col2.metric("Toplam Stok", int(df_result["Stok"].sum()) if "Stok" in df_result.columns else 0)
    col3.metric("Toplam Satış", int(df_result["Satış Adeti"].sum()) if "Satış Adeti" in df_result.columns else 0)
    alarm_count = len(df_result[df_result["Aciliyet"].str.contains("Kırmızı Alarm", na=False)]) if "Aciliyet" in df_result.columns else 0
    col4.metric("Kırmızı Alarm", alarm_count)

    st.markdown("---")
    st.subheader("Ürün Analiz ve Sütun Bazlı Karar Matrisi")
    
    # Tabloyu tam ekran ve sütun sütun göster
    st.dataframe(df_result, use_container_width=True)

    @st.cache_data
    def convert_df_to_excel(df):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Aksiyon_Listesi")
        return output.getvalue()

    excel_data = convert_df_to_excel(df_result)

    st.download_button(
        label="📥 Sütun Bazlı Tabloyu Excel Olarak İndir",
        data=excel_data,
        file_name="akilli_fiyatlandirma_detayli.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

except Exception as e:
    st.error(f"Hata oluştu: {e}")
