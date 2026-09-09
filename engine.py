import pandas as pd

def calculate_smart_pricing(row):
    """
    Maliyet, stok, satış ve fiyat sütunlarını esnek bir şekilde okuyarak 
    akıllı indirim veya fiyat artış kararı veren motor.
    """
    # Sütun adlarındaki olası farklılıklar için güvenli okuma (fallback)
    cost = float(row.get('Maliyet', row.get('Cost', 0)) or 0)
    current_price = float(row.get('Mevcut Fiyat', row.get('İlk Fiyat', row.get('Fiyat', 0))) or 0)
    stock_qty = float(row.get('Stok', row.get('Stok Adedi', 0)) or 0)
    weekly_sales = float(row.get('Satış Adeti', row.get('Haftalık Satış', 0)) or 0)
    
    # Mutlak Taban Sınır (Stop-Loss): Mark-up en az 1.2 olmalı
    min_allowable_price = cost * 1.20
    
    # Stok Ömrü (WOS) hesaplama
    if weekly_sales == 0:
        wos = 99.0
    else:
        wos = stock_qty / weekly_sales
        
    action = "Fiyatı Koru"
    suggested_price = current_price
    urgency = "Normal"
    
    # Karar Mekanizması
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

    # Stop-Loss Kontrolü
    if suggested_price < min_allowable_price:
        suggested_price = min_allowable_price
        urgency = "Kırmızı Alarm (Taban Fiyat)"
        
    discount_rate = round((1 - (suggested_price / current_price)) * 100, 2) if current_price > 0 else 0.0

    return pd.Series({
        "WOS_Hafta": round(wos, 1),
        "Aksiyon": action,
        "Aciliyet": urgency,
        "Onerilen_Fiyat": round(suggested_price, 2),
        "Onerilen_Indirim_Yuzde": max(0.0, discount_rate)
    })
