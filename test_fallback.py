import asyncio
from llm_service import LLMService
import json

svc = LLMService()
svc.use_fallback = True

history = [
    {'role': 'user', 'content': 'hi i am arthur wonna work as a english teacher and python developer'}
]

result = asyncio.run(svc.get_response(history, {}))
print("RESULT:")
print(json.dumps(result, indent=2, ensure_ascii=False))
