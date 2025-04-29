from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional

from config.oauth import get_current_user
from models.user import UserInDB

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

async def get_optional_user(token: Optional[str] = Depends(oauth2_scheme)):
    """Get the current user if authenticated, otherwise return None."""
    if not token:
        return None
    
    try:
        return await get_current_user(token)
    except HTTPException:
        return None

def admin_required(current_user: UserInDB = Depends(get_current_user)):
    """Check if the current user is an admin."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized as an admin",
        )
    return current_user
