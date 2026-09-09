import pandas as pd

def clean_numeric(val):
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip().replace('.', '').replace(',', '.')
    try:
        return float(val_str)
    except:
        return 0.0

def calculate_smart_pricing(df_grouped):
    """
    Ürün bazında birleştirilmiş veriler üzerinden akıllı fiyatlandırma çalıştırır.
    DataFrame veya tekli satır (Series) durumlarını güvenle yönetir.
    """
    # Tekli satır/filtrelenmiş veri Series gelirse DataFrame'e çevir
    if isinstance(df_grouped, pd.Series):
        df_grouped = pd.DataFrame([df_grouped])
        
    results = []
    
    for _, row in df_grouped.iterrows():
        cost = clean_numeric(row.get('Maliyet', row.get('Cost', 0)))
        current_price = clean_numeric(row.get('İndirimli Fiyat', row.get('Mevcut Fiyat', row.get('İlk Fiyat', 0))))
        stock_qty = clean_numeric(row.get('Stok', row.get('Stok Adedi', 0)))
        weekly_sales = clean_numeric(row.get('Satış Adeti', row.get('Haftalık Satış', 0)))
        
        min_allowable_price = cost * 1.20
        
        if weekly_sales == 0:
            wos = 99.0
        else:
            wos = stock_qty / weekly_sales
            
        action = "Fiyatı Koru"
        suggested_price = current_price
        urgency = "Normal"
        
        if wos < 2 and weekly_sales > 2:
            action = "Fiyat Artır / Koru"
            suggested_price = current_price
            urgency = "Düşük"
        elif wos > 10 or (weekly_sales == 0 and stock_qty > 5):
            action = "1. Kademe İndirim (%15)"
            suggested_price = current_price * 0.85
            urgency = "Orta"
        elif wos > 15:
            action = "Tasfiye İndirimi (%30)"
            suggested_price = current_price * 0.70
            urgency = "Yüksek"

        if suggested_price < min_allowable_price:
            suggested_price = min_allowable_price
            urgency = "Kırmızı Alarm (Taban Fiyat)"
            
        discount_rate = round((1 - (suggested_price / current_price)) * 100, 2) if current_price > 0 else 0.0

        results.append({
            "WOS_Hafta": round(wos, 1),
            "Aksiyon": action,
            "Aciliyet": urgency,
            "Onerilen_Fiyat": round(suggested_price, 2),
            "Onerilen_Indirim_Yuzde": max(0.0, discount_rate)
        })
        
    return pd.DataFrame(results)
