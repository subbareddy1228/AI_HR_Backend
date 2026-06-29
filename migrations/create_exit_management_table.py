"""
migrations/create_exit_management_tables.py
────────────────────────────────────────────
Creates all 3 Exit Management tables.

Run from project root:
    python migrations/create_exit_management_tables.py
"""

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import engine, Base
from model.HR_Operations.exit_management import ExitManagement, Alumni, Settlement

TABLES = [
    ExitManagement.__table__,
    Alumni.__table__,
    Settlement.__table__,
]

if __name__ == "__main__":
    print("Creating Exit Management & Clearance tables …")
    Base.metadata.create_all(bind=engine, tables=TABLES, checkfirst=True)
    print("Done.")
    for t in TABLES:
        print(f"  ✓ {t.name}")
