"""
migrations/create_promotions_tables.py
──────────────────────────────────────
Creates all 5 Promotions & Career Progression tables.

Run from the project root:
    python migrations/create_promotions_tables.py
"""

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import engine, Base

# Import models so Base.metadata is aware of them
from model.HR_Operations.probation_management import ProbationManagement
from model.HR_Operations.employee_confirmation import EmployeeConfirmation
from model.HR_Operations.promotion import Promotion
from model.HR_Operations.buddy_program import BuddyProgram, BuddyAssignment

TABLES = [
    ProbationManagement.__table__,
    EmployeeConfirmation.__table__,
    Promotion.__table__,
    BuddyProgram.__table__,
    BuddyAssignment.__table__,
]

if __name__ == "__main__":
    print("Creating Promotions & Career Progression tables …")
    Base.metadata.create_all(bind=engine, tables=TABLES, checkfirst=True)
    print("Done.")
    for t in TABLES:
        print(f"  ✓ {t.name}")
