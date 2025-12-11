# Legacy LLM Service - Deprecated
# This file is kept as a dummy to prevent ImportErrors if any old code references it.
# Please use llm_gateway.py instead.

class LLMService:
    def __init__(self):
        print("[LLMService] Warning: This is a deprecated dummy service. Use LLMGateway.")
        self.available = False

    async def chat(self, user_message: str, system_context: str) -> str:
        return "System Error: Legacy LLM Service called. Please update code to use LLMGateway."