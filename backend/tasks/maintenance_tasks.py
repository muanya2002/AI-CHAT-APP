from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
from tasks.celery_app import celery_app
from database.mongodb import get_database

# Configure logging
logger = get_task_logger(__name__)

@shared_task
async def cleanup_old_tasks():
    """Clean up old tasks and logs."""
    logger.info("Running cleanup task")
    
    # Get database
    db = get_database()
    
    # Delete old chat logs (older than 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    result = await db.chats.delete_many({
        "created_at": {"$lt": thirty_days_ago}
    })
    
    logger.info(f"Deleted {result.deleted_count} old chat logs")
    
    # Delete old notifications (older than 60 days)
    sixty_days_ago = datetime.utcnow() - timedelta(days=60)
    
    result = await db.notifications.delete_many({
        "created_at": {"$lt": sixty_days_ago}
    })
    
    logger.info(f"Deleted {result.deleted_count} old notifications")
    
    return {
        "status": "success",
        "message": "Cleanup completed successfully"
    }

@celery_app.task
async def notify_low_credits_users():
    db = get_database()
    users_cursor = db.users.find({"credits": {"$lte": 2}})
    
    async for user in users_cursor:
        notification = {
            "user_id": user["_id"],
            "message": "You're low on credits. Top up to keep chatting!",
            "read": False,
            "created_at": datetime.utcnow(),
        }
        await db.notifications.insert_one(notification)