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
    
    # 1. Tip Kontrolü (DataFrame Garantisi)
    if isinstance(df, pd.Series):
        df = df.to_frame().T

    df.columns = df.columns.str.strip()
    
    # Hafta sütununu kümüle rapordan çıkarıyoruz
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

    # Id bazlı kümüle gruplama
    id_col = "Id" if "Id" in df.columns else ("ID" if "ID" in df.columns else ("id" if "id" in df.columns else None))

    if id_col and id_col in df.columns:
        agg_rules = {"Stok_num": "last", "Satis_num": "sum"}
        for col in df.columns:
            if col not in [id_col, "Stok_num", "Satis_num", "Stok", "Satış Adeti"]:
                agg_rules[col] = "first"
                
        df_grouped = df.groupby(id_col, as_index=False).agg(agg_rules)
    else:
        df_grouped = df

    # 2. Tip Kontrolü (Groupby sonrası Series kalma riskine karşı)
    if isinstance(df_grouped, pd.Series):
        df_grouped = df_grouped.to_frame().T

    df_grouped["Stok"] = df_grouped["Stok_num"]
    df_grouped["Satış Adeti"] = df_grouped["Satis_num"]
    df_grouped = df_grouped.drop(columns=["Stok_num", "Satis_num"], errors="ignore")

    if "Maliyet" in df_grouped.columns:
        df_grouped["Maliyet"] = clean_numeric(df_grouped["Maliyet"])
    if "İndirimli Fiyat" in df_grouped.columns:
        df_grouped["İndirimli Fiyat"] = clean_numeric(df_grouped["İndirimli Fiyat"])
        
    return df_grouped

try:
    df_grouped = load_and_aggregate_data(SHEET_URL)
    st.success("Veriler Id bazlı kümüle edildi ve yüklendi!")

    # Sol Menü Filtre Paneli
    st.sidebar.subheader("Filtreleme Paneli")
    id_col = "Id" if "Id" in df_grouped.columns else ("ID" if "ID" in df_grouped.columns else None)
    filter_col = id_col if id_col else ("Ürün Kodu" if "Ürün Kodu" in df_grouped.columns else "Ürün Adı")

    if filter_col and filter_col in df_grouped.columns:
        unique_codes = df_grouped[filter_col].dropna().unique().tolist()
        selected_code = st.sidebar.selectbox(f"{filter_col} Seçin", ["Tümü"] + [str(x) for x in unique_codes])
        
        if selected_code != "Tümü":
            df_filtered = df_grouped[df_grouped[filter_col].astype(str) == str(selected_code)].copy()
        else:
            df_filtered = df_grouped.copy()
    else:
        df_filtered = df_grouped.copy()

    df_filtered = df_filtered.reset_index(drop=True)

    # Motoru çalıştır
    metrics_df = calculate_smart_pricing(df_filtered)
    
    # Hesaplanan sütunları ana tabloya ekle
    for col in metrics_df.columns:
        df_filtered[col] = metrics_df[col].values

    df_result = df_filtered

    # Dashboard Metrik Kartları
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Toplam Çeşit / Id", len(df_result))
    col2.metric("Toplam Stok", int(df_result["Stok"].sum()) if "Stok" in df_result.columns else 0)
    col3.metric("Toplam Satış", int(df_result["Satış Adeti"].sum()) if "Satış Adeti" in df_result.columns else 0)
    alarm_count = len(df_result[df_result["Aciliyet Seviyesi"].str.contains("Kırmızı Alarm", na=False)]) if "Aciliyet Seviyesi" in df_result.columns else 0
    col4.metric("Kırmızı Alarm", alarm_count)

    st.markdown("---")
    st.subheader("Ürün Bazlı Kümüle Fiyat ve Karar Analizi")
    
    st.dataframe(df_result, use_container_width=True)

    @st.cache_data
    def convert_df_to_excel(df):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Aksiyon_Listesi")
        return output.getvalue()

    excel_data = convert_df_to_excel(df_result)

    st.download_button(
        label="📥 Net Raporu Excel Olarak İndir",
        data=excel_data,
        file_name="akilli_fiyatlandirma_kumule.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

except Exception as e:
    st.error(f"Hata oluştu: {e}")
