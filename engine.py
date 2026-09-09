import io
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Smart Pricing Engine", layout="wide")

st.title("Akıllı Fiyatlandırma ve Karar Destek Paneli")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1VWZsQvYK7CyZQiogmgLiVovufr9gnwWboa3sBt17VMA/export?format=csv&gid=0"


def clean_numeric(series):
  if isinstance(series, (int, float)):
    return float(series)
  if not isinstance(series, pd.Series):
    series = pd.Series([series])

  cleaned = (
      series.astype(str)
      .str.strip()
      .str.replace(".", "", regex=False)
      .str.replace(",", ".", regex=False)
  )
  return pd.to_numeric(cleaned, errors="coerce").fillna(0.0)


def calculate_smart_pricing(df):
  if isinstance(df, pd.Series):
    df = df.to_frame().T

  cost = clean_numeric(
      df.get(
          "Maliyet",
          df.get("SMM", df.get("Cost", pd.Series([0] * len(df)))),
      )
  )
  current_price = clean_numeric(
      df.get(
          "İndirimli Fiyat",
          df.get(
              "PSF DEĞERİ",
              df.get("Mevcut Fiyat", df.get("İlk Fiyat", pd.Series([0] * len(df)))),
          ),
      )
  )
  stock_qty = clean_numeric(
      df.get("Stok", df.get("Stok Adedi", pd.Series([0] * len(df))))
  )
  total_sales = clean_numeric(
      df.get(
          "Satış Adeti",
          df.get("Satış adedi payı", pd.Series([0] * len(df))),
      )
  )

  active_weeks = 1.0
  weekly_sales_rate = total_sales / active_weeks
  wos = np.where(weekly_sales_rate == 0, 99.0, stock_qty / weekly_sales_rate)

  inventory_cost = stock_qty * cost
  realized_profit = clean_numeric(
      df.get("Satılan Net Kâr", (current_price - cost) * total_sales)
  )
  gmroi = np.where(inventory_cost > 0, realized_profit / inventory_cost, 0.0)

  min_allowable_price = cost * 1.20

  mask_high_performer = (wos < 3) & (gmroi > 2.0)
  mask_tier1_discount = (
      (wos > 10) | (gmroi < 0.5) | ((weekly_sales_rate == 0) & (stock_qty > 5))
  )
  mask_liquidation = (wos > 15) & (gmroi < 0.2)

  action = np.select(
      [mask_liquidation, mask_tier1_discount, mask_high_performer],
      [
          "Tasfiye İndirimi (%30)",
          "1. Kademe İndirim (%15)",
          "Fiyat Artır / Koru",
      ],
      default="Fiyatı Koru (Optimum)",
  )

  urgency = np.select(
      [mask_liquidation, mask_tier1_discount, mask_high_performer],
      ["Yüksek", "Orta", "Düşük"],
      default="Normal",
  )

  suggested_price = np.select(
      [mask_liquidation, mask_tier1_discount],
      [current_price * 0.70, current_price * 0.85],
      default=current_price,
  )

  is_under_stoploss = suggested_price < min_allowable_price
  suggested_price = np.where(
      is_under_stoploss, min_allowable_price, suggested_price
  )
  urgency = np.where(is_under_stoploss, "Kırmızı Alarm (Taban Fiyat)", urgency)

  discount_rate = np.where(
      current_price > 0,
      np.round((1 - (suggested_price / current_price)) * 100, 2),
      0.0,
  )
  discount_rate = np.maximum(0.0, discount_rate)

  return pd.DataFrame(
      {
          "Haftalık Satış Hızı": np.round(weekly_sales_rate, 2),
          "Stok Ömrü (WOS)": np.round(wos, 1),
          "Brüt Kâr (TL)": np.round(realized_profit, 2),
          "GMROI Verimliliği": np.round(gmroi, 2),
          "Önerilen Aksiyon": action,
          "Aciliyet Seviyesi": urgency,
          "Önerilen Yeni Fiyat (TL)": np.round(suggested_price, 2),
          "Önerilen İndirim (%)": discount_rate,
      },
      index=df.index,
  )


