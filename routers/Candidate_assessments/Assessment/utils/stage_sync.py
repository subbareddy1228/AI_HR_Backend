"""
Helper function to synchronize candidate stage between Candidate (SQLModel), 
candidate_records, and Application tables.
This ensures all three tables stay in sync when stage changes occur.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text, func
from sqlmodel import select
from model.models import Candidate, CandidateRecord, Application


def update_candidate_stage_all_tables(db: Session, email: str, new_stage: str) -> bool:
    """
    Update candidate stage in Candidate (SQLModel), candidate_records, and Application tables.
    Uses case-insensitive email matching for robustness.
    
    Args:
        db: Database session
        email: Candidate email address (used to link all tables)
        new_stage: New stage value (e.g., "Applied", "Screening", "Rejected", "Interview", "Offer", "Hired")
    
    Returns:
        bool: True if at least one table was updated, False otherwise
    """
    updated = False
    email_normalized = email.lower().strip() if email else None
    
    if not email_normalized:
        return False
    
    try:
        # Update Candidate table (SQLModel) - case-insensitive matching
        try:
            # Try SQLModel exec() first, fallback to query() for compatibility
            try:
                statement = select(Candidate).where(func.lower(func.trim(Candidate.email)) == email_normalized)
                candidate = db.exec(statement).first()
            except AttributeError:
                # Fallback to SQLAlchemy query() if exec() not available
                candidate = db.query(Candidate).filter(
                    func.lower(func.trim(Candidate.email)) == email_normalized
                ).first()
            
            if candidate:
                candidate.stage = new_stage
                db.add(candidate)
                db.commit()
                try:
                    db.refresh(candidate)
                except:
                    pass  # refresh() might not be available in all session types
                print(f" Updated Candidate.stage to '{new_stage}' for {email}")
                updated = True
        except Exception as e:
            print(f"Warning: Could not update Candidate table: {e}")
            import traceback
            traceback.print_exc()
        
        # Update candidate_records table (Base/SQLAlchemy) - case-insensitive matching
        try:
            candidate_record_result = db.execute(
                text("""
                    SELECT id FROM candidate_records 
                    WHERE LOWER(TRIM(candidate_email)) = LOWER(:email)
                    LIMIT 1
                """),
                {"email": email_normalized}
            ).first()
            
            if candidate_record_result:
                candidate_record_id = candidate_record_result[0]
                db.execute(
                    text("""
                        UPDATE candidate_records 
                        SET stage = :stage 
                        WHERE id = :id
                    """),
                    {"stage": new_stage, "id": candidate_record_id}
                )
                db.commit()
                print(f" Updated candidate_records.stage to '{new_stage}' for {email}")
                updated = True
        except Exception as e:
            print(f"Warning: Could not update candidate_records table: {e}")
            import traceback
            traceback.print_exc()
        
        # Update Application table (SQLModel) - case-insensitive matching
        try:
            # Update by candidate_email
            result = db.execute(
                text("""
                    UPDATE application 
                    SET stage = :stage,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE LOWER(TRIM(candidate_email)) = LOWER(:email)
                      AND (stage IS NULL 
                           OR (stage NOT IN ('Screening', 'Interview', 'Offer', 'Hired') AND stage != :stage))
                """),
                {"stage": new_stage, "email": email_normalized}
            )
            db.commit()
            apps_updated_by_email = result.rowcount
            
            # Also update by candidate_id if we found a candidate
            if candidate:
                result2 = db.execute(
                    text("""
                        UPDATE application 
                        SET stage = :stage,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE candidate_id = :candidate_id
                          AND (stage IS NULL 
                               OR (stage NOT IN ('Screening', 'Interview', 'Offer', 'Hired') AND stage != :stage))
                    """),
                    {"stage": new_stage, "candidate_id": candidate.id}
                )
                db.commit()
                apps_updated_by_id = result2.rowcount
                
                if apps_updated_by_id > 0:
                    print(f" Updated {apps_updated_by_id} Application record(s) by candidate_id to '{new_stage}' for {email}")
                    updated = True
            
            if apps_updated_by_email > 0:
                print(f" Updated {apps_updated_by_email} Application record(s) by email to '{new_stage}' for {email}")
                updated = True
        except Exception as e:
            print(f"Warning: Could not update Application table: {e}")
            import traceback
            traceback.print_exc()
        
        return updated
        
    except Exception as e:
        print(f"Error updating candidate stage in all tables: {e}")
        import traceback
        traceback.print_exc()
        return False


# Keep the old function name for backward compatibility
def update_candidate_stage_both_tables(db: Session, email: str, new_stage: str) -> bool:
    """
    Backward compatibility wrapper - calls update_candidate_stage_all_tables
    """
    return update_candidate_stage_all_tables(db, email, new_stage)
