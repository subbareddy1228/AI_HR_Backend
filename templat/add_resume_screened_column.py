"""
Add resume_screened column to candidate_records table
Run this once to add the new column to the database

Usage:
    python add_resume_screened_column.py
"""

import sys
import os
import codecs

# Add parent directory to path to import core module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from core.database import DATABASE_URL

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def add_resume_screened_column():
    """Add resume_screened column to candidate_records table"""
    
    print(" Adding resume_screened column to candidate_records table...")
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Execute ALTER TABLE command
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Check if column already exists
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'candidate_records' 
                        AND column_name = 'resume_screened'
                    );
                """))
                column_exists = result.scalar()
                
                if column_exists:
                    print(" Column 'resume_screened' already exists!")
                    trans.rollback()
                    return True
                
                # Add the column
                print(" Adding resume_screened column...")
                conn.execute(text("""
                    ALTER TABLE candidate_records 
                    ADD COLUMN resume_screened VARCHAR(20) DEFAULT 'no';
                """))
                
                # Update existing records to 'no' (they haven't been screened yet)
                print(" Setting default value for existing records...")
                conn.execute(text("""
                    UPDATE candidate_records 
                    SET resume_screened = 'no' 
                    WHERE resume_screened IS NULL;
                """))
                
                # Commit transaction
                trans.commit()
                
                print(" SUCCESS! Column added successfully!")
                print("   - resume_screened column added with default value 'no'")
                print("   - All existing records set to 'no'")
                print("\n You can now track resume screening status!")
                
            except Exception as e:
                trans.rollback()
                print(f" Error during ALTER TABLE: {e}")
                raise
                
    except Exception as e:
        print(f" Failed to connect to database: {e}")
        print("\nTry running this SQL command manually:")
        print("ALTER TABLE candidate_records ADD COLUMN resume_screened VARCHAR(20) DEFAULT 'no';")
        print("UPDATE candidate_records SET resume_screened = 'no' WHERE resume_screened IS NULL;")
        return False
    
    return True

if __name__ == "__main__":
    print("="*60)
    print("Add resume_screened Column to candidate_records")
    print("="*60)
    print()
    
    success = add_resume_screened_column()
    
    if success:
        print()
        print("="*60)
        print(" Migration completed successfully!")
        print("="*60)
    else:
        print()
        print("="*60)
        print(" Migration failed. Please check the error above.")
        print("="*60)
        sys.exit(1)

