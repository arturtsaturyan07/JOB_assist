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
            # Careful update: Don't overwrite existing data with empty values
            for k, v in extraction.extracted.items():
                if v:
                    if k == "job_role":
                        if k in self.user_profile:
                            self.user_profile[k] += f" and {v}"
                        else:
                            self.user_profile[k] = v
                    elif k == "skills":
                        if not isinstance(v, list):
                            v = [s.strip() for s in v.split(",") if s.strip()]
                        if k not in self.user_profile:
                            self.user_profile[k] = []
                        self.user_profile[k].extend(v)
                        self.user_profile[k] = list(set(self.user_profile[k]))  # dedup
                    else:
                        self.user_profile[k] = v
        
        # 5. Check for Special AI Intents (Interview / Salary)
        msg_lower = text.lower()
        
        # Intent: Salary Prediction
        if "salary" in msg_lower and ("predict" in msg_lower or "what is" in msg_lower or "estimate" in msg_lower):
            # Parse role/location quickly (simple heuristic for now)
            # "Salary for Python Dev in London"
            role = self.user_profile.get("job_role", "Software Engineer")
            loc = self.user_profile.get("location", "London")
            
            from market_intelligence import SalaryPredictor
            predictor = SalaryPredictor()
            prediction = await predictor.predict_salary(role, loc)
            
            if "error" not in prediction:
                curr = prediction.get('currency', 'USD')
                r = f"💰 **Estimated Salary for {role} in {loc}:**\n"
                r += f"Range: {prediction.get('min'):,} - {prediction.get('max'):,} {curr}\n"
                r += f"Median: {prediction.get('median'):,} {curr}\n"
                r += f"Confidence: {prediction.get('confidence')}"
                self.chat_history.append({"role": "assistant", "content": r})
                return r, False # Not ready to search for jobs, just answered a query
        
        # Intent: Mock Interview
        if "interview" in msg_lower and ("me" in msg_lower or "practice" in msg_lower or "mock" in msg_lower):
            import re
            # Try to extract role from specific intents: "interview me for [ROLE]"
            match = re.search(r"interview (?:me )?(?:for |as )?(?:a )?(.+)", msg_lower)
            if match:
                # remove common trailing words if user said "interview me for a taxi driver job"
                role_candidate = match.group(1).replace("job", "").replace("role", "").replace("position", "").strip()
                if len(role_candidate) > 2:
                    role = role_candidate.title()
                else:
                    role = self.user_profile.get("job_role", "General Role")
            else:
                role = self.user_profile.get("job_role", "General Role")
            
            # If we recently searched, pick the first job (mock logic)
            # Ideally, we'd pick a specific job_id, but for now we generalize.
            
            from agents.interviewer_agent import InterviewerAgent
            interviewer = InterviewerAgent()
            # Pass the SPECIFIC role to the generator
            questions = await interviewer.generate_questions(role, f"Job Description for {role}")
            
            r = f"🎙️ **Mock Interview for {role}**\n\nHere are 3 questions to practice:\n"
            for i, q in enumerate(questions, 1):
                r += f"{i}. {q}\n"
            r += "\nType your answer to one of them, and I'll review it!"
            self.chat_history.append({"role": "assistant", "content": r})
            return r, False # Not ready to search for jobs, just initiated an interview
        
        # 6. Check if we are ready to search
        # We need at least: (skills OR job_role) AND location
        has_role_or_skills = bool(self.user_profile.get("skills")) or bool(self.user_profile.get("job_role"))
        has_location = bool(self.user_profile.get("location"))
        
        ready_to_search = has_role_or_skills and has_location
        
        # 7. Generate Response
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
        - "min_rate": Minimum hourly rate (number). If they specify currency (e.g. "20 GBP"), extract it to "currency" field.
        - "currency": Currency code (USD, GBP, EUR, AED, AMD, RUB). Default to "USD" if unsure but symbol is $.
        - "max_hours": Max hours per week (number)
        - "busy_schedule": Dictionary of busy times per day. Format: {"Mon": [[start_min, end_min], ...], "Tue": ...}. 
          "Day off" phrases (e.g., "Wednesday is my day off") -> Full day busy: {"Wed": [[0, 1440]]}.
          "Mornings only" (wants to work mornings) -> Busy in afternoons/evenings: Every day [[720, 1440]] (12pm-12am busy).
          "Afternoons only" -> Busy in mornings: Every day [[0, 720]] (12am-12pm busy).
          "Weekends off" -> Busy Sat/Sun [[0, 1440]].
          "Weekdays only" -> Same as Weekends off.
        
        Task:
        1. Analyze the user's latest message.
        2. Return a JSON object with ONLY the fields found in the message.
        3. Do NOT invent information. If the user didn't say it, DO NOT include the key.
        4. If input is empty or just a greeting, return {}.
        5. If user says "no", "none", or declines a preference question, DO NOT return an empty string for that field. Just omit it.
        
        Example Input: "I am John, looking for python jobs or driver work in London, busy on mondays"
        Example Output: {"name": "John", "job_role": "Python Developer and Driver", "skills": ["Python", "Driving"], "location": "London", "busy_schedule": {"Mon": [[0, 1440]]}}
        
        Example Input: "no"  (User responding to 'any company preference?')
        Example Output: {}
        
        Example Input: "Hi"
        Example Output: {}
        """

        # Call LLM with JSON mode
        response_text = await self.llm.chat(
            messages=[{"role": "user", "content": text}],
            system_instruction=system_prompt,
            model_preference="gemini",
            json_mode=True
        )
        
        if not response_text:
            return ExtractionResult(extracted={})
            
        try:
            # 1. Try direct parsing
            return ExtractionResult(extracted=json.loads(response_text))
        except json.JSONDecodeError:
            # 2. Try regex extraction if model added chattiness
            import re
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                try:
                    return ExtractionResult(extracted=json.loads(match.group(0)))
                except:
                    pass
            
            # 3. Fallback
            print(f"[UserAgent] JSON Parse Error. Raw: {response_text}")
            return ExtractionResult(extracted={})
            
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
