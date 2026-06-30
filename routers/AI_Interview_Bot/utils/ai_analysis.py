import os
from dotenv import load_dotenv
from openai import OpenAI
import re

load_dotenv()


try:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(" WARNING: OPENAI_API_KEY not found in environment variables. AI scoring will use fallback.")
        client = None
    else:
        client = OpenAI(api_key=api_key)
        print("OpenAI client initialized successfully")
except Exception as e:
    print(f" WARNING: Failed to initialize OpenAI client: {str(e)}")
    client = None

def score_answer(question: str, answer: str) -> int:
    """
    Score an interview answer using AI.
    Returns a score between 0-10.
    Falls back to simple length-based scoring if AI is unavailable.
    """
    
   
    if not client:
        print(" Using fallback scoring (no OpenAI)")
        
        if not answer or len(answer.strip()) < 10:
            return 0
        elif len(answer.strip()) < 50:
            return 5
        elif len(answer.strip()) < 150:
            return 7
        else:
            return 8
    
    try:
        
        prompt = f"""You are an expert interviewer. Score this interview answer on a scale of 0 to 10.
Consider: relevance, completeness, clarity, and depth.

Question: {question}
Answer: {answer}

Provide ONLY a number between 0 and 10 as your response (e.g., "7" or "8.5")."""

        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[
                {"role": "system", "content": "You are an expert interviewer who scores answers objectively. Always respond with just a number from 0 to 10."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=10
        )
        
        score_text = response.choices[0].message.content.strip()
        
        
        numbers = re.findall(r'\d+\.?\d*', score_text)
        if numbers:
            score = float(numbers[0])
            
            score = max(0, min(10, score))
            return int(round(score))
        else:
            print(f" Could not parse AI score from: {score_text}")
            return 5  
            
    except Exception as e:
        print(f" Error in AI scoring: {str(e)}")
        
        if not answer or len(answer.strip()) < 10:
            return 0
        elif len(answer.strip()) < 50:
            return 4
        elif len(answer.strip()) < 150:
            return 6
        else:
            return 7
