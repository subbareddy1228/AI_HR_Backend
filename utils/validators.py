import re
def validate_ifsc(ifsc: str) -> bool:
    return bool(re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', ifsc))


def validate_pincode(pincode: str):
    if not pincode.isdigit():
        raise ValueError("Pincode must be numeric")



def validate_pan(pan: str) -> bool:
    return bool(re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan))

def validate_aadhaar(aadhaar: str) -> bool:
    return aadhaar.isdigit() and len(aadhaar) == 12

def validate_phone(phone: str) -> bool:
    return bool(re.fullmatch(r"\d{10}", phone))


