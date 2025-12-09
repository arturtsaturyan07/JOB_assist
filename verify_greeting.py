import asyncio
from conversation_engine import ConversationEngine, ConversationState

async def test_greeting_improvements():
    engine = ConversationEngine()
    
    print("--- Test 1: Russian Greeting 'хи' (should NOT be a name) ---")
    result, response = await engine.process_user_input("хи", {})
    print(f"Response: {response}")
    if "your name" in response.lower() or "call you" in response.lower():
        print("✅ PASS: Correctly identified as greeting, not name")
    else:
        print(f"❌ FAIL: Treated as name or other: {response}")

    print("\n--- Test 2: 'Hello' during Skill Extraction (should NOT advance) ---")
    # Force state to SKILLS
    engine.current_state = ConversationState.SKILLS_EXTRACT
    result, response = await engine.process_user_input("hello", {"name": "TestUser"})
    print(f"Response: {response}")
    if "kind of job" in response or "job you want" in response:
        print("✅ PASS: 'Hello' did not advance state, asked for clarification")
    else:
        print(f"❌ FAIL: Unexpected state transition or response: {response}")

    print("\n--- Test 3: Clarification 'what?' (should give help) ---")
    # Still in SKILLS state
    result, response = await engine.process_user_input("what?", {"name": "TestUser"})
    print(f"Response: {response}")
    if "need to know" in response.lower() or "job you want" in response.lower():
        print("✅ PASS: Provided helpful context for SKILLS state")
    else:
        print(f"❌ FAIL: Generic or wrong response: {response}")

    print("\n--- Test 4: 'whats up' (Should be Greeting) ---")
    # Reset to greeting
    engine.current_state = ConversationState.GREETING
    result, response = await engine.process_user_input("whats up", {})
    print(f"Input: 'whats up'")
    print(f"Extracted: {result.extracted}")
    print(f"Response: {response}")
    
    if not result.extracted.get("name") and not result.state_progressed:
        print("✅ PASS: 'whats up' recognized as greeting (no name extracted)")
    else:
        print(f"❌ FAIL: extracted name '{result.extracted.get('name')}'")

if __name__ == "__main__":
    asyncio.run(test_greeting_improvements())
