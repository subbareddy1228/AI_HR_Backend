"""
migrations/create_transfers_table.py
──────────────────────────────────────
Creates the transfers table.

Run from the project root:
    python migrations/create_transfers_table.py
"""

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import engine, Base
from model.HR_Operations.transfer import Transfer

if __name__ == "__main__":
    print("Creating Transfer & Movement Management table …")
    Base.metadata.create_all(
        bind=engine,
        tables=[Transfer.__table__],
        checkfirst=True,
    )
    print("  ✓ transfers")
    print("Done.")
