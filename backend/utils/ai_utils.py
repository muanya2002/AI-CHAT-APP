import os
import google.generativeai as genai
from celery import Celery

# Initialize Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Initialize Celery
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery('ai_chat', broker=REDIS_URL, backend=REDIS_URL)

@celery_app.task
def generate_ai_response(message: str):
    """Generate AI response using Google's Gemini API."""
    try:
        response = model.generate_content(message)
        return response.text
    except Exception as e:
        print(f"AI Generation Error: {str(e)}")
        raise Exception(f"Failed to generate AI response: {str(e)}")

async def get_ai_response(message: str):
    """Get AI response (non-Celery version for simpler implementation)."""
    try:
        response = model.generate_content(message)
        return response.text
    except Exception as e:
        print(f"AI Generation Error: {str(e)}")
        raise Exception(f"Failed to generate AI response: {str(e)}")
