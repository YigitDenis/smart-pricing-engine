import io
import traceback
import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Smart Pricing Engine",
    page_icon="💰",
    layout="wide"
)

st.title("Akıllı Fiyatlandırma ve Karar Destek Paneli")


# ============================================================
# GOOGLE SHEETS
# ============================================================

SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1VWZsQvYK7CyZQiogmgLiVovufr9gnwWboa3sBt17VMA/"
    "export?format=csv&gid=0"
)


# ============================================================
# SAYISAL VERİ TEMİZLEME
# ============================================================

def clean_numeric(series):

    if isinstance(series, (int, float, np.integer, np.floating)):
        return float(series)

    if not isinstance(series, pd.Series):
        series = pd.Series([series])

    s = series.astype(str).str.strip()

    # Boş / null değerler
    s = s.replace(
        ["", "nan", "None", "NaN", "null", "NULL"],
        np.nan
    )

    # Türkçe sayı formatı:
    # 1.250,50 -> 1250.50
    s = (
        s.str.replace(".", "", regex=False)
         .str.replace(",", ".", regex=False)
    )

    return pd.to_numeric(
        s,
        errors="coerce"
    ).fillna(0.0)


# ============================================================
# KOLON BULMA YARDIMCISI
# ============================================================

def find_column(df, candidates):

    for col in candidates:
        if col in df.columns:
            return col

    return None


# ============================================================
# VERİYİ YÜKLE + ID BAZLI KÜMÜLE ET
# ============================================================