@st.cache_data(ttl=3600)
def load_data(url):
  df = pd.read_csv(url)

  if isinstance(df, pd.Series):
    df = df.to_frame().T

  df.columns = df.columns.str.strip()

  # Hafta sütununu rapordan tamamen siliyoruz
  if "Hafta" in df.columns:
    df = df.drop(columns=["Hafta"])

  if "Stok" in df.columns:
    df["Stok"] = clean_numeric(df["Stok"])
  else:
    df["Stok"] = 0.0

  if "Satış Adeti" in df.columns:
    df["Satış Adeti"] = clean_numeric(df["Satış Adeti"])
  else:
    df["Satış Adeti"] = 0.0

  if "Maliyet" in df.columns:
    df["Maliyet"] = clean_numeric(df["Maliyet"])
  if "İndirimli Fiyat" in df.columns:
    df["İndirimli Fiyat"] = clean_numeric(df["İndirimli Fiyat"])

  return df


try:
  df_raw = load_data(SHEET_URL)
  st.success("Veriler başarıyla yüklendi!")

  # Sol Menü Filtre Paneli ve Çalıştır Butonu
  st.sidebar.subheader("Filtreleme ve Kontrol Paneli")

  id_col = (
      "Id"
      if "Id" in df_raw.columns
      else ("ID" if "ID" in df_raw.columns else None)
  )
  filter_col = (
      id_col if id_col else ("Ürün Kodu" if "Ürün Kodu" in df_raw.columns else "Ürün Adı")
  )

  selected_code = "Tümü"
  if filter_col and filter_col in df_raw.columns:
    unique_codes = df_raw[filter_col].dropna().unique().tolist()
    selected_code = st.sidebar.selectbox(
        f"{filter_col} Seçin", ["Tümü"] + [str(x) for x in unique_codes]
    )

  st.sidebar.markdown("---")
  run_button = st.sidebar.button("🚀 Analizi Çalıştır", type="primary")

  # Çalıştır butonuna basılana kadar veya ilk açılışta veriyi hazırla
  if run_button or selected_code != "Tümü":
    if selected_code != "Tümü":
      df_filtered = df_raw[
          df_raw[filter_col].astype(str) == str(selected_code)
      ].copy()
    else:
      df_filtered = df_raw.copy()

    df_filtered = df_filtered.reset_index(drop=True)

    metrics_df = calculate_smart_pricing(df_filtered)

    for col in metrics_df.columns:
      df_filtered[col] = metrics_df[col].values

    df_result = df_filtered

    # Üst Dashboard Metrikleri
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Toplam Çeşit / Id", len(df_result))
    col2.metric(
        "Toplam Stok",
        int(df_result["Stok"].sum()) if "Stok" in df_result.columns else 0,
    )
    col3.metric(
        "Toplam Satış",
        int(df_result["Satış Adeti"].sum())
        if "Satış Adeti" in df_result.columns
        else 0,
    )
    alarm_count = (
        len(
            df_result[
                df_result["Aciliyet Seviyesi"].str.contains(
                    "Kırmızı Alarm", na=False
                )
            ]
        )
        if "Aciliyet Seviyesi" in df_result.columns
        else 0
    )
    col4.metric("Kırmızı Alarm", alarm_count)

    st.markdown("---")
    st.subheader("Ürün Bazlı Fiyat ve Karar Analizi Raporu")

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
        file_name="akilli_fiyatlandirma_raporu.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
  else:
    st.info(
        "Lütfen sol menüden bir ürün (Id) seçin ve **Analizi Çalıştır**"
        " butonuna basın."
    )

except Exception as e:
  st.error(f"Hata oluştu: {e}")
