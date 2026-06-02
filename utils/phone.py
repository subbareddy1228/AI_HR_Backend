def normalize_indian_phone(phone: str) -> str:
    phone = phone.strip()
    if phone.startswith("+91"):
        phone = phone[3:]
    return phone
