import numpy as np
import pandas as pd

def clean_numeric(series):
    """Sayısal verileri Türkçe/İngilizce format farketmeksizin hızlı temizler"""
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
    """
    Kümüle veriler ve perakende metrikleri (WOS, GMROI, Kâr, İlk/Son Hafta) üzerinden 
    akıllı fiyatlandırma ve karar analizi yapar.
    """
    if isinstance(df_grouped, pd.Series):
        df_grouped = pd.DataFrame([df_grouped])
        
    df = df_grouped.copy()
    
    # Temel finansal ve stok değişkenleri
    cost = clean_numeric(df.get('Maliyet', df.get('SMM', df.get('Cost', pd.Series([0] * len(df))))))
    current_price = clean_numeric(df.get('İndirimli Fiyat', df.get('PSF DEĞERİ', df.get('Mevcut Fiyat', df.get('İlk Fiyat', pd.Series([0] * len(df)))))))
    stock_qty = clean_numeric(df.get('Stok', df.get('Stok Adedi', pd.Series([0] * len(df)))))
    total_sales = clean_numeric(df.get('Satış Adeti', df.get('Satış adedi payı', pd.Series([0] * len(df)))))
    
    # İlk ve Son Giriş Haftası analizi (Eğer kolonlar varsa aktif yaşam süresi bulunur)
    if 'İlk Giriş Haftası' in df.columns and 'Son Giriş Haftası' in df.columns:
        first_week = clean_numeric(df['İlk Giriş Haftası'])
        last_week = clean_numeric(df['Son Giriş Haftası'])
        active_weeks = np.maximum(1.0, (last_week - first_week) + 1.0)
    else:
        # Varsayılan olarak aktif süre 1 hafta kabul edilir veya veri içinden tahmin edilir
        active_weeks = 1.0

    # Gerçekçi Haftalık Satış Hızı
    weekly_sales_rate = total_sales / active_weeks

    # WOS (Stok Ömrü) Hesabı (Haftalık satış hızına göre)
    wos = np.where(weekly_sales_rate == 0, 99.0, stock_qty / weekly_sales_rate)
    
    # Envanter Maliyeti ve GMROI Hesaplamaları
    inventory_cost = stock_qty * cost
    # Kümüle brüt kâr (Satılan miktar üzerinden üretilen kâr tahmini veya mevcut kâr)
    realized_profit = clean_numeric(df.get('Satılan Net Kâr', (current_price - cost) * total_sales))
    
    # GMROI = Brüt Kâr / Ortalama Envanter Maliyeti
    gmroi = np.where(inventory_cost > 0, realized_profit / inventory_cost, 0.0)

    min_allowable_price = cost * 1.20 # Stop-Loss (Taban Fiyat Sınırı)
    
    # Karar Matrisi Kriterleri (WOS + GMROI Kombinasyonu)
    mask_high_performer = (wos < 3) & (gmroi > 2.0) # Çok karlı ve hızlı dönen -> Fiyat Artır / Koru
    mask_tier1_discount = (wos > 10) | (gmroi < 0.5) | ((weekly_sales_rate == 0) & (stock_qty > 5)) # Yavaş dönen / düşük getirili -> %15 İndirim
    mask_liquidation = (wos > 15) & (gmroi < 0.2) # Ölü stok -> %30 Tasfiye
    
    action = np.select(
        [mask_liquidation, mask_tier1_discount, mask_high_performer],
        ["Tasfiye İndirimi (%30)", "1. Kademe İndirim (%15)", "Fiyat Artır / Koru (Yüksek GMROI)"],
        default="Fiyat Koru (Optimum Seviye)"
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
    
    # Stop-Loss (Taban Fiyat) Koruması
    is_under_stoploss = suggested_price < min_allowable_price
    suggested_price = np.where(is_under_stoploss, min_allowable_price, suggested_price)
    urgency = np.where(is_under_stoploss, "Kırmızı Alarm (Taban Fiyat)", urgency)
    
    discount_rate = np.where(current_price > 0, np.round((1 - (suggested_price / current_price)) * 100, 2), 0.0)
    discount_rate = np.maximum(0.0, discount_rate)
    
    result_df = pd.DataFrame({
        "Aktif_Hafta_Sayisi": np.round(active_weeks, 1),
        "Haftalik_Satis_Hizi": np.round(weekly_sales_rate, 2),
        "WOS_Hafta": np.round(wos, 1),
        "GMROI": np.round(gmroi, 2),
        "Aksiyon": action,
        "Aciliyet": urgency,
        "Onerilen_Fiyat": np.round(suggested_price, 2),
        "Onerilen_Indirim_Yuzde": discount_rate
    }, index=df.index)
    
    return result_df
