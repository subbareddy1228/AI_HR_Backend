import uuid

def generate_employee_code() -> str:
    return f"EMP-{uuid.uuid4().hex[:8].upper()}"
