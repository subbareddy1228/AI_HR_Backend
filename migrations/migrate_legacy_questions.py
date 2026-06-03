# """
# Migration Script: Transfer data from legacy_questions to aptitude_questions

# This script transfers all data from the old legacy_questions table 
# to the new aptitude_questions table.

# Usage:
#     python migrate_legacy_questions.py
# """

# import sys
# import codecs

# # Fix UTF-8 encoding for Windows console
# if sys.platform == 'win32':
#     sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# from sqlalchemy import create_engine, text, inspect
# from sqlalchemy.orm import Session
# from core.database import DATABASE_URL, SessionLocal
# from model import LegacyQuestion
# import json

# def migrate_questions():
#     """Transfer all data from legacy_questions to aptitude_questions"""
    
#     engine = create_engine(DATABASE_URL)
    
#     try:
#         with Session(engine) as session:
#             # Check if legacy_questions table exists
#             inspector = inspect(engine)
#             tables = inspector.get_table_names()
            
#             if 'legacy_questions' not in tables:
#                 print("Table 'legacy_questions' does not exist. Nothing to migrate.")
#                 return
            
#             # Check if aptitude_questions table exists (it should, created by SQLAlchemy)
#             if 'aptitude_questions' not in tables:
#                 print(" Table 'aptitude_questions' does not exist. Creating it...")
#                 # Create the table using the model
#                 LegacyQuestion.__table__.create(engine, checkfirst=True)
#                 print("Created aptitude_questions table")
            
#             # Count existing records in both tables
#             legacy_count = session.execute(
#                 text("SELECT COUNT(*) FROM legacy_questions")
#             ).scalar()
            
#             aptitude_count = session.execute(
#                 text("SELECT COUNT(*) FROM aptitude_questions")
#             ).scalar()
            
#             print(f"\nCurrent Status:")
#             print(f"   legacy_questions: {legacy_count} records")
#             print(f"   aptitude_questions: {aptitude_count} records")
            
#             if legacy_count == 0:
#                 print("\nNo data in legacy_questions table. Nothing to migrate.")
#                 return
            
#             if aptitude_count > 0:
#                 print(f"\n aptitude_questions already has {aptitude_count} records.")
#                 response = input("   Do you want to continue? This will add more records. (y/n): ")
#                 if response.lower() != 'y':
#                     print("Migration cancelled.")
#                     return
            
#             # Transfer all data from legacy_questions to aptitude_questions
#             print(f"\n ransferring {legacy_count} records from legacy_questions to aptitude_questions...")
            
#             # First, clear aptitude_questions if it exists and has data
#             if aptitude_count > 0:
#                 print(f"   Clearing existing {aptitude_count} records from aptitude_questions...")
#                 session.execute(text("TRUNCATE TABLE aptitude_questions"))
#                 session.commit()
#                 print("  Cleared aptitude_questions table")
            
#             # Use raw SQL to copy all data
#             # Simple INSERT ... SELECT without ON CONFLICT since we cleared the table
#             try:
#                 # Check column types match
#                 print("   Checking table structures...")
                
#                 # Get all data from legacy_questions
#                 legacy_data = session.execute(
#                     text("SELECT id, set_no, question, options::text, answer FROM legacy_questions ORDER BY id")
#                 ).fetchall()
                
#                 print(f"   Found {len(legacy_data)} records to transfer")
#                 print("   Inserting records...")
                
#                 transferred_count = 0
#                 batch_size = 100
                
#                 for i in range(0, len(legacy_data), batch_size):
#                     batch = legacy_data[i:i+batch_size]
#                     for row in batch:
#                         try:
#                             # Convert options back to JSON if it's a string
#                             options_value = row[3]
#                             if isinstance(options_value, str):
#                                 import json
#                                 options_value = json.loads(options_value)
                            
#                             session.execute(
#                                 text("""
#                                     INSERT INTO aptitude_questions (id, set_no, question, options, answer)
#                                     VALUES (:id, :set_no, :question, :options, :answer)
#                                 """),
#                                 {
#                                     "id": row[0],
#                                     "set_no": row[1],
#                                     "question": row[2],
#                                     "options": json.dumps(options_value) if not isinstance(options_value, str) else options_value,
#                                     "answer": row[4]
#                                 }
#                             )
#                             transferred_count += 1
#                         except Exception as insert_error:
#                             print(f" Error inserting ID {row[0]}: {insert_error}")
#                             continue
                    
#                     session.commit()
#                     if (i + batch_size) % 500 == 0:
#                         print(f"   Progress: {transferred_count}/{len(legacy_data)} records...")
                
#                 print(f" Successfully inserted {transferred_count} records")
            
#             except Exception as e:
#                 print(f"  Error during transfer: {e}")
#                 import traceback
#                 traceback.print_exc()
#                 session.rollback()
#                 raise
            
#             # Verify migration
#             new_count = session.execute(
#                 text("SELECT COUNT(*) FROM aptitude_questions")
#             ).scalar()
            
#             print(f"\n Migration Complete!")
#             print(f"   Transferred: {legacy_count} records")
#             print(f"   Total in aptitude_questions: {new_count} records")
            
#             # Show sample records
#             sample = session.execute(
#                 text("SELECT id, set_no, LEFT(question, 50) as question_preview FROM aptitude_questions LIMIT 5")
#             ).fetchall()
            
#             if sample:
#                 print(f"\nnnSample records in aptitude_questions:")
#                 for row in sample:
#                     print(f"   ID: {row[0]}, Set: {row[1]}, Question: {row[2]}...")
            
#             print("\n All data has been successfully migrated!")
#             print("   You can now safely drop the legacy_questions table if needed.")
            
#     except Exception as e:
#         print(f"\n  Error during migration: {e}")
#         import traceback
#         traceback.print_exc()
#         return False
    
