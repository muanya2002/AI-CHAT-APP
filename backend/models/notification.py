from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class NotificationBase(BaseModel):
    message: str

class NotificationCreate(NotificationBase):
    user_id: str
    read: bool = False

class NotificationResponse(NotificationBase):
    id: str
    user_id: str
    read: bool
    created_at: datetime

class NotificationInDB(NotificationBase):
    id: str
    user_id: str
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class NotificationList(BaseModel):
    notifications: List[NotificationResponse]
