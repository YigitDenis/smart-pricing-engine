import pandas as pd

def calculate_smart_pricing(row):
    """
    Maliyet, son hafta stoğu, son hafta satışı ve ilk fiyata göre
    akıllı indirim veya fiyat artış kararı veren motor.
    """
    cost = row['Maliyet']
    current_price = row['Mevcut Fiyat']
    stock_qty = row['Stok']
    weekly_sales = row['Satış Adeti']
    
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
