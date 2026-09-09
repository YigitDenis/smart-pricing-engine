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

    # Hafta sütununu tamamen devre dışı bırakıyoruz (Kümüle görünüm için)
    if "Hafta" in df.columns:
        df = df.drop(columns=["Hafta"])

    # Sayısal dönüşümler
    df["Stok_num"] = df["Stok"].apply(clean_numeric) if "Stok" in df.columns else 0
    df["Satis_num"] = df["Satış Adeti"].apply(clean_numeric) if "Satış Adeti" in df.columns else 0

    # Kümüle Gruplama Sözlüğü: Satışlar toplanır, Stok son değer alınır
    aggregation_dict = {
        "Ürün Adı": "first",
        "ANAKATEGORİ Açıklama": "first",
        "Renk Kodu": "first",
        "Renk Açıklaması": "first",
        "Ürün açıklama": "first",
        "Maliyet": "first",
        "İlk Fiyat": "first",
        "İndirimli Fiyat": "first",
        "İndirim Oranı": "first",
        "Stok_num": "last",
        "Satis_num": "sum",
    }

    group_cols = [col for col in ["Ürün Kodu", "Renk Kodu"] if col in df.columns]
    if not group_cols and "Ürün Adı" in df.columns:
        group_cols = ["Ürün Adı"]

    if group_cols:
        df_grouped = df.groupby(group_cols).agg(
            {k: v for k, v in aggregation_dict.items() if k in df.columns}
        ).reset_index()
        df_grouped["Stok"] = df_grouped["Stok_num"]
        df_grouped["Satış Adeti"] = df_grouped["Satis_num"]
    else:
        df_grouped = df.copy()

    df_grouped["Maliyet"] = df_grouped["Maliyet"].apply(clean_numeric) if "Maliyet" in df_grouped.columns else 0
    df_grouped["İndirimli Fiyat"] = df_grouped["İndirimli Fiyat"].apply(clean_numeric) if "İndirimli Fiyat" in df_grouped.columns else 0

    # --- SOL MENÜ: Ürün Kodu Filtresi ---
    st.sidebar.subheader("Filtreleme Paneli")
    unique_codes = df_grouped["Ürün Kodu"].unique().tolist() if "Ürün Kodu" in df_grouped.columns else []
    selected_code = st.sidebar.selectbox("Ürün Kodu Seçin", ["Tümü"] + unique_codes)

    if selected_code != "Tümü" and "Ürün Kodu" in df_grouped.columns:
        df_filtered = df_grouped[df_grouped["Ürün Kodu"] == selected_code]
    else:
        df_filtered = df_grouped

    # Motoru çalıştır
    results_df = calculate_smart_pricing(df_filtered)
    results_df = results_df.reset_index(drop=True)
    df_filtered = df_filtered.reset_index(drop=True)
    
    df_result = pd.concat([df_filtered, results_df], axis=1)

    # --- DASHBOARD ÖZET KARTLARI ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Toplam Ürün/Varyant", len(df_result))
    col2.metric("Toplam Stok", int(df_result["Stok"].sum()) if "Stok" in df_result.columns else 0)
    col3.metric("Toplam Satış Adeti", int(df_result["Satış Adeti"].sum()) if "Satış Adeti" in df_result.columns else 0)
    alarm_count = len(df_result[df_result["Aciliyet"].str.contains("Kırmızı Alarm", na=False)]) if "Aciliyet" in df_result.columns else 0
    col4.metric("Kırmızı Alarm (Taban)", alarm_count)

    st.markdown("---")
    st.subheader("Ürün Analiz ve Aksiyon Listesi (Kümüle)")
    st.dataframe(df_result, use_container_width=True)

    # --- EXCEL İNDİRME ---
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
    st.error(f"Hata oluştu: {e}")
