import os
import google.generativeai as genai
from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional, Union

class LLMGateway:
    """
    Unified gateway for LLM interactions.
    Supports OpenAI (GPT-4o/Turbo) and Google Gemini (Pro/Flash).
    """
    
    def __init__(self):
        # Load API Keys
        self.gemini_key = self._load_key("gemini_api_key.txt")
        self.openai_key = self._load_key("openai_api_key.txt")
        
        # Initialize Gemini
        self.gemini_avaliable = False
        if self.gemini_key:
            try:
                genai.configure(api_key=self.gemini_key)
                # Try multiple model names in order of preference
                model_names = [
                    'gemini-1.5-flash-latest',
                    'gemini-1.5-pro-latest', 
                    'gemini-1.5-flash',
                    'gemini-pro'
                ]
                
                for model_name in model_names:
                    try:
                        self.gemini_model = genai.GenerativeModel(model_name)
                        # Test the model with a simple call
                        test_response = self.gemini_model.generate_content("Hi")
                        self.gemini_avaliable = True
                        print(f"[LLMGateway] Gemini initialized with model: {model_name} ✅")
                        break
                    except Exception as model_error:
                        print(f"[LLMGateway] Model {model_name} failed: {model_error}")
                        continue
                
                if not self.gemini_avaliable:
                    print("[LLMGateway] All Gemini models failed - will use OpenAI fallback")
                    
            except Exception as e:
                print(f"[LLMGateway] Gemini init failed: {e}")

        # Initialize OpenAI
        self.openai_client = None
        if self.openai_key:
            try:
                self.openai_client = AsyncOpenAI(api_key=self.openai_key)
                print("[LLMGateway] OpenAI initialized ✅")
            except Exception as e:
                print(f"[LLMGateway] OpenAI init failed: {e}")

    def _load_key(self, filename: str) -> Optional[str]:
        """Load key from file safely."""
        print(f"[LLMGateway] Loading key from {filename}...")
        try:
            if os.path.exists(filename):
                # Force UTF-8 and ignore errors
                with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                    raw_key = f.read().strip()
                    
                # Sanitize: Keep only valid API key characters (A-Z, a-z, 0-9, -, _)
                # This removes BOMs, zero-width spaces, newlines, etc.
                import re
                key = re.sub(r'[^a-zA-Z0-9\-_]', '', raw_key)
                
                print(f"[LLMGateway] Found key in {filename} (original_len={len(raw_key)}, sanitized_len={len(key)})")
                return key
            else:
                print(f"[LLMGateway] File not found: {os.path.abspath(filename)}")
        except Exception as e:
            print(f"[LLMGateway] Error loading key: {e}")
        return None

    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        system_instruction: str = "",
        model_preference: str = "gemini", # 'gemini' or 'openai'
        json_mode: bool = False
    ) -> str:
        """
        Unified chat method.
        messages format: [{"role": "user", "content": "..."}]
        """
        response = None
        
        # Primary Attempt
        if model_preference == "openai" and self.openai_client:
            response = await self._call_openai(messages, system_instruction, json_mode)
        elif model_preference == "gemini" and self.gemini_avaliable:
            response = await self._call_gemini(messages, system_instruction, json_mode)
        
        # Failover Attempt
        if not response:
            print(f"[LLMGateway] Primary model {model_preference} failed or N/A. Trying failover...")
            if model_preference == "openai" and self.gemini_avaliable:
                response = await self._call_gemini(messages, system_instruction, json_mode)
            elif model_preference == "gemini" and self.openai_client:
                response = await self._call_openai(messages, system_instruction, json_mode)

        if not response:
            raise Exception("All LLM providers failed or are unconfigured.")
            
        return response

    async def _call_openai(self, messages: List[Dict[str, str]], system_instruction: str, json_mode: bool) -> Optional[str]:
        try:
            msgs = []
            if system_instruction:
                msgs.append({"role": "system", "content": system_instruction})
            msgs.extend(messages)
            
            completion = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini", # Cost-effective & fast
                messages=msgs,
                response_format={"type": "json_object"} if json_mode else None
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"[LLMGateway] OpenAI Error: {e}")
            return None

    async def _call_gemini(self, messages: List[Dict[str, str]], system_instruction: str, json_mode: bool) -> Optional[str]:
        try:
            # Convert OpenAI format to Gemini format
            # Gemini: history list of content parts
            history = []
            last_message = ""
            
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                content = msg["content"]
                if msg == messages[-1] and role == "user":
                    last_message = content
                else:
                    history.append({"role": role, "parts": [content]})
            
            # Configure generation
            generation_config = genai.types.GenerationConfig(
                temperature=0.7,
                response_mime_type="application/json" if json_mode else "text/plain"
            )

            # Create chat session
            chat = self.gemini_model.start_chat(history=history)
            
            # If system instruction is present, prepend it to the final prompt or use system_instruction param if supported by library version
            # (gemini-1.5 supports system instruction in model init, but here we just prepend to context for simplicity/compatibility)
            final_prompt = last_message
            if system_instruction:
                final_prompt = f"System Instruction: {system_instruction}\n\nUser: {last_message}"
            
            response = await chat.send_message_async(final_prompt, generation_config=generation_config)
            return response.text
        except Exception as e:
            print(f"[LLMGateway] Gemini Error: {e}")
            return None
