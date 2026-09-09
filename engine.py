import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import time

pd.set_option("styler.render.max_elements", 1000000)

st.set_page_config(
    page_title="Molène Executive Envanter & RPT Paneli", 
    page_icon="⚡", 
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

st.title("⚡ Molène Executive Envanter, Satış & RPT Karar Destek Paneli")
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
        
        first_week_name = str(first_row.get('Hafta', '1.Hafta')).strip()
        last_week_name = str(last_row.get('Hafta', '1.Hafta')).strip()
        
        first_week_num = first_row['Hafta_Num']
        last_week_num = last_row['Hafta_Num']
        
        weeks_in_sales = len(group_sorted['Hafta_Num'].unique())
        total_sales = int(group_sorted['Satis'].sum()) if 'Satis' in group_sorted.columns else 0
        total_ciro = float(group_sorted['Ciro'].sum()) if 'Ciro' in group_sorted.columns else 0.0
        
        obf = round(total_ciro / total_sales, 2) if total_sales > 0 else 0.0
        
        # Aktif satış süresi: İlk giriş haftasından son giriş haftasına kadar geçen net hafta sayısı (en az 1)
        active_span_weeks = max((last_week_num - first_week_num + 1), 1)
        avg_weekly_sales = round(total_sales / active_span_weeks, 1) if active_span_weeks > 0 else 0.0
        
        latest_stock = int(stock_map.get(product_id, int(round(last_row.get('Stok_Data', 0)))))
        
        last_week_sales = int(group_sorted[group_sorted['Hafta_Num'] == last_week_num]['Satis'].sum()) if 'Satis' in group_sorted.columns else 0
        prev_week_sales = int(group_sorted[group_sorted['Hafta_Num'] == (last_week_num - 1)]['Satis'].sum()) if (last_week_num - 1) in group_sorted['Hafta_Num'].values else 0
        
        weekly_growth = 0.0
        if prev_week_sales > 0:
            weekly_growth = round(((last_week_sales - prev_week_sales) / prev_week_sales) * 100, 1)
        elif last_week_sales > 0:
            weekly_growth = 100.0

        urun_kodu = str(first_row.get('Urun_Kodu', '')).strip()
        urun_adi = str(first_row.get('Urun_Adi', '')).strip()
        renk_kodu = str(first_row.get('Renk_Kodu', '')).strip()
        renk = str(first_row.get('Renk_Aciklamasi', '')).strip()
        ana_kat = str(first_row.get('Anakategori', 'Diğer')).strip()
        
        deniz_aciklama = str(last_row.get('Urun_Aciklama', '')).strip()
        if deniz_aciklama == 'nan':
            deniz_aciklama = ""
        
        urun_icerigi = str(last_row.get('Urun_Icerigi', '')).strip()
        kumas_dokusu = str(last_row.get('Kumas_Dokusu', '')).strip()
        koleksiyon = str(last_row.get('Koleksiyon', '')).strip()
        sezon = str(last_row.get('Sezon', 'Sonbahar')).strip()
        
        urun_yasam_dongusu = "Yeni Ürün (≤4 Hafta) 🚀" if active_span_weeks <= 4 else "Aktif / Olgun Ürün 📈"

        total_input = total_sales + latest_stock
        st_percentage = round((total_sales / total_input) * 100, 1) if total_input > 0 else 0.0
        
        zero_stock_weeks = group_sorted[group_sorted['Stok_Data'] <= 1]['Hafta_Num'].tolist() if 'Stok_Data' in group_sorted.columns else []
        lost_sales = 0
        if latest_stock <= 5 and avg_weekly_sales > 0 and len(zero_stock_weeks) > 0:
            first_zero_w = zero_stock_weeks[0]
            if last_week_num > first_zero_w:
                gap_weeks = last_week_num - first_zero_w
                lost_sales = int(round(gap_weeks * avg_weekly_sales))
        
        lost_sales_amount = lost_sales * obf
        
        active_weeks_with_stock = group_sorted[group_sorted['Stok_Data'] > 1]
        if len(active_weeks_with_stock) > 0:
            true_weekly_sales = round(active_weeks_with_stock['Satis'].sum() / len(active_weeks_with_stock), 1)
        else:
            true_weekly_sales = avg_weekly_sales

        true_weekly_sales = true_weekly_sales + (lost_sales / active_span_weeks if active_span_weeks > 0 else 0)

        weeks_of_supply = round(latest_stock / true_weekly_sales, 1) if true_weekly_sales > 0 else 999.0

        sezon_lower = sezon.lower()
        is_closed_season = any(s in sezon_lower for s in ['ilkbahar', 'yaz', 'spring', 'summer'])
        is_active_season = any(s in sezon_lower for s in ['sonbahar', 'sezonsuz', 'autumn', 'winter', 'mevsim'])
        
        rpt_karari = "Beklemede ⚖️"
        onerilen_rpt_adeti = 0
        
        production_lead_time = 4
        buffer_stock_weeks = 4
        target_total_weeks = production_lead_time + buffer_stock_weeks
        
        if is_closed_season:
            rpt_karari = "Sezonu Kapandı - RPT Yok 🛑"
            onerilen_rpt_adeti = 0
        elif weeks_of_supply <= 4.0 or latest_stock <= 25:
            if is_active_season or sezon == '' or sezon.lower() == 'nan':
                calc_qty = int(round((true_weekly_sales * target_total_weeks) - latest_stock))
                if calc_qty < 50:
                    rpt_karari = "Takipte / Sonraki Haftaya Sakla ⏳"
                    onerilen_rpt_adeti = max(calc_qty, 0)
                else:
                    rpt_karari = "Acil RPT Gerekli 🚀"
                    onerilen_rpt_adeti = calc_qty
            else:
                rpt_karari = "Sezon Dışı Planlama ⏳"
        else:
            rpt_karari = "Stok Yeterli ✅"

        agg_rows.append({
            'ID': product_id,
            'Ürün Kodu': '' if urun_kodu == 'nan' else urun_kodu,
            'Ürün Adı': '' if urun_adi == 'nan' else urun_adi,
            'Renk Kodu': '' if renk_kodu == 'nan' else renk_kodu,
            'Renk': '' if renk == 'nan' else renk,
            'Anakategori': '' if ana_kat == 'nan' else ana_kat,
            'Deniz Açıklama': deniz_aciklama,
            'Ürün Yaşam Döngüsü': urun_yasam_dongusu,
            'Koleksiyon': '' if koleksiyon == 'nan' else koleksiyon,
            'Ürün Sezonu': 'Sonbahar' if (sezon == '' or sezon.lower() == 'nan') else sezon,
            'RPT Kararı': rpt_karari,
            'Önerilen RPT Adeti': onerilen_rpt_adeti,
            'Mevcut Stok Kaç Hafta Gider (WOS)': f"{weeks_of_supply} Hafta",
            'Ürün İçeriği': '' if urun_icerigi == 'nan' else urun_icerigi,
            'Kumaş Dokusu': '' if kumas_dokusu == 'nan' else kumas_dokusu,
            'İlk Giriş Haftası': first_week_name,
            'Son Giriş Haftası': last_week_name,
            'Kümülatif Satış': total_sales,
            'Toplam Ciro': total_ciro,
            'Güncel Stok (Genel Depo)': latest_stock,
            'ST %': st_percentage,
            'OBF (Birim Fiyat)': obf,
            'Haftalık Ortalama Satış Adeti': round(true_weekly_sales, 1),
            'Son Hafta Satış': last_week_sales,
            'Haftalık Büyüme %': weekly_growth,
            'Satış Kaybı Adet': lost_sales,
            'Satış Kaybı Tutarı (TL)': lost_sales_amount
        })
        
    df_summary = pd.DataFrame(agg_rows)
    
    unique_weeks_sorted = sorted(df_data['Hafta'].dropna().unique().tolist(), key=lambda x: extract_week_num(x))
    
    # --- FİLTRELER ---
    st.sidebar.markdown("### 🔍 Global Ürün / Kod Arama")
    with st.sidebar.form(key='search_form'):
        search_code = st.text_input("🔑 Ürün Kodu / ID / Renk ile Ara", placeholder="Örn: D-2036 veya S-102")
        
        all_categories = ['Tümü'] + sorted(df_summary['Anakategori'].dropna().unique().tolist())
        selected_category = st.selectbox("📂 ANA KATEGORİ", options=all_categories, index=0)
        
        all_contents = ['Tümü'] + sorted(df_summary['Ürün İçeriği'].dropna().unique().tolist())
        selected_content = st.selectbox("🧵 ÜRÜN İÇERİĞİ", options=all_contents, index=0)
        
        all_textures = ['Tümü'] + sorted(df_summary['Kumaş Dokusu'].dropna().unique().tolist())
        selected_texture = st.selectbox("🧶 KUMAŞ DOKUSU", options=all_textures, index=0)
        
        all_collections = ['Tümü'] + sorted(df_summary['Koleksiyon'].dropna().unique().tolist())
        selected_collection = st.selectbox("🏷️ Koleksiyon", options=all_collections, index=0)
        
        all_seasons = ['Tümü'] + sorted(df_summary['Ürün Sezonu'].dropna().unique().tolist())
        selected_season = st.selectbox("☀️/❄️ Ürün Sezonu", options=all_seasons, index=0)
        
        all_weeks = ['Tümü'] + unique_weeks_sorted
        selected_week = st.selectbox("📅 Perakende Haftası", options=all_weeks, index=0)
        
        critical_rpt_only = st.checkbox("🚨 Sadece Acil RPT Gerekenler")
        
        submit_search = st.form_submit_button(label='Filtrele ⚡')

    df_filtered = df_summary.copy()
    
    if search_code.strip():
        s_clean = search_code.strip().lower()
        df_filtered = df_filtered[
            df_filtered['Ürün Kodu'].str.lower().str.contains(s_clean, na=False) |
            df_filtered['ID'].str.lower().str.contains(s_clean, na=False) |
            df_filtered['Renk'].str.lower().str.contains(s_clean, na=False) |
            df_filtered['Ürün Adı'].str.lower().str.contains(s_clean, na=False) |
            df_filtered['Renk Kodu'].str.lower().str.contains(s_clean, na=False)
        ]
        
    if selected_category != 'Tümü':
        df_filtered = df_filtered[df_filtered['Anakategori'] == selected_category]
    if selected_content != 'Tümü':
        df_filtered = df_filtered[df_filtered['Ürün İçeriği'] == selected_content]
    if selected_texture != 'Tümü':
        df_filtered = df_filtered[df_filtered['Kumaş Dokusu'] == selected_texture]
    if selected_collection != 'Tümü':
        df_filtered = df_filtered[df_filtered['Koleksiyon'] == selected_collection]
    if selected_season != 'Tümü':
        df_filtered = df_filtered[df_filtered['Ürün Sezonu'] == selected_season]
    
    if selected_week != 'Tümü':
        # Seçilen haftaya göre filtrelenen haftalık verilerden ilgili ID'leri süzüyoruz
        matching_ids = df_data[df_data['Hafta'] == selected_week]['Id_clean'].unique()
        df_filtered = df_filtered[df_filtered['ID'].isin(matching_ids)]
        
    if critical_rpt_only:
        df_filtered = df_filtered[df_filtered['RPT Kararı'] == 'Acil RPT Gerekli 🚀']
    # ----------------------------------------

    st.success(f"🟢 Canlı E-Tablo Bağlantısı Başarılı! Gösterilen kayıt adedi: {len(df_filtered)} / {len(df_summary)}")
    
    tot_satis = int(df_filtered['Kümülatif Satış'].sum())
    tot_ciro = float(df_filtered['Toplam Ciro'].sum())
    tot_stok = int(df_filtered['Güncel Stok (Genel Depo)'].sum())
    
    tot_lost_sales = int(df_filtered['Satış Kaybı Adet'].sum())
    tot_lost_amount = float(df_filtered['Satış Kaybı Tutarı (TL)'].sum())
    
    uretilen_toplam_adet = tot_satis + tot_stok
    global_st = round((tot_satis / uretilen_toplam_adet) * 100, 1) if uretilen_toplam_adet > 0 else 0.0
    global_obf = round(tot_ciro / tot_satis, 2) if tot_satis > 0 else 0.0
    
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Satış", format_tr_int(tot_satis))
    c2.metric("Ciro", f"{format_tr_float(tot_ciro)} TL")
    c3.metric("Genel OBF", f"{format_tr_float(global_obf)} TL")
    c4.metric("Satış Kaybı Adet", format_tr_int(tot_lost_sales))
    c5.metric("Satış Kaybı Tutarı", f"{format_tr_float(tot_lost_amount)} TL")
    c6.metric("Genel ST %", f"%{global_st}")
    c7.metric("Stok", format_tr_int(tot_stok))
    
    st.divider()

    def highlight_sales_stock(val):
        return 'background-color: #1e3a8a; color: #93c5fd; font-weight: bold;'

    def highlight_stock(val):
        return 'background-color: #065f46; color: #6ee7b7; font-weight: bold;'

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎯 ID Bazlı Satır İnceleme Modu")
    all_ids_list = ['(Seçiniz)'] + list(df_filtered['ID'].unique())
    selected_id_to_inspect = st.sidebar.selectbox("İncelemek İçin ID Seç", options=all_ids_list)

    def highlight_inspected_row(row):
        if selected_id_to_inspect != '(Seçiniz)' and str(row['ID']).strip().upper() == str(selected_id_to_inspect).strip().upper():
            return ['background-color: #7c2d12; color: #fed7aa; font-weight: bold;'] * len(row)
        return [''] * len(row)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Genel Özet & Anakategori",
        "🔥 En Çok Satan Top 10 (Toplam Satış & Güncel Stok)",
        "📦 En Çok Stoku Olan Top 10 (Güncel Stok & Toplam Satış)",
        "🚀 RPT Öneri Listesi (Kritik)",
        "🎨 Hafta Bazlı Trend Raporu"
    ])
    
    format_dict = {
        'Kümülatif Satış': lambda x: format_tr_int(x),
        'Toplam Ciro': lambda x: f"{format_tr_float(x)} TL",
        'Güncel Stok (Genel Depo)': lambda x: format_tr_int(x),
        'Önerilen RPT Adeti': lambda x: format_tr_int(x),
        'Satış Kaybı Adet': lambda x: format_tr_int(x),
        'Satış Kaybı Tutarı (TL)': lambda x: f"{format_tr_float(x)} TL",
        'OBF (Birim Fiyat)': lambda x: f"{format_tr_float(x)} TL",
        'ST %': lambda x: f"{x}%",
        'Haftalık Ortalama Satış Adeti': lambda x: f"{x:.1f}".replace(".", ",")
    }

    with tab1:
        st.subheader("Ürün / Renk Varyant Bazlı Tekil Genel Özet")
        
        display_cols_t1 = [
            'ID', 'Ürün Kodu', 'Ürün Adı', 'Renk Kodu', 'Renk', 'Anakategori', 
            'Deniz Açıklama', 'Ürün Yaşam Döngüsü', 'Koleksiyon', 'Ürün Sezonu', 
            'RPT Kararı', 'Önerilen RPT Adeti', 'Mevcut Stok Kaç Hafta Gider (WOS)', 
            'İlk Giriş Haftası', 'Son Giriş Haftası', 
            'Kümülatif Satış', 'Toplam Ciro', 'Güncel Stok (Genel Depo)', 'ST %', 
            'OBF (Birim Fiyat)', 'Satış Kaybı Adet', 'Satış Kaybı Tutarı (TL)', 
            'Haftalık Ortalama Satış Adeti', 'Ürün İçeriği', 'Kumaş Dokusu'
        ]
        available_t1_cols = [c for c in display_cols_t1 if c in df_filtered.columns]
        
        styled_df1 = df_filtered[available_t1_cols].style.apply(
            highlight_inspected_row, axis=1
        ).map(
            highlight_sales_stock, subset=['Kümülatif Satış'] if 'Kümülatif Satış' in available_t1_cols else []
        ).map(
            highlight_stock, subset=['Güncel Stok (Genel Depo)'] if 'Güncel Stok (Genel Depo)' in available_t1_cols else []
        ).format(format_dict)
        st.dataframe(styled_df1, use_container_width=True, height=600)
        
    with tab2:
        st.subheader("🔥 Bu Zamana Kadar En Çok Satan Top 10 Model (Toplam Satış & Güncel Stok)")
        top_10_sales = df_filtered.sort_values(by='Kümülatif Satış', ascending=False).head(10)
        
        t2_cols = ['ID', 'Ürün Kodu', 'Ürün Adı', 'Renk Kodu', 'Renk', 'Anakategori', 'Deniz Açıklama', 'İlk Giriş Haftası', 'Son Giriş Haftası', 'Kümülatif Satış', 'Güncel Stok (Genel Depo)', 'Mevcut Stok Kaç Hafta Gider (WOS)', 'Ürün Yaşam Döngüsü', 'Ürün Sezonu', 'RPT Kararı']
        available_t2_cols = [c for c in t2_cols if c in top_10_sales.columns]
        
        styled_top10_sales = top_10_sales[available_t2_cols].style.apply(
            highlight_inspected_row, axis=1
        ).map(
            highlight_sales_stock, subset=['Kümülatif Satış'] if 'Kümülatif Satış' in available_t2_cols else []
        ).map(
            highlight_stock, subset=['Güncel Stok (Genel Depo)'] if 'Güncel Stok (Genel Depo)' in available_t2_cols else []
        ).format(format_dict)
        st.dataframe(styled_top10_sales, use_container_width=True, height=450)

    with tab3:
        st.subheader("📦 En Çok Stoku Olan Top 10 Model (Güncel Stok & Toplam Satış)")
        top_10_stock = df_filtered.sort_values(by='Güncel Stok (Genel Depo)', ascending=False).head(10)
        
        t3_cols = ['ID', 'Ürün Kodu', 'Ürün Adı', 'Renk Kodu', 'Renk', 'Anakategori', 'Deniz Açıklama', 'İlk Giriş Haftası', 'Son Giriş Haftası', 'Güncel Stok (Genel Depo)', 'Kümülatif Satış', 'Mevcut Stok Kaç Hafta Gider (WOS)', 'Ürün Yaşam Döngüsü', 'Ürün Sezonu', 'RPT Kararı']
        available_t3_cols = [c for c in t3_cols if c in top_10_stock.columns]
        
        styled_top10_stock = top_10_stock[available_t3_cols].style.apply(
            highlight_inspected_row, axis=1
        ).map(
            highlight_sales_stock, subset=['Kümülatif Satış'] if 'Kümülatif Satış' in available_t3_cols else []
        ).map(
            highlight_stock, subset=['Güncel Stok (Genel Depo)'] if 'Güncel Satış' in available_t3_cols or 'Güncel Stok (Genel Depo)' in available_t3_cols else []
        ).format(format_dict)
        st.dataframe(styled_top10_stock, use_container_width=True, height=450)
        
    with tab4:
        st.subheader("🚀 RPT Öneri Listesi (Kritik & Optimize Edilmiş - Ürün Bazlı)")
        auto_rpt = df_filtered[df_filtered['RPT Kararı'] == 'Acil RPT Gerekli 🚀'].sort_values(by='Önerilen RPT Adeti', ascending=False)
        st.metric("Acil RPT Verilmesi Gereken Renk Varyant Adedi", len(auto_rpt))
        
        rpt_display_cols = ['ID', 'Ürün Kodu', 'Ürün Adı', 'Renk Kodu', 'Renk', 'Anakategori', 'Deniz Açıklama', 'RPT Kararı', 'Önerilen RPT Adeti', 'Mevcut Stok Kaç Hafta Gider (WOS)', 'İlk Giriş Haftası', 'Son Giriş Haftası', 'Haftalık Ortalama Satış Adeti', 'Güncel Stok (Genel Depo)', 'Kümülatif Satış', 'Ürün Yaşam Döngüsü', 'Ürün Sezonu', 'Ürün İçeriği', 'Kumaş Dokusu']
        available_rpt_cols = [c for c in rpt_display_cols if c in auto_rpt.columns]
        
        styled_rpt = auto_rpt[available_rpt_cols].style.apply(
            highlight_inspected_row, axis=1
        ).map(
            highlight_sales_stock, subset=['Haftalık Ortalama Satış Adeti'] if 'Haftalık Ortalama Satış Adeti' in available_rpt_cols else []
        ).map(
            highlight_stock, subset=['Güncel Stok (Genel Depo)'] if 'Güncel Stok (Genel Depo)' in available_rpt_cols else []
        ).format(format_dict)
        st.dataframe(styled_rpt, use_container_width=True, height=500)
        
    with tab5:
        st.subheader("📅 Hafta Bazlı Genel Satış, Ciro ve Stok Özeti")
        
        # Hafta bazlı trend için ham df_data üzerinde filtreli ID'leri grupluyoruz
        filtered_ids = df_filtered['ID'].unique()
        df_weekly_trend_source = df_data[df_data['Id_clean'].isin(filtered_ids)]
        
        df_weekly_trend = df_weekly_trend_source.groupby('Hafta').agg({
            'Satis': 'sum',
            'Ciro': 'sum',
            'Stok_Data': 'sum',
            'Id_clean': 'count'
        }).reset_index()
        
        df_weekly_trend['Hafta_Num'] = df_weekly_trend['Hafta'].apply(extract_week_num)
        df_weekly_trend = df_weekly_trend.sort_values(by='Hafta_Num').drop(columns=['Hafta_Num', 'Id_clean'])
        df_weekly_trend = df_weekly_trend.rename(columns={'Satis': 'Toplam Hafta Satışı', 'Ciro': 'Toplam Hafta Cirosu', 'Stok_Data': 'Toplam Hafta Stoku'})
        
        format_dict_trend = {
            'Toplam Hafta Satışı': lambda x: format_tr_int(x),
            'Toplam Hafta Cirosu': lambda x: f"{format_tr_float(x)} TL",
            'Toplam Hafta Stoku': lambda x: format_tr_int(x)
        }
        
        styled_trend = df_weekly_trend.style.format(format_dict_trend)
        st.dataframe(styled_trend, use_container_width=True, height=500)
            
    st.divider()
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_filtered.to_excel(writer, index=False, sheet_name='Filtrelenmis_Rapor')
        auto_rpt.to_excel(writer, index=False, sheet_name='Acil_RPT_Listesi')
        top_10_sales.to_excel(writer, index=False, sheet_name='Top_10_Satanlar')
        top_10_stock.to_excel(writer, index=False, sheet_name='Top_10_Stoklar')
        df_weekly_trend.to_excel(writer, index=False, sheet_name='Hafta_Forecast_Trend')
        
    processed_data = output.getvalue()
    
    st.download_button(
        label="📥 Tüm Raporu ve Analizleri Excel Olarak İndir (Çoklu Sekme)",
        data=processed_data,
        file_name="Molene_Executive_MultiSheet_Rapor.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

except Exception as e:
    st.error(f"⚠️ Google E-Tablo okunurken hata oluştu: {e}")
    st.info("Lütfen Google E-Tablonuzun 'Bağlantıya sahip olan herkes görüntüleyebilir' şeklinde paylaşıma açık olduğundan emin olun.")
