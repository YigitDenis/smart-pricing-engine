import io
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Smart Pricing Engine", layout="wide")

st.title("Akıllı Fiyatlandırma ve Karar Destek Paneli")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1VWZsQvYK7CyZQiogmgLiVovufr9gnwWboa3sBt17VMA/export?format=csv&gid=0"


def format_tl(val):
  try:
    if pd.isna(val) or str(val).strip() == "" or str(val).strip() == "nan":
      return "0,00 TL"
    val_str = str(val).upper().strip()
    if "TL" in val_str or "TRY" in val_str:
      cleaned_str = (
          val_str.replace("TRY", "")
          .replace("TL", "")
          .strip()
          .replace(".", "")
          .replace(",", ".")
      )
      f_val = float(cleaned_str)
    else:
      cleaned_str = val_str.replace(".", "").replace(",", ".")
      f_val = float(cleaned_str)
    return (
        f"{f_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        + " TL"
    )
  except:
    return str(val) if pd.notna(val) else "0,00 TL"


def format_percentage(val):
  try:
    if pd.isna(val) or str(val).strip() == "" or str(val).strip() == "nan":
      return "%0,00"
    val_str = str(val).replace("%", "").strip().replace(",", ".")
    f_val = float(val_str)
    if 0 < f_val <= 1:
      f_val = f_val * 100
    return (
        "%"
        + f"{f_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
  except:
    return str(val) if pd.notna(val) else "%0,00"


def sanitize_name(name):
  return (
      str(name)
      .lower()
      .replace("\xa0", " ")
      .replace("İ", "i")
      .replace("ı", "i")
      .replace("Ş", "s")
      .replace("ş", "s")
      .replace("Ğ", "g")
      .replace("ğ", "g")
      .replace("Ü", "u")
      .replace("ü", "u")
      .replace("Ö", "o")
      .replace("ö", "o")
      .replace("Ç", "c")
      .replace("ç", "c")
      .strip()
  )


@st.cache_data(ttl=3600)
def load_and_process_data(url):
  df = pd.read_csv(url)

  if isinstance(df, pd.Series):
    df = df.to_frame().T

  df.columns = [str(c).strip().replace("\xa0", " ") for c in df.columns]

  if "Hafta" in df.columns:
    df = df.drop(columns=["Hafta"])
  else:
    for c in list(df.columns):
      if sanitize_name(c) == "hafta":
        df = df.drop(columns=[c])

  original_columns = list(df.columns)
  cols_list = list(df.columns)

  id_col, stok_col, satis_col, maliyet_col, ilk_fiyat_col, indirimli_col, ciro_col, indirim_oran_col = (
      None,
      None,
      None,
      None,
      None,
      None,
      None,
      None,
  )

  for col in cols_list:
    c = sanitize_name(col)
    if c in ["id", "urun kodu", "urun_kodu"] and not id_col:
      id_col = col
    elif "stok" in c and not stok_col:
      stok_col = col
    elif "satis" in c and not satis_col:
      satis_col = col
    elif any(k in c for k in ["maliyet", "smm", "cost"]) and not maliyet_col:
      maliyet_col = col
    elif "ilk fiyat" in c or (
        "ilk" in c and "fiyat" in c and not ilk_fiyat_col
    ):
      ilk_fiyat_col = col
    elif (
        "indirimli fiyat" in c
        or "indirimli" in c
        or ("fiyat" in c and "ilk" not in c and not indirimli_col)
    ):
      if not indirimli_col and "oran" not in c:
        indirimli_col = col
    elif any(k in c for k in ["ciro", "tutar"]) and not ciro_col:
      ciro_col = col
    elif any(k in c for k in ["oran", "indirim oran"]) and not indirim_oran_col:
      indirim_oran_col = col

  # Konum bazlı emniyet garantileri (E-tablodaki sütun sırasına göre)
  if not id_col and len(cols_list) > 1:
    id_col = cols_list[1]
  if not ciro_col and len(cols_list) >= 10:
    ciro_col = cols_list[9]
  if not maliyet_col and len(cols_list) >= 12:
    maliyet_col = cols_list[11]
  if not ilk_fiyat_col and len(cols_list) >= 13:
    ilk_fiyat_col = cols_list[12]
  if not indirimli_col and len(cols_list) >= 14:
    indirimli_col = cols_list[13]
  if not indirim_oran_col and len(cols_list) >= 15:
    indirim_oran_col = cols_list[14]

  # Ham sayısal veriler
  df["Stok_num"] = pd.to_numeric(
      df[stok_col].astype(str).str.replace(",", "."), errors="coerce"
  ).fillna(0)
  df["Satis_num"] = pd.to_numeric(
      df[satis_col].astype(str).str.replace(",", "."), errors="coerce"
  ).fillna(0)

  df["Raw_Maliyet"] = df[maliyet_col] if maliyet_col else 0
  df["Raw_Ilk_Fiyat"] = df[ilk_fiyat_col] if ilk_fiyat_col else 0
  df["Raw_Indirimli_Fiyat"] = df[indirimli_col] if indirimli_col else 0
  df["Raw_Ciro"] = df[ciro_col] if ciro_col else 0
  df["Raw_Indirim_Orani"] = df[indirim_oran_col] if indirim_oran_col else 0

  group_col = id_col if id_col else cols_list[0]

  # Sayısal değerlerin temizlenmesi (Güvenli parse)
  df["Maliyet_val"] = (
      df["Raw_Maliyet"]
      .astype(str)
      .str.upper()
      .str.replace("TRY", "", regex=False)
      .str.replace("TL", "", regex=False)
      .str.strip()
      .str.replace(".", "", regex=False)
      .str.replace(",", ".", regex=False)
  )
  df["Maliyet_val"] = pd.to_numeric(df["Maliyet_val"], errors="coerce").fillna(0)

  df["Indirimli_val"] = (
      df["Raw_Indirimli_Fiyat"]
      .astype(str)
      .str.upper()
      .str.replace("TRY", "", regex=False)
      .str.replace("TL", "", regex=False)
      .str.strip()
      .str.replace(".", "", regex=False)
      .str.replace(",", ".", regex=False)
  )
  df["Indirimli_val"] = pd.to_numeric(
      df["Indirimli_val"], errors="coerce"
  ).fillna(0)

  df["Ciro_val"] = (
      df["Raw_Ciro"]
      .astype(str)
      .str.upper()
      .str.replace("TRY", "", regex=False)
      .str.replace("TL", "", regex=False)
      .str.strip()
      .str.replace(".", "", regex=False)
      .str.replace(",", ".", regex=False)
  )
  df["Ciro_val"] = pd.to_numeric(df["Ciro_val"], errors="coerce").fillna(0)

  agg_rules = {
      "Stok_num": "last",
      "Satis_num": "sum",
      "Maliyet_val": "first",
      "Indirimli_val": "first",
      "Ciro_val": "sum",
  }
  for col in df.columns:
    if col not in [
        group_col,
        "Stok_num",
        "Satis_num",
        "Maliyet_val",
        "Indirimli_val",
        "Ciro_val",
        stok_col,
        satis_col,
        maliyet_col,
        ilk_fiyat_col,
        indirimli_col,
        ciro_col,
        indirim_oran_col,
    ]:
      agg_rules[col] = "first"

  df_grouped = df.groupby(group_col, as_index=False).agg(agg_rules)

  if isinstance(df_grouped, pd.Series):
    df_grouped = df_grouped.to_frame().T

  df_grouped["Stok"] = df_grouped["Stok_num"]
  df_grouped["Satış Adeti"] = df_grouped["Satis_num"]
  df_grouped["Giriş Adeti"] = df_grouped["Satış Adeti"] + df_grouped["Stok"]

  raw_cost = df_grouped["Maliyet_val"]
  raw_current_price = df_grouped["Indirimli_val"]
  stock_qty = df_grouped["Stok"]
  total_sales = df_grouped["Satış Adeti"]

  calculated_ciro = raw_current_price * total_sales
  final_ciro_vals = np.where(
      df_grouped["Ciro_val"] > 0, df_grouped["Ciro_val"], calculated_ciro
  )

  # WOS hesaplaması (Satış hızı 0 ise stok ömrü 99 olarak güvenle sabitlenir)
  active_weeks = 1.0
  weekly_sales_rate = total_sales / active_weeks
  wos = np.where(
      (weekly_sales_rate == 0) | pd.isna(weekly_sales_rate),
      99.0,
      stock_qty / weekly_sales_rate,
  )

  inventory_cost = stock_qty * raw_cost
  realized_profit = (raw_current_price - raw_cost) * total_sales
  gmroi = np.where(inventory_cost > 0, realized_profit / inventory_cost, 0.0)

  min_allowable_price = raw_cost * 1.20

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

  # Önerilen fiyat hesaplamasının patlamaması için mantıksal sınır
  target_increase_price = raw_current_price
  suggested_price = np.select(
      [mask_liquidation, mask_tier1_discount, mask_high_performer],
      [
          raw_current_price * 0.70,
          raw_current_price * 0.85,
          target_increase_price,
      ],
      default=raw_current_price,
  )

  is_under_stoploss = suggested_price < min_allowable_price
  suggested_price = np.where(
      is_under_stoploss, min_allowable_price, suggested_price
  )
  urgency = np.where(is_under_stoploss, "Kırmızı Alarm (Taban Fiyat)", urgency)

  suggested_discount = np.where(
      raw_current_price > 0,
      np.round((1 - (suggested_price / raw_current_price)) * 100, 2),
      0.0,
  )

  # Orijinal tablo sütunlarını güvenle işliyoruz
  if ciro_col and ciro_col in df_grouped.columns:
    df_grouped[ciro_col] = pd.Series(final_ciro_vals).apply(format_tl)
  else:
    df_grouped["Ciro"] = pd.Series(final_ciro_vals).apply(format_tl)

  if maliyet_col and maliyet_col in df_grouped.columns:
    df_grouped[maliyet_col] = df_grouped["Raw_Maliyet"].apply(format_tl)
  else:
    df_grouped["Maliyet"] = df_grouped["Raw_Maliyet"].apply(format_tl)

  if ilk_fiyat_col and ilk_fiyat_col in df_grouped.columns:
    df_grouped[ilk_fiyat_col] = df_grouped["Raw_Ilk_Fiyat"].apply(format_tl)
  else:
    df_grouped["İlk Fiyat"] = df_grouped["Raw_Ilk_Fiyat"].apply(format_tl)

  if indirimli_col and indirimli_col in df_grouped.columns:
    df_grouped[indirimli_col] = df_grouped["Raw_Indirimli_Fiyat"].apply(
        format_tl
    )
  else:
    df_grouped["İndirimli Fiyat"] = df_grouped["Raw_Indirimli_Fiyat"].apply(
        format_tl
    )

  if indirim_oran_col and indirim_oran_col in df_grouped.columns:
    df_grouped[indirim_oran_col] = df_grouped["Raw_Indirim_Orani"].apply(
        format_percentage
    )
  else:
    df_grouped["İndirim Oranı"] = df_grouped["Raw_Indirim_Orani"].apply(
        format_percentage
    )

  df_grouped["Haftalık Satış Hızı"] = np.round(weekly_sales_rate, 2)
  df_grouped["Stok Ömrü (WOS)"] = np.round(wos, 1)
  df_grouped["Brüt Kâr (TL)"] = pd.Series(realized_profit).apply(format_tl)
  df_grouped["GMROI Verimliliği"] = np.round(gmroi, 2)
  df_grouped["Önerilen Aksiyon"] = action
  df_grouped["Aciliyet Seviyesi"] = urgency
  df_grouped["Önerilen Yeni Fiyat (TL)"] = pd.Series(suggested_price).apply(
      format_tl
  )
  df_grouped["Önerilen İndirim (%)"] = suggested_discount

  drop_cols = [
      "Stok_num",
      "Satis_num",
      "Maliyet_val",
      "Indirimli_val",
      "Ciro_val",
      "Raw_Maliyet",
      "Raw_Ilk_Fiyat",
      "Raw_Indirimli_Fiyat",
      "Raw_Ciro",
      "Raw_Indirim_Orani",
  ]
  df_grouped = df_grouped.drop(columns=drop_cols, errors="ignore")

  final_cols = []
  for col in original_columns:
    if col in df_grouped.columns:
      final_cols.append(col)

  extra_cols = [
      "Haftalık Satış Hızı",
      "Stok Ömrü (WOS)",
      "Brüt Kâr (TL)",
      "GMROI Verimliliği",
      "Önerilen Aksiyon",
      "Aciliyet Seviyesi",
      "Önerilen Yeni Fiyat (TL)",
      "Önerilen İndirim (%)",
  ]
  for ec in extra_cols:
    if ec in df_grouped.columns and ec not in final_cols:
      final_cols.append(ec)

  df_grouped = df_grouped[final_cols]

  return df_grouped, group_col


try:
  df_result, group_col = load_and_process_data(SHEET_URL)
  st.success("Tüm veriler, stok ömrü ve fiyatlar tamamen düzeltildi!")

  st.sidebar.subheader("Filtreleme Paneli")
  search_query = st.sidebar.text_input(
      "Stok Kodu Ara (Örn: 514, 821)", value=""
  ).strip()

  if search_query:
    df_filtered = df_result[
        df_result.astype(str)
        .apply(
            lambda row: row.str.contains(search_query, case=False).any(), axis=1
        )
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
