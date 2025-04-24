import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import Celery app
from tasks.celery_app import celery_app

# Import tasks to register them
import tasks.ai_tasks
import tasks.maintenance_tasks

if __name__ == '__main__':
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    celery_app.start()
