"""
Migration script to add question_text and template_question_index columns to answers table
and make question_id nullable for template-based questions.
"""
from sqlalchemy import create_engine, text
from core.database import engine
import os

def migrate():
    """Add new columns to answers table"""
    try:
        with engine.begin() as conn:
            # Check if question_text column exists
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'answers' 
                AND column_name = 'question_text'
            """))
            
            if result.scalar() == 0:
                # Add question_text column
                conn.execute(text("""
                    ALTER TABLE answers 
                    ADD COLUMN question_text TEXT
                """))
                print("Added 'question_text' column to answers table")
            
            # Check if template_question_index column exists
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'answers' 
                AND column_name = 'template_question_index'
            """))
            
            if result.scalar() == 0:
                # Add template_question_index column
                conn.execute(text("""
                    ALTER TABLE answers 
                    ADD COLUMN template_question_index INTEGER
                """))
                print("Added 'template_question_index' column to answers table")
            
            # Make question_id nullable (if not already)
            # First check current constraint
            result = conn.execute(text("""
                SELECT is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'answers' 
                AND column_name = 'question_id'
            """))
            
            if result.scalar() == 'NO':
                # Drop the foreign key constraint temporarily
                conn.execute(text("""
                    ALTER TABLE answers 
                    DROP CONSTRAINT IF EXISTS answers_question_id_fkey
                """))
                
                # Make question_id nullable
                conn.execute(text("""
                    ALTER TABLE answers 
                    ALTER COLUMN question_id DROP NOT NULL
                """))
                
                # Re-add foreign key constraint (now nullable)
                conn.execute(text("""
                    ALTER TABLE answers 
                    ADD CONSTRAINT answers_question_id_fkey 
                    FOREIGN KEY (question_id) 
                    REFERENCES questions(id)
                """))
                print("Made 'question_id' nullable in answers table")
            
            print("Migration completed successfully!")
            
    except Exception as e:
        print(f"Migration error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    migrate()

