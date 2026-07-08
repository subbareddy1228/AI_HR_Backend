"""
Initialize AI Interview Questions in Database

This script adds sample interview questions to the database.
Run this once to set up default questions.

Usage:
    python init_ai_interview_questions.py
"""

from sqlalchemy.orm import Session
from core.database import SessionLocal, engine
from model.models import Question, Base

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

def init_questions():
    """Initialize default AI interview questions"""
    
    db: Session = SessionLocal()
    
    try:
        # Check if questions already exist
        existing_count = db.query(Question).count()
        if existing_count > 0:
            print(f" Questions already exist ({existing_count} questions)")
            response = input("Do you want to add more questions anyway? (y/n): ")
            if response.lower() != 'y':
                print(" Cancelled")
                return
        
        # Sample interview questions
        questions = [
            {
                "question_text": "Tell me about yourself and your background.",
                "question_type": "text"
            },
            {
                "question_text": "What are your greatest strengths and how do they relate to this position?",
                "question_type": "text"
            },
            {
                "question_text": "Describe a challenging project you worked on and how you overcame obstacles.",
                "question_type": "text"
            },
            {
                "question_text": "Where do you see yourself in 5 years?",
                "question_type": "text"
            },
            {
                "question_text": "Why do you want to work for our company?",
                "question_type": "text"
            },
            {
                "question_text": "Describe a time when you had to work under pressure.",
                "question_type": "video"
            },
            {
                "question_text": "Tell me about a time you failed and what you learned from it.",
                "question_type": "video"
            },
            {
                "question_text": "How do you handle conflict with team members?",
                "question_type": "video"
            },
            {
                "question_text": "What is your greatest professional achievement?",
                "question_type": "text"
            },
            {
                "question_text": "Why should we hire you over other candidates?",
                "question_type": "video"
            }
        ]
        
        # Add questions to database
        added_count = 0
        for q_data in questions:
            # Check if question already exists
            existing = db.query(Question).filter(
                Question.question_text == q_data["question_text"]
            ).first()
            
            if not existing:
                question = Question(
                    question_text=q_data["question_text"],
                    question_type=q_data["question_type"]
                )
                db.add(question)
                added_count += 1
        
        db.commit()
        print(f"\n Successfully added {added_count} new questions!")
        print(f" Total questions in database: {db.query(Question).count()}")
        
        # Display all questions
        print("\n Current Questions:")
        all_questions = db.query(Question).all()
        for i, q in enumerate(all_questions, 1):
            icon = "📝" if q.question_type == "text" else "📹"
            print(f"{i}. {icon} {q.question_text[:60]}...")
            
    except Exception as e:
        print(f" Error: {e}")
        db.rollback()
    finally:
        db.close()

def clear_questions():
    """Clear all questions from database (use with caution!)"""
    db: Session = SessionLocal()
    
    try:
        count = db.query(Question).count()
        if count == 0:
            print(" No questions to delete")
            return
            
        response = input(f" Are you sure you want to delete all {count} questions? (yes/no): ")
        if response.lower() == 'yes':
            db.query(Question).delete()
            db.commit()
            print(f" Deleted {count} questions")
        else:
            print(" Cancelled")
    except Exception as e:
        print(f" Error: {e}")
        db.rollback()
    finally:
        db.close()

def list_questions():
    """List all questions in database"""
    db: Session = SessionLocal()
    
    try:
        questions = db.query(Question).all()
        
        if not questions:
            print(" No questions found in database")
            print(" Run option 1 to initialize questions")
            return
        
        print(f"\n Total Questions: {len(questions)}\n")
        
        text_questions = [q for q in questions if q.question_type == "text"]
        video_questions = [q for q in questions if q.question_type == "video"]
        
        print(f" Text Questions: {len(text_questions)}")
        for i, q in enumerate(text_questions, 1):
            print(f"  {i}. {q.question_text}")
        
        print(f"\n Video Questions: {len(video_questions)}")
        for i, q in enumerate(video_questions, 1):
            print(f"  {i}. {q.question_text}")
            
    except Exception as e:
        print(f" Error: {e}")
    finally:
        db.close()

def menu():
    """Interactive menu"""
    print("\n" + "="*60)
    print(" AI Interview Questions - Database Manager")
    print("="*60)
    print("\n1. Initialize/Add Questions")
    print("2. List All Questions")
    print("3. Clear All Questions ( Dangerous)")
    print("4. Exit")
    print("\n" + "="*60)
    
    choice = input("\nSelect option (1-4): ")
    
    if choice == "1":
        init_questions()
    elif choice == "2":
        list_questions()
    elif choice == "3":
        clear_questions()
    elif choice == "4":
        print("Goodbye!")
        exit()
    else:
        print(" Invalid option")
    
    # Show menu again
    input("\nPress Enter to continue...")
    menu()

if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        print("\n\n Goodbye!")
    except Exception as e:
        print(f"\n Error: {e}")



