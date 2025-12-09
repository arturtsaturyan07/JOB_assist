"""
Multi-Model LLM Service for TwinWork AI

Provides intelligent model routing with support for:
- Gemini API (primary)
- Local Ollama models (future: Mistral, Llama, Gemma)
- Rule-based fallback extraction

Architecture designed for easy Ollama integration when available.
"""

import os
import json
import re
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

# Gemini imports
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google-generativeai not installed")

# Ollama imports (for future use)
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


class TaskType(Enum):
    """Types of tasks for model routing"""
    CONVERSATION = "conversation"      # Simple chat, greetings
    PROFILE_EXTRACTION = "profile"     # Extract user profile data
    JOB_ANALYSIS = "job_analysis"      # Deep job description analysis
    SCHEDULE_PARSING = "schedule"      # Parse schedule from text
    CV_ANALYSIS = "cv_analysis"        # CV/resume parsing
    TRANSLATION = "translation"        # Language detection/translation


class ModelProvider(Enum):
    """Available model providers"""
    GEMINI = "gemini"
    OLLAMA = "ollama"
    FALLBACK = "fallback"  # Rule-based extraction


@dataclass
class ModelConfig:
    """Configuration for a specific model"""
    provider: ModelProvider
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 2048


# Model routing configuration
MODEL_ROUTES = {
    TaskType.CONVERSATION: [
        ModelConfig(ModelProvider.OLLAMA, "gemma:2b", 0.8),      # Fast, small
        ModelConfig(ModelProvider.GEMINI, "gemini-2.0-flash", 0.7),
    ],
    TaskType.PROFILE_EXTRACTION: [
        ModelConfig(ModelProvider.GEMINI, "gemini-2.0-flash", 0.3),  # Low temp for accuracy
        ModelConfig(ModelProvider.OLLAMA, "mistral", 0.3),
    ],
    TaskType.JOB_ANALYSIS: [
        ModelConfig(ModelProvider.OLLAMA, "mistral", 0.4),       # Best for extraction
        ModelConfig(ModelProvider.GEMINI, "gemini-2.0-flash", 0.4),
    ],
    TaskType.SCHEDULE_PARSING: [
        ModelConfig(ModelProvider.GEMINI, "gemini-2.0-flash", 0.2),  # Very low temp
        ModelConfig(ModelProvider.OLLAMA, "mistral", 0.2),
    ],
    TaskType.CV_ANALYSIS: [
        ModelConfig(ModelProvider.GEMINI, "gemini-2.0-flash", 0.3),
        ModelConfig(ModelProvider.OLLAMA, "mistral", 0.3),
    ],
}


