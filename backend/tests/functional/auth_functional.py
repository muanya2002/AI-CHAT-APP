import uuid
import pytest
from fastapi.testclient import TestClient
from main import app  # Adjust this import to match your app structure

@pytest.fixture
def client():
    """Create a test client."""
    with TestClient(app) as test_client:
        yield test_client

def test_register_user(client):
    """Test user registration endpoint."""
    # Generate unique email and username with UUID to avoid conflicts
    unique_id = str(uuid.uuid4())[:8]
    response = client.post("/api/auth/register", json={
        "username": f"newuser_{unique_id}",
        "email": f"new_{unique_id}@example.com",
        "password": "securepass123"
    })
    
    assert response.status_code == 200
    # Add more assertions as needed to verify response structure
    assert "token" in response.json()
    assert "user" in response.json()


def test_login_user(client):
    """Test user login endpoint."""
    # Generate unique email and username with UUID to avoid conflicts
    unique_id = str(uuid.uuid4())[:8]
    test_user = {
        "username": f"logintest_{unique_id}",
        "email": f"login_{unique_id}@example.com",
        "password": "securepass123"
    }
    
    # First register a user
    register_response = client.post("/api/auth/register", json=test_user)
    assert register_response.status_code == 200
    
    # Then try to login
    login_response = client.post("/api/auth/login", json={
        "email": test_user["email"],
        "password": test_user["password"]
    })
    
    assert login_response.status_code == 200
    assert "token" in login_response.json()
    assert "user" in login_response.json()