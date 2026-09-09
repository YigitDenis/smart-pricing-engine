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
def load_and_aggregate_data(url):
  df = pd.read_csv(url)

  if isinstance(df, pd.Series):
    df = df.to_frame().T

  df.columns = df.columns.str.strip()

  # Hafta sütununu kümüle rapordan tamamen çıkarıyoruz
  if "Hafta" in df.columns:
    df = df.drop(columns=["Hafta"])

  # Sayısal dönüşümler için geçici alanlar
  if "Stok" in df.columns:
    df["Stok_num"] = clean_numeric(df["Stok"])
  else:
    df["Stok_num"] = 0.0

  if "Satış Adeti" in df.columns:
    df["Satis_num"] = clean_numeric(df["Satış Adeti"])
  else:
    df["Satis_num"] = 0.0

  # Id bazlı kümüle gruplama (Aynı Id'leri tekilleştir, satışı topla, stoku son değer al)
  id_col = (
      "Id"
      if "Id" in df.columns
      else ("ID" if "ID" in df.columns else ("id" if "id" in df.columns else None))
  )

  if id_col and id_col in df.columns:
    agg_rules = {"Stok_num": "last", "Satis_num": "sum"}
    for col in df.columns:
      if col not in [
          id_col,
          "Stok_num",
          "Satis_num",
          "Stok",
          "Satış Adeti",
      ]:
        agg_rules[col] = "first"

    df_grouped = df.groupby(id_col, as_index=False).agg(agg_rules)
  else:
    df_grouped = df

  if isinstance(df_grouped, pd.Series):
    df_grouped = df_grouped.to_frame().T

  df_grouped["Stok"] = df_grouped["Stok_num"]
  df_grouped["Satış Adeti"] = df_grouped["Satis_num"]
  df_grouped = df_grouped.drop(
      columns=["Stok_num", "Satis_num"], errors="ignore"
  )

  cost = clean_numeric(
      df_grouped.get(
          "Maliyet",
          df_grouped.get("SMM", df_grouped.get("Cost", pd.Series([0] * len(df_grouped)))),
      )
  )
  current_price = clean_numeric(
      df_grouped.get(
          "İndirimli Fiyat",
          df_grouped.get(
              "PSF DEĞERİ",
              df_grouped.get("Mevcut Fiyat", df_grouped.get("İlk Fiyat", pd.Series([0] * len(df_grouped)))),
          ),
      )
  )
  stock_qty = df_grouped["Stok"]
  total_sales = df_grouped["Satış Adeti"]

  df_grouped["Maliyet"] = cost
  df_grouped["İndirimli Fiyat"] = current_price

  # Metrik Hesaplamaları (Kümüle Veri Üzerinden)
  active_weeks = 1.0
  weekly_sales_rate = total_sales / active_weeks
  wos = np.where(weekly_sales_rate == 0, 99.0, stock_qty / weekly_sales_rate)

  inventory_cost = stock_qty * cost
  realized_profit = clean_numeric(
      df_grouped.get("Satılan Net Kâr", (current_price - cost) * total_sales)
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

  # Sütunları tabloya ekle
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
  df_result = load_and_aggregate_data(SHEET_URL)
  st.success("Veriler Id bazlı kümüle edildi ve başarıyla yüklendi!")

  # Sol Menü Filtre Paneli
  st.sidebar.subheader("Filtreleme Paneli")

  id_col = (
      "Id"
      if "Id" in df_result.columns
      else ("ID" if "ID" in df_result.columns else None)
  )
  filter_col = (
      id_col if id_col else ("Ürün Kodu" if "Ürün Kodu" in df_result.columns else "Ürün Adı")
  )

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

  # Üst Dashboard Metrikleri
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