@st.cache_data(ttl=3600)
def load_and_aggregate_data(url):

    # --------------------------------------------------------
    # CSV OKU
    # --------------------------------------------------------

    df = pd.read_csv(url)

    # Güvenlik kontrolü
    if isinstance(df, pd.Series):
        df = df.to_frame().T

    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            f"CSV sonucu DataFrame olmalı. "
            f"Gelen tip: {type(df)}"
        )

    # Kolon isimlerini temizle
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
    )

    # --------------------------------------------------------
    # ID KOLONU
    # --------------------------------------------------------

    id_col = find_column(
        df,
        ["Id", "ID", "id"]
    )

    # --------------------------------------------------------
    # HAFTA BİLGİSİNİ KAYBETMEDEN SAYISALA ÇEVİR
    # --------------------------------------------------------

    hafta_col = find_column(
        df,
        ["Hafta", "HAFTA", "hafta"]
    )

    if hafta_col:

        df["Hafta_num"] = clean_numeric(
            df[hafta_col]
        )

    else:

        df["Hafta_num"] = 1.0

    # --------------------------------------------------------
    # STOK
    # --------------------------------------------------------

    stok_col = find_column(
        df,
        ["Stok", "Stok Adedi", "STOK"]
    )

    if stok_col:

        df["Stok_num"] = clean_numeric(
            df[stok_col]
        )

    else:

        df["Stok_num"] = 0.0

    # --------------------------------------------------------
    # SATIŞ
    # --------------------------------------------------------

    satis_col = find_column(
        df,
        [
            "Satış Adeti",
            "Satış adedi",
            "SATIŞ ADETİ"
        ]
    )

    if satis_col:

        df["Satis_num"] = clean_numeric(
            df[satis_col]
        )

    else:

        df["Satis_num"] = 0.0

    # --------------------------------------------------------
    # GİRİŞ TARİHİ VARSA TEMİZLE
    # --------------------------------------------------------

    giris_tarihi_col = find_column(
        df,
        [
            "Giriş Tarihi",
            "Giris Tarihi",
            "İlk Giriş Tarihi",
            "Tarih",
            "Tarih"
        ]
    )

    if giris_tarihi_col:

        df["Giris_Tarihi_num"] = pd.to_datetime(
            df[giris_tarihi_col],
            errors="coerce",
            dayfirst=True
        )

    # ========================================================
    # ID YOKSA KÜMÜLE ETMEDEN DEVAM
    # ========================================================

    if id_col is None:

        df_grouped = df.copy()

        df_grouped["İlk Giriş Haftası"] = (
            df_grouped["Hafta_num"]
        )

        df_grouped["Son Giriş Haftası"] = (
            df_grouped["Hafta_num"]
        )

        if giris_tarihi_col:

            df_grouped["İlk Giriş Tarihi"] = (
                df_grouped["Giris_Tarihi_num"]
            )

            df_grouped["Son Giriş Tarihi"] = (
                df_grouped["Giris_Tarihi_num"]
            )

    # ========================================================
    # ID BAZLI KÜMÜLE
    # ========================================================

    else:

        # ----------------------------------------------------
        # ÖNCE HAFTAYA GÖRE SIRALA
        # Böylece "last" gerçekten son haftayı ifade eder.
        # ----------------------------------------------------

        df = df.sort_values(
            by=[id_col, "Hafta_num"],
            ascending=[True, True]
        ).reset_index(drop=True)

        # ----------------------------------------------------
        # AGGREGATION KURALLARI
        # ----------------------------------------------------

        agg_rules = {

            # Son haftadaki stok
            "Stok_num": "last",

            # Tüm haftaların satış toplamı
            "Satis_num": "sum",

            # İlk hafta
            "Hafta_num": "min"
        }

        # ----------------------------------------------------
        # SON HAFTA
        # ----------------------------------------------------

        # Son hafta için ayrıca max hesaplayacağız.
        # İlk/son tarih için de min/max kullanacağız.

        # Diğer kolonlarda ilk değer
        excluded_cols = {
            id_col,
            "Stok_num",
            "Satis_num",
            "Stok",
            "Stok Adedi",
            "Satış Adeti",
            "Satış adedi",
            "Hafta",
            "HAFTA",
            "hafta",
            "Hafta_num",
            "Giris_Tarihi_num"
        }

        for col in df.columns:

            if col not in excluded_cols:

                agg_rules[col] = "first"

        # ----------------------------------------------------
        # GRUPLA
        # ----------------------------------------------------

        df_grouped = (
            df
            .groupby(id_col, as_index=False)
            .agg(agg_rules)
        )

        # ----------------------------------------------------
        # SON HAFTA AYRI HESAPLA
        # ----------------------------------------------------

        last_week_df = (
            df
            .groupby(id_col)["Hafta_num"]
            .max()
            .reset_index()
            .rename(
                columns={
                    "Hafta_num": "Son Giriş Haftası"
                }
            )
        )

        # ----------------------------------------------------
        # İLK HAFTA
        # ----------------------------------------------------

        df_grouped = df_grouped.rename(
            columns={
                "Hafta_num": "İlk Giriş Haftası"
            }
        )

        # ----------------------------------------------------
        # SON HAFTA BİRLEŞTİR
        # ----------------------------------------------------

        df_grouped = df_grouped.merge(
            last_week_df,
            on=id_col,
            how="left"
        )

        # ----------------------------------------------------
        # GİRİŞ TARİHLERİ
        # ----------------------------------------------------

        if giris_tarihi_col:

            first_date_df = (
                df
                .groupby(id_col)["Giris_Tarihi_num"]
                .min()
                .reset_index()
                .rename(
                    columns={
                        "Giris_Tarihi_num":
                        "İlk Giriş Tarihi"
                    }
                )
            )

            last_date_df = (
                df
                .groupby(id_col)["Giris_Tarihi_num"]
                .max()
                .reset_index()
                .rename(
                    columns={
                        "Giris_Tarihi_num":
                        "Son Giriş Tarihi"
                    }
                )
            )

            df_grouped = df_grouped.merge(
                first_date_df,
                on=id_col,
                how="left"
            )

            df_grouped = df_grouped.merge(
                last_date_df,
                on=id_col,
                how="left"
            )

        # ----------------------------------------------------
        # STOK VE SATIŞ İSİMLERİNİ GERİ GETİR
        # ----------------------------------------------------

        df_grouped["Stok"] = (
            df_grouped["Stok_num"]
        )

        df_grouped["Satış Adeti"] = (
            df_grouped["Satis_num"]
        )

        # Yardımcı kolonları kaldır
        df_grouped = df_grouped.drop(
            columns=[
                "Stok_num",
                "Satis_num"
            ],
            errors="ignore"
        )

    # ========================================================
    # MALİYET
    # ========================================================

    cost_col = find_column(
        df_grouped,
        [
            "Maliyet",
            "SMM",
            "Cost"
        ]
    )

    if cost_col:

        df_grouped[cost_col] = clean_numeric(
            df_grouped[cost_col]
        )

        if cost_col != "Maliyet":

            df_grouped["Maliyet"] = (
                df_grouped[cost_col]
            )

    else:

        df_grouped["Maliyet"] = 0.0

    # ========================================================
    # FİYAT
    # ========================================================

    price_col = find_column(
        df_grouped,
        [
            "İndirimli Fiyat",
            "PSF DEĞERİ",
            "Mevcut Fiyat",
            "İlk Fiyat"
        ]
    )

    if price_col:

        df_grouped[price_col] = clean_numeric(
            df_grouped[price_col]
        )

        if price_col != "İndirimli Fiyat":

            df_grouped["İndirimli Fiyat"] = (
                df_grouped[price_col]
            )

    else:

        df_grouped["İndirimli Fiyat"] = 0.0

    # ========================================================
    # SON GÜVENLİK KONTROLÜ
    # ========================================================

    if not isinstance(
        df_grouped,
        pd.DataFrame
    ):

        raise TypeError(
            "Kümüle edilen veri DataFrame değil!"
        )

    return df_grouped