class MultiModelService:
    """
    Multi-model LLM orchestrator with intelligent routing.
    
    Currently uses Gemini API with fallback extraction.
    Designed for future Ollama integration.
    """
    
    def __init__(self, gemini_api_key_file: str = "gemini_api_key.txt"):
        self.gemini_key = self._load_api_key(gemini_api_key_file)
        self.gemini_model = None
        self.ollama_available = OLLAMA_AVAILABLE and self._check_ollama()
        
        # Initialize Gemini
        if self.gemini_key and GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=self.gemini_key)
                self.gemini_model = "gemini-2.0-flash"
                print("✅ Multi-Model Service: Gemini initialized")
            except Exception as e:
                print(f"⚠️ Gemini init failed: {e}")
        
        # Check Ollama
        if self.ollama_available:
            print("✅ Multi-Model Service: Ollama available")
        else:
            print("ℹ️ Multi-Model Service: Ollama not available (using Gemini + fallback)")
        
        # Response cache
        self._cache: Dict[str, Any] = {}
    
    def _load_api_key(self, filepath: str) -> Optional[str]:
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return f.read().strip()
        return None
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is running and accessible"""
        if not OLLAMA_AVAILABLE:
            return False
        try:
            # Try to list models
            ollama.list()
            return True
        except Exception:
            return False
    
    def _get_cache_key(self, task_type: TaskType, content: str) -> str:
        """Generate cache key for response caching"""
        import hashlib
        return f"{task_type.value}:{hashlib.md5(content.encode()).hexdigest()}"
    
    async def process(
        self, 
        task_type: TaskType, 
        content: str, 
        system_prompt: str = "",
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Process content using the best available model for the task.
        
        Args:
            task_type: Type of task for model routing
            content: The content to process
            system_prompt: Optional system prompt
            use_cache: Whether to use response caching
        
        Returns:
            Dict with 'response' and optional 'extracted_data'
        """
        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(task_type, content)
            if cache_key in self._cache:
                print(f"📦 Cache hit for {task_type.value}")
                return self._cache[cache_key]
        
        # Get model routes for this task
        routes = MODEL_ROUTES.get(task_type, MODEL_ROUTES[TaskType.CONVERSATION])
        
        # Try each model in order
        for config in routes:
            try:
                if config.provider == ModelProvider.OLLAMA and self.ollama_available:
                    result = await self._call_ollama(config, content, system_prompt)
                elif config.provider == ModelProvider.GEMINI and self.gemini_model:
                    result = await self._call_gemini(config, content, system_prompt)
                else:
                    continue
                
                # Cache successful result
                if use_cache and result:
                    self._cache[cache_key] = result
                
                return result
                
            except Exception as e:
                print(f"⚠️ Model {config.model_name} failed: {e}")
                continue
        
        # All models failed, use fallback
        print("🔄 Using fallback extraction")
        return self._fallback_extraction(task_type, content)
    
    async def _call_gemini(
        self, 
        config: ModelConfig, 
        content: str, 
        system_prompt: str
    ) -> Dict[str, Any]:
        """Call Gemini API"""
        try:
            model = genai.GenerativeModel(config.model_name)
            
            full_prompt = f"{system_prompt}\n\n{content}" if system_prompt else content
            
            generation_config = genai.GenerationConfig(
                temperature=config.temperature,
                max_output_tokens=config.max_tokens,
            )
            
            response = model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            text = response.text.strip()
            
            # Try to parse as JSON
            try:
                # Clean up JSON if wrapped in markdown
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
                
                return json.loads(text)
            except json.JSONDecodeError:
                return {"response": text}
                
        except Exception as e:
            raise Exception(f"Gemini error: {e}")
    
    async def _call_ollama(
        self, 
        config: ModelConfig, 
        content: str, 
        system_prompt: str
    ) -> Dict[str, Any]:
        """Call Ollama local model (for future use)"""
        if not self.ollama_available:
            raise Exception("Ollama not available")
        
        try:
            response = ollama.generate(
                model=config.model_name,
                prompt=f"{system_prompt}\n\n{content}" if system_prompt else content,
                options={
                    "temperature": config.temperature,
                    "num_predict": config.max_tokens,
                }
            )
            
            text = response.get("response", "").strip()
            
            # Try to parse as JSON
            try:
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
                
                return json.loads(text)
            except json.JSONDecodeError:
                return {"response": text}
                
        except Exception as e:
            raise Exception(f"Ollama error: {e}")
    
    def _fallback_extraction(
        self, 
        task_type: TaskType, 
        content: str
    ) -> Dict[str, Any]:
        """Rule-based fallback extraction when all models fail"""
        
        if task_type == TaskType.PROFILE_EXTRACTION:
            return self._extract_profile_fallback(content)
        elif task_type == TaskType.JOB_ANALYSIS:
            return self._extract_job_fallback(content)
        elif task_type == TaskType.SCHEDULE_PARSING:
            return self._extract_schedule_fallback(content)
        else:
            return {"response": content}
    
    def _extract_profile_fallback(self, text: str) -> Dict[str, Any]:
        """Extract user profile using regex patterns"""
        text_lower = text.lower()
        extracted = {}
        
        # Name patterns (English, Russian, Armenian)
        name_patterns = [
            r"i\s+am\s+(\w+)",
            r"i'm\s+(\w+)",
            r"my\s+name\s+is\s+(\w+)",
            r"меня\s+зовут\s+(\w+)",
            r"я\s+(\w+)",
            r"իdelays\s+անdelays+(\w+)",
            r"^(\w+)$",
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE | re.UNICODE)
            if match:
                name = match.group(1).capitalize()
                skip_words = ['a', 'the', 'i', 'am', 'is', 'yes', 'no', 'hi', 'hello']
                if name.lower() not in skip_words:
                    extracted['name'] = name
                    break
        
        # Skills extraction
        skill_keywords = [
            'python', 'javascript', 'java', 'react', 'angular', 'vue',
            'sql', 'docker', 'aws', 'azure', 'devops', 'ai', 'ml',
            'design', 'marketing', 'sales', 'teaching', 'medicine'
        ]
        found_skills = [s for s in skill_keywords if s in text_lower]
        if found_skills:
            extracted['skills'] = found_skills
        
        # Location extraction
        locations = [
            'yerevan', 'moscow', 'london', 'dubai', 'remote',
            'new york', 'san francisco', 'berlin', 'paris'
        ]
        for loc in locations:
            if loc in text_lower:
                extracted['location'] = loc.title()
                break
        
        # Remote preference
        if 'remote' in text_lower:
            extracted['remote_ok'] = True
        if 'office' in text_lower or 'onsite' in text_lower:
            extracted['onsite_ok'] = True
        
        return {"extracted_data": extracted, "response": ""}
    
    def _extract_job_fallback(self, text: str) -> Dict[str, Any]:
        """Extract job information using regex patterns"""
        text_lower = text.lower()
        
        job_data = {
            "title": "",
            "company": "",
            "location": "",
            "required_skills": [],
            "nice_to_have_skills": [],
            "schedule": {"days": [], "start": "", "end": ""},
            "salary": "",
            "employment_type": "",
            "red_flags": [],
            "culture_signals": []
        }
        
        # Title extraction
        title_patterns = [
            r"(senior|junior|lead|principal)?\s*(python|java|javascript|react|devops|data|software)\s*(developer|engineer|architect|analyst)",
            r"(english|math|physics)\s*teacher",
            r"(project|product|marketing)\s*manager",
        ]
        for pattern in title_patterns:
            match = re.search(pattern, text_lower)
            if match:
                job_data["title"] = match.group(0).title()
                break
        
        # Skills extraction
        skill_keywords = [
            'python', 'javascript', 'typescript', 'java', 'c++', 'go', 'rust',
            'react', 'angular', 'vue', 'node', 'django', 'fastapi', 'flask',
            'sql', 'postgresql', 'mongodb', 'redis', 'docker', 'kubernetes',
            'aws', 'azure', 'gcp', 'git', 'linux', 'agile', 'scrum'
        ]
        job_data["required_skills"] = [s for s in skill_keywords if s in text_lower]
        
        # Schedule extraction
        schedule_pattern = r"(\d{1,2})\s*(?::|am|pm)\s*(?:-|to)\s*(\d{1,2})\s*(?::|am|pm)?"
        match = re.search(schedule_pattern, text_lower)
        if match:
            job_data["schedule"]["start"] = f"{match.group(1)}:00"
            job_data["schedule"]["end"] = f"{match.group(2)}:00"
        
        # Employment type
        if "full-time" in text_lower or "full time" in text_lower:
            job_data["employment_type"] = "full-time"
        elif "part-time" in text_lower or "part time" in text_lower:
            job_data["employment_type"] = "part-time"
        
        # Red flags
        red_flag_keywords = [
            "unpaid", "no benefits", "long hours", "unlimited pto",
            "fast-paced", "wear many hats", "startup culture"
        ]
        job_data["red_flags"] = [rf for rf in red_flag_keywords if rf in text_lower]
        
        # Culture signals
        culture_keywords = [
            "work-life balance", "flexible hours", "remote-friendly",
            "professional development", "mentorship", "team events"
        ]
        job_data["culture_signals"] = [c for c in culture_keywords if c in text_lower]
        
        return {"job_data": job_data}
    
    def _extract_schedule_fallback(self, text: str) -> Dict[str, Any]:
        """Extract schedule information using regex"""
        text_lower = text.lower()
        
        schedule = {
            "days": [],
            "start": "",
            "end": ""
        }
        
        # Day extraction
        day_patterns = {
            "mon": ["monday", "mon", "пн", "понедельник"],
            "tue": ["tuesday", "tue", "вт", "вторник"],
            "wed": ["wednesday", "wed", "ср", "среда"],
            "thu": ["thursday", "thu", "чт", "четверг"],
            "fri": ["friday", "fri", "пт", "пятница"],
            "sat": ["saturday", "sat", "сб", "суббота"],
            "sun": ["sunday", "sun", "вс", "воскресенье"]
        }
        
        for day_key, patterns in day_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    schedule["days"].append(day_key.capitalize())
                    break
        
        # If "Mon-Fri" or similar range
        if "mon-fri" in text_lower or "monday-friday" in text_lower:
            schedule["days"] = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        
        # Time extraction
        time_pattern = r"(\d{1,2}):?(\d{2})?\s*(am|pm)?\s*[-–to]+\s*(\d{1,2}):?(\d{2})?\s*(am|pm)?"
        match = re.search(time_pattern, text_lower)
        if match:
            start_hour = int(match.group(1))
            end_hour = int(match.group(4))
            
            # Handle AM/PM
            if match.group(3) == "pm" and start_hour < 12:
                start_hour += 12
            if match.group(6) == "pm" and end_hour < 12:
                end_hour += 12
            
            schedule["start"] = f"{start_hour:02d}:00"
            schedule["end"] = f"{end_hour:02d}:00"
        
        return {"schedule": schedule}
    
    def clear_cache(self):
        """Clear the response cache"""
        self._cache.clear()
    
    def get_status(self) -> Dict[str, bool]:
        """Get status of available providers"""
        return {
            "gemini": self.gemini_model is not None,
            "ollama": self.ollama_available,
            "fallback": True  # Always available
        }


