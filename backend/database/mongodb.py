import os
import uuid
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
from datetime import datetime
from fastapi import FastAPI

# MongoDB connection string
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "ai_chat_db")

# MongoDB client
client = None
_db = None

app = FastAPI()

@app.on_event("startup")
async def startup_db_client():
    await connect_to_db()

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_db_connection()

# Add this to debug
async def check_db_setup():
    try:
        db = get_database()
        collections = await db.list_collection_names()
        print(f"Available collections: {collections}")
        if "users" not in collections:
            print("Users collection doesn't exist yet - it will be created on first insert")
    except Exception as e:
        print(f"Error checking database setup: {str(e)}")
        
        
async def test_db_insert():
    try:
        db = get_database()
        result = await db.test_collection.insert_one({"test": "data"})
        print(f"Test document inserted with ID: {result.inserted_id}")
        
        # Verify it was inserted
        doc = await db.test_collection.find_one({"_id": result.inserted_id})
        print(f"Retrieved test document: {doc}")
    except Exception as e:
        print(f"Error in test insert: {str(e)}")


async def connect_to_db():
    """Connect to MongoDB."""
    global client, _db
    try:
        client = AsyncIOMotorClient(MONGODB_URI)
        print(f"Attempting to connect to MongoDB with URI: {MONGODB_URI}")
        
        # Verify the connection
        await client.admin.command('ping')
        _db = client[DB_NAME]
        print(f"Connected to DB: {DB_NAME}")
        
        # Ensure collections and indexes exist
        await setup_collections()
        
    except ConnectionFailure:
        print("Failed to connect to MongoDB")
        raise

async def setup_collections():
    """Set up collections and indexes."""
    # Setup users collection
    user_indexes = [
        IndexModel([("username", ASCENDING)], unique=True),
        IndexModel([("email", ASCENDING)], unique=True),
        IndexModel([("google_id", ASCENDING)], sparse=True),
        IndexModel([("role", ASCENDING)])
    ]
    
    await _db.users.create_indexes(user_indexes)
    
    # Setup payments collection
    payment_indexes = [
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)])
    ]
    
    await _db.payments.create_indexes(payment_indexes)
    
    # Setup chats collection
    chat_indexes = [
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("message", TEXT), ("response", TEXT)])
    ]
    
    await _db.chats.create_indexes(chat_indexes)
    
    print("MongoDB collections and indexes set up")

async def close_db_connection():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
        print("Closed MongoDB connection")

def get_database():
    """Get database instance."""
    if _db is None:
        raise Exception("Database not initialized. Call connect_to_db first.")
    return _db

# Database helper functions

async def create_user(user_data, password_hash_function=None):
    """
    Create a new user in the database.
    
    Args:
        user_data: User creation data with username, email, password
        password_hash_function: Function to hash passwords
        
    Returns:
        Created user document
    """
    db = get_database()
    
    # Check if user with email already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise ValueError("User with this email already exists")
    
    # Check if username is taken
    existing_username = await db.users.find_one({"username": user_data.username})
    if existing_username:
        raise ValueError("Username already taken")
    
    # Create user document
    user_id = str(uuid.uuid4())
    user_doc = {
        "_id": user_id,
        "username": user_data.username,
        "email": user_data.email,
        "hashed_password": password_hash_function(user_data.password) if password_hash_function else user_data.password,
        "google_id": None,
        "avatar": None,
        "credits": 10,  # Starting credits
        "role": "user",
        "created_at": datetime.utcnow()
    }
    
    # Insert into database
    await db.users.insert_one(user_doc)
    
    # Return created user
    return user_doc

async def get_user_by_email(email):
    """
    Get user by email.
    
    Args:
        email: User email
        
    Returns:
        User document or None
    """
    db = get_database()
    return await db.users.find_one({"email": email})

async def get_user_by_id(user_id):
    """
    Get user by ID.
    
    Args:
        user_id: User ID
        
    Returns:
        User document or None
    """
    db = get_database()
    return await db.users.find_one({"_id": user_id})

async def record_chat(user_id, message, response):
    """
    Record a chat in the database and deduct credits.
    
    Args:
        user_id: User ID
        message: User message
        response: AI response
        
    Returns:
        Chat ID
    """
    db = get_database()
    
    chat_id = str(uuid.uuid4())
    chat_doc = {
        "_id": chat_id,
        "user_id": user_id,
        "message": message,
        "response": response,
        "created_at": datetime.utcnow()
    }
    
    await db.chats.insert_one(chat_doc)
    
    # Deduct credits for the chat
    await db.users.update_one(
        {"_id": user_id},
        {"$inc": {"credits": -1}}
    )
    
    return chat_id

async def record_payment(user_id, amount, credits):
    """
    Record a payment transaction and add credits to user.
    
    Args:
        user_id: User ID
        amount: Payment amount
        credits: Credits purchased
        
    Returns:
        Payment ID
    """
    db = get_database()
    
    payment_id = str(uuid.uuid4())
    payment_doc = {
        "_id": payment_id,
        "user_id": user_id,
        "amount": amount,
        "credits": credits,
        "status": "succeeded",
        "created_at": datetime.utcnow()
    }
    
    await db.payments.insert_one(payment_doc)
    
    # Add credits to user
    await db.users.update_one(
        {"_id": user_id},
        {"$inc": {"credits": credits}}
    )
    
    return payment_id

async def get_user_credit_history(user_id):
    """
    Get user credit history (payments and chat usage).
    
    Args:
        user_id: User ID
        
    Returns:
        List of credit history items
    """
    db = get_database()
    
    # Get payments (credits added)
    payments_cursor = db.payments.find(
        {"user_id": user_id, "status": "succeeded"}
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
        {"user_id": user_id}
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

async def get_user_chat_history(user_id, limit=50):
    """
    Get user chat history.
    
    Args:
        user_id: User ID
        limit: Maximum number of chats to return
        
    Returns:
        List of chat history items grouped by day
    """
    db = get_database()
    
    # Get chats
    chats_cursor = db.chats.find(
        {"user_id": user_id}
    ).sort("created_at", -1).limit(limit)
    
    # Group by day
    chats_by_day = {}
    
    async for chat in chats_cursor:
        created_at = chat["created_at"]
        if isinstance(created_at, str):
            from dateutil.parser import parse
            created_at = parse(created_at)
        
        date_str = created_at.strftime("%Y-%m-%d")
        
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

async def update_user_profile(user_id, update_data):
    """
    Update user profile.
    
    Args:
        user_id: User ID
        update_data: Dictionary with fields to update
        
    Returns:
        Updated user document
    """
    db = get_database()
    
    # Update user
    await db.users.update_one({"_id": user_id}, {"$set": update_data})
    
    # Get updated user
    return await db.users.find_one({"_id": user_id})

async def update_user_credits(user_id, credits):
    """
    Update user credits.
    
    Args:
        user_id: User ID
        credits: New credit amount
        
    Returns:
        Updated credit amount
    """
    db = get_database()
    
    await db.users.update_one(
        {"_id": user_id},
        {"$set": {"credits": credits}}
    )
    
    # Get updated user
    user = await db.users.find_one({"_id": user_id})
    return user["credits"]