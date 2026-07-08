"""
Script to sync candidate stages based on scores in candidate_records table.
This fixes candidates who have been screened but their stages weren't updated correctly.
"""
import sys
import codecs
from sqlalchemy import create_engine, text
from core.database import DATABASE_URL
from routers.Resume_parsing.routers.config import SCORE_THRESHOLD

# Handle Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def sync_candidate_stages():
    """Sync candidate stages based on scores in candidate_records"""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            print("=" * 60)
            print("Syncing Candidate Stages Based on Scores")
            print("=" * 60)
            print(f"Score Threshold: {SCORE_THRESHOLD}")
            print()
            
            # 1. Update candidate_records stages based on scores
            print("  Updating candidate_records stages...")
            update_records_query = text("""
                UPDATE candidate_records 
                SET stage = CASE 
                    WHEN score IS NULL THEN 'Applied'
                    WHEN score < :threshold THEN 'Rejected'
                    ELSE 'Applied'
                END
                WHERE (stage IS NULL 
                   OR (score IS NOT NULL AND score < :threshold AND stage NOT IN ('Screening', 'Interview', 'Offer', 'Hired') AND stage != 'Rejected')
                   OR (score IS NOT NULL AND score >= :threshold AND stage = 'Rejected' AND stage NOT IN ('Screening', 'Interview', 'Offer', 'Hired')))
            """)
            
            result = conn.execute(update_records_query, {"threshold": SCORE_THRESHOLD})
            conn.commit()
            records_updated = result.rowcount
            print(f"  Updated {records_updated} candidate_records")
            
            # 2. Update candidate table stages based on candidate_records
            print("\n Syncing candidate table stages from candidate_records...")
            sync_candidates_query = text("""
                UPDATE candidate c
                SET stage = cr.stage
                FROM candidate_records cr
                WHERE LOWER(TRIM(c.email)) = LOWER(TRIM(cr.candidate_email))
                  AND cr.stage IS NOT NULL
                  AND (c.stage IS NULL 
                       OR (c.stage NOT IN ('Screening', 'Interview', 'Offer', 'Hired') AND c.stage != cr.stage))
            """)
            
            result = conn.execute(sync_candidates_query)
            conn.commit()
            candidates_updated = result.rowcount
            print(f"  Updated {candidates_updated} candidate records")
            
            # 3. Update application table stages based on candidate_records
            print("\nSyncing application table stages from candidate_records...")
            sync_applications_from_records_query = text("""
                UPDATE application a
                SET stage = cr.stage,
                    updated_at = CURRENT_TIMESTAMP
                FROM candidate_records cr
                WHERE LOWER(TRIM(a.candidate_email)) = LOWER(TRIM(cr.candidate_email))
                  AND cr.stage IS NOT NULL
                  AND (a.stage IS NULL 
                       OR (a.stage NOT IN ('Screening', 'Interview', 'Offer', 'Hired') AND a.stage != cr.stage))
            """)
            
            result = conn.execute(sync_applications_from_records_query)
            conn.commit()
            applications_from_records_updated = result.rowcount
            print(f"   Updated {applications_from_records_updated} application records from candidate_records")
            
            # 4. Update application table stages based on candidate table
            print("\n Syncing application table stages from candidate table...")
            sync_applications_from_candidate_query = text("""
                UPDATE application a
                SET stage = c.stage,
                    updated_at = CURRENT_TIMESTAMP
                FROM candidate c
                WHERE a.candidate_id = c.id
                  AND c.stage IS NOT NULL
                  AND (a.stage IS NULL 
                       OR (a.stage NOT IN ('Screening', 'Interview', 'Offer', 'Hired') AND a.stage != c.stage))
            """)
            
            result = conn.execute(sync_applications_from_candidate_query)
            conn.commit()
            applications_from_candidate_updated = result.rowcount
            print(f" Updated {applications_from_candidate_updated} application records from candidate table")
            
            # 5. Show statistics
            print("\n Current Statistics:")
            
            # Count by stage in candidate_records
            stats_query = text("""
                SELECT 
                    stage,
                    COUNT(*) as count,
                    AVG(score) as avg_score,
                    COUNT(CASE WHEN score IS NULL THEN 1 END) as null_scores
                FROM candidate_records
                GROUP BY stage
                ORDER BY stage
            """)
            
            stats = conn.execute(stats_query).fetchall()
            print("\n   candidate_records table:")
            for stage, count, avg_score, null_scores in stats:
                avg_str = f"{avg_score:.2f}" if avg_score else "N/A"
                null_str = f" ({null_scores} NULL scores)" if null_scores > 0 else ""
                print(f"      {stage}: {count} candidates (avg score: {avg_str}){null_str}")
            
            # Count by stage in candidate table
            candidate_stats_query = text("""
                SELECT 
                    stage,
                    COUNT(*) as count
                FROM candidate
                GROUP BY stage
                ORDER BY stage
            """)
            
            candidate_stats = conn.execute(candidate_stats_query).fetchall()
            print("\n   candidate table:")
            for stage, count in candidate_stats:
                print(f"      {stage}: {count} candidates")
            
            # Count by stage in application table
            application_stats_query = text("""
                SELECT stage, COUNT(*) as count
                FROM application
                GROUP BY stage
                ORDER BY stage
            """)
            
            application_stats = conn.execute(application_stats_query).fetchall()
            print("\n   application table:")
            for stage, count in application_stats:
                print(f"      {stage}: {count} applications")
            
            # 4. Find mismatches
            print("\n4️ Checking for mismatches...")
            mismatch_query = text("""
                SELECT 
                    c.id,
                    c.email,
                    c.stage as candidate_stage,
                    cr.stage as record_stage,
                    cr.score
                FROM candidate c
                JOIN candidate_records cr ON LOWER(TRIM(c.email)) = LOWER(TRIM(cr.candidate_email))
                WHERE c.stage != cr.stage
                   OR (cr.score IS NOT NULL AND cr.score < :threshold AND c.stage != 'Rejected')
                   OR (cr.score IS NOT NULL AND cr.score >= :threshold AND c.stage = 'Rejected' AND c.stage != 'Screening' AND c.stage != 'Interview')
                LIMIT 20
            """)
            
            mismatches = conn.execute(mismatch_query, {"threshold": SCORE_THRESHOLD}).fetchall()
            if mismatches:
                print(f"    Found {len(mismatches)} mismatches (showing first 20):")
                for c_id, email, c_stage, r_stage, score in mismatches:
                    score_str = f"{score:.2f}" if score else "NULL"
                    print(f"      Email: {email} | candidate.stage: {c_stage} | candidate_records.stage: {r_stage} | score: {score_str}")
            else:
                print("    No mismatches found!")
            
            print("\n" + "=" * 60)
            print(" Sync completed successfully!")
            print("=" * 60)
            
            return True
            
    except Exception as e:
        print(f"\n Error during sync: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        engine.dispose()

if __name__ == "__main__":
    success = sync_candidate_stages()
    sys.exit(0 if success else 1)

