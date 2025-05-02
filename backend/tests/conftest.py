import pytest_asyncio
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from httpx import AsyncClient
import jwt
from datetime import datetime, timedelta


# Import your FastAPI app
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app
from database.mongodb import connect_to_db, close_db_connection

# Test database settings
TEST_MONGO_URI = os.getenv("TEST_MONGO_URI", "mongodb://localhost:27017/test_ai_chat_db")
JWT_SECRET = os.getenv("JWT_SECRET", "test_secret_key")

@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def test_db():
    """Set up test database."""
    # Connect to test database
    client = AsyncIOMotorClient(TEST_MONGO_URI)
    db_name = TEST_MONGO_URI.split("/")[-1]
    db = client[db_name]
    
    # Override the database connection in your app
    app.state.mongodb = db
    
    yield db
    
    # Clean up: drop test database
    await client.drop_database(db_name)
    client.close()

@pytest_asyncio.fixture
async def client():
    """Create a test client for the FastAPI app."""
    async with AsyncClient(
        base_url="http://test",
        transport=app.transport if hasattr(app, "transport") else None,
        ) as ac:
        yield ac

@pytest_asyncio.fixture
async def test_user(test_db):
    """Create a test user."""
    from config.oauth import get_password_hash
    
    # Create a test user
    user_id = "test_user_id"
    user_data = {
        "_id": user_id,
        "username": "testuser",
        "email": "test@example.com",
        "hashed_password": get_password_hash("password123"),
        "credits": 10,
        "role": "user",
        "created_at": datetime.utcnow()
    }
    
    # Check if user already exists
    existing_user = await test_db.users.find_one({"_id": user_id})
    if not existing_user:
        await test_db.users.insert_one(user_data)
    
    return user_data

@pytest_asyncio.fixture
def auth_token(test_user):
    """Create an authentication token for the test user."""
    payload = {
        "sub": test_user["_id"],
        "exp": datetime.utcnow() + timedelta(days=1)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return token