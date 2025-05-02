# test_chat_unit.py
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from models.chat import ChatMessage
from routes.chat_router import send_message
from utils.ai_utils import get_ai_response


@pytest.mark.asyncio
async def test_generate_ai_response():
    """Test AI response generation."""
    with patch('utils.ai_utils.model') as mock_model:
        # Setup mock
        mock_response = MagicMock()
        mock_response.text = "This is an AI response"
        mock_model.generate_content.return_value = mock_response

        # Call function
        response = await get_ai_response("Hello AI")

        # Assertions
        assert response == "This is an AI response"
        mock_model.generate_content.assert_called_once_with("Hello AI")


@pytest.mark.asyncio
async def test_send_message_endpoint():
    """Test send message endpoint."""
    with patch('routes.chat_router.get_database') as mock_get_db, \
         patch('routes.chat_router.generate_ai_response') as mock_generate:

        # Setup mocks
        mock_db = AsyncMock()
        mock_db.users.update_one = AsyncMock()
        mock_db.users.find_one = AsyncMock(return_value={"credits": 9})
        mock_db.chats.insert_one = AsyncMock(return_value=MagicMock(inserted_id="chat123"))
        mock_get_db.return_value = mock_db
        mock_generate.delay.return_value.get.return_value = "AI response to your message"

        # Mock current user
        current_user = MagicMock()
        current_user.id = "user123"
        current_user.username = "testuser"
        current_user.credits = 10

        # Use ChatMessage Pydantic model instead of dict
        message = ChatMessage(message="Hello AI")

        # Call function
        response = await send_message(message, background_tasks={}, current_user=current_user)

        # Assertions
        assert response["response"] == "AI response to your message"
        assert response["user_id"] == "user123"
        assert response["message"] == "Hello AI"
        mock_db.users.update_one.assert_called_once()
