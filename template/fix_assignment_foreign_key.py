"""
Fix Assignment Table - Drop Foreign Key Constraint on candidate_id
This allows assignments to reference candidates from any table (candidate_records, candidate, etc.)
"""

import sys
import codecs
from sqlalchemy import create_engine, text
from core.database import DATABASE_URL

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def fix_assignment_foreign_key():
    """Remove foreign key constraint from candidate_id column"""
    
    print(" Fixing assignment table foreign key...")
    print()
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Execute ALTER TABLE commands
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                print("Step 1: Dropping foreign key constraint...")
                # Drop the foreign key constraint
                conn.execute(text(
                    "ALTER TABLE assignment DROP CONSTRAINT IF EXISTS assignment_candidate_id_fkey;"
                ))
                print("Foreign key constraint removed")
                
                print()
                print("Step 2: Verifying candidate_id is nullable...")
                # Ensure column is nullable (should already be done, but let's be sure)
                conn.execute(text(
                    "ALTER TABLE assignment ALTER COLUMN candidate_id DROP NOT NULL;"
                ))
                print(" Column is nullable")
                
                # Commit transaction
                trans.commit()
                
                print()
                print("="*60)
                print(" SUCCESS! Assignment table completely fixed!")
                print("="*60)
                print()
                print("What changed:")
                print("  • Foreign key constraint REMOVED")
                print("  • candidate_id can now be:")
                print("    - NULL (no candidate)")
                print("    - Any number (from any candidate table)")
                print("    - No validation required!")
                print()
                print(" You can now assign assessments to ANY candidate!")
                
            except Exception as e:
                trans.rollback()
                print(f" Error during ALTER TABLE: {e}")
                print()
                print("Try running these SQL commands manually:")
                print("  ALTER TABLE assignment DROP CONSTRAINT IF EXISTS assignment_candidate_id_fkey;")
                print("  ALTER TABLE assignment ALTER COLUMN candidate_id DROP NOT NULL;")
                raise
                
    except Exception as e:
        print(f" Failed to connect to database: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("="*60)
    print("Assignment Table Foreign Key Fix")
    print("="*60)
    print()
    print("This will remove the foreign key constraint that requires")
    print("candidate_id to exist in the 'candidate' table.")
    print()
    print("After this fix, you can assign assessments to candidates")
    print("from ANY table (candidate_records, candidate, etc.)")
    print()
    print("="*60)
    print()
    
    success = fix_assignment_foreign_key()
    
    print()
    print("="*60)
    if success:
        print(" FIX COMPLETE!")
        print()
        print("Next steps:")
        print("1. Restart your backend: uvicorn main:app --reload")
        print("2. Try assigning an assessment - it will work now!")
        print("3. You can use candidate ID 8 or ANY other ID!")
    else:
        print(" Fix failed - see error above")
    print("="*60)



