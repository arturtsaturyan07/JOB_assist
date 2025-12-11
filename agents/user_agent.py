from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from llm_gateway import LLMGateway
import json

class ConversationState(str, Enum):
    # Kept for compatibility, though widely unused in new logic
    GREETING = "greeting"
    READY_TO_SEARCH = "ready_to_search"

@dataclass
class ExtractionResult:
    extracted: Dict[str, Any]
    ready_to_search: bool = False
    feedback_message: Optional[str] = None

class UserContextAgent:
    """
    Agent 1: The "Face"
    Responsibility: Talk to user, understand intent, maintain context.
    """
    def __init__(self, llm_gateway: LLMGateway):
        self.llm = llm_gateway
        self.user_profile = {}
        self.chat_history = []  # List of {"role": "user"|"assistant", "content": "..."}
        self.language = "english"
        
        # Define what we need before searching
        self.required_fields = ["location"] 
        # "skills" OR "job_role" is also needed, checking logic below

    async def process_message(self, text: str) -> Tuple[str, bool]:
        """
        Process user message, update state, return response.
        Returns: (response_text, ready_to_search_boolean)
        """
        # 1. Update History
        self.chat_history.append({"role": "user", "content": text})
        
        # 2. Detect Language (simple heuristic, can be improved)
        self.language = self._detect_language(text)
        
        # 3. Holistic Extraction: Try to extract EVERYTHING new from this message
        # Skip if text is empty (initial connection) or too short to contain info
        if not text or len(text.strip()) < 2:
            extraction = ExtractionResult({})
        else:
            extraction = await self._extract_info(text)
        
        # 4. Update Profile with new info
        if extraction.extracted:
            print(f"[UserAgent] Extracted new info: {extraction.extracted}")
            # Merge lists if needed, or overwrite single values
            self.user_profile.update(extraction.extracted)
            
            # Special normalization for skills/role if comma-separated
            if "skills" in self.user_profile and isinstance(self.user_profile["skills"], str):
                self.user_profile["skills"] = [s.strip() for s in self.user_profile["skills"].split(",")]
        
        # 5. Check if we are ready to search
        # We need at least: (skills OR job_role) AND location
        has_role_or_skills = bool(self.user_profile.get("skills")) or bool(self.user_profile.get("job_role"))
        has_location = bool(self.user_profile.get("location"))
        
        ready_to_search = has_role_or_skills and has_location
        
        # 6. Generate Response
        response = await self._generate_response(text, ready_to_search)
        
        self.chat_history.append({"role": "assistant", "content": response})
        return response, ready_to_search

    async def _extract_info(self, text: str) -> ExtractionResult:
        """
        Extract ALL relevant fields from the text, regardless of state.
        """
        system_prompt = """You are a smart job recruiter assistant. 
        Extract structured data from the user's message.
        
        Fields to extract:
        - "name": User's name
        - "job_role": Desired job title(s). If multiple, join them with 'and' (e.g. "Driver and Teacher").
        - "skills": List of skills (e.g. ["Math", "Teaching", "Python"])
        - "location": Desired city/country (e.g. "Yerevan", "Remote")
        - "remote_type": "remote", "onsite", "hybrid", or "any"
        - "min_rate": Minimum hourly rate (number)
        - "max_hours": Max hours per week (number)
        
        Task:
        1. Analyze the user's latest message.
        2. Return a JSON object with ONLY the fields found in the message.
        3. Do NOT invent information. If the user didn't say it, DO NOT include the key.
        4. If input is empty or just a greeting, return {}.
        
        Example Input: "I am John, looking for python jobs or driver work in London"
        Example Output: {"name": "John", "job_role": "Python Developer and Driver", "skills": ["Python", "Driving"], "location": "London"}
        
        Example Input: "Hi"
        Example Output: {}
        """

        try:
            resp = await self.llm.chat(
                messages=[{"role": "user", "content": text}],
                system_instruction=system_prompt,
                model_preference="gemini",
                json_mode=True
            )
            
            # Sanitize possible markdown
            clean_text = resp.replace('```json', '').replace('```', '').strip()
            if not clean_text: return ExtractionResult({})
            
            data = json.loads(clean_text)
            return ExtractionResult(data)
            
        except Exception as e:
            print(f"[UserAgent] Extraction error: {e}")
            return ExtractionResult({})

    async def _generate_response(self, user_text: str, ready_to_search: bool) -> str:
        """
        Generate a conversational response based on what we know and what we need.
        """
        # Determine missing fields for the prompt
        missing = []
        if not self.user_profile.get("job_role") and not self.user_profile.get("skills"):
            missing.append("desired job role or skills")
        if not self.user_profile.get("location"):
            missing.append("location")
            
        # Persona
        persona = self._get_persona_prompt()
        
        state_context = f"""
        Current User Profile: {self.user_profile}
        Missing Information: {', '.join(missing) if missing else 'None - Ready to Search!'}
        Ready to Search: {ready_to_search}
        """

        task_prompt = "Task: Reply to the user. Acknowledge what they said."
        if missing:
            task_prompt += f" Politely ask for the missing info: {', '.join(missing)}."
        elif ready_to_search:
            task_prompt += " Tell them you will look for matching jobs now (don't ask more questions)."
        
        # IMPORTANT: Pass history for context
        # We'll take the last 5 turns to keep context window manageable
        recent_history = self.chat_history[-5:] if self.chat_history else []
        
        full_messages = recent_history + [{"role": "user", "content": f"[System Note: {state_context}]\n[Instruction: {task_prompt}]"}]
        
        resp = await self.llm.chat(
            messages=full_messages, 
            system_instruction=persona, 
            model_preference="openai"
        )
        return resp

    def _detect_language(self, text: str) -> str:
        armenian_chars = sum(1 for c in text if '\u0530' <= c <= '\u0588')
        russian_chars = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
        if armenian_chars > 3: return "armenian"
        if russian_chars > 3: return "russian"
        return "english"

    def _get_persona_prompt(self) -> str:
        if self.language == "russian":
            return "Ты TwinWork AI — дружелюбный помощник в поиске работы. Будь краток и профессионален."
        if self.language == "armenian":
            return "Դու TwinWork AI-ն ես՝ աշխատանքի որոնման ընկերասեր օգնական: Խոսիր հակիրճ:"
        return "You are TwinWork AI, a friendly job search assistant. Keep it short, professional, and warm. Don't be repetitive."
