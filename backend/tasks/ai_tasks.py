import os
import google.generativeai as genai
from celery.utils.log import get_task_logger
from tasks.celery_app import celery_app
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logger = get_task_logger(__name__)

# Initialize Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("models/gemini-1.5-pro-002")
response = model.generate_content


@celery_app.task
def generate_ai_response(message, user_id):
    print(f"[TASK START] Received message: {message} from user: {user_id}")
    try:
        response = model.generate_content(message)
        print(f"[TASK COMPLETE] Gemini response: {response.text}")
        return response.text
    except Exception as e:
        print(f"[TASK ERROR] {e}")
        return "Error generating response."

