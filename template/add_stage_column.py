"""
Migration script to add 'stage' column to candidate_records table.
This script adds the stage column with default value 'Applied' for existing records.
"""

import sys
from pathlib import Path

# Add Backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from core.database import DATABASE_URL

def add_stage_column():
    """Add stage column to candidate_records table if it doesn't exist"""
    
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Check if column already exists
            check_column_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='candidate_records' AND column_name='stage'
            """)
            
            result = conn.execute(check_column_query).first()
            
            if result:
                print("[OK] Column 'stage' already exists in candidate_records table")
                return True
            
            # Add the stage column
            print("[INFO] Adding 'stage' column to candidate_records table...")
            
            add_column_query = text("""
                ALTER TABLE candidate_records 
                ADD COLUMN stage VARCHAR(50) DEFAULT 'Applied'
            """)
            
            conn.execute(add_column_query)
            conn.commit()
            
            # Create index on stage column for better query performance
            print("[INFO] Creating index on 'stage' column...")
            create_index_query = text("""
                CREATE INDEX IF NOT EXISTS idx_candidate_records_stage 
                ON candidate_records(stage)
            """)
            
            conn.execute(create_index_query)
            conn.commit()
            
            # Update existing records to have 'Applied' stage if they don't have one
            print("[INFO] Updating existing records to set stage='Applied'...")
            update_query = text("""
                UPDATE candidate_records 
                SET stage = 'Applied' 
                WHERE stage IS NULL
            """)
            
            conn.execute(update_query)
            conn.commit()
            
            # Verify the column was added
            verify_query = text("""
                SELECT column_name, data_type, column_default 
                FROM information_schema.columns 
                WHERE table_name='candidate_records' AND column_name='stage'
            """)
            
            verify_result = conn.execute(verify_query).first()
            
            if verify_result:
                print(f"[OK] Successfully added 'stage' column:")
                print(f"   Column: {verify_result[0]}")
                print(f"   Type: {verify_result[1]}")
                print(f"   Default: {verify_result[2]}")
                
                # Count records
                count_query = text("SELECT COUNT(*) FROM candidate_records")
                count_result = conn.execute(count_query).scalar()
                print(f"\n[INFO] Total candidate_records: {count_result}")
                
                # Show stage distribution
                stage_dist_query = text("""
                    SELECT stage, COUNT(*) as count 
                    FROM candidate_records 
                    GROUP BY stage
                """)
                
                stage_dist = conn.execute(stage_dist_query).fetchall()
                if stage_dist:
                    print(f"\n[INFO] Stage distribution:")
                    for stage, count in stage_dist:
                        print(f"   {stage}: {count}")
                
                return True
            else:
                print("[ERROR] Column was not added successfully")
                return False
                
    except Exception as e:
        print(f"[ERROR] Error adding stage column: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        engine.dispose()

if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add 'stage' column to candidate_records table")
    print("=" * 60)
    
    success = add_stage_column()
    
    if success:
        print("\n" + "=" * 60)
        print("[OK] Migration completed successfully!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("[ERROR] Migration failed. Please check the error messages above.")
        print("=" * 60)
        sys.exit(1)

