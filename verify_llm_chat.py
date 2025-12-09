import asyncio
from llm_service import LLMService
from conversation_engine import ConversationEngine, ConversationState

async def test_llm_chat():
    print("--- Initializing Services ---")
    llm_service = LLMService()
    print(f"LLM Provider: {llm_service.provider}")
    
    engine = ConversationEngine(llm_service)
    
    print("\n--- Test 1: Normal Extraction (Should NOT use LLM) ---")
    # "I am Arthur" -> Name extraction
    result, response = await engine.process_user_input("I am Arthur", {})
    print(f"Input: 'I am Arthur'")
    print(f"Extracted: {result.extracted}")
    print(f"Response: {response}")
    
    if result.state_progressed and result.extracted.get("name") == "Arthur":
        print("✅ PASS: Normal extraction worked")
    else:
        print("❌ FAIL: Normal extraction failed")

    print("\n--- Test 2: General Chat (Should trigger LLM) ---")
    # "Do you understand me?" -> Regex fails -> LLM
    # Note: State is now SKILLS_EXTRACT because of previous step
    user_input = "Do you understand me?"
    result, response = await engine.process_user_input(user_input, {"name": "Arthur"})
    
    print(f"Input: '{user_input}'")
    print(f"Result State Progressed: {result.state_progressed}")
    print(f"Response: {response}")
    
    if not result.state_progressed and "understand" in response.lower():
        print("✅ PASS: LLM responded correctly.")
    elif "interference" in response:
        print("⚠️ WARN: LLM Connection failure (expected if no valid key/network)")
    elif "clarify" in response:
        print("❌ FAIL: Fallback to generic error message instead of LLM")
    else:
        print(f"❓ UNDEFINED: {response}")

if __name__ == "__main__":
    asyncio.run(test_llm_chat())
