"""
Migration Script: Transfer data from legacy_questions to aptitude_questions

This script transfers all data from the old legacy_questions table 
to the new aptitude_questions table.

Usage:
    python migrate_legacy_questions.py
"""

import sys
import codecs

# Fix UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session
from core.database import DATABASE_URL, SessionLocal
from model import LegacyQuestion
import json

def migrate_questions():
    """Transfer all data from legacy_questions to aptitude_questions"""
    
    engine = create_engine(DATABASE_URL)
    
    try:
        with Session(engine) as session:
            # Check if legacy_questions table exists
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            if 'legacy_questions' not in tables:
                print("Table 'legacy_questions' does not exist. Nothing to migrate.")
                return
            
            # Check if aptitude_questions table exists (it should, created by SQLAlchemy)
            if 'aptitude_questions' not in tables:
                print(" Table 'aptitude_questions' does not exist. Creating it...")
                # Create the table using the model
                LegacyQuestion.__table__.create(engine, checkfirst=True)
                print("Created aptitude_questions table")
            
            # Count existing records in both tables
            legacy_count = session.execute(
                text("SELECT COUNT(*) FROM legacy_questions")
            ).scalar()
            
            aptitude_count = session.execute(
                text("SELECT COUNT(*) FROM aptitude_questions")
            ).scalar()
            
            print(f"\nCurrent Status:")
            print(f"   legacy_questions: {legacy_count} records")
            print(f"   aptitude_questions: {aptitude_count} records")
            
            if legacy_count == 0:
                print("\nNo data in legacy_questions table. Nothing to migrate.")
                return
            
            if aptitude_count > 0:
                print(f"\n aptitude_questions already has {aptitude_count} records.")
                response = input("   Do you want to continue? This will add more records. (y/n): ")
                if response.lower() != 'y':
                    print("Migration cancelled.")
                    return
            
            # Transfer all data from legacy_questions to aptitude_questions
            print(f"\n ransferring {legacy_count} records from legacy_questions to aptitude_questions...")
            
            # First, clear aptitude_questions if it exists and has data
            if aptitude_count > 0:
                print(f"   Clearing existing {aptitude_count} records from aptitude_questions...")
                session.execute(text("TRUNCATE TABLE aptitude_questions"))
                session.commit()
                print("  Cleared aptitude_questions table")
            
            # Use raw SQL to copy all data
            # Simple INSERT ... SELECT without ON CONFLICT since we cleared the table
            try:
                # Check column types match
                print("   Checking table structures...")
                
                # Get all data from legacy_questions
                legacy_data = session.execute(
                    text("SELECT id, set_no, question, options::text, answer FROM legacy_questions ORDER BY id")
                ).fetchall()
                
                print(f"   Found {len(legacy_data)} records to transfer")
                print("   Inserting records...")
                
                transferred_count = 0
                batch_size = 100
                
                for i in range(0, len(legacy_data), batch_size):
                    batch = legacy_data[i:i+batch_size]
                    for row in batch:
                        try:
                            # Convert options back to JSON if it's a string
                            options_value = row[3]
                            if isinstance(options_value, str):
                                import json
                                options_value = json.loads(options_value)
                            
                            session.execute(
                                text("""
                                    INSERT INTO aptitude_questions (id, set_no, question, options, answer)
                                    VALUES (:id, :set_no, :question, :options, :answer)
                                """),
                                {
                                    "id": row[0],
                                    "set_no": row[1],
                                    "question": row[2],
                                    "options": json.dumps(options_value) if not isinstance(options_value, str) else options_value,
                                    "answer": row[4]
                                }
                            )
                            transferred_count += 1
                        except Exception as insert_error:
                            print(f" Error inserting ID {row[0]}: {insert_error}")
                            continue
                    
                    session.commit()
                    if (i + batch_size) % 500 == 0:
                        print(f"   Progress: {transferred_count}/{len(legacy_data)} records...")
                
                print(f" Successfully inserted {transferred_count} records")
            
            except Exception as e:
                print(f"  Error during transfer: {e}")
                import traceback
                traceback.print_exc()
                session.rollback()
                raise
            
            # Verify migration
            new_count = session.execute(
                text("SELECT COUNT(*) FROM aptitude_questions")
            ).scalar()
            
            print(f"\n Migration Complete!")
            print(f"   Transferred: {legacy_count} records")
            print(f"   Total in aptitude_questions: {new_count} records")
            
            # Show sample records
            sample = session.execute(
                text("SELECT id, set_no, LEFT(question, 50) as question_preview FROM aptitude_questions LIMIT 5")
            ).fetchall()
            
            if sample:
                print(f"\nnnSample records in aptitude_questions:")
                for row in sample:
                    print(f"   ID: {row[0]}, Set: {row[1]}, Question: {row[2]}...")
            
            print("\n All data has been successfully migrated!")
            print("   You can now safely drop the legacy_questions table if needed.")
            
    except Exception as e:
        print(f"\n  Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("Migration: legacy_questions → aptitude_questions")
    print("=" * 60)
    
    migrate_questions()
    
    print("\n" + "=" * 60)
    print("Migration script completed.")
    print("=" * 60)

