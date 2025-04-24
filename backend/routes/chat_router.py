from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
import uuid
from datetime import datetime
from typing import List
import asyncio
import logging
from models.user import UserInDB
from models.chat import ChatMessage, ChatResponse
from config.oauth import get_current_user
from tasks.ai_tasks import generate_ai_response
from database.mongodb import get_database

router = APIRouter()

##//test to check if my ai is working
##import google.generativeai as genai
##import os
##from dotenv import load_dotenv
##load_dotenv()
##GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
##genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
##print("GEMINI_API_KEY:", os.getenv("GEMINI_API_KEY"))  # just to confirm it's being read

##model = genai.GenerativeModel("models/gemini-1.5-pro-002")
##response = model.generate_content("What is the capital of Nigeria?")
##print(response.text)


@router.post("/", response_model=ChatResponse)
async def send_message(message: ChatMessage, background_tasks: BackgroundTasks, current_user: UserInDB = Depends(get_current_user)):
    """Send message to AI."""
    db = get_database()
    
    # Check if user has enough credits
    if current_user.credits <= 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits",
        )
    
    # Deduct a credit
    await db.users.update_one(
        {"_id": current_user.id},
        {"$inc": {"credits": -1}}
    )
    
    try:
        # Generate AI response using Celery task
        task = generate_ai_response.delay(message.message, current_user.id)
        print("Task ID:", task.id)
        ai_response = task.get(timeout=0)


        # Save chat to database
        chat_id = str(uuid.uuid4())
        chat = {
            "_id": chat_id,
            "user_id": current_user.id,
            "message": message.message,
            "response": ai_response,
            "created_at": datetime.utcnow(),
        }
        
        await db.chats.insert_one(chat)
        
        # Get updated user credits
        user = await db.users.find_one({"_id": current_user.id})
        
        return {
            "id": chat_id,
            "user_id": current_user.id,
            "message": message.message,
            "response": ai_response,
            "created_at": chat["created_at"],
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        # Refund the credit if AI response fails
        await db.users.update_one(
            {"_id": current_user.id},
            {"$inc": {"credits": 1}}
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI response: {str(e)}",
        )

@router.get("/", response_model=List[ChatResponse])
async def get_chat_history(current_user: UserInDB = Depends(get_current_user)):
    """Get chat history."""
    db = get_database()
    
    chats_cursor = db.chats.find(
        {"user_id": current_user.id}).sort("created_at", -1).limit(20)
    
    chats = []
    async for chat in chats_cursor:
        chats.append({
            "id": chat["_id"],
            "user_id": chat["user_id"],
            "message": chat["message"],
            "response": chat["response"],
            "created_at": chat["created_at"],
        })
    
    return chats

@router.post("/stream")
async def stream_message(message: ChatMessage, current_user: UserInDB = Depends(get_current_user)):
    """Stream message to AI."""
    db = get_database()
    
    # Check if user has enough credits
    if current_user.credits <= 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits",
        )
    
    # Deduct a credit
    await db.users.update_one(
        {"_id": current_user.id},
        {"$inc": {"credits": -1}}
    )
    
    
    async def fake_stream():
        try:
            # Generate AI response
            task = generate_ai_response.delay(message.message, current_user.id)
            
            # Poll for task result
            while not task.ready():
                yield f"data: Thinking...\n\n"
                await asyncio.sleep(0.5)
            
            ai_response = task.get()
            
            # Save chat to database
            chat_id = str(uuid.uuid4())
            chat = {
                "_id": chat_id,
                "user_id": current_user.id,
                "message": message.message,
                "response": ai_response,
                "created_at": datetime.utcnow(),
            }
            
            await db.chats.insert_one(chat)
            
            # Stream the response
            for char in ai_response:
                yield f"data: {char}\n\n"
                await asyncio.sleep(0.01)
                
        except Exception as e:
            # Refund the credit if AI response fails
            await db.users.update_one(
                {"_id": current_user.id},
                {"$inc": {"credits": 1}}
            )
            
            yield f"data: Error: {str(e)}\n\n"
    
    return StreamingResponse(fake_stream(), media_type="text/event-stream")
