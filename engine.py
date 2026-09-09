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

def calculate_smart_pricing(df):
    cost = clean_numeric(df.get('Maliyet', df.get('SMM', df.get('Cost', pd.Series([0] * len(df))))))
    current_price = clean_numeric(df.get('İndirimli Fiyat', df.get('PSF DEĞERİ', df.get('Mevcut Fiyat', df.get('İlk Fiyat', pd.Series([0] * len(df)))))))
    stock_qty = clean_numeric(df.get('Stok', df.get('Stok Adedi', pd.Series([0] * len(df)))))
    total_sales = clean_numeric(df.get('Satış Adeti', df.get('Satış adedi payı', pd.Series([0] * len(df)))))
    
    # Aktif Hafta ve Satış Hızı Hesabı
    if 'İlk Giriş Haftası' in df.columns and 'Son Giriş Haftası' in df.columns:
        first_week = clean_numeric(df['İlk Giriş Haftası'])
        last_week = clean_numeric(df['Son Giriş Haftası'])
        active_weeks = np.maximum(1.0, (last_week - first_week) + 1.0)
    else:
        active_weeks = 1.0

    weekly_sales_rate = total_sales / active_weeks
    wos = np.where(weekly_sales_rate == 0, 99.0, stock_qty / weekly_sales_rate)
    
    # Envanter Maliyeti, Brüt Kâr ve GMROI Hesabı
    inventory_cost = stock_qty * cost
    realized_profit = clean_numeric(df.get('Satılan Net Kâr', (current_price - cost) * total_sales))
    gmroi = np.where(inventory_cost > 0, realized_profit / inventory_cost, 0.0)

    # Stop-Loss (Taban Fiyat) Sınırı
    min_allowable_price = cost * 1.20
    
    # Karar Matrisi
    mask_high_performer = (wos < 3) & (gmroi > 2.0)
    mask_tier1_discount = (wos > 10) | (gmroi < 0.5) | ((weekly_sales_rate == 0) & (stock_qty > 5))
    mask_liquidation = (wos > 15) & (gmroi < 0.2)
    
    action = np.select(
        [mask_liquidation, mask_tier1_discount, mask_high_performer],
        ["Tasfiye İndirimi (%30)", "1. Kademe İndirim (%15)", "Fiyat Artır / Koru"],
        default="Fiyatı Koru (Optimum)"
    )
    
    urgency = np.select(
        [mask_liquidation, mask_tier1_discount, mask_high_performer],
        ["Yüksek", "Orta", "Düşük"],
        default="Normal"
    )
    
    suggested_price = np.select(
        [mask_liquidation, mask_tier1_discount],
        [current_price * 0.70, current_price * 0.85],
        default=current_price
    )
    
    is_under_stoploss = suggested_price < min_allowable_price
    suggested_price = np.where(is_under_stoploss, min_allowable_price, suggested_price)
    urgency = np.where(is_under_stoploss, "Kırmızı Alarm (Taban Fiyat)", urgency)
    
    discount_rate = np.where(current_price > 0, np.round((1 - (suggested_price / current_price)) * 100, 2), 0.0)
    discount_rate = np.maximum(0.0, discount_rate)
    
    return pd.DataFrame({
        "Aktif Hafta": np.round(active_weeks, 1),
        "Haftalık Satış Hızı": np.round(weekly_sales_rate, 2),
        "Stok Ömrü (WOS)": np.round(wos, 1),
        "Brüt Kâr (TL)": np.round(realized_profit, 2),
        "GMROI Verimliliği": np.round(gmroi, 2),
        "Önerilen Aksiyon": action,
        "Aciliyet Seviyesi": urgency,
        "Önerilen Yeni Fiyat (TL)": np.round(suggested_price, 2),
        "Önerilen İndirim (%)": discount_rate
    }, index=df.index)
