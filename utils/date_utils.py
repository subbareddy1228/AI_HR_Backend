from datetime import datetime

def calculate_financial_year(start_month: int):
    year = datetime.now().year
    if datetime.now().month >= start_month:
        return f"{year}-{year+1}", f"{year-1}-{year}", f"{year+1}-{year+2}"
    return f"{year-1}-{year}", f"{year-2}-{year-1}", f"{year}-{year+1}"
