import numpy as np
import pandas as pd

def clean_numeric(series):
    if isinstance(series, (int, float)):
        return float(series)
    if not isinstance(series, pd.Series):
        series = pd.Series([series])
    
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    return pd.to_numeric(cleaned, errors='coerce').fillna(0.0)

def calculate_smart_pricing(df_grouped):
    if isinstance(df_grouped, pd.Series):
        df_grouped = pd.DataFrame([df_grouped])
        
    df = df_grouped.copy()
    
    cost = clean_numeric(df.get('Maliyet', df.get('Cost', pd.Series([0] * len(df)))))
    current_price = clean_numeric(df.get('İndirimli Fiyat', df.get('Mevcut Fiyat', df.get('İlk Fiyat', pd.Series([0] * len(df))))))
    stock_qty = clean_numeric(df.get('Stok', df.get('Stok Adedi', pd.Series([0] * len(df)))))
    weekly_sales = clean_numeric(df.get('Satış Adeti', df.get('Haftalık Satış', pd.Series([0] * len(df)))))
    
    min_allowable_price = cost * 1.20
    wos = np.where(weekly_sales == 0, 99.0, stock_qty / weekly_sales)
    
    mask_tier1 = (wos > 10) | ((weekly_sales == 0) & (stock_qty > 5))
    mask_tier2 = wos > 15
    
    action = np.select(
        [mask_tier2, mask_tier1, (wos < 2) & (weekly_sales > 2)],
        ["Tasfiye İndirimi (%30)", "1. Kademe İndirim (%15)", "Fiyat Artır / Koru"],
        default="Fiyat Koru (Optimum Seviye)"
    )
    
    urgency = np.select(
        [mask_tier2, mask_tier1, (wos < 2) & (weekly_sales > 2)],
        ["Yüksek", "Orta", "Düşük"],
        default="Normal"
    )
    
    suggested_price = np.select(
        [mask_tier2, mask_tier1],
        [current_price * 0.70, current_price * 0.85],
        default=current_price
    )
    
    is_under_stoploss = suggested_price < min_allowable_price
    suggested_price = np.where(is_under_stoploss, min_allowable_price, suggested_price)
    urgency = np.where(is_under_stoploss, "Kırmızı Alarm (Taban Fiyat)", urgency)
    
    discount_rate = np.where(current_price > 0, np.round((1 - (suggested_price / current_price)) * 100, 2), 0.0)
    discount_rate = np.maximum(0.0, discount_rate)
    
    result_df = pd.DataFrame({
        "WOS_Hafta": np.round(wos, 1),
        "Aksiyon": action,
        "Aciliyet": urgency,
        "Onerilen_Fiyat": np.round(suggested_price, 2),
        "Onerilen_Indirim_Yuzde": discount_rate
    }, index=df.index)
    
    return result_df
