@st.cache_data(ttl=3600)
def load_and_aggregate_data(url):
  df = pd.read_csv(url)
  df.columns = df.columns.str.strip()

  # Hafta sütununu kümüle raporda kirlilik yapmaması için tamamen çıkarıyoruz
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
  id_col = (
      "Id"
      if "Id" in df.columns
      else ("ID" if "ID" in df.columns else ("id" in df.columns and "id" or None))
  )

  if id_col and id_col in df.columns:
    agg_rules = {"Stok_num": "last", "Satis_num": "sum"}
    for col in df.columns:
      if col not in [id_col, "Stok_num", "Satis_num", "Stok", "Satış Adeti"]:
        agg_rules[col] = "first"

    df_grouped = df.groupby(id_col, as_index=False).agg(agg_rules)
    df_grouped["Stok"] = df_grouped["Stok_num"]
    df_grouped["Satış Adeti"] = df_grouped["Satis_num"]
    df_grouped = df_grouped.drop(columns=["Stok_num", "Satis_num"])
  else:
    df_grouped = df

  if "Maliyet" in df_grouped.columns:
    df_grouped["Maliyet"] = clean_numeric(df_grouped["Maliyet"])
  if "İndirimli Fiyat" in df_grouped.columns:
    df_grouped["İndirimli Fiyat"] = clean_numeric(df_grouped["İndirimli Fiyat"])

  return df_grouped