# ============================================================
# SMART PRICING ENGINE
# ============================================================

def calculate_smart_pricing(df):

    # --------------------------------------------------------
    # DATAFRAME KONTROLÜ
    # --------------------------------------------------------

    if not isinstance(df, pd.DataFrame):

        raise TypeError(
            "calculate_smart_pricing() "
            "DataFrame bekliyor. "
            f"Gelen veri tipi: {type(df)}"
        )

    # --------------------------------------------------------
    # MALİYET
    # --------------------------------------------------------

    cost_source = df.get(
        "Maliyet",
        df.get(
            "SMM",
            df.get(
                "Cost",
                pd.Series(
                    0.0,
                    index=df.index
                )
            )
        )
    )

    cost = clean_numeric(
        cost_source
    )

    # --------------------------------------------------------
    # MEVCUT FİYAT
    # --------------------------------------------------------

    price_source = df.get(
        "İndirimli Fiyat",
        df.get(
            "PSF DEĞERİ",
            df.get(
                "Mevcut Fiyat",
                df.get(
                    "İlk Fiyat",
                    pd.Series(
                        0.0,
                        index=df.index
                    )
                )
            )
        )
    )

    current_price = clean_numeric(
        price_source
    )

    # --------------------------------------------------------
    # STOK
    # --------------------------------------------------------

    stock_source = df.get(
        "Stok",
        df.get(
            "Stok Adedi",
            pd.Series(
                0.0,
                index=df.index
            )
        )
    )

    stock_qty = clean_numeric(
        stock_source
    )

    # --------------------------------------------------------
    # SATIŞ
    # --------------------------------------------------------

    sales_source = df.get(
        "Satış Adeti",
        df.get(
            "Satış adedi payı",
            pd.Series(
                0.0,
                index=df.index
            )
        )
    )

    total_sales = clean_numeric(
        sales_source
    )

    # ========================================================
    # AKTİF HAFTA
    # ========================================================

    if (
        "İlk Giriş Haftası" in df.columns
        and
        "Son Giriş Haftası" in df.columns
    ):

        first_week = clean_numeric(
            df["İlk Giriş Haftası"]
        )

        last_week = clean_numeric(
            df["Son Giriş Haftası"]
        )

        active_weeks = np.maximum(
            1.0,
            (last_week - first_week) + 1.0
        )

    else:

        active_weeks = np.ones(
            len(df),
            dtype=float
        )

    # ========================================================
    # HAFTALIK SATIŞ HIZI
    # ========================================================

    weekly_sales_rate = np.divide(
        total_sales,
        active_weeks,
        out=np.zeros_like(
            total_sales,
            dtype=float
        ),
        where=active_weeks > 0
    )

    # ========================================================
    # WOS
    # ========================================================

    wos = np.where(
        weekly_sales_rate <= 0,
        99.0,
        stock_qty / weekly_sales_rate
    )

    # ========================================================
    # ENVANTER MALİYETİ
    # ========================================================

    inventory_cost = (
        stock_qty * cost
    )

    # ========================================================
    # BRÜT KÂR
    # ========================================================

    # Eğer Satılan Net Kâr kolonu varsa onu kullan.
    # Yoksa:
    #
    # (Satış Fiyatı - Maliyet) × Satış Adedi

    if "Satılan Net Kâr" in df.columns:

        realized_profit = clean_numeric(
            df["Satılan Net Kâr"]
        )

    else:

        realized_profit = (
            current_price - cost
        ) * total_sales

    # ========================================================
    # GMROI
    # ========================================================

    gmroi = np.where(
        inventory_cost > 0,
        realized_profit / inventory_cost,
        0.0
    )

    # ========================================================
    # TABAN FİYAT
    # ========================================================

    min_allowable_price = (
        cost * 1.20
    )

    # ========================================================
    # KARAR MATRİSİ
    # ========================================================

    mask_high_performer = (
        (wos < 3)
        &
        (gmroi > 2.0)
    )

    mask_tier1_discount = (
        (wos > 10)
        |
        (gmroi < 0.5)
        |
        (
            (weekly_sales_rate == 0)
            &
            (stock_qty > 5)
        )
    )

    mask_liquidation = (
        (wos > 15)
        &
        (gmroi < 0.2)
    )

    # ========================================================
    # AKSİYON
    # ========================================================

    action = np.select(

        [
            mask_liquidation,
            mask_tier1_discount,
            mask_high_performer
        ],

        [
            "Tasfiye İndirimi (%30)",
            "1. Kademe İndirim (%15)",
            "Fiyat Artır / Koru"
        ],

        default="Fiyatı Koru (Optimum)"
    )

    # ========================================================
    # ACİLİYET
    # ========================================================

    urgency = np.select(

        [
            mask_liquidation,
            mask_tier1_discount,
            mask_high_performer
        ],

        [
            "Yüksek",
            "Orta",
            "Düşük"
        ],

        default="Normal"
    )

    # ========================================================
    # ÖNERİLEN FİYAT
    # ========================================================

    suggested_price = np.select(

        [
            mask_liquidation,
            mask_tier1_discount
        ],

        [
            current_price * 0.70,
            current_price * 0.85
        ],

        default=current_price
    )

    # ========================================================
    # STOP LOSS
    # ========================================================

    is_under_stoploss = (
        suggested_price
        <
        min_allowable_price
    )

    suggested_price = np.where(
        is_under_stoploss,
        min_allowable_price,
        suggested_price
    )

    urgency = np.where(
        is_under_stoploss,
        "Kırmızı Alarm (Taban Fiyat)",
        urgency
    )

    # ========================================================
    # İNDİRİM ORANI
    # ========================================================

    discount_rate = np.where(

        current_price > 0,

        np.round(
            (
                1
                -
                (
                    suggested_price
                    /
                    current_price
                )
            )
            * 100,
            2
        ),

        0.0
    )

    discount_rate = np.maximum(
        0.0,
        discount_rate
    )

    # ========================================================
    # SONUÇ DATAFRAME
    # ========================================================

    return pd.DataFrame(

        {
            "Aktif Hafta":
                np.round(
                    active_weeks,
                    1
                ),

            "Haftalık Satış Hızı":
                np.round(
                    weekly_sales_rate,
                    2
                ),

            "Stok Ömrü (WOS)":
                np.round(
                    wos,
                    1
                ),

            "Envanter Maliyeti (TL)":
                np.round(
                    inventory_cost,
                    2
                ),

            "Brüt Kâr (TL)":
                np.round(
                    realized_profit,
                    2
                ),

            "GMROI Verimliliği":
                np.round(
                    gmroi,
                    2
                ),

            "Önerilen Aksiyon":
                action,

            "Aciliyet Seviyesi":
                urgency,

            "Önerilen Yeni Fiyat (TL)":
                np.round(
                    suggested_price,
                    2
                ),

            "Önerilen İndirim (%)":
                discount_rate
        },

        index=df.index
    )


