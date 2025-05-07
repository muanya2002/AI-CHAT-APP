import os
from celery import Celery
from dotenv import load_dotenv
load_dotenv()
# Redis URL for Celery
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery
celery_app = Celery(
    'ai_chat',
    broker=REDIS_URL,
        backend=REDIS_URL,
        include=['tasks.ai_tasks', 'tasks.maintenance_tasks']
    )

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
)
 


# Optional: Define periodic tasks
celery_app.conf.beat_schedule = {
    'cleanup-old-tasks': {
        'task': 'tasks.maintenance_tasks.cleanup_old_tasks',
        'schedule': 1728000.0,  # Once a day
    },
    'notify-low-credits': {
        'task': 'tasks.maintenance_tasks.notify_low_credits_users',
        'schedule': 86400.0,  # every 24 hours
},
}
from tasks import ai_tasks