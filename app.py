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
      .str.upper()
      .str.replace("TRY", "", regex=False)
      .str.replace("TL", "", regex=False)
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

  if "Hafta" in df.columns:
    df = df.drop(columns=["Hafta"])

  stok_col, satis_col, maliyet_col, fiyat_col, ilk_fiyat_col, id_col = (
      None,
      None,
      None,
      None,
      None,
      None,
  )

  for col in df.columns:
    col_clean = col.lower()
    if col_clean == "id" and not id_col:
      id_col = col
    elif (
        "ürün kodu" in col_clean
        or "urun kodu" in col_clean
        and not id_col
    ):
      id_col = col
    elif col_clean in ["stok", "stok adedi"] and not stok_col:
      stok_col = col
    elif (
        col_clean in ["satış adeti", "satis adeti", "satış adedi"]
        and not satis_col
    ):
      satis_col = col
    elif col_clean in ["maliyet", "smm", "cost"] and not maliyet_col:
      maliyet_col = col
    elif (
        "indirimli" in col_clean or "psf değeri" in col_clean
    ) and not fiyat_col:
      fiyat_col = col
    elif "ilk fiyat" in col_clean or "liste" in col_clean or col_clean == "fiyat":
      ilk_fiyat_col = col

  if not id_col:
    for col in df.columns:
      if "id" in col.lower() or "kod" in col.lower():
        id_col = col
        break

  if not stok_col:
    for col in df.columns:
      if "stok" in col.lower():
        stok_col = col
        break
  if not satis_col:
    for col in df.columns:
      if "satış" in col.lower() or "satis" in col.lower():
        satis_col = col
        break
  if not maliyet_col:
    for col in df.columns:
      if "maliyet" in col.lower() or "smm" in col.lower():
        maliyet_col = col
        break
  if not fiyat_col:
    for col in df.columns:
      if "indirimli" in col.lower():
        fiyat_col = col
        break
  if not ilk_fiyat_col:
    for col in df.columns:
      if "ilk" in col.lower() or "fiyat" in col.lower():
        ilk_fiyat_col = col
        break

  df["Stok_num"] = clean_numeric(df[stok_col]) if stok_col else 0.0
  df["Satis_num"] = clean_numeric(df[satis_col]) if satis_col else 0.0
  df["Maliyet_num"] = clean_numeric(df[maliyet_col]) if maliyet_col else 0.0
  df["Fiyat_num"] = clean_numeric(df[fiyat_col]) if fiyat_col else 0.0
  df["Ilk_Fiyat_num"] = clean_numeric(df[ilk_fiyat_col]) if ilk_fiyat_col else df["Fiyat_num"]

  group_col = id_col if id_col else df.columns[0]

  agg_rules = {
      "Stok_num": "last",
      "Satis_num": "sum",
      "Maliyet_num": "first",
      "Fiyat_num": "first",
      "Ilk_Fiyat_num": "first",
  }
  for col in df.columns:
    if col not in [
        group_col,
        "Stok_num",
        "Satis_num",
        "Maliyet_num",
        "Fiyat_num",
        "Ilk_Fiyat_num",
        stok_col,
        satis_col,
        maliyet_col,
        fiyat_col,
        ilk_fiyat_col,
    ]:
      agg_rules[col] = "first"

  df_grouped = df.groupby(group_col, as_index=False).agg(agg_rules)

  if isinstance(df_grouped, pd.Series):
    df_grouped = df_grouped.to_frame().T

  df_grouped["Stok"] = df_grouped["Stok_num"]
  df_grouped["Satış Adeti"] = df_grouped["Satis_num"]
  df_grouped["Maliyet"] = df_grouped["Maliyet_num"]
  df_grouped["İndirimli Fiyat"] = df_grouped["Fiyat_num"]
  df_grouped["İlk Fiyat"] = df_grouped["Ilk_Fiyat_num"]

  df_grouped = df_grouped.drop(
      columns=["Stok_num", "Satis_num", "Maliyet_num", "Fiyat_num", "Ilk_Fiyat_num"],
      errors="ignore",
  )

  stock_qty = df_grouped["Stok"]
  total_sales = df_grouped["Satış Adeti"]
  cost = df_grouped["Maliyet"]
  current_price = df_grouped["İndirimli Fiyat"]
  first_price = df_grouped["İlk Fiyat"]

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

  # Mantıklı Fiyat Önerisi:
  # - Tasfiye ve İndirimde: Mevcut indirimli fiyat üzerinden düşüş
  # - Fiyat Artır / Koru durumunda: Eğer İlk Fiyat mevcut fiyattan yüksekse İlk Fiyata çek, değilse mevcut fiyatı koru
  target_increase_price = np.where(first_price > current_price, first_price, current_price)

  suggested_price = np.select(
      [mask_liquidation, mask_tier1_discount, mask_high_performer],
      [
          current_price * 0.70,
          current_price * 0.85,
          target_increase_price,
      ],
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

  df_grouped["Haftalık Satış Hızı"] = np.round(weekly_sales_rate, 2)
  df_grouped["Stok Ömrü (WOS)"] = np.round(wos, 1)
  df_grouped["Brüt Kâr (TL)"] = np.round(realized_profit, 2)
  df_grouped["GMROI Verimliliği"] = np.round(gmroi, 2)
  df_grouped["Önerilen Aksiyon"] = action
  df_grouped["Aciliyet Seviyesi"] = urgency
  df_grouped["Önerilen Yeni Fiyat (TL)"] = np.round(suggested_price, 2)
  df_grouped["Önerilen İndirim (%)"] = discount_rate

  return df_grouped, group_col


try:
  df_result, group_col = load_and_process_data(SHEET_URL)
  st.success("İlk Fiyat ve akıllı fiyatlandırma mantığı başarıyla entegre edildi!")

  st.sidebar.subheader("Filtreleme Paneli")
  search_query = st.sidebar.text_input(
      "Stok Kodu Ara (Örn: 514, 821)", value=""
  ).strip()

  if search_query:
    df_filtered = df_result[
        df_result.astype(str)
        .apply(lambda row: row.str.contains(search_query, case=False).any(), axis=1)
    ].copy()
  else:
    df_filtered = df_result.copy()

  df_filtered = df_filtered.reset_index(drop=True)

  col1, col2, col3, col4 = st.columns(4)
  col1.metric("Toplam Tekil Varyant", len(df_filtered))
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
  st.subheader("Ürün ve Renk Bazlı Kümüle Fiyat Analizi Raporu")

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
      file_name="kumule_fiyat_analiz_raporu.xlsx",
      mime=(
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ),
  )

except Exception as e:
  st.error(f"Hata oluştu: {e}")
