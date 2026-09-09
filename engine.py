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
    st.success("Veriler Google Sheets'ten başarıyla yüklendi!")

    # Hafta sütununu kümüle analiz için temizle
    if "Hafta" in df.columns:
        df = df.drop(columns=["Hafta"])

    # Sayısal alanları temizle ve hazırla
    df["Stok_num"] = df["Stok"].apply(clean_numeric) if "Stok" in df.columns else 0
    df["Satis_num"] = df["Satış Adeti"].apply(clean_numeric) if "Satış Adeti" in df.columns else 0

    # Dinamik gruplama (Ürün Kodu ve Renk Kodu varsa birleştir, yoksa Ürün Adı baz al)
    possible_group_cols = [c for c in ["Ürün Kodu", "Renk Kodu"] if c in df.columns]
    if not possible_group_cols and "Ürün Adı" in df.columns:
        possible_group_cols = ["Ürün Adı"]

    if possible_group_cols:
        aggregation_dict = {c: "first" for c in df.columns if c not in possible_group_cols + ["Stok_num", "Satis_num"]}
        if "Stok_num" in df.columns: aggregation_dict["Stok_num"] = "last"
        if "Satis_num" in df.columns: aggregation_dict["Satis_num"] = "sum"

        df_grouped = df.groupby(possible_group_cols, as_index=False).agg(aggregation_dict)
        if "Stok_num" in df_grouped.columns:
            df_grouped["Stok"] = df_grouped["Stok_num"]
        if "Satis_num" in df_grouped.columns:
            df_grouped["Satış Adeti"] = df_grouped["Satis_num"]
    else:
        df_grouped = df.copy()

    # Fiyat ve maliyetleri sayısal yap
    if "Maliyet" in df_grouped.columns:
        df_grouped["Maliyet"] = df_grouped["Maliyet"].apply(clean_numeric)
    if "İndirimli Fiyat" in df_grouped.columns:
        df_grouped["İndirimli Fiyat"] = df_grouped["İndirimli Fiyat"].apply(clean_numeric)

    # --- SOL MENÜ: ÜRÜN KODU FİLTRESİ ---
    st.sidebar.subheader("Filtreleme Paneli")
    if "Ürün Kodu" in df_grouped.columns:
        unique_codes = df_grouped["Ürün Kodu"].dropna().unique().tolist()
        selected_code = st.sidebar.selectbox("Ürün Kodu Seçin", ["Tümü"] + unique_codes)
        
        if selected_code != "Tümü":
            df_filtered = df_grouped[df_grouped["Ürün Kodu"] == selected_code]
        else:
            df_filtered = df_grouped
    else:
        df_filtered = df_grouped
        st.sidebar.info("Ürün Kodu sütunu bulunamadı.")

    # Motoru çalıştır
    results_df = calculate_smart_pricing(df_filtered)
    results_df = results_df.reset_index(drop=True)
    df_filtered = df_filtered.reset_index(drop=True)
    
    df_result = pd.concat([df_filtered, results_df], axis=1)

    # --- DASHBOARD ÖZET KARTLARI ---
    st.markdown("### 📊 Yönetici Özeti (Dashboard)")
    d_col1, d_col2, d_col3, d_col4 = st.columns(4)
    
    total_items = len(df_result)
    total_stock = int(df_result["Stok"].sum()) if "Stok" in df_result.columns else 0
    total_sales = int(df_result["Satış Adeti"].sum()) if "Satış Adeti" in df_result.columns else 0
    alarm_count = len(df_result[df_result["Aciliyet"].str.contains("Kırmızı Alarm", na=False)]) if "Aciliyet" in df_result.columns else 0

    d_col1.metric("Toplam Çeşit/Varyant", total_items)
    d_col2.metric("Toplam Güncel Stok", total_stock)
    d_col3.metric("Toplam Kümüle Satış", total_sales)
    d_col4.metric("Kırmızı Alarm (Taban Sınır)", alarm_count)

    st.markdown("---")
    st.subheader("Ürün Analiz ve Aksiyon Listesi (Kümüle)")
    st.dataframe(df_result, use_container_width=True)

    # --- DÜZGÜN EXCEL İNDİRME ---
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_result.to_excel(writer, index=False, sheet_name="Aksiyon_Listesi")
    excel_data = output.getvalue()

    st.download_button(
        label="📥 Tabloyu Excel Olarak İndir",
        data=excel_data,
        file_name="akilli_fiyatlandirma_kumule.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

except Exception as e:
    st.error(f"Veri işlenirken bir hata oluştu: {e}")
