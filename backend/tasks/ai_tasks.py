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
    logger.info(f"[TASK START] Received message: {message} from user: {user_id}")
    try:
        model = genai.GenerativeModel("models/gemini-1.5-pro-002")
        response = model.generate_content(message)
        logger.info(f"[TASK COMPLETE] Generated {len(response.text)} chars response")
        return {"text": response.text}  # <<< RETURN A DICT INSTEAD OF STRING
    except Exception as e:
        logger.error(f"[TASK ERROR] {e}")
        return {"error": "Error generating response"}


