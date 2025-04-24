from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    id: str
    user_id: str
    message: str
    response: str
    created_at: datetime

class ChatInDB(BaseModel):
    id: str
    user_id: str
    message: str
    response: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ChatHistory(BaseModel):
    date: str
    chats: List[ChatResponse]
