import asyncio
import os
import google.generativeai as genai
import httpx
from llm_service import LLMService

async def debug_llm():
    print("--- Debugging LLM Service ---")
    
    # Check Files
    print(f"Gemini Key File Exists: {os.path.exists('gemini_api_key.txt')}")
    print(f"OpenAI Key File Exists: {os.path.exists('openai_api_key.txt')}")
    
    service = LLMService()
    print(f"Active Provider: {service.provider}")
    print(f"OpenAI Key Loaded: {bool(service.openai_key)} (Length: {len(service.openai_key) if service.openai_key else 0})")
    print(f"Gemini Key Loaded: {bool(service.gemini_key)} (Length: {len(service.gemini_key) if service.gemini_key else 0})")
    
    # Test OpenAI directly if key exists
    if service.openai_key:
        print("\nTesting OpenAI Direct Call...")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {service.openai_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": "Ping"}],
                        "max_tokens": 5
                    }
                )
                print(f"OpenAI Status: {resp.status_code}")
                if resp.status_code != 200:
                    print(f"OpenAI Error: {resp.text}")
                else:
                    print(f"OpenAI Success: {resp.json()['choices'][0]['message']['content']}")
        except Exception as e:
            print(f"OpenAI Exception: {e}")

    # Test Gemini directly if key exists
    if service.gemini_key:
        print("\nTesting Gemini Direct Call...")
        try:
            genai.configure(api_key=service.gemini_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            resp = await model.generate_content_async("Ping")
            print(f"Gemini Success: {resp.text}")
        except Exception as e:
            print(f"Gemini Exception: {e}")

if __name__ == "__main__":
    asyncio.run(debug_llm())
