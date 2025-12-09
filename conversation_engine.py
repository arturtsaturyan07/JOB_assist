
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class ConversationState(str, Enum):
    GREETING = "greeting"
    NAME_EXTRACT = "name_extract"
    SKILLS_EXTRACT = "skills_extract"  # Job title/skills
    LOCATION_EXTRACT = "location_extract"
    REMOTE_PREF_EXTRACT = "remote_pref_extract" # Remote/Onsite/Both
    RATE_EXTRACT = "rate_extract"       # Hourly rate
    HOURS_EXTRACT = "hours_extract"     # Availability
    OFFERS_EXTRACT = "offers_extract"   # How many offers to show?
    READY_TO_SEARCH = "ready_to_search"  # Ready to search
    SEARCH_RESULTS = "search_results"   # Showing results
    REFINING = "refining"           # Refining search


@dataclass
class ExtractionResult:
    """Result of extraction"""
    extracted: Dict[str, Any]
    state_progressed: bool
    next_state: ConversationState
    confidence: float  # 0.0 to 1.0
    feedback_message: Optional[str] = None  # Custom feedback to user if not progressed


class ConversationEngine:
    """
    Intelligent conversation engine without API dependencies.
    
    Handles:
    - Multi-language user input (English, Russian, Armenian)
    - Progressive user profile extraction
    - Smart state machine transitions
    - Graceful fallbacks
    """
    
    def __init__(self, llm_service=None):
        self.current_state = ConversationState.GREETING
        self.user_profile = {}
        self.extraction_history = []
        self.llm_service = llm_service
        
    def get_system_prompt(self, language: str = "english") -> str:
        """Get system prompt for conversation"""
        prompts = {
            "english": """You are TwinWork AI — an advanced, multi-model AI job assistant.

CORE OBJECTIVE:
Find 1 or 2 compatible jobs simultaneously that maximize income and fit the user's schedule.

SYSTEM INSTRUCTIONS (STRICT):
1. Multi-Model Architecture
   - Conversation Engine: Small, fast model for chat.
   - Job Intelligence: Extract structure from ANY job posting (skills, schedule, salary).
   - Semantic Matching: Use embeddings for skill matching.
   - Schedule Engine: Detect collisions and generate time grids.

2. API Usage Rules
   - NO paid APIs unless absolutely necessary.
   - Fallback to local data/scraping if APIs fail.

3. Features
   - Create complete user profile (skills, schedule, etc.)
   - Extract structured job data (JSON format).
   - Matching Engine: Optimization for 2 jobs (Income/Sanity).
   - Multilingual: English, Russian, Armenian.

4. Output Style
   - Structured, polite, transparent.
   - Explain WHY you recommend jobs.
""",
            
            "russian": """Ты TwinWork AI, полезный помощник по поиску работы.

Твоя работа:
1. Помочь пользователям найти 1-2 совместимые работы
2. Понять их навыки, местоположение и расписание
3. Обнаружить конфликты работы и максимизировать доход
4. Быть дружелюбным, профессиональным и прозрачным

Всегда объясняй, почему ты рекомендуешь эту работу.""",
            
            "armenian": """Դու TwinWork AI, օգտակար աշխատանքի որոնման օգնական:

Քո աշխատանք:
1. Օգտատերերին օգնել գտնել 1-2 համատեղ աշխատանք
2. Հասկանալ նրանց հմտությունները, գտնվելու վայրը և ժամանակացուցակը
3. Հայտնաբերել աշխատանքային հակամարտությունները և առավելագույնացնել եկամուտը
4. Լինել բարեկամական, պրոֆեսիոնալ և թափանցիկ

Միշտ բացատրի, թե ինչու ես այս աշխատանքն առաջարկում:"""
        }
        return prompts.get(language, prompts["english"])
    
    def detect_language(self, text: str) -> str:
        """Detect if text is English, Russian, or Armenian"""
        # Armenian Unicode range: U+0530-U+0588
        armenian_chars = sum(1 for c in text if '\u0530' <= c <= '\u0588')
        
        # Russian Unicode range: U+0400-U+04FF (Cyrillic)
        russian_chars = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
        
        total_chars = len(text)
        
        if armenian_chars > total_chars * 0.3:
            return "armenian"
        elif russian_chars > total_chars * 0.3:
            return "russian"
        else:
            return "english"
    
    def get_next_question(
        self,
        state: ConversationState,
        user_name: str = "",
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Get the next question to ask based on conversation state"""
        questions = {
            ConversationState.GREETING: {
                "english": "Hi! I'm TwinWork AI. What's your name?",
                "russian": "Привет! Я TwinWork AI. Как тебя зовут?",
                "armenian": "Բարեւ! Ես TwinWork AI-ն եմ: Ինչ է քո անունը?"
            },
            ConversationState.SKILLS_EXTRACT: {
                "english": f"Nice to meet you, {user_name}! What kind of work are you looking for? (for example: Python developer, driver, teacher)",
                "russian": f"Приятно, {user_name}! Какую работу ты ищешь? (например: разработчик Python, водитель, учитель)",
                "armenian": f"Հաճելի, {user_name}! Ի՞նչ աշխատանք ես փնտրում: (օրինակ: Python մշակողներ, վարորդ, ուսուչ)"
            },
            ConversationState.LOCATION_EXTRACT: {
                "english": "Got it! Where are you located? (or just say 'remote' if you prefer working from home)",
                "russian": "Понимаю! Где ты находишься? (или напиши 'удаленно' если предпочитаешь работать дома)",
                "armenian": "Հասկացա! Որտե՞ղ ես գտնվում: (կամ գրիր 'հեռավար' եթե նախընտրում ես տնից աշխատել)"
            },
            ConversationState.REMOTE_PREF_EXTRACT: {
                "english": "Do you prefer remote work, office work, or are you open to both?",
                "russian": "Предпочитаешь удаленную работу, офис или тебя устроит и то, и другое?",
                "armenian": "Նախընտրում ես հեռավար, գրասենյակային, թե երկուսն էլ?"
            },
            ConversationState.RATE_EXTRACT: {
                "english": "What's your minimum hourly rate? (Feel free to skip if you're flexible)",
                "russian": "Какой минимум по часам тебе нужен? (Можешь пропустить, если гибко)",
                "armenian": "Ո՞րն է քո նվազագույն ժամային դրույքը: (Կարող ես բաց թողել, եթե ճկուն ես)"
            },
            ConversationState.HOURS_EXTRACT: {
                "english": "How many hours per week can you work? (Or skip if no preference)",
                "russian": "Сколько часов в неделю можешь работать? (Или пропусти, если нет ограничений)",
                "armenian": "Քանի՞ ժամ շաբաթական կարող ես աշխատել: (Կամ բաց թողել, եթե սահմանափակում չկա)"
            },
            ConversationState.OFFERS_EXTRACT: {
                "english": "How many job listings would you like to see? (5, 10, 20?)",
                "russian": "Сколько вакансий хочешь увидеть? (5, 10, 20?)",
                "armenian": "Քանի՞ աշխատանքային տեղավորում կուզեր տեսնել: (5, 10, 20?)"
            },
            ConversationState.READY_TO_SEARCH: {
                "english": f"Perfect, {user_name}! I've got everything I need. Let me search for jobs that match your profile...",
                "russian": f"Отлично, {user_name}! У меня есть все, что нужно. Ищу подходящие вакансии...",
                "armenian": f"Կատարյալ, {user_name}! Ունեմ ամեն ինչ: Փնտրում եմ համապատասխան աշխատանք..."
            }
        }
        
        lang = self.detect_language(user_name)
        if lang == "armenian":
            lang = "armenian"
        elif lang == "russian":
            lang = "russian"
        else:
            lang = "english"
        
        question = questions.get(state, {}).get(lang, "What would you like to tell me next?")

        profile_context = user_profile or self.user_profile

        if state == ConversationState.REMOTE_PREF_EXTRACT:
            custom = self._build_remote_pref_question(profile_context, lang)
            if custom:
                return custom

        return question

    def _build_remote_pref_question(self, user_profile: Dict[str, Any], language: str) -> Optional[str]:
        roles = self._extract_roles(user_profile)
        if not roles:
            return None

        onsite_roles = [role for role in roles if role in self._onsite_only_roles()]
        if not onsite_roles:
            return None

        role_fragment = self._format_role_list(onsite_roles)
        location = user_profile.get("location", "your city")

        templates = {
            "english": (
                f"{role_fragment} usually require showing up in person around {location}. "
                "Should I stick to local/on-site roles, or do you also want me to keep an eye out "
                "for remote opportunities (like tele-support)?"
            ),
            "russian": (
                f"Для таких ролей как {role_fragment} обычно нужно работать на месте в регионе {location}. "
                "Оставляем только локальные вакансии или ищем ещё и удалённые варианты (например, онлайн-консультации)?"
            ),
            "armenian": (
                f"{role_fragment} գործերի համար սովորաբար պետք է գտնվել տեղում՝ {location}-ում։ "
                "Թողնե՞մ միայն տեղական տարբերակները, թե՞ փնտրեմ նաեւ հեռավար հնարավորություններ։"
            ),
        }

        return templates.get(language)

    @staticmethod
    def _onsite_only_roles() -> set:
        return {
            "dentist",
            "doctor",
            "surgeon",
            "nurse",
            "driver",
            "taxi driver",
            "mechanic",
            "bartender",
            "waiter",
            "construction",
            "warehouse",
            "cook",
            "chef",
        }

    @staticmethod
    def _format_role_list(roles: List[str]) -> str:
        cleaned = [role.title() for role in roles]
        if not cleaned:
            return "these roles"
        if len(cleaned) == 1:
            return cleaned[0]
        return ", ".join(cleaned[:-1]) + f" and {cleaned[-1]}"

    @staticmethod
    def _extract_roles(user_profile: Dict[str, Any]) -> List[str]:
        raw = user_profile.get("career_goals") or ""
        roles = [role.strip().lower() for role in raw.split(",") if role.strip()]
        return roles
    
    def extract_name(self, text: str, user_profile: Dict[str, Any]) -> ExtractionResult:
        """Extract name from user input - multilingual support"""
        text_orig = text.strip()
        text_lower = text.lower()
        extracted = {}
        
        # Name extraction patterns - supports English, Russian, Armenian
        name_patterns = [
            # English
            (r"i\s+am\s+(\w+)", "english"),
            (r"i'm\s+(\w+)", "english"),
            (r"my\s+name\s+is\s+(\w+)", "english"),
            (r"call\s+me\s+(\w+)", "english"),
            # Russian
            (r"я\s+(\w+)", "russian"),
            (r"меня\s+зовут\s+(\w+)", "russian"),
            (r"мое\s+имя\s+(\w+)", "russian"),
            # Armenian
            (r"ես\s+եմ\s+(\w+)", "armenian"),
            (r"ես\s+(\w+)", "armenian"),
            (r"իմ\s+անունը\s+(\w+)", "armenian"),
            (r"ինձ\s+անվանեք\s+(\w+)", "armenian"),
        ]
        
        stop_words = ['a', 'the', 'and', 'or', 'but', 'as', 'in', 'yes', 'no', 'remote', 
                      'both', 'skip', 'any', 'ok', 'okay', 'sure', 'thanks', 'cool', 'good', 
                      'fine', 'how', 'are', 'you', 'doing', 'what', 'is', 'your', 'name', 
                      'who', 'am', 'i', 'chatbot', 'bot', 'ai', 'assistant', 'hi', 'hello']
        
        greeting_words = [
            'hi', 'hello', 'hey', 'greetings', 'yo', 'sup', 
            'privet', 'привет', 'здрасьте', 'здравствуйте', 'хи', 'хей',
            'barev', 'բարև', 'ողջույն', 'վողջույն',
            'whats up', 'what\'s up', 'wassup', 'wazzup', 'howdy'
        ]

        # 1. Try explicit patterns first
        for pattern, lang_type in name_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE | re.UNICODE)
            if match:
                name = match.group(1).capitalize()
                if name.lower() not in stop_words and len(name) >= 2:
                    extracted['name'] = name
                    return ExtractionResult(
                        extracted=extracted,
                        state_progressed=True,
                        next_state=ConversationState.SKILLS_EXTRACT,
                        confidence=0.95
                    )

        # 2. Handle pure greetings specifically (PREVENTS "хи" -> name "Хи")
        # Check against greeting list + stop words to be safe
        cleaned_input = text_lower.strip(".,!?")
        if any(w == cleaned_input for w in greeting_words):
             return ExtractionResult(
                extracted={},
                state_progressed=False,
                next_state=ConversationState.GREETING, # Stay in greeting
                confidence=0.0,
                feedback_message="Hi there! 👋 I'm excited to help you find a job. Ideally, what should I call you?"
            )
        
        # 3. Check for "Bare word" (just the name)
        words = text_orig.split()
        # Filter out stop words AND greeting words to avoid "Hi" becoming a name
        clean_words = [w for w in words if w.lower().strip(",.!?") not in stop_words + greeting_words]
        
        if 1 <= len(clean_words) <= 2:
            potential_name = " ".join(clean_words).strip(",.!?")
            # Ensure it looks like a name (not all numbers/symbols) and is NOT a greeting
            if potential_name.replace(" ", "").isalpha() and len(potential_name) >= 2:
                 extracted['name'] = potential_name.title()
                 return ExtractionResult(
                    extracted=extracted,
                    state_progressed=True,
                    next_state=ConversationState.SKILLS_EXTRACT,
                    confidence=0.8
                )
        
        # No name extracted
        return ExtractionResult(
            extracted={},
            state_progressed=False,
            next_state=ConversationState.NAME_EXTRACT,
            confidence=0.0
        )
    
    def extract_skills(self, text: str, user_profile: Dict[str, Any]) -> ExtractionResult:
        """Extract job preferences/skills from user input"""
        text_orig = text.strip()
        text_lower = text.lower()
        extracted = {}
        
        # Check if user accidentally said a greeting here
        greeting_words = [
            'hi', 'hello', 'hey', 'greetings', 'yo', 'sup', 
            'privet', 'привет', 'здрасьте', 'здравствуйте', 'хи', 'хей',
            'barev', 'բարև', 'ողջույն', 'վողջույն'
        ]
        if any(w == text_lower.strip(".,!?") for w in greeting_words):
             return ExtractionResult(
                extracted={},
                state_progressed=False, # Do not progress
                next_state=ConversationState.SKILLS_EXTRACT,
                confidence=0.0,
                feedback_message="Hello! 👋 Could you tell me what kind of job you're looking for?"
            )

        # Greatly expanded roles list
        roles = [
            # Tech
            'developer', 'engineer', 'programmer', 'coder', 'architect', 'admin', 'administrator',
            'analyst', 'scientist', 'researcher', 'consultant', 'tester', 'qa', 'devops', 'sre',
            'designer', 'product manager', 'project manager', 'scrum master', 'cto', 'ceo', 'cio',
            # Medical
            'doctor', 'surgeon', 'nurse', 'dentist', 'pharmacist', 'therapist', 'psychologist',
            'paramedic', 'physician', 'veterinarian', 'optician', 'cardiologist', 'neurologist',
            # Education
            'teacher', 'tutor', 'professor', 'lecturer', 'instructor', 'coach', 'trainer',
            'principal', 'counselor', 'librarian',
            # Service / Trades
            'driver', 'truck driver', 'taxi driver', 'courier', 'delivery', 'chef', 'cook', 
            'waiter', 'waitress', 'barista', 'bartender', 'cleaner', 'housekeeper', 'janitor',
            'plumber', 'electrician', 'mechanic', 'carpenter', 'painter', 'welder', 'builder',
            'construction', 'laborer', 'technician', 'security', 'guard', 'hairdresser', 'barber',
            # Business / Office
            'accountant', 'auditor', 'bookkeeper', 'lawyer', 'attorney', 'paralegal',
            'manager', 'director', 'supervisor', 'executive', 'assistant', 'secretary',
            'receptionist', 'clerk', 'hr', 'recruiter', 'marketing', 'sales', 'salesperson',
            'agent', 'broker', 'representative', 'specialist', 'coordinator', 'officer',
            # Creative
            'writer', 'editor', 'journalist', 'author', 'translator', 'interpreter',
            'artist', 'illustrator', 'photographer', 'videographer', 'musician', 'actor',
            'producer', 'director',
            # Other
            'pilot', 'captain', 'flight attendant', 'farmer', 'gardener', 'florist'
        ]
        
        domains = [
            'python', 'javascript', 'java', 'c\\+\\+', 'c#', 'php', 'ruby', 'go', 'rust', 'swift',
            'kotlin', 'scala', 'r', 'matlab', 'sql', 'nosql', 'html', 'css', 'react', 'angular',
            'vue', 'node', 'django', 'flask', 'spring', 'net', 'aws', 'azure', 'gcp', 'cloud',
            'docker', 'kubernetes', 'linux', 'windows', 'macos', 'android', 'ios',
            'english', 'spanish', 'french', 'german', 'russian', 'armenian', 'chinese', 'japanese',
            'data', 'ai', 'ml', 'machine learning', 'deep learning', 'nlp', 'cv', 'computer vision',
            'web', 'mobile', 'frontend', 'backend', 'fullstack', 'game', 'embedded', 'security',
            'cyber', 'network', 'system', 'database', 'blockchain', 'crypto', 'finance', 'banking',
            'medical', 'legal', 'education', 'automotive', 'retail', 'real estate'
        ]
        
        # First, normalize text: "truck driver" → test for individual role "driver"
        # Split by common separators (and, or, &, ,) to get individual job phrases
        job_phrases = re.split(r'\s+(?:and|or|&|,)\s+', text_lower)
        
        skills = []
        career_goals = []
        
        for phrase in job_phrases:
            phrase = phrase.strip()
            if not phrase:
                continue
            
            # Try to match "[domain] [role]" pattern first
            for domain in domains:
                for role in roles:
                    pattern = rf'{domain}\s+{role}'
                    if re.search(pattern, phrase, re.IGNORECASE):
                        domain_name = domain.replace('\\', '').capitalize()
                        role_name = role.capitalize()
                        if domain_name not in skills:
                            skills.append(domain_name)
                        goal = f"{domain_name} {role_name}"
                        if goal not in career_goals:
                            career_goals.append(goal)
            
            # Match standalone roles (this includes compound roles like "truck driver")
            for role in roles:
                # Match role as standalone word or part of compound (e.g., "truck driver")
                if re.search(rf'\b{role}\b', phrase, re.IGNORECASE):
                    role_name = role.capitalize()
                    if role_name not in career_goals:
                        career_goals.append(role_name)
        
        # Fallback with checks
        if snippet := text_orig.strip():
             words = snippet.split()
             # Only accept as fallback if it's NOT a greeting and short enough
             clean_snippet = snippet.strip(".,!?")
             bad_words = ['skip', 'no', 'none', 'later', 'pass']
             
             if (len(words) < 5 
                 and not career_goals 
                 and not skills 
                 and clean_snippet.lower() not in bad_words 
                 and clean_snippet.lower() not in greeting_words): # Explicit check
                 
                 career_goals.append(clean_snippet.title())

        if skills or career_goals:
            if skills:
                extracted['skills'] = skills
            if career_goals:
                extracted['career_goals'] = ', '.join(career_goals)
            
            return ExtractionResult(
                extracted=extracted,
                state_progressed=True,
                next_state=ConversationState.LOCATION_EXTRACT,
                confidence=0.85
            )
        
        return ExtractionResult(
            extracted={},
            state_progressed=False,
            next_state=ConversationState.SKILLS_EXTRACT,
            confidence=0.0
        )
    
    def extract_location(self, text: str, user_profile: Dict[str, Any]) -> ExtractionResult:
        """Extract location from user input"""
        text_lower = text.lower()
        extracted = {}
        
        locations = [
            'yerevan', 'moscow', 'london', 'dubai', 'new york', 'chicago', 'san francisco',
            'los angeles', 'toronto', 'paris', 'berlin', 'sydney', 'tokyo', 'singapore',
            'remote', 'armenia', 'usa', 'uk', 'canada', 'australia'
        ]
        
        for loc in locations:
            if loc in text_lower:
                extracted['location'] = loc.capitalize()
                break
        
        if extracted:
            return ExtractionResult(
                extracted=extracted,
                state_progressed=True,
                next_state=ConversationState.REMOTE_PREF_EXTRACT,
                confidence=0.95
            )
        
        return ExtractionResult(
            extracted={},
            state_progressed=False,
            next_state=ConversationState.LOCATION_EXTRACT,
            confidence=0.0
        )
    
    def extract_remote_preference(self, text: str, user_profile: Dict[str, Any]) -> ExtractionResult:
        """Extract remote/onsite preference"""
        text_lower = text.lower()
        extracted = {}
        
        if 'remote' in text_lower:
            extracted['remote_ok'] = True
        if 'office' in text_lower or 'onsite' in text_lower or 'in-office' in text_lower:
            extracted['onsite_ok'] = True
        if 'both' in text_lower:
            extracted['remote_ok'] = True
            extracted['onsite_ok'] = True
        
        if extracted:
            return ExtractionResult(
                extracted=extracted,
                state_progressed=True,
                next_state=ConversationState.RATE_EXTRACT,
                confidence=0.95
            )
        
        return ExtractionResult(
            extracted={},
            state_progressed=False,
            next_state=ConversationState.REMOTE_PREF_EXTRACT,
            confidence=0.0
        )
    
    def extract_rate(self, text: str, user_profile: Dict[str, Any]) -> ExtractionResult:
        """Extract hourly rate"""
        text_lower = text.lower()
        extracted = {}
        
        rate_patterns = [
            r'\$(\d+(?:\.\d{2})?)',
            r'(\d+(?:\.\d{2})?)\s*(?:per|\/)\s*(?:hour|hr|h)',
        ]
        
        for pattern in rate_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    rate = float(match.group(1))
                    extracted['min_rate'] = rate
                    break
                except:
                    pass
        
        # Handle "skip", "any"
        if not extracted:
            skip_keywords = ['skip', 'any', 'flexible', "doesn't matter", 'whatever']
            if any(kw in text_lower for kw in skip_keywords):
                extracted['min_rate'] = 0  # 0 = flexible
        
        if extracted:
            return ExtractionResult(
                extracted=extracted,
                state_progressed=True,
                next_state=ConversationState.HOURS_EXTRACT,
                confidence=0.90
            )
        
        return ExtractionResult(
            extracted={},
            state_progressed=False,
            next_state=ConversationState.RATE_EXTRACT,
            confidence=0.0
        )
    
    def extract_hours(self, text: str, user_profile: Dict[str, Any]) -> ExtractionResult:
        """Extract hours per week"""
        text_lower = text.lower()
        extracted = {}
        
        hours_match = re.search(r'(\d+)\s*(?:hours?|hrs?)\s*(?:per\s*week|\/week)?', text_lower)
        if hours_match:
            try:
                hours = int(hours_match.group(1))
                if 1 <= hours <= 168:  # Reasonable range
                    extracted['max_hours'] = hours
            except:
                pass
        
        # Handle "skip", "no limit"
        if not extracted:
            skip_keywords = ['skip', 'no limit', 'any', 'flexible', 'whatever']
            if any(kw in text_lower for kw in skip_keywords):
                extracted['max_hours'] = 999  # 999 = unlimited
        
        if extracted:
            return ExtractionResult(
                extracted=extracted,
                state_progressed=True,
                next_state=ConversationState.OFFERS_EXTRACT,
                confidence=0.90
            )
        
        return ExtractionResult(
            extracted={},
            state_progressed=False,
            next_state=ConversationState.HOURS_EXTRACT,
            confidence=0.0
        )
    
    def extract_num_offers(self, text: str, user_profile: Dict[str, Any]) -> ExtractionResult:
        """Extract number of offers wanted"""
        text_lower = text.lower()
        extracted = {}
        
        offers_patterns = [
            r'(?:show\s+)?(\d+)\s*(?:offers?|jobs?|positions?|opportunities?)',
            r'^(\d+)$'  # Just a number
        ]
        
        for pattern in offers_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    num = int(match.group(1))
                    if 1 <= num <= 100:
                        extracted['num_offers'] = num
                        break
                except:
                    pass
        
        if extracted:
            return ExtractionResult(
                extracted=extracted,
                state_progressed=True,
                next_state=ConversationState.READY_TO_SEARCH,
                confidence=0.95
            )
        
        return ExtractionResult(
            extracted={},
            state_progressed=False,
            next_state=ConversationState.OFFERS_EXTRACT,
            confidence=0.0
        )
    
    async def process_user_input(self, text: str, user_profile: Dict[str, Any]) -> Tuple[ExtractionResult, str]:
        """Process user input with custom feedback support (Async)"""
        
        result = ExtractionResult({}, False, self.current_state, 0.0)
        
        # Detect confusion / questions first (Global Handler)
        confusion_words = [
            'what?', 'what do you mean', 'don\'t understand', 'explain', 
            'help', 'why', 'huh', 'what is this', 'do you understand', 'can you understand',
            'do you get it', 'are you there', 'hello?', 'are you listening'
        ]
        text_lower = text.lower()
        if any(w in text_lower for w in confusion_words) and len(text_lower) < 50:
             # User is confused. Give a helpful update based on state.
             response = ""
             if self.current_state == ConversationState.SKILLS_EXTRACT:
                 response = "I need to know what job you want so I can search for it. For example: 'Python Developer' or 'Taxi Driver'."
             elif self.current_state == ConversationState.LOCATION_EXTRACT:
                 response = "I need to know which city or country to look in. You can also say 'Remote'."
             elif self.current_state in [ConversationState.GREETING, ConversationState.NAME_EXTRACT]:
                 response = "Yes, I understand you perfectly! I just need your name to get started. What should I call you?"
             else:
                 response = "I'm trying to build your profile to find the best jobs. Could you answer the last question?"
             
             return ExtractionResult({}, False, self.current_state, 0.0, feedback_message=response), response

        if self.current_state in [ConversationState.GREETING, ConversationState.NAME_EXTRACT]:
             result = self.extract_name(text, user_profile)
        
        elif self.current_state == ConversationState.SKILLS_EXTRACT:
             result = self.extract_skills(text, user_profile)
        
        elif self.current_state == ConversationState.LOCATION_EXTRACT:
             result = self.extract_location(text, user_profile)
             
        elif self.current_state == ConversationState.REMOTE_PREF_EXTRACT:
             result = self.extract_remote_preference(text, user_profile)
             
        elif self.current_state == ConversationState.RATE_EXTRACT:
             result = self.extract_rate(text, user_profile)
             
        elif self.current_state == ConversationState.HOURS_EXTRACT:
             result = self.extract_hours(text, user_profile)
             
        elif self.current_state == ConversationState.OFFERS_EXTRACT:
             result = self.extract_num_offers(text, user_profile)

        # Handle Result
        if result.state_progressed:
            self.current_state = result.next_state
            user_profile.update(result.extracted)
            self.user_profile = user_profile
            response = self.get_next_question(
                self.current_state,
                result.extracted.get('name', user_profile.get('name', '')),
                user_profile=user_profile,
            )
        else:
            if result.feedback_message:
                response = result.feedback_message
            else:
                # LLM Fallback for "Normal Chat"
                if self.llm_service:
                    # Context for the LLM
                    context = f"Current State: {self.current_state}. User Name: {user_profile.get('name')}."
                    
                    # Only fallback if it's NOT a simple short answer that just failed regex
                    # (Prevent LLM triggering on simple typos of skill names, though LLM might handle that better too)
                    # For now, if regex failed, we try AI.
                    response = await self.llm_service.chat(text, system_context=context)
                else:
                    # Better generic fallback
                    if self.current_state == ConversationState.LOCATION_EXTRACT:
                        response = "I'm not sure which city that is. Could you check the spelling or mention a nearby major city?"
                    else:
                        response = "I didn't quite catch that. Could you please clarify?"
        
        return result, response
