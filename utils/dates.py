from datetime import timedelta

def default_confirmation_date(joining_date):
    return joining_date + timedelta(days=30)
