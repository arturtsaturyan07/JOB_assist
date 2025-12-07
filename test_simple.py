import asyncio
from llm_service import LLMService
import json

async def test():
    svc = LLMService()
    svc.use_fallback = True
    
    # Simulate the full conversation
    history = []
    profile = {}
    
    print("Conversation flow test:")
    print("-" * 50)
    
    # User message 1
    history.append({'role': 'user', 'content': 'hi i am arthur wonna work as a english teacher and python developer'})
    result = await svc.get_response(history, profile)
    profile.update(result['extracted_data'])
    print('After msg 1:')
    print(f'  Ready: {result["extracted_data"].get("ready_to_search", False)}')
    print(f'  Name: {result["extracted_data"].get("name")}')
    print(f'  Goals: {result["extracted_data"].get("career_goals")}')
    
    # User message 2
    history.append({'role': 'assistant', 'content': result['response']})
    history.append({'role': 'user', 'content': 'remote'})
    result = await svc.get_response(history, profile)
    profile.update(result['extracted_data'])
    print('\nAfter msg 2 (remote):')
    print(f'  Ready: {result["extracted_data"].get("ready_to_search", False)}')
    print(f'  Location: {result["extracted_data"].get("location")}')
    print(f'  Remote OK: {result["extracted_data"].get("remote_ok")}')
    
    # User message 3
    history.append({'role': 'assistant', 'content': result['response']})
    history.append({'role': 'user', 'content': 'both'})
    result = await svc.get_response(history, profile)
    profile.update(result['extracted_data'])
    print('\nAfter msg 3 (both):')
    print(f'  Ready: {result["extracted_data"].get("ready_to_search", False)}')
    print(f'  Remote OK: {result["extracted_data"].get("remote_ok")}')
    print(f'  Onsite OK: {result["extracted_data"].get("onsite_ok")}')
    
    print("\nFinal Profile:")
    for key in ['name', 'skills', 'career_goals', 'location', 'remote_ok', 'onsite_ok']:
        print(f'  {key}: {profile.get(key)}')

asyncio.run(test())
