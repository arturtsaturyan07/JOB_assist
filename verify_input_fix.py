import asyncio
import json
from unittest.mock import AsyncMock, Mock

# Mock imports since we can't import main.py directly easily without running app code
class MockWebSocket:
    async def send_json(self, data):
        print(f"WS Send JSON: {data}")

class ConversationEngine:
    async def process_user_input(self, text, user_profile):
        print(f"Engine Process: {text}")
        return Mock(), "Response"

class ChatSession:
    def __init__(self, websocket):
        self.websocket = websocket
        self.history = []
        self.conversation_engine = ConversationEngine()
        self.user_profile_data = {}

    async def process_input(self, text):
        print(f"Processing Input: {text}")

    async def handle_message(self, raw_message: str):
        """Handle incoming WebSocket messages (text or JSON) - COPIED FROM MAIN.PY"""
        try:
            # Try to parse as JSON for special commands
            data = json.loads(raw_message)
            
            # If data is not a dictionary (e.g. just a number "10"), treat as text
            if not isinstance(data, dict):
                await self.process_input(str(data))
                return

            if data.get("type") == "feedback":
                pass
                return
            
            if data.get("type") == "cv_upload":
                pass
                return
            
            # Regular text message
            text = data.get("text", data.get("message", ""))
            await self.process_input(text)
            
        except json.JSONDecodeError:
            # Plain text message
            await self.process_input(raw_message)

async def test_numeric_input():
    print("--- Test: Numeric Input Crash Fix ---")
    ws = MockWebSocket()
    session = ChatSession(ws)
    
    # Test case: User sends "10" (which json.loads as int 10)
    print("\nSending '10'...")
    try:
        await session.handle_message("10")
        print("✅ PASS: '10' handled without crash")
    except AttributeError as e:
        print(f"❌ FAIL: Crash detected: {e}")
    except Exception as e:
        print(f"❌ FAIL: Unexpected error: {e}")

    # Test case: User sends "Hello" (invalid JSON)
    print("\nSending 'Hello'...")
    try:
        await session.handle_message("Hello")
        print("✅ PASS: 'Hello' handled without crash")
    except Exception as e:
        print(f"❌ FAIL: Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(test_numeric_input())