#     return True

# if __name__ == "__main__":
#     print("=" * 60)
#     print("Migration: legacy_questions → aptitude_questions")
#     print("=" * 60)
    
#     migrate_questions()
    
#     print("\n" + "=" * 60)
#     print("Migration script completed.")
#     print("=" * 60)

"""
Alembic migration: HR Operations — Letters & Exit Management
Revision: 0002_hr_letters_exit
Depends on: 0001_base (existing platform tables)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_hr_letters_exit"
down_revision = "0001_base"
branch_labels = None
depends_on = None


def upgrade():
    # ── hr_letter_templates ──────────────────────────────────────────────────
    op.create_table(
        "hr_letter_templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("letter_type", sa.String(50), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("variables", sa.Text(), nullable=True),      # JSON array
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), default=False, nullable=False),
    )
    op.create_index("ix_hr_letter_templates_name", "hr_letter_templates", ["name"])
    op.create_index("ix_hr_letter_templates_type", "hr_letter_templates", ["letter_type"])

    # ── hr_letters ───────────────────────────────────────────────────────────
    op.create_table(
        "hr_letters",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("hr_letter_templates.id"), nullable=True),
        sa.Column("letter_type", sa.String(50), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column("status", sa.String(50), default="draft", nullable=False),
        sa.Column("issued_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("issued_on", sa.Date(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), default=False, nullable=False),
    )
    op.create_index("ix_hr_letters_employee_id", "hr_letters", ["employee_id"])
    op.create_index("ix_hr_letters_letter_type", "hr_letters", ["letter_type"])
    op.create_index("ix_hr_letters_status", "hr_letters", ["status"])

    # ── resignations ─────────────────────────────────────────────────────────
    op.create_table(
        "resignations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resignation_date", sa.Date(), nullable=False),
        sa.Column("last_working_day", sa.Date(), nullable=True),
        sa.Column("notice_period_days", sa.Integer(), default=0, nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), default="pending", nullable=False),
        sa.Column("accepted_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("hr_remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), default=False, nullable=False),
    )
    op.create_index("ix_resignations_employee_id", "resignations", ["employee_id"])
    op.create_index("ix_resignations_status", "resignations", ["status"])

    # ── clearance_checklists ─────────────────────────────────────────────────
    op.create_table(
        "clearance_checklists",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resignation_id", sa.Integer(), sa.ForeignKey("resignations.id"), nullable=False),
        sa.Column("overall_status", sa.String(50), default="pending", nullable=False),
        sa.Column("initiated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("initiated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # ── clearance_items ──────────────────────────────────────────────────────
    op.create_table(
        "clearance_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("checklist_id", sa.Integer(), sa.ForeignKey("clearance_checklists.id"), nullable=False),
        sa.Column("department", sa.String(50), nullable=False),
        sa.Column("task_description", sa.String(500), nullable=False),
        sa.Column("is_completed", sa.Boolean(), default=False, nullable=False),
        sa.Column("completed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
    )
    op.create_index("ix_clearance_items_checklist_id", "clearance_items", ["checklist_id"])

    # ── exit_interviews ──────────────────────────────────────────────────────
    op.create_table(
        "exit_interviews",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resignation_id", sa.Integer(), sa.ForeignKey("resignations.id"), nullable=False),
        sa.Column("reason_for_leaving", sa.Text(), nullable=True),
        sa.Column("job_satisfaction_score", sa.Integer(), nullable=True),
        sa.Column("management_score", sa.Integer(), nullable=True),
        sa.Column("work_environment_score", sa.Integer(), nullable=True),
        sa.Column("growth_opportunity_score", sa.Integer(), nullable=True),
        sa.Column("would_rejoin", sa.Boolean(), nullable=True),
        sa.Column("suggestions", sa.Text(), nullable=True),
        sa.Column("additional_comments", sa.Text(), nullable=True),
        sa.Column("sentiment_label", sa.String(50), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_exit_interviews_employee_id", "exit_interviews", ["employee_id"])

    # ── fnf_settlements ──────────────────────────────────────────────────────
    op.create_table(
        "fnf_settlements",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resignation_id", sa.Integer(), sa.ForeignKey("resignations.id"), nullable=False),
        sa.Column("basic_salary", sa.Float(), default=0.0),
        sa.Column("hra", sa.Float(), default=0.0),
        sa.Column("other_allowances", sa.Float(), default=0.0),
        sa.Column("leave_encashment", sa.Float(), default=0.0),
        sa.Column("gratuity", sa.Float(), default=0.0),
        sa.Column("bonus_payout", sa.Float(), default=0.0),
        sa.Column("notice_period_payment", sa.Float(), default=0.0),
        sa.Column("notice_period_recovery", sa.Float(), default=0.0),
        sa.Column("loan_recovery", sa.Float(), default=0.0),
        sa.Column("advance_recovery", sa.Float(), default=0.0),
        sa.Column("tax_deduction", sa.Float(), default=0.0),
        sa.Column("other_deductions", sa.Float(), default=0.0),
        sa.Column("gross_earnings", sa.Float(), default=0.0),
        sa.Column("total_deductions", sa.Float(), default=0.0),
        sa.Column("net_payable", sa.Float(), default=0.0),
        sa.Column("status", sa.String(50), default="draft", nullable=False),
        sa.Column("calculated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("calculated_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_fnf_settlements_employee_id", "fnf_settlements", ["employee_id"])


def downgrade():
    op.drop_table("fnf_settlements")
    op.drop_table("exit_interviews")
    op.drop_table("clearance_items")
    op.drop_table("clearance_checklists")
    op.drop_table("resignations")
    op.drop_table("hr_letters")
    op.drop_table("hr_letter_templates")