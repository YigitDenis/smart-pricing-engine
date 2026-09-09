def parse_money(val):
    if pd.isna(val):
        return 0.0

    s = str(val).strip().upper()
    if not s or s == "NAN":
        return 0.0

    s = (
        s.replace("TRY", "")
        .replace("TL", "")
        .replace("₺", "")
        .replace(" ", "")
    )

    # Hem 1.299,90 hem 1299.90 destekle
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    
    try:
        return float(s)
    except ValueError:
        return 0.0