# Convenience functions for common operations
async def analyze_job_description(text: str) -> Dict[str, Any]:
    """Analyze a job description and extract structured data"""
    service = MultiModelService()
    
    system_prompt = """You are a job analysis expert. Extract structured information from this job posting.
    
    Return JSON with these fields:
    {
        "title": "Job title",
        "company": "Company name",
        "location": "Location",
        "required_skills": ["skill1", "skill2"],
        "nice_to_have_skills": ["skill1"],
        "schedule": {"days": ["Mon", "Tue"], "start": "09:00", "end": "17:00"},
        "salary": "Salary range or amount",
        "employment_type": "full-time/part-time/contract",
        "red_flags": ["Any concerning aspects"],
        "culture_signals": ["Positive culture indicators"]
    }
    """
    
    return await service.process(TaskType.JOB_ANALYSIS, text, system_prompt)


async def extract_user_profile(conversation_history: List[Dict], current_profile: Dict) -> Dict[str, Any]:
    """Extract user profile information from conversation"""
    service = MultiModelService()
    
    # Build conversation context
    context = f"Current profile: {json.dumps(current_profile)}\n\nConversation:\n"
    for msg in conversation_history[-5:]:  # Last 5 messages
        context += f"{msg['role']}: {msg['content']}\n"
    
    system_prompt = """You are a friendly job assistant gathering user profile information.
    
    Extract any NEW information from the conversation. Return JSON:
    {
        "response": "Your friendly response in the user's language",
        "extracted_data": {
            "name": "if mentioned",
            "location": "if mentioned",
            "skills": ["if mentioned"],
            "career_goals": "if mentioned",
            "remote_ok": true/false,
            "onsite_ok": true/false,
            "min_rate": number if mentioned,
            "max_hours": number if mentioned,
            "ready_to_search": true if all essential info collected
        }
    }
    
    Only include fields that are newly extracted. Be warm and friendly!
    """
    
    return await service.process(TaskType.PROFILE_EXTRACTION, context, system_prompt)
