# test_auth_unit.py
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from jose import jwt
from datetime import datetime, timedelta, timezone

from config.oauth import verify_password, get_password_hash, create_access_token, get_current_user

def test_password_hashing():
    """Test password hashing and verification."""
    password = "secure_password123"
    hashed = get_password_hash(password)
    
    # Verify the hash is different from the original password
    assert hashed != password
    
    # Verify the password verification works
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False

def test_create_access_token():
    """Test JWT token creation."""
    fixed_now = datetime(2025, 5, 1, 8, 0, 0, tzinfo=timezone.utc)  # Fixed datetime for consistent testing
    # Mock the datetime to have consistent expiration
    with patch('config.oauth.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = fixed_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        # Create token
        user_id = "user123"
        token = create_access_token({"sub": user_id})
        
        # Decode and verify token
        decoded = jwt.decode(token, "your_secret_key", algorithms=["HS256"])
        expected_exp = int((fixed_now + timedelta(days=7)).timestamp())
        assert decoded["sub"] == user_id
        assert decoded["exp"] == expected_exp

@pytest.mark.asyncio
async def test_get_current_user_valid_token():
    """Test getting current user with valid token."""
    # Mock dependencies
    with patch('config.oauth.jwt.decode') as mock_decode, \
         patch('config.oauth.get_database') as mock_get_db:
        
        # Setup mocks
        mock_decode.return_value = {"sub": "user123"}
        mock_db = AsyncMock()
        mock_db.users.find_one = AsyncMock(return_value={
            "_id": "user123",
            "username": "testuser",
            "email": "test@example.com",
            "credits": 10
        })
        mock_get_db.return_value = mock_db
        
        # Call function
        user = await get_current_user("valid_token")
        
        # Assertions
        assert user.id == "user123"
        assert user.username == "testuser"