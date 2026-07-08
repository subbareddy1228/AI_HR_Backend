"""
Fix Assignment Table - Drop NOT NULL constraint on candidate_id column
Run this once to fix the database table structure
"""

import sys
import codecs
from sqlalchemy import create_engine, text
from core.database import DATABASE_URL

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def fix_assignment_table():
    """Remove NOT NULL constraint from candidate_id column"""
    
    print(" Fixing assignment table...")
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Execute ALTER TABLE command
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Drop NOT NULL constraint
                conn.execute(text(
                    "ALTER TABLE assignment ALTER COLUMN candidate_id DROP NOT NULL;"
                ))
                
                # Commit transaction
                trans.commit()
                
                print(" SUCCESS! Assignment table fixed!")
                print("   - candidate_id column now allows NULL values")
                print("\n You can now assign assessments without errors!")
                
            except Exception as e:
                trans.rollback()
                print(f" Error during ALTER TABLE: {e}")
                raise
                
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        print("\nTry running this SQL command manually:")
        print("ALTER TABLE assignment ALTER COLUMN candidate_id DROP NOT NULL;")
        return False
    
    return True

if __name__ == "__main__":
    print("="*60)
    print("Assignment Table Fix")
    print("="*60)
    print()
    
    success = fix_assignment_table()
    
    print()
    print("="*60)
    if success:
        print("Next steps:")
        print("1. Restart your backend: uvicorn main:app --reload")
        print("2. Try assigning an assessment - it should work now!")
    print("="*60)



