from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: str
    credits: int
    avatar: Optional[str] = None
    role: UserRole = UserRole.USER
    created_at: datetime

    class Config:
        from_attributes = True

class UserInDB(UserBase):
    id: str = Field(..., alias="_id")
    hashed_password: Optional[str] = None
    google_id: Optional[str] = None
    avatar: Optional[str] = None
    credits: int = 0
    role: UserRole = UserRole.USER
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
class Config:
    allow_population_by_field_name = True


class TokenResponse(BaseModel):
    token: str
    user: UserResponse

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None

class CreditUpdate(BaseModel):
    credits: int
