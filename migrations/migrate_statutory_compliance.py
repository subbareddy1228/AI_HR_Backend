# migrate_compliance.py
# Run once from your project root:
#   python migrate_compliance.py

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from core.database import Base, engine
from model.Payroll.statutory_compliance import (
    StatutoryConfig,
    PFStatement,
    PFRemittance,
    ECRSubmission,
    VPFEnrollment,
    UANActivation,
)

def run():
    print("Creating statutory compliance tables...")
    Base.metadata.create_all(
        bind=engine,
        tables=[
            StatutoryConfig.__table__,
            PFStatement.__table__,
            PFRemittance.__table__,
            ECRSubmission.__table__,
            VPFEnrollment.__table__,
            UANActivation.__table__,
        ],
        checkfirst=True,   # skip if already exists
    )
    print("✓ statutory_configs       (extended with PF/ESI/VPF settings)")
    print("✓ pf_statements           (per-employee monthly PF)")
    print("✓ pf_remittances          (monthly challan summary)")
    print("✓ ecr_submissions         (EPFO Electronic Challan-cum-Return)")
    print("✓ vpf_enrollments         (Voluntary PF per employee)")
    print("✓ uan_activations         (UAN management)")
    print("\nMigration complete.")

if __name__ == "__main__":
    run()
