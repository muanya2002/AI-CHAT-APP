import os
import requests
from fastapi import APIRouter, HTTPException, Depends, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse, HTMLResponse
from typing import Optional
from pydantic import BaseModel
import uuid
from datetime import datetime
from passlib.context import CryptContext

from models.user import UserCreate, UserLogin, TokenResponse, UserResponse, UserInDB
from models.notification import NotificationInDB
from config.oauth import create_access_token, verify_google_token
from database.mongodb import get_database

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Frontend URL for redirects
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:8080")

# Google OAuth settings
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = f"{os.getenv('API_BASE_URL', 'http://localhost:8080')}/api/auth/google/callback"

def verify_password(plain_password, hashed_password):
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Hash password."""
    return pwd_context.hash(password)

class RegisterUser(BaseModel):
    username: str
    email: str
    password: str
 
    
@router.post("/register", response_model=TokenResponse)
async def register(user_data: RegisterUser):
    print("Registering user:", user_data)
    
    """Register a new user."""
    db = get_database()
    
    # Check if email already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        print("Email already in use:" , user_data.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Check if username already exists
    existing_username = await db.users.find_one({"username": user_data.username})
    if existing_username:
        print("Username already in use:" , user_data.username)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )
    
    # Create user
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user_data.password)
    
    user = {
        "_id": user_id,
        "username": user_data.username,
        "email": user_data.email,
        "hashed_password": hashed_password,
        "credits": 5,  # Give new users 5 free credits
        "role": "user",
        "avatar": "",
        "created_at": datetime.utcnow(),
    }
    
    await db.users.insert_one(user)
    
    # Create welcome notification
    notification = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "message": "Welcome! You received 5 free credits to start chatting.",
        "read": False,
        "created_at": datetime.utcnow(),
    }
    await db.notifications.insert_one(notification)
    
    # Create access token
    access_token = create_access_token({"sub": user_id})
    
    return {
        "token": access_token,
        "user": {
            "id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "credits": 5,
            "avatar": "",
            "role": "user",
            "created_at": user["created_at"],
        }
    }

@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    """Authenticate a user."""
    db = get_database()
    
    # Find user by email
    user = await db.users.find_one({"email": user_data.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Verify password
    if not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Create access token
    access_token = create_access_token({"sub": user["_id"]})
    
    return {
        "token": access_token,
        "user": {
            "id": user["_id"],
            "username": user["username"],
            "email": user["email"],
            "credits": user["credits"],
            "avatar": user.get("avatar", ""),
            "role": user.get("role", "user"),
            "created_at": user["created_at"],
        }
    }

@router.post("/token")
async def get_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Get OAuth2 token (for Swagger UI)."""
    db = get_database()
    
    user = await db.users.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token({"sub": user["_id"]})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/google/login")
async def google_login():
    """Redirect to Google OAuth login."""
    auth_url = f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20email%20profile&access_type=offline"
    print(f"Redirecting to: {auth_url}")
    print(f"GOOGLE_REDIRECT_URI is: {GOOGLE_REDIRECT_URI}")
    
    return RedirectResponse(url=auth_url)

@router.get("/google/callback")
async def google_callback(code: str = None, error: str = None):
    """Handle Google OAuth callback."""
    if error:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error={error}")
    
    if not code:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=no_code")
    
    # Exchange code for tokens
    try:
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        token_json = token_response.json()
        
        # Get user info from ID token
        id_token = token_json.get("id_token")
        if not id_token:
            return RedirectResponse(url=f"{FRONTEND_URL}/login?error=no_id_token")
        
        # Verify the ID token
        user_info = await verify_google_token(id_token)
        
        # Process user info
        db = get_database()
        
        # Check if user exists with Google ID
        user = await db.users.find_one({"google_id": user_info["sub"]})
        
        if not user:
            # Check if email already exists
            email_user = await db.users.find_one({"email": user_info["email"]})
            if email_user:
                # Link Google ID to existing account
                await db.users.update_one(
                    {"_id": email_user["_id"]},
                    {"$set": {"google_id": user_info["sub"]}}
                )
                user = await db.users.find_one({"_id": email_user["_id"]})
            else:
                # Create new user
                user_id = str(uuid.uuid4())
                new_user = {
                    "_id": user_id,
                    "username": user_info["name"],
                    "email": user_info["email"],
                    "google_id": user_info["sub"],
                    "avatar": user_info.get("picture", ""),
                    "credits": 5,  # Give new users 5 free credits
                    "role": "user",
                    "created_at": datetime.utcnow(),
                }
                
                await db.users.insert_one(new_user)
                user = new_user
                
                # Create welcome notification
                notification = {
                    "_id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "message": "Welcome! You received 5 free credits to start chatting.",
                    "read": False,
                    "created_at": datetime.utcnow(),
                }
                await db.notifications.insert_one(notification)
        
        # Create access token
        access_token = create_access_token({"sub": user["_id"]})
        
        # Return HTML that posts the token to the parent window and closes itself
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Successful</title>
            <script>
                window.onload = function() {{
                    // Store the token in localStorage
                    localStorage.setItem('currentUser', JSON.stringify({{
                        id: '{user["_id"]}',
                        username: '{user["username"]}',
                        email: '{user["email"]}',
                        credits: {user["credits"]},
                        token: '{access_token}',
                        avatar: '{user.get("avatar", "")}'
                    }}));
                    
                    // Redirect to chat page
                    window.location.href = '{FRONTEND_URL}/chat.html';
                }}
            </script>
        </head>
        <body>
            <h1>Authentication Successful</h1>
            <p>You are being redirected to the application...</p>
        </body>
        </html>
        """)
        
    except Exception as e:
        print(f"Google OAuth error: {str(e)}")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=oauth_error")




