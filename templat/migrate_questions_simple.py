"""
Simple Migration: Rename legacy_questions to aptitude_questions

This is faster than copying - just renames the table.
ONLY use this if aptitude_questions table is empty or doesn't exist yet.

Usage:
    python migrate_questions_simple.py
"""

import sys
import codecs

# Fix UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session
from core.database import DATABASE_URL

def migrate_rename():
    """Rename legacy_questions table to aptitude_questions (fastest method)"""
    
    engine = create_engine(DATABASE_URL)
    
    try:
        with Session(engine) as session:
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            if 'legacy_questions' not in tables:
                print("Table 'legacy_questions' does not exist. Nothing to migrate.")
                return
            
            if 'aptitude_questions' in tables:
                # Check if aptitude_questions has data
                count = session.execute(
                    text("SELECT COUNT(*) FROM aptitude_questions")
                ).scalar()
                
                if count > 0:
                    print(f" Table 'aptitude_questions' already exists with {count} records.")
                    print("   Cannot rename - table already exists with data.")
                    print("   Use migrate_legacy_questions.py instead to copy data.")
                    return
            
            # Get count from legacy_questions
            legacy_count = session.execute(
                text("SELECT COUNT(*) FROM legacy_questions")
            ).scalar()
            
            print(f"\n Found {legacy_count} records in legacy_questions")
            print("Renaming table...")
            
            # Rename the table (fastest method)
            session.execute(
                text("ALTER TABLE legacy_questions RENAME TO aptitude_questions")
            )
            session.commit()
            
            print(f"Successfully renamed legacy_questions → aptitude_questions")
            print(f"   Migrated {legacy_count} records instantly!")
            
            # Verify
            new_count = session.execute(
                text("SELECT COUNT(*) FROM aptitude_questions")
            ).scalar()
            
            print(f"\nVerification: aptitude_questions now has {new_count} records")
            
    except Exception as e:
        print(f"\nError during migration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("Fast Migration: Rename legacy_questions → aptitude_questions")
    print("=" * 60)
    print("\n Note: This will rename the table.")
    print("   Use this if aptitude_questions is empty or doesn't exist.")
    print()
    
    migrate_rename()
    
    print("\n" + "=" * 60)

