from datetime import datetime
from typing import Optional

def parse_date_str(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse a date string from query params.
    Supports multiple formats:
      - YYYY-MM-DD
      - DD-MM-YYYY
      - DD/MM/YYYY
      - YYYY-MM (defaults to day 1)
      - YYYY/MM (defaults to day 1)
    Returns None if input is None or invalid.
    """
    if not date_str:
        return None

    date_str = date_str.strip()
    formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m", "%Y/%m"]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if fmt in ("%Y-%m", "%Y/%m"):
                dt = dt.replace(day=1)
            return dt
        except ValueError:
            continue

    return None
