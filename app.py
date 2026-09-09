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


@st.cache_data(ttl=3600)
def load_and_process_data(url):
  df = pd.read_csv(url)

  if isinstance(df, pd.Series):
    df = df.to_frame().T

  df.columns = df.columns.str.strip()

  # Hafta sütununu temizle
  if "Hafta" in df.columns:
    df = df.drop(columns=["Hafta"])

  # Sütunları tam adlarıyla veya esnek eşleştirme ile bul
  stok_col, satis_col, maliyet_col, fiyat_col, id_col = None, None, None, None, None

  for col in df.columns:
    col_lower = col.lower()
    if col_lower == "id" and not id_col:
      id_col = col
    elif "stok" in col_lower and not stok_col:
      stok_col = col
    elif ("satış adeti" in col_lower or "satis adeti" in col_lower) and not satis_col:
      satis_col = col
    elif ("maliyet" in col_lower or "smm" in col_lower or "cost" in col_lower) and not maliyet_col:
      maliyet_col = col
    elif ("indirimli fiy" in col_lower or "indirimli" in col_lower or "psf" in col_lower) and not fiyat_col:
      fiyat_col = col

  if not id_col:
    for col in df.columns:
      if "id" in col.lower():
        id_col = col
        break

  df["Stok_num"] = clean_numeric(df[stok_col]) if stok_col else 0.0
  df["Satis_num"] = clean_numeric(df[satis_col]) if satis_col else 0.0
  df["Maliyet_num"] = clean_numeric(df[maliyet_col]) if maliyet_col else 0.0
  df["Fiyat_num"] = clean_numeric(df[fiyat_col]) if fiyat_col else 0.0

  if id_col:
    agg_rules = {
        "Stok_num": "last",
        "Satis_num": "sum",
        "Maliyet_num": "first",
        "Fiyat_num": "first",
    }
    for col in df.columns:
      if col not in [
          id_col,
          "Stok_num",
          "Satis_num",
          "Maliyet_num",
          "Fiyat_num",
          stok_col,
          satis_col,
          maliyet_col,
          fiyat_col,
      ]:
        agg_rules[col] = "first"

    df_grouped = df.groupby(id_col, as_index=False).agg(agg_rules)
  else:
    df_grouped = df

  if isinstance(df_grouped, pd.Series):
    df_grouped = df_grouped.to_frame().T

  df_grouped["Stok"] = df_grouped["Stok_num"]
  df_grouped["Satış Adeti"] = df_grouped["Satis_num"]
  df_grouped["Maliyet"] = df_grouped["Maliyet_num"]
  df_grouped["İndirimli Fiyat"] = df_grouped["Fiyat_num"]

  df_grouped = df_grouped.drop(
      columns=["Stok_num", "Satis_num", "Maliyet_num", "Fiyat_num"],
      errors="ignore",
  )

  # Eğer Id sütunu varsa en başa taşı
  if id_col and id_col in df_grouped.columns:
    cols = [id_col] + [c for c in df_grouped.columns if c != id_col]
    df_grouped = df_grouped[cols]

  stock_qty = df_grouped["Stok"]
  total_sales = df_grouped["Satış Adeti"]
  cost = df_grouped["Maliyet"]
  current_price = df_grouped["İndirimli Fiyat"]

  active_weeks = 1.0
  weekly_sales_rate = total_sales / active_weeks
  wos = np.where(weekly_sales_rate == 0, 99.0, stock_qty / weekly_sales_rate)

  inventory_cost = stock_qty * cost
  realized_profit = (current_price - cost) * total_sales
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

  df_grouped["Haftalık Satış Hızı"] = np.round(weekly_sales_rate, 2)
  df_grouped["Stok Ömrü (WOS)"] = np.round(wos, 1)
  df_grouped["Brüt Kâr (TL)"] = np.round(realized_profit, 2)
  df_grouped["GMROI Verimliliği"] = np.round(gmroi, 2)
  df_grouped["Önerilen Aksiyon"] = action
  df_grouped["Aciliyet Seviyesi"] = urgency
  df_grouped["Önerilen Yeni Fiyat (TL)"] = np.round(suggested_price, 2)
  df_grouped["Önerilen İndirim (%)"] = discount_rate

  return df_grouped


try:
  df_result = load_and_process_data(SHEET_URL)
  st.success("Veriler Id bazlı kümüle edildi ve başarıyla yüklendi!")

  st.sidebar.subheader("Filtreleme Paneli")
  filter_col = None
  for col in df_result.columns:
    if col.lower() == "id":
      filter_col = col
      break
  if not filter_col and len(df_result.columns) > 0:
    filter_col = df_result.columns[0]

  selected_code = "Tümü"
  if filter_col and filter_col in df_result.columns:
    unique_codes = df_result[filter_col].dropna().unique().tolist()
    selected_code = st.sidebar.selectbox(
        f"{filter_col} Seçin", ["Tümü"] + [str(x) for x in unique_codes]
    )

  if selected_code != "Tümü":
    df_filtered = df_result[
        df_result[filter_col].astype(str) == str(selected_code)
    ].copy()
  else:
    df_filtered = df_result.copy()

  df_filtered = df_filtered.reset_index(drop=True)

  col1, col2, col3, col4 = st.columns(4)
  col1.metric("Toplam Çeşit / Id", len(df_filtered))
  col2.metric(
      "Toplam Stok",
      int(df_filtered["Stok"].sum()) if "Stok" in df_filtered.columns else 0,
  )
  col3.metric(
      "Toplam Satış",
      int(df_filtered["Satış Adeti"].sum())
      if "Satış Adeti" in df_filtered.columns
      else 0,
  )
  alarm_count = (
      len(
          df_filtered[
              df_filtered["Aciliyet Seviyesi"].str.contains(
                  "Kırmızı Alarm", na=False
              )
          ]
      )
      if "Aciliyet Seviyesi" in df_filtered.columns
      else 0
  )
  col4.metric("Kırmızı Alarm", alarm_count)

  st.markdown("---")
  st.subheader("Ürün Bazlı Kümüle Fiyat ve Karar Analizi Raporu")

  st.dataframe(df_filtered, use_container_width=True)


  @st.cache_data
  def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
      df.to_excel(writer, index=False, sheet_name="Aksiyon_Listesi")
    return output.getvalue()


  excel_data = convert_df_to_excel(df_filtered)

  st.download_button(
      label="📥 Net Raporu Excel Olarak İndir",
      data=excel_data,
      file_name="akilli_fiyatlandirma_kumule_rapor.xlsx",
      mime=(
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ),
  )

except Exception as e:
  st.error(f"Hata oluştu: {e}")
