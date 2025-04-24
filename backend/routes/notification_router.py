from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import uuid
from datetime import datetime

from models.user import UserInDB
from models.notification import NotificationResponse, NotificationCreate, NotificationList
from config.oauth import get_current_user
from database.mongodb import get_database

router = APIRouter()

@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(current_user: UserInDB = Depends(get_current_user)):
    """Get user notifications."""
    db = get_database()
    
    notifications_cursor = db.notifications.find(
        {"user_id": current_user.id}
    ).sort("created_at", -1).limit(20)
    
    notifications = []
    async for notification in notifications_cursor:
        notifications.append({
            "id": notification["_id"],
            "user_id": notification["user_id"],
            "message": notification["message"],
            "read": notification["read"],
            "created_at": notification["created_at"],
        })
    
    return notifications

@router.put("/mark-read")
async def mark_notifications_read(current_user: UserInDB = Depends(get_current_user)):
    """Mark notifications as read."""
    db = get_database()
    
    await db.notifications.update_many(
        {"user_id": current_user.id, "read": False},
        {"$set": {"read": True}}
    )
    
    return {"success": True}

@router.post("/", response_model=NotificationResponse)
async def create_notification(notification_data: NotificationCreate, current_user: UserInDB = Depends(get_current_user)):
    """Create a notification."""
    db = get_database()
    
    notification_id = str(uuid.uuid4())
    notification = {
        "_id": notification_id,
        "user_id": current_user.id,
        "message": notification_data.message,
        "read": False,
        "created_at": datetime.utcnow(),
    }
    
    await db.notifications.insert_one(notification)
    
    return {
        "id": notification_id,
        "user_id": current_user.id,
        "message": notification_data.message,
        "read": False,
        "created_at": notification["created_at"],
    }
