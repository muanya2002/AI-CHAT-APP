from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import uuid
from datetime import datetime
from dateutil.parser import parse
from models.user import UserResponse, UserUpdate, CreditUpdate, UserInDB
from models.payment import CreditHistory
from models.chat import ChatHistory, ChatResponse
from config.oauth import get_current_user, is_admin
from database.mongodb import get_database

router = APIRouter()

@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: UserInDB = Depends(get_current_user)):
    """Get user profile."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "credits": current_user.credits,
        "avatar": current_user.avatar,
        "role": current_user.role,
        "created_at": current_user.created_at,
    }

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Get user by ID."""
    db = get_database()
    
    # Ensure user can only access their own data unless they're admin
    if user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user's data",
        )
    
    user = await db.users.find_one({"_id": user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return {
        "id": user["_id"],
        "username": user["username"],
        "email": user["email"],
        "credits": user["credits"],
        "avatar": user.get("avatar", ""),
        "role": user.get("role", "user"),
        "created_at": user.get("created_at", datetime.utcnow())
    }

@router.put("/profile", response_model=UserResponse)
async def update_profile(user_data: UserUpdate, current_user: UserInDB = Depends(get_current_user)):
    """Update user profile."""
    db = get_database()
    
    update_data = {}
    
    # Check if username is being updated
    if user_data.username and user_data.username != current_user.username:
        # Check if username is taken
        existing_user = await db.users.find_one({"username": user_data.username})
        if existing_user and existing_user["_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )
        update_data["username"] = user_data.username
    
    # Update password if provided
    if user_data.password:
        from config.oauth import get_password_hash
        update_data["hashed_password"] = get_password_hash(user_data.password)
    
    # Update user if there are changes
    if update_data:
        await db.users.update_one(
            {"_id": current_user.id},
            {"$set": update_data}
        )
    
    # Get updated user
    user = await db.users.find_one({"_id": current_user.id})
    
    return {
        "id": user["_id"],
        "username": user["username"],
        "email": user["email"],
        "credits": user["credits"],
        "avatar": user.get("avatar", ""),
        "role": user.get("role", "user"),
        "created_at": user.get("created_at", datetime.utcnow())
    }

@router.put("/credits", response_model=dict)
async def update_credits(credit_data: CreditUpdate, current_user: UserInDB = Depends(get_current_user)):
    """Update user credits."""
    db = get_database()
    
    await db.users.update_one(
        {"_id": current_user.id},
        {"$set": {"credits": credit_data.credits}}
    )
    
    return {"credits": credit_data.credits}

@router.get("/credit-history", response_model=List[CreditHistory])
async def get_credit_history(current_user: UserInDB = Depends(get_current_user)):
    """Get user credit history."""
    db = get_database()
    
    # Get payments (credits added)
    payments_cursor = db.payments.find(
        {"user_id": current_user.id, "status": "succeeded"}
    ).sort("created_at", -1)
    
    payments = []
    async for payment in payments_cursor:
        payments.append({
            "date": payment["created_at"],
            "description": "Credit purchase",
            "amount": payment["credits"],
            "type": "purchase"
        })
    
    # Get chats (credits used)
    chats_cursor = db.chats.find(
        {"user_id": current_user.id}
    ).sort("created_at", -1)
    
    chats = []
    async for chat in chats_cursor:
        chats.append({
            "date": chat["created_at"],
            "description": "Chat with AI",
            "amount": -1,
            "type": "usage"
        })
    
    # Combine and sort
    credit_history = payments + chats
    credit_history.sort(key=lambda x: x["date"], reverse=True)
    
    return credit_history

@router.get("/chat-history", response_model=List[ChatHistory])
async def get_chat_history(current_user: UserInDB = Depends(get_current_user)):
    """Get user chat history."""
    db = get_database()
    
    # Get chats
    chats_cursor = db.chats.find(
        {"user_id": current_user.id}
    ).sort("created_at", -1).limit(50)
    
    # Group by day
    chats_by_day = {}
    
    async for chat in chats_cursor:
        created_at = chat["created_at"]
        if isinstance(created_at, str):
            created_at = parse(created_at)
        
        date_str = chat["created_at"].strftime("%Y-%m-%d")
        
        if date_str not in chats_by_day:
            chats_by_day[date_str] = []
        
        chats_by_day[date_str].append({
            "id": chat["_id"],
            "user_id": chat["user_id"],
            "message": chat["message"],
            "response": chat["response"],
            "created_at": chat["created_at"]
        })
    
    # Convert to list format
    chat_history = [
        {"date": date, "chats": chats}
        for date, chats in chats_by_day.items()
    ]
    
    return chat_history

@router.get("/", response_model=List[UserResponse])
async def get_all_users(current_user: UserInDB = Depends(is_admin)):
    """Get all users (admin only)."""
    db = get_database()
    
    users_cursor = db.users.find()
    
    users = []
    async for user in users_cursor:
        users.append({
            "id": user["_id"],
            "username": user["username"],
            "email": user["email"],
            "credits": user["credits"],
            "avatar": user.get("avatar", ""),
            "role": user.get("role", "user"),
            "created_at": user.get("created_at", datetime.utcnow())
        })
    
    return users