# ============================================================
# ANA UYGULAMA
# ============================================================

try:

    # --------------------------------------------------------
    # VERİYİ YÜKLE
    # --------------------------------------------------------

    df_grouped = load_and_aggregate_data(
        SHEET_URL
    )

    st.success(
        "Veriler Google Sheets'ten başarıyla "
        "yüklendi ve Id bazlı kümüle edildi!"
    )

    # --------------------------------------------------------
    # DEBUG / DATAFRAME KONTROLÜ
    # --------------------------------------------------------

    if not isinstance(
        df_grouped,
        pd.DataFrame
    ):

        raise TypeError(
            f"df_grouped DataFrame değil: "
            f"{type(df_grouped)}"
        )

    # --------------------------------------------------------
    # ID KOLONU
    # --------------------------------------------------------

    id_col = find_column(
        df_grouped,
        ["Id", "ID", "id"]
    )

    # --------------------------------------------------------
    # FİLTRE KOLONU
    # --------------------------------------------------------

    if id_col:

        filter_col = id_col

    elif "Ürün Kodu" in df_grouped.columns:

        filter_col = "Ürün Kodu"

    elif "Ürün Adı" in df_grouped.columns:

        filter_col = "Ürün Adı"

    else:

        filter_col = None

    # ========================================================
    # SIDEBAR
    # ========================================================

    st.sidebar.subheader(
        "🔎 Filtreleme Paneli"
    )

    if (
        filter_col
        and
        filter_col in df_grouped.columns
    ):

        unique_codes = (
            df_grouped[filter_col]
            .dropna()
            .unique()
            .tolist()
        )

        selected_code = st.sidebar.selectbox(

            f"{filter_col} Seçin",

            ["Tümü"]
            +
            [
                str(x)
                for x in unique_codes
            ]
        )

        if selected_code != "Tümü":

            df_filtered = (
                df_grouped[
                    df_grouped[
                        filter_col
                    ]
                    .astype(str)
                    ==
                    str(selected_code)
                ]
                .copy()
            )

        else:

            df_filtered = (
                df_grouped.copy()
            )

    else:

        df_filtered = (
            df_grouped.copy()
        )

    # --------------------------------------------------------
    # INDEX SIFIRLA
    # --------------------------------------------------------

    df_filtered = (
        df_filtered
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # SMART PRICING MOTORU
    # --------------------------------------------------------

    if not isinstance(
        df_filtered,
        pd.DataFrame
    ):

        raise TypeError(
            f"df_filtered DataFrame değil: "
            f"{type(df_filtered)}"
        )

    metrics_df = calculate_smart_pricing(
        df_filtered
    )

    if not isinstance(
        metrics_df,
        pd.DataFrame
    ):

        raise TypeError(
            f"metrics_df DataFrame değil: "
            f"{type(metrics_df)}"
        )

    # --------------------------------------------------------
    # METRİKLERİ ANA DATAFRAME'E EKLE
    # --------------------------------------------------------

    for col in metrics_df.columns:

        df_filtered[col] = (
            metrics_df[col].values
        )

    df_result = df_filtered.copy()

    # ========================================================
    # DASHBOARD
    # ========================================================

    col1, col2, col3, col4 = st.columns(4)

    # Çeşit
    col1.metric(
        "Toplam Çeşit / Id",
        len(df_result)
    )

    # Stok
    if "Stok" in df_result.columns:

        total_stock = int(
            clean_numeric(
                df_result["Stok"]
            ).sum()
        )

    else:

        total_stock = 0

    col2.metric(
        "Toplam Stok",
        total_stock
    )

    # Satış
    if "Satış Adeti" in df_result.columns:

        total_sales = int(
            clean_numeric(
                df_result["Satış Adeti"]
            ).sum()
        )

    else:

        total_sales = 0

    col3.metric(
        "Toplam Satış",
        total_sales
    )

    # Kırmızı alarm
    if (
        "Aciliyet Seviyesi"
        in df_result.columns
    ):

        alarm_count = len(
            df_result[
                df_result[
                    "Aciliyet Seviyesi"
                ]
                .astype(str)
                .str.contains(
                    "Kırmızı Alarm",
                    na=False
                )
            ]
        )

    else:

        alarm_count = 0

    col4.metric(
        "🚨 Kırmızı Alarm",
        alarm_count
    )

    # ========================================================
    # İKİNCİ DASHBOARD
    # ========================================================

    st.markdown("---")

    st.subheader(
        "📊 Genel Performans"
    )

    m1, m2, m3, m4 = st.columns(4)

    if len(df_result) > 0:

        avg_wos = (
            pd.to_numeric(
                df_result[
                    "Stok Ömrü (WOS)"
                ],
                errors="coerce"
            )
            .replace(
                [np.inf, -np.inf],
                np.nan
            )
            .mean()
        )

        avg_gmroi = (
            pd.to_numeric(
                df_result[
                    "GMROI Verimliliği"
                ],
                errors="coerce"
            )
            .replace(
                [np.inf, -np.inf],
                np.nan
            )
            .mean()
        )

        total_profit = (
            pd.to_numeric(
                df_result[
                    "Brüt Kâr (TL)"
                ],
                errors="coerce"
            )
            .fillna(0)
            .sum()
        )

        avg_discount = (
            pd.to_numeric(
                df_result[
                    "Önerilen İndirim (%)"
                ],
                errors="coerce"
            )
            .fillna(0)
            .mean()
        )

    else:

        avg_wos = 0
        avg_gmroi = 0
        total_profit = 0
        avg_discount = 0

    m1.metric(
        "Ortalama WOS",
        f"{avg_wos:.1f} hafta"
    )

    m2.metric(
        "Ortalama GMROI",
        f"{avg_gmroi:.2f}"
    )

    m3.metric(
        "Toplam Brüt Kâr",
        f"{total_profit:,.2f} TL"
    )

    m4.metric(
        "Ort. Önerilen İndirim",
        f"%{avg_discount:.1f}"
    )

    # ========================================================
    # TABLO
    # ========================================================

    st.markdown("---")

    st.subheader(
        "📋 Ürün Bazlı Kümüle Fiyat ve Karar Analizi"
    )

    st.dataframe(
        df_result,
        use_container_width=True,
        hide_index=True
    )

    # ========================================================
    # EXCEL
    # ========================================================

    @st.cache_data
    def convert_df_to_excel(df):

        output = io.BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:

            df.to_excel(
                writer,
                index=False,
                sheet_name="Aksiyon_Listesi"
            )

        return output.getvalue()

    excel_data = (
        convert_df_to_excel(
            df_result
        )
    )

    st.download_button(

        label="📥 Net Raporu Excel Olarak İndir",

        data=excel_data,

        file_name=(
            "akilli_fiyatlandirma_kumule.xlsx"
        ),

        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )


# ============================================================
# HATA YAKALAMA
# ============================================================

except Exception as e:

    st.error(
        f"❌ Uygulama çalışırken hata oluştu: {e}"
    )

    # Gerçek hata satırını göster
    with st.expander(
        "🔧 Teknik hata detayını göster"
    ):

        st.code(
            traceback.format_exc(),
            language="text"
        )
