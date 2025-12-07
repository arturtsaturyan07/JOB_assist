import asyncio
from llm_service import LLMService
import json
import sys
import io

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test_conversation():
    svc = LLMService()
    svc.use_fallback = True

    # Simulate conversation
    history = []
    profile = {}
    
    print("=" * 60)
    print("Test 1: Initial greeting")
    print("=" * 60)
    
    result = await svc.get_response(history, profile)
    print(f"Response: {result['response']}")
    print(f"Extracted: {result['extracted_data']}")
    print(f"Ready: {result['extracted_data'].get('ready_to_search', False)}")
    profile.update(result['extracted_data'])
    history.append({"role": "user", "content": ""})
    history.append({"role": "assistant", "content": result['response']})
    
    print("\n" + "=" * 60)
    print("Test 2: User introduces name and job")
    print("=" * 60)
    
    user_input = "hi i am arthur wonna work as a english teacher and python developer"
    history.append({"role": "user", "content": user_input})
    result = await svc.get_response(history, profile)
    print(f"User: {user_input}")
    print(f"Response: {result['response']}")
    print(f"Extracted: {result['extracted_data']}")
    print(f"Ready: {result['extracted_data'].get('ready_to_search', False)}")
    profile.update(result['extracted_data'])
    history.append({"role": "assistant", "content": result['response']})
    
    print("\n" + "=" * 60)
    print("Test 3: User says 'remote'")
    print("=" * 60)
    
    user_input = "remote"
    history.append({"role": "user", "content": user_input})
    result = await svc.get_response(history, profile)
    print(f"User: {user_input}")
    print(f"Response: {result['response']}")
    print(f"Extracted: {result['extracted_data']}")
    print(f"Ready: {result['extracted_data'].get('ready_to_search', False)}")
    profile.update(result['extracted_data'])
    history.append({"role": "assistant", "content": result['response']})
    
    print("\n" + "=" * 60)
    print("Test 4: User says 'both'")
    print("=" * 60)
    
    user_input = "both"
    history.append({"role": "user", "content": user_input})
    result = await svc.get_response(history, profile)
    print(f"User: {user_input}")
    print(f"Response: {result['response']}")
    print(f"Extracted: {result['extracted_data']}")
    print(f"Ready: {result['extracted_data'].get('ready_to_search', False)}")
    profile.update(result['extracted_data'])
    
    print("\n" + "=" * 60)
    print("Final Profile:")
    print("=" * 60)
    print(json.dumps(profile, indent=2, ensure_ascii=False))

asyncio.run(test_conversation())
