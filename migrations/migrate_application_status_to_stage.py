"""
Migration script to rename 'status' column to 'stage' in application table
and sync stage values across application, candidate, and candidate_records tables.
"""
import sys
import codecs
from sqlalchemy import create_engine, text
from core.database import DATABASE_URL

# Handle Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def migrate_application_status_to_stage():
    """Rename status to stage in application table and sync with other tables"""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            print("=" * 60)
            print("Migration: Rename 'status' to 'stage' in application table")
            print("=" * 60)
            
            # Check if column already exists
            check_stage_query = text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='application' AND column_name='stage'
            """)
            
            stage_exists = conn.execute(check_stage_query).first()
            
            if stage_exists:
                print("[OK] Column 'stage' already exists in application table")
            else:
                # Check if status column exists
                check_status_query = text("""
                    SELECT column_name, data_type FROM information_schema.columns
                    WHERE table_name='application' AND column_name='status'
                """)
                
                status_exists = conn.execute(check_status_query).first()
                
                if not status_exists:
                    print("[ERROR] Neither 'status' nor 'stage' column found in application table")
                    return False
                
                # Add stage column
                print("[INFO] Adding 'stage' column to application table...")
                add_stage_query = text("""
                    ALTER TABLE application 
                    ADD COLUMN stage VARCHAR(50)
                """)
                conn.execute(add_stage_query)
                conn.commit()
                print("[OK] Added 'stage' column")
                
                # Migrate data from status to stage (map enum values to stage values)
                print("[INFO] Migrating data from 'status' to 'stage'...")
                migrate_data_query = text("""
                    UPDATE application 
                    SET stage = CASE 
                        WHEN status::text = 'applied' THEN 'Applied'
                        WHEN status::text = 'rejected' THEN 'Rejected'
                        WHEN status::text = 'hired' THEN 'Hired'
                        WHEN status::text = 'pipeline' THEN 'Screening'
                        ELSE 'Applied'
                    END
                    WHERE stage IS NULL
                """)
                conn.execute(migrate_data_query)
                conn.commit()
                print("[OK] Migrated data from status to stage")
                
                # Set default for stage column
                print("[INFO] Setting default value for 'stage' column...")
                set_default_query = text("""
                    ALTER TABLE application 
                    ALTER COLUMN stage SET DEFAULT 'Applied'
                """)
                conn.execute(set_default_query)
                conn.commit()
                print("[OK] Set default value")
                
                # Drop old status column (optional - comment out if you want to keep it)
                print("[INFO] Dropping old 'status' column...")
                drop_status_query = text("""
                    ALTER TABLE application 
                    DROP COLUMN IF EXISTS status
                """)
                conn.execute(drop_status_query)
                conn.commit()
                print("[OK] Dropped 'status' column")
            
            # Create index on stage column
            print("[INFO] Creating index on 'stage' column...")
            create_index_query = text("""
                CREATE INDEX IF NOT EXISTS idx_application_stage 
                ON application(stage)
            """)
            conn.execute(create_index_query)
            conn.commit()
            print("[OK] Created index")
            
            # Sync stages across all three tables
            print("\n[INFO] Syncing stages across application, candidate, and candidate_records...")
            
            # 1. Sync from candidate_records to candidate and application
            sync_from_records_query = text("""
                -- Update candidate table from candidate_records
                UPDATE candidate c
                SET stage = cr.stage
                FROM candidate_records cr
                WHERE LOWER(TRIM(c.email)) = LOWER(TRIM(cr.candidate_email))
                  AND cr.stage IS NOT NULL
                  AND (c.stage IS NULL OR (c.stage NOT IN ('Screening', 'Interview', 'Offer', 'Hired') AND c.stage != cr.stage));
                
                -- Update application table from candidate_records
                UPDATE application a
                SET stage = cr.stage
                FROM candidate_records cr
                WHERE LOWER(TRIM(a.candidate_email)) = LOWER(TRIM(cr.candidate_email))
                  AND cr.stage IS NOT NULL
                  AND (a.stage IS NULL OR (a.stage NOT IN ('Screening', 'Interview', 'Offer', 'Hired') AND a.stage != cr.stage));
            """)
            result1 = conn.execute(sync_from_records_query)
            conn.commit()
            print(f"[OK] Synced from candidate_records: {result1.rowcount} records updated")
            
            # 2. Sync from candidate to application
            sync_from_candidate_query = text("""
                UPDATE application a
                SET stage = c.stage
                FROM candidate c
                WHERE a.candidate_id = c.id
                  AND c.stage IS NOT NULL
                  AND (a.stage IS NULL OR (a.stage NOT IN ('Screening', 'Interview', 'Offer', 'Hired') AND a.stage != c.stage))
            """)
            result2 = conn.execute(sync_from_candidate_query)
            conn.commit()
            print(f"[OK] Synced from candidate: {result2.rowcount} records updated")
            
            # 3. Sync from application to candidate (for cases where application stage is more advanced)
            sync_from_application_query = text("""
                UPDATE candidate c
                SET stage = a.stage
                FROM application a
                WHERE c.id = a.candidate_id
                  AND a.stage IN ('Screening', 'Interview', 'Offer', 'Hired')
                  AND (c.stage IS NULL OR c.stage NOT IN ('Screening', 'Interview', 'Offer', 'Hired') OR c.stage != a.stage)
            """)
            result3 = conn.execute(sync_from_application_query)
            conn.commit()
            print(f"[OK] Synced from application (advanced stages): {result3.rowcount} records updated")
            
            # Show statistics
            print("\n[INFO] Current Statistics:")
            
            # Application table stats
            app_stats_query = text("""
                SELECT stage, COUNT(*) as count
                FROM application
                GROUP BY stage
                ORDER BY stage
            """)
            app_stats = conn.execute(app_stats_query).fetchall()
            print("\n   application table:")
            for stage, count in app_stats:
                print(f"      {stage}: {count} applications")
            
            # Candidate table stats
            candidate_stats_query = text("""
                SELECT stage, COUNT(*) as count
                FROM candidate
                GROUP BY stage
                ORDER BY stage
            """)
            candidate_stats = conn.execute(candidate_stats_query).fetchall()
            print("\n   candidate table:")
            for stage, count in candidate_stats:
                print(f"      {stage}: {count} candidates")
            
            # Candidate_records stats
            records_stats_query = text("""
                SELECT stage, COUNT(*) as count
                FROM candidate_records
                GROUP BY stage
                ORDER BY stage
            """)
            records_stats = conn.execute(records_stats_query).fetchall()
            print("\n   candidate_records table:")
            for stage, count in records_stats:
                print(f"      {stage}: {count} records")
            
            print("\n" + "=" * 60)
            print("[OK] Migration completed successfully!")
            print("=" * 60)
            
            return True
            
    except Exception as e:
        print(f"\n[ERROR] Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        engine.dispose()

if __name__ == "__main__":
    success = migrate_application_status_to_stage()
    
    if success:
        print("\n" + "=" * 60)
        print("[OK] Migration completed successfully!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("[ERROR] Migration failed. Please check the error messages above.")
        print("=" * 60)
        sys.exit(1)









