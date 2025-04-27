import os
from jose import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from google.oauth2 import id_token
from google.auth.transport import requests
from models.user import UserInDB
from database.mongodb import get_database
import uuid

# JWT settings
JWT_SECRET = os.getenv("JWT_SECRET", "your_secret_key")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Google OAuth settings
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

def verify_password(plain_password, hashed_password):
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Hash password."""
    return pwd_context.hash(password)

def create_access_token(data: dict):
    """Create JWT token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)  # Fixed to use the constant
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.JWTError:
        raise credentials_exception
    
    db = get_database()
    user = await db.users.find_one({"_id": user_id})
    
    if user is None:
        raise credentials_exception
    
    return UserInDB(**user)

async def verify_google_token(token: str):
    """Verify Google ID token with client_id from environment variable.
    This function now automatically uses the GOOGLE_CLIENT_ID from environment.
    """
    if not GOOGLE_CLIENT_ID:
        raise Exception("GOOGLE_CLIENT_ID environment variable is not set")
        
    try:
        request_adapter = requests.Request()
        idinfo = id_token.verify_oauth2_token(token, request_adapter, GOOGLE_CLIENT_ID, clock_skew_in_seconds=20)

        # Optionally check the issuer
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')

        return idinfo  # Contains user's email, sub, name, etc.

    except ValueError as e:
        raise Exception(f"Invalid Google token: {str(e)}")
        
def is_admin(user: UserInDB = Depends(get_current_user)):
    """Check if user is admin."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized as an admin",
        )
    return user