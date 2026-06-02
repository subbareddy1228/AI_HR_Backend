def to_total_minutes(days=0, hours=0, minutes=0) -> int:
    return (days or 0) * 24 * 60 + (hours or 0) * 60 + (minutes or 0)
