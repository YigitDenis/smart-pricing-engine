import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import time

pd.set_option("styler.render.max_elements", 1000000)

st.set_page_config(
    page_title="Molène Executive Fiyat & İndirim Optimizasyon Paneli", 
    page_icon="🏷️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ŞİFRE KORUMA SİSTEMİ ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.subheader("🔒 Molène Güvenli Yönetici Girişi")
            pwd = st.text_input("Lütfen Yönetici Şifresini Giriniz", type="password", key="password_input")
            if st.button("Giriş Yap"):
                if pwd == "1":
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("😕 Hatalı şifre, lütfen tekrar deneyin.")
        return False
    return True

if not check_password():
    st.stop()
# ---------------------------

st.markdown("""
    <style>
        .main { background-color: #0b0f19; color: #f3f4f6; font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
        [data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #1f2937; }
        [data-testid="stSidebar"] .block-container { padding-top: 2rem; }
        h1, h2, h3 { color: #f9fafb; font-weight: 700; letter-spacing: -0.025em; }
        .stSubheader { color: #e5e7eb; border-bottom: 2px solid #1f2937; padding-bottom: 8px; margin-bottom: 20px; }
        
        [data-testid="stDataFrame"] {
            background-color: #ffffff !important;
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid #e5e7eb;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        [data-testid="stDataFrame"] iframe {
            background-color: #ffffff !important;
        }

        .stMetric {
            background: linear-gradient(135deg, #161e2e 0%, #111827 100%);
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #1f2937;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
            transition: all 0.3s ease;
        }
        [data-testid="stMetricLabel"] { font-size: 13px !important; color: #9ca3af !important; }
        [data-testid="stMetricValue"] { font-size: 22px !important; font-weight: 700 !important; color: #f9fafb !important; }

        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background-color: #111827;
            padding: 8px;
            border-radius: 10px;
            border: 1px solid #1f2937;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: transparent;
            border-radius: 6px;
            color: #9ca3af;
            padding: 10px 20px;
            font-weight: 600;
            font-size: 14px;
            border: none;
            transition: all 0.2s;
        }
        .stTabs [data-baseweb="tab"]:hover {
            color: #ffffff;
            background-color: #1f2937;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
            color: white !important;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        }
        .stSuccess, .stInfo {
            background-color: #111827;
            border: 1px solid #1f2937;
            border-left: 4px solid #3b82f6;
            color: #f3f4f6;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🏷️ Molène Executive Fiyat, İndirim & Simülasyon Paneli")
st.markdown("<p style='color: #9ca3af; font-size: 14px; margin-top: -10px;'>Google E-Tablolar Canlı Entegrasyon Altyapısı</p>", unsafe_allow_html=True)

SHEET_ID = "188jdoFLyTxudrz9cvzF7JV9c_EDxpUbATSpVOkPwoM4"
sheet_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&t={int(time.time())}"

def extract_week_num(week_str):
    match = re.search(r'(\d+)', str(week_str))
    return int(match.group(1)) if match else 0

def format_tr_int(val):
    try:
        return f"{int(val):,}".replace(",", ".")
    except:
        return "0"

def format_tr_float(val):
    try:
        formatted = f"{float(val):,.2f}"
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0,00"

def clean_numeric(val):
    if pd.isna(val):
        return 0.0
    val_str = str(val).strip()
    if val_str == '' or val_str.lower() == 'nan':
        return 0.0
    val_str = val_str.replace('.', '').replace(',', '.')
    try:
        return float(val_str)
    except:
        cleaned = re.sub(r'[^0-9.-]', '', val_str)
        try:
            return float(cleaned)
        except:
            return 0.0

try:
    df_data = pd.read_csv(sheet_url)
    
    column_mapping = {}
    for col in df_data.columns:
        col_clean = str(col).replace('\n', ' ').strip().lower()
        if 'hafta' in col_clean and 'ilk' not in col_clean and 'son' not in col_clean:
            column_mapping[col] = 'Hafta'
        elif col_clean == 'id':
            column_mapping[col] = 'Id'
        elif 'kategori' in col_clean:
            column_mapping[col] = 'Anakategori'
        elif 'ürün kod' in col_clean or 'urunkod' in col_clean:
            column_mapping[col] = 'Urun_Kodu'
        elif 'ürün ad' in col_clean or 'urunadi' in col_clean:
            column_mapping[col] = 'Urun_Adi'
        elif 'renk kod' in col_clean or 'renkkod' in col_clean:
            column_mapping[col] = 'Renk_Kodu'
        elif 'açıklama' in col_clean and 'renk' in col_clean:
            column_mapping[col] = 'Renk_Aciklamasi'
        elif 'satış adeti' in col_clean or 'satis' in col_clean:
            column_mapping[col] = 'Satis'
        elif col_clean == 'stok':
            column_mapping[col] = 'Stok_Data'
        elif 'ciro' in col_clean:
            column_mapping[col] = 'Ciro'
        elif 'ürün açıklama' in col_clean or 'urun aciklama' in col_clean:
            column_mapping[col] = 'Urun_Aciklama'
        elif 'ürün içeriği' in col_clean or 'urunicerigi' in col_clean:
            column_mapping[col] = 'Urun_Icerigi'
        elif 'kumaş dokusu' in col_clean or 'kumasdokusu' in col_clean:
            column_mapping[col] = 'Kumas_Dokusu'
        elif 'koleksiyon' in col_clean:
            column_mapping[col] = 'Koleksiyon'
        elif 'sezon' in col_clean:
            column_mapping[col] = 'Sezon'
            
    df_data = df_data.rename(columns=column_mapping)
    
    expected_cols = [
        'Hafta', 'Id', 'Anakategori', 'Urun_Kodu', 'Urun_Adi', 
        'Renk_Kodu', 'Renk_Aciklamasi', 'Satis', 'Stok_Data', 'Ciro', 
        'Urun_Aciklama', 'Urun_Icerigi', 'Kumas_Dokusu', 'Koleksiyon', 'Sezon'
    ]
    
    for i, c_name in enumerate(expected_cols):
        if c_name not in df_data.columns and len(df_data.columns) > i:
            df_data = df_data.rename(columns={df_data.columns[i]: c_name})

    df_data['Id_clean'] = df_data['Id'].astype(str).str.strip().str.upper()
    df_data['Hafta_Num'] = df_data['Hafta'].apply(extract_week_num)
    
    if 'Satis' in df_data.columns:
        df_data['Satis'] = df_data['Satis'].apply(clean_numeric)
    if 'Stok_Data' in df_data.columns:
        df_data['Stok_Data'] = df_data['Stok_Data'].apply(clean_numeric)
    if 'Ciro' in df_data.columns:
        df_data['Ciro'] = df_data['Ciro'].apply(clean_numeric)

    stock_map = {}
    if 'Stok_Data' in df_data.columns:
        df_sorted_for_stock = df_data.sort_values(by=['Id_clean', 'Hafta_Num'])
        for p_id, group in df_sorted_for_stock.groupby('Id_clean'):
            if p_id and p_id != 'NAN':
                max_w_row = group.loc[group['Hafta_Num'] == group['Hafta_Num'].max()]
                latest_s_val = max_w_row.iloc[-1]['Stok_Data']
                stock_map[p_id] = int(round(latest_s_val))

    df_sorted = df_data.sort_values(by=['Id_clean', 'Hafta_Num'])
    
    agg_rows = []
    for product_id, group in df_sorted.groupby('Id_clean'):
        group_sorted = group.sort_values('Hafta_Num')
        
        first_row = group_sorted.iloc[0]
        last_row = group_sorted.iloc[-1]
        
        total_sales = int(group_sorted['Satis'].sum()) if 'Satis' in group_sorted.columns else 0
        total_ciro = float(group_sorted['Ciro'].sum()) if 'Ciro' in group_sorted.columns else 0.0
        
        obf = round(total_ciro / total_sales, 2) if total_sales > 0 else 0.0
        latest_stock = int(stock_map.get(product_id, int(round(last_row.get('Stok_Data', 0)))))
        
        urun_kodu = str(first_row.get('Urun_Kodu', '')).strip()
        urun_adi = str(first_row.get('Urun_Adi', '')).strip()
        renk_kodu = str(first_row.get('Renk_Kodu', '')).strip()
        renk = str(first_row.get('Renk_Aciklamasi', '')).strip()
        ana_kat = str(first_row.get('Anakategori', 'Diğer')).strip()
        deniz_aciklama = str(last_row.get('Urun_Aciklama', '')).strip()
        if deniz_aciklama == 'nan':
            deniz_aciklama = ""
            
        koleksiyon = str(last_row.get('Koleksiyon', '')).strip()
        sezon = str(last_row.get('Sezon', 'Sonbahar')).strip()

        total_input = total_sales + latest_stock
        st_percentage = round((total_sales / total_input) * 100, 1) if total_input > 0 else 0.0

        agg_rows.append({
            'ID': product_id,
            'Ürün Kodu': '' if urun_kodu == 'nan' else urun_kodu,
            'Ürün Adı': '' if urun_adi == 'nan' else urun_adi,
            'Renk Kodu': '' if renk_kodu == 'nan' else renk_kodu,
            'Renk': '' if renk == 'nan' else renk,
            'Anakategori': '' if ana_kat == 'nan' else ana_kat,
            'Deniz Açıklama': deniz_aciklama,
            'Koleksiyon': '' if koleksiyon == 'nan' else koleksiyon,
            'Ürün Sezonu': 'Sonbahar' if (sezon == '' or sezon.lower() == 'nan') else sezon,
            'Mevcut Fiyat (OBF)': obf,
            'Toplam Satış': total_sales,
            'Toplam Ciro': total_ciro,
            'Güncel Stok': latest_stock,
            'ST %': st_percentage
        })
        
    df_summary = pd.DataFrame(agg_rows)
    
    # --- FİYAT / İNDİRİM SİMÜLASYON PARAMETRELERİ ---
    st.sidebar.markdown("### 🎛️ Fiyat & İndirim Simülasyonu")
    global_discount_pct = st.sidebar.slider("Global İndirim Oranı (%)", min_value=0, max_value=70, value=0, step=5)
    elasticity_factor = st.sidebar.slider("Fiyat Esneklik Katsayısı (Esneklik)", min_value=0.5, max_value=3.0, value=1.5, step=0.1)

    # Simüle edilmiş metrikler
    df_summary['Simüle İndirimli Fiyat'] = round(df_summary['Mevcut Fiyat (OBF)'] * (1 - global_discount_pct / 100.0), 2)
    
    # Talep artışı: (İndirim Oranı * Esneklik)
    demand_multiplier = 1.0 + ((global_discount_pct / 100.0) * elasticity_factor)
    df_summary['Simüle Satış Adeti'] = (df_summary['Toplam Satış'] * demand_multiplier).apply(lambda x: int(round(x)))
    df_summary['Simüle Ciro'] = round(df_summary['Simüle İndirimli Fiyat'] * df_summary['Simüle Satış Adeti'], 2)

    st.success(f"🟢 Canlı E-Tablo Bağlantısı Başarılı! Toplam Model/Varyant: {len(df_summary)}")
    
    tot_satis = int(df_summary['Toplam Satış'].sum())
    tot_ciro = float(df_summary['Toplam Ciro'].sum())
    tot_stok = int(df_summary['Güncel Stok'].sum())
    sim_tot_satis = int(df_summary['Simüle Satış Adeti'].sum())
    sim_tot_ciro = float(df_summary['Simüle Ciro'].sum())
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Mevcut Toplam Satış", format_tr_int(tot_satis))
    c2.metric("Mevcut Toplam Ciro", f"{format_tr_float(tot_ciro)} TL")
    c3.metric("Simüle Satış Adeti", format_tr_int(sim_tot_satis), delta=f"{sim_tot_satis - tot_satis} adet")
    c4.metric("Simüle Toplam Ciro", f"{format_tr_float(sim_tot_ciro)} TL", delta=f"{format_tr_float(sim_tot_ciro - tot_ciro)} TL")
    c5.metric("Toplam Güncel Stok", format_tr_int(tot_stok))
    
    st.divider()

    tab1, tab2 = st.tabs([
        "📊 Fiyat & İndirim Simülasyon Tablosu",
        "🔥 En Çok Ciro Yapanlar ve Fiyat Analizi"
    ])
    
    format_dict = {
        'Mevcut Fiyat (OBF)': lambda x: f"{format_tr_float(x)} TL",
        'Simüle İndirimli Fiyat': lambda x: f"{format_tr_float(x)} TL",
        'Toplam Satış': lambda x: format_tr_int(x),
        'Simüle Satış Adeti': lambda x: format_tr_int(x),
        'Toplam Ciro': lambda x: f"{format_tr_float(x)} TL",
        'Simüle Ciro': lambda x: f"{format_tr_float(x)} TL",
        'Güncel Stok': lambda x: format_tr_int(x),
        'ST %': lambda x: f"{x}%"
    }

    with tab1:
        st.subheader("Ürün Bazlı Fiyat ve İndirim Simülasyonu")
        display_cols = [
            'ID', 'Ürün Kodu', 'Ürün Adı', 'Renk', 'Anakategori', 'Deniz Açıklama',
            'Mevcut Fiyat (OBF)', 'Simüle İndirimli Fiyat', 'Toplam Satış', 
            'Simüle Satış Adeti', 'Toplam Ciro', 'Simüle Ciro', 'Güncel Stok', 'ST %'
        ]
        available_cols = [c for c in display_cols if c in df_summary.columns]
        
        styled_df = df_summary[available_cols].style.format(format_dict)
        st.dataframe(styled_df, use_container_width=True, height=600)
        
    with tab2:
        st.subheader("🔥 En Çok Ciro Yapan Top 10 Model")
        top_revenue = df_summary.sort_values(by='Toplam Ciro', ascending=False).head(10)
        styled_top = top_revenue[available_cols].style.format(format_dict)
        st.dataframe(styled_top, use_container_width=True, height=450)
            
    st.divider()
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_summary.to_excel(writer, index=False, sheet_name='Fiyat_Simulasyon_Raporu')
        top_revenue.to_excel(writer, index=False, sheet_name='Top_Ciro_Yapanlar')
        
    processed_data = output.getvalue()
    
    st.download_button(
        label="📥 Fiyat ve Simülasyon Raporunu Excel Olarak İndir",
        data=processed_data,
        file_name="Molene_Fiyat_Simulasyon_Raporu.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

except Exception as e:
    st.error(f"⚠️ Google E-Tablo okunurken hata oluştu: {e}")
    st.info("Lütfen Google E-Tablonuzun 'Bağlantıya sahip olan herkes görüntüleyebilir' şeklinde paylaşıma açık olduğundan emin olun.")
