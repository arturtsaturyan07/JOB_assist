import re
import random
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
            "english": """You are TwinWork AI — a friendly, natural job assistant.

CORE OBJECTIVE:
Help users find jobs that fit their skills, schedule, and preferences through natural conversation.

CONVERSATION STYLE:
- Sound like a real friend, not a bot
- Ask follow-up questions naturally based on their answers
- Weave information gathering into the conversation flow
- Show genuine interest in their situation
- Use their name when you know it
- Acknowledge and build on what they've told you
- Be encouraging but realistic

INFORMATION TO GATHER (naturally, not as a checklist):
1. Name - Introduce yourself and ask theirs
2. Current situation - What are they doing now? Why looking for work?
3. Job interests - What type of work appeals to them? Why?
4. Skills & experience - What can they do? How long have they been doing it?
5. Location & work style - Where are they? Remote, office, or flexible?
6. Availability - How much time can they dedicate?
7. Expectations - What salary/rate range? What's important to them?

NATURAL CONVERSATION RULES:
- Don't ask all questions at once
- Let answers flow into the next question
- Skip questions if they've already answered them
- Mention market insights when relevant (salary trends, in-demand skills)
- Build rapport before diving into details
- Confirm understanding by paraphrasing occasionally
- Make it feel like you're helping them think through their options

TONE:
- Warm and encouraging
- Professional but not stiff
- Curious about their goals
- Honest about market realities
- Keep responses 1-3 sentences (conversational length)
""",
            
            "russian": """Ты TwinWork AI — дружелюбный помощник по поиску работы.

ОСНОВНАЯ ЦЕЛЬ:
Помочь пользователям найти работу через естественный разговор.

СТИЛЬ РАЗГОВОРА:
- Говори как настоящий друг, не как бот
- Задавай вопросы естественно, основываясь на их ответах
- Вплетай сбор информации в разговор
- Проявляй искренний интерес
- Используй их имя
- Ссылайся на то, что они уже сказали
- Будь ободряющим

ИНФОРМАЦИЯ ДЛЯ СБОРА (естественно):
1. Имя
2. Текущая ситуация - чем они занимаются?
3. Интересующая работа - что им нравится?
4. Навыки и опыт - что они умеют?
5. Местоположение и стиль работы - где? удалённо или офис?
6. Доступность - сколько времени могут уделить?
7. Ожидания - зарплата, что важно?

ПРАВИЛА:
- Не задавай все вопросы сразу
- Пусть разговор течёт естественно
- Пропускай вопросы, если уже знаешь ответ
- Упоминай рыночные тренды когда уместно
- Подтверждай понимание, перефразируя
- Держи ответы короткими (1-3 предложения)
""",
            
            "armenian": """Դու TwinWork AI, բարեկամական աշխատանքի որոնման օգնական:

ՀԻՄՆԱԿԱՆ ՆՊԱՏԱԿ:
Օգտատերերին օգնել գտնել աշխատանք բնական խոսակցության միջոցով:

ԽՈՍԱԿՑՈՒԹՅԱՆ ՈՐ:
- Խոսիր ինչպես իսկական ընկեր, ոչ թե բոտ
- Հարցրու բնական կերպով
- Ցույց տուր իսկական հետաքրքրություն
- Օգտագործիր նրանց անունը
- Ծանուցիր նրանց պատասխանների վրա
- Լինել խրախուսող

ՏԵՂԵԿԱՏՎՈՒԹՅՈՒՆ ՀԱՎԱՔԵԼՈՒ ՀԱՄԱՐ:
1. Անունը
2. Ներկա իրավիճակը
3. Աշխատանքային հետաքրքրություններ
4. Հմտություններ և փորձ
5. Տեղանիշ և աշխատանքային ոճ
6. Հասանելիություն
7. Ակնկալիքներ
"""
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
    
    async def get_next_question_from_api(
        self,
        state: ConversationState,
        user_name: str = "",
        user_profile: Optional[Dict[str, Any]] = None,
        language: str = "english"
    ) -> str:
        """Generate natural question using LLM API instead of hardcoded templates"""
        if not self.llm_service:
            return self.get_next_question(state, user_name, user_profile)
        
        profile_context = user_profile or self.user_profile
        gathered = ", ".join([f"{k}: {v}" for k, v in profile_context.items() if v])
        
        state_info = {
            ConversationState.GREETING: "Ask for their name in a friendly way. Be warm and welcoming.",
            ConversationState.SKILLS_EXTRACT: "Ask what type of work they're interested in. Be specific and encouraging.",
            ConversationState.LOCATION_EXTRACT: "Ask where they're located or if they prefer remote work.",
            ConversationState.REMOTE_PREF_EXTRACT: "Ask if they prefer remote, office, or hybrid work arrangements.",
            ConversationState.RATE_EXTRACT: "Ask about their minimum hourly rate. Make it optional and casual.",
            ConversationState.HOURS_EXTRACT: "Ask how many hours per week they can work. Be flexible.",
            ConversationState.OFFERS_EXTRACT: "Ask how many job offers they'd like to see.",
            ConversationState.READY_TO_SEARCH: f"Confirm that you have all info and will search. Personalize with {user_name}'s name.",
        }
        
        prompt = f"""Generate a natural, conversational question for a job search chatbot.

Current state: {state}
User name: {user_name}
Already gathered: {gathered if gathered else 'nothing yet'}

Task: {state_info.get(state, 'Ask the next question')}

Rules:
- One question only, keep it short (max 1 sentence)
- Be friendly and natural (not robotic)
- If you know their name, use it
- Acknowledge previous answers when relevant
- Make it optional where appropriate

Just output the question, no preamble."""
        
        try:
            question = await self.llm_service.chat(prompt, system_context=self.get_system_prompt(language))
            return question.strip()
        except Exception as e:
            print(f"API error generating question: {e}")
            # Fallback to hardcoded
            return self.get_next_question(state, user_name, user_profile)

    def get_next_question(
        self,
        state: ConversationState,
        user_name: str = "",
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Get the next question based on conversation state (Fallback if no API)"""
        questions = {
            ConversationState.GREETING: {
                "english": "👋 Hi! I'm TwinWork AI. What's your name?",
                "russian": "👋 Привет! Я TwinWork AI. Как тебя зовут?",
                "armenian": "👋 Բարեւ! Ես TwinWork AI-ն եմ: Ինչ է քո անունը?"
            },
            ConversationState.SKILLS_EXTRACT: {
                "english": f"Nice to meet you, {user_name}! What kind of work are you looking for?",
                "russian": f"Приятно, {user_name}! Какую работу ты ищешь?",
                "armenian": f"Հաճելի, {user_name}! Ի՞նչ աշխատանք ես փնտրում:"
            },
            ConversationState.LOCATION_EXTRACT: {
                "english": "Where are you located or do you prefer remote work?",
                "russian": "Где ты находишься или ты предпочитаешь удаленную работу?",
                "armenian": "Որտե՞ղ ես գտնվում կամ հեռավար աշխատանք?"
            },
            ConversationState.REMOTE_PREF_EXTRACT: {
                "english": "Do you prefer remote, office, or both?",
                "russian": "Ты предпочитаешь удаленную работу, офис или оба?",
                "armenian": "Նախընտրում ես հեռավար, գրասենյակային, թե երկուսն էլ?"
            },
            ConversationState.RATE_EXTRACT: {
                "english": "What's your minimum hourly rate? (optional)",
                "russian": "Какой минимум по часам тебе нужен? (опционально)",
                "armenian": "Ո՞րն է քո նվազագույն ժամային դրույքը: (ընտրովի)"
            },
            ConversationState.HOURS_EXTRACT: {
                "english": "How many hours per week can you work?",
                "russian": "Сколько часов в неделю можешь работать?",
                "armenian": "Քանի՞ ժամ շաբաթական կարող ես աշխատել:"
            },
            ConversationState.OFFERS_EXTRACT: {
                "english": "How many job listings would you like to see?",
                "russian": "Сколько вакансий хочешь увидеть?",
                "armenian": "Քանի՞ աշխատանքային տեղավորում կուզեր տեսնել:"
            },
            ConversationState.READY_TO_SEARCH: {
                "english": f"Perfect, {user_name}! Let me search for jobs that match your profile...",
                "russian": f"Отлично, {user_name}! Ищу подходящие вакансии...",
                "armenian": f"Կատարյալ, {user_name}! Փնտրում եմ համապատասխան աշխատանք..."
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
    
    async def extract_name_with_ai(self, text: str, user_profile: Dict[str, Any]) -> ExtractionResult:
        """Use LLM to intelligently extract name from casual user input"""
        if not self.llm_service:
            return ExtractionResult({}, False, ConversationState.NAME_EXTRACT, 0.0)
        
        try:
            prompt = f"""
Extract the person's name from this message. Be intelligent about it.

Message: "{text}"

Instructions:
1. Look for their name in the message
2. Ignore greetings like "how are you", "what's up", etc.
3. Return ONLY a JSON object with the extracted name if found
4. If no name found, return {{"name": null}}

Examples:
- "hi i am artur how are you" -> {{"name": "Artur"}}
- "my name is john smith" -> {{"name": "John"}}
- "you can call me mike" -> {{"name": "Mike"}}
- "how are you today" -> {{"name": null}}

Return ONLY valid JSON:
            """
            
            response = await self.llm_service.chat(text, system_context="Extract name from user input")
            
            # Try to parse response as JSON
            try:
                import json
                # Clean markdown code blocks if present
                clean_response = response.strip()
                if clean_response.startswith("```"):
                    clean_response = clean_response.split("```")[1]
                    if clean_response.startswith("json"):
                        clean_response = clean_response[4:]
                    clean_response = clean_response.strip()
                
                data = json.loads(clean_response)
                name = data.get("name")
                
                if name and len(name) >= 2:
                    return ExtractionResult(
                        extracted={"name": name},
                        state_progressed=True,
                        next_state=ConversationState.SKILLS_EXTRACT,
                        confidence=0.85,
                        feedback_message=f"Great! Nice to meet you, {name}!"
                    )
            except:
                pass
        
        except Exception as e:
            print(f"LLM name extraction error: {e}")
        
        return ExtractionResult({}, False, ConversationState.NAME_EXTRACT, 0.0)
    
    def extract_skills(self, text: str, user_profile: Dict[str, Any]) -> ExtractionResult:
        """Extract job preferences/skills from user input"""
        text_orig = text.strip()
        text_lower = text.lower()
        extracted = {}
        
        print(f"[DEBUG extract_skills] Input: '{text}', Lower: '{text_lower}'")
        
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
    
    async def extract_skills_with_ai(self, text: str, user_profile: Dict[str, Any]) -> ExtractionResult:
        """Use LLM to intelligently extract job/skills from casual user input"""
        if not self.llm_service:
            return ExtractionResult({}, False, ConversationState.SKILLS_EXTRACT, 0.0)
        
        try:
            prompt = f"""
Extract the job titles or skills from this message. Be intelligent and flexible.

Message: "{text}"

Instructions:
1. Extract job titles or skills they're interested in
2. Look for ANY job-related keywords (driver, developer, teacher, doctor, etc.)
3. Handle multiple jobs separated by "and", commas, or "or"
4. Return JSON with "jobs" array
5. If they say they don't work, have no experience, or just started - ask what interests them

Examples:
- "I want to be a developer and designer" -> {{"jobs": ["developer", "designer"]}}
- "taxi driver or bus driver" -> {{"jobs": ["taxi driver", "bus driver"]}}
- "i dont work but interested in programming" -> {{"jobs": ["programming"]}}
- "how are you" -> {{"jobs": []}}

Return ONLY valid JSON:
            """
            
            response = await self.llm_service.chat(text, system_context="Extract job/skills interests")
            
            # Try to parse response as JSON
            try:
                import json
                clean_response = response.strip()
                if clean_response.startswith("```"):
                    clean_response = clean_response.split("```")[1]
                    if clean_response.startswith("json"):
                        clean_response = clean_response[4:]
                    clean_response = clean_response.strip()
                
                data = json.loads(clean_response)
                jobs = data.get("jobs", [])
                
                if jobs and len(jobs) > 0:
                    # Filter out empty strings
                    jobs = [j.strip() for j in jobs if j.strip()]
                    if jobs:
                        return ExtractionResult(
                            extracted={"career_goals": ", ".join(jobs)},
                            state_progressed=True,
                            next_state=ConversationState.LOCATION_EXTRACT,
                            confidence=0.85
                        )
            except:
                pass
        
        except Exception as e:
            print(f"LLM skills extraction error: {e}")
        
        return ExtractionResult({}, False, ConversationState.SKILLS_EXTRACT, 0.0)
    
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
        """Process user input with API-driven conversation for natural interactions"""
        
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

        # Try extraction based on current state
        if self.current_state in [ConversationState.GREETING, ConversationState.NAME_EXTRACT]:
             result = self.extract_name(text, user_profile)
             
             # If regex extraction failed, try AI extraction
             if not result.state_progressed and self.llm_service:
                 try:
                     result = await self.extract_name_with_ai(text, user_profile)
                 except Exception as e:
                     print(f"Name extraction error: {type(e).__name__}: {str(e)[:100]}")
             
             # If both regex and AI failed, use fallback
             if not result.state_progressed:
                 words = text.split()
                 # Only accept multi-letter words as names, skip single letters
                 if words and 2 <= len(words[0]) <= 20 and words[0].isalpha():
                     result = ExtractionResult(
                         extracted={'name': words[0].capitalize()},
                         state_progressed=True,
                         next_state=ConversationState.SKILLS_EXTRACT,
                         confidence=0.6
                     )
                     print(f"[Name fallback] Extracted: '{words[0].capitalize()}'")
                 else:
                     # If we can't extract, ask for the name explicitly
                     print(f"[Name extraction failed] Can't extract from: '{text}'")
                     result = ExtractionResult(
                         extracted={},
                         state_progressed=False,
                         next_state=ConversationState.NAME_EXTRACT,
                         confidence=0.0,
                         feedback_message="Could you tell me your name so I can personalize your job search?"
                     )
        
        elif self.current_state == ConversationState.SKILLS_EXTRACT:
             result = self.extract_skills(text, user_profile)
             # If regex extraction failed and LLM available, try AI extraction
             if not result.state_progressed and self.llm_service:
                 try:
                     result = await self.extract_skills_with_ai(text, user_profile)
                 except Exception as e:
                     print(f"Skills extraction error: {e}")
        
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

        # Handle Result with immediate response (no API calls - focus on extraction)
        if result.state_progressed:
            self.current_state = result.next_state
            user_profile.update(result.extracted)
            self.user_profile = user_profile
            
            # Generate next question immediately (synchronous, fast, reliable)
            detected_lang = self.detect_language(user_profile.get('name', ''))
            response = self.generate_natural_followup(
                state=self.current_state,
                user_profile=user_profile,
                language=detected_lang
            )
        else:
            # Extraction failed
            if result.feedback_message:
                response = result.feedback_message
            else:
                # Generate default clarification message based on state
                clarification_hints = {
                    ConversationState.NAME_EXTRACT: "What's your name?",
                    ConversationState.SKILLS_EXTRACT: "What job position are you interested in? (e.g., 'Python Developer', 'Nurse')",
                    ConversationState.LOCATION_EXTRACT: "Which city or country? (or 'Remote' for remote work)",
                    ConversationState.REMOTE_PREF_EXTRACT: "Do you prefer remote work, on-site, or either?",
                    ConversationState.RATE_EXTRACT: "What's your hourly rate or salary expectation?",
                    ConversationState.HOURS_EXTRACT: "How many hours per week do you want to work?",
                    ConversationState.OFFERS_EXTRACT: "How many job offers would you like to see?",
                }
                
                response = clarification_hints.get(
                    self.current_state,
                    "Could you clarify that a bit more?"
                )
        
        return result, response
    
    def generate_natural_followup(
        self,
        state: ConversationState,
        user_profile: Dict[str, Any],
        language: str = "english"
    ) -> str:
        """
        Generate a natural follow-up question that builds on what we know.
        This creates conversational flow by referencing previous answers.
        """
        name = user_profile.get('name', '')
        skills = user_profile.get('skills', '')
        location = user_profile.get('location', '')
        remote_pref = user_profile.get('remote_preference', '')
        experience = user_profile.get('experience_years', '')
        
        templates = {
            "english": {
                ConversationState.SKILLS_EXTRACT: [
                    f"Got it! So you're interested in {skills}. How many years of experience do you have in this field?",
                    f"That's great! {skills} is in high demand right now. What's your experience level?",
                    f"Interesting! {skills} is a solid choice. How long have you been working in this area?",
                ],
                ConversationState.LOCATION_EXTRACT: [
                    f"Perfect! So you're based in {location}. Do you prefer working on-site, remote, or are you flexible?",
                    f"Got it, {location} it is. Would you be open to remote opportunities, or do you prefer being in an office?",
                    f"Thanks for that info! In {location}, would you rather work from home, go to an office, or either?",
                ],
                ConversationState.REMOTE_PREF_EXTRACT: [
                    f"Great! So {remote_pref} works for you. How many hours per week can you realistically dedicate to work?",
                    f"Perfect, {remote_pref} it is. What's your availability like—how many hours weekly?",
                    f"Got it! With {remote_pref} work, how many hours per week are you looking to work?",
                ],
                ConversationState.RATE_EXTRACT: [
                    f"Thanks for sharing that. What's your minimum hourly rate or salary expectation? (No pressure if you're unsure!)",
                    f"Understood. Do you have a target hourly rate in mind? (Totally optional if you'd rather skip this)",
                    f"Got it. What kind of hourly rate or salary would you be looking for? (Feel free to skip if you prefer)",
                ],
                ConversationState.HOURS_EXTRACT: [
                    f"Awesome! So {experience} years of experience and {skills} skills. How many hours per week can you commit?",
                    f"Great background! How many hours per week are you available to work?",
                    f"Perfect! With your experience, how many hours weekly can you dedicate to work?",
                ],
                ConversationState.READY_TO_SEARCH: [
                    f"Excellent, {name}! I have everything I need. Let me search for {skills} roles that match your preferences...",
                    f"Perfect! I'm going to find some {skills} opportunities that fit your schedule and location. Give me a moment...",
                    f"Great! Searching for {skills} positions in {location} that match what you're looking for...",
                ],
            },
            "russian": {
                ConversationState.SKILLS_EXTRACT: [
                    f"Понял! Ты ищешь работу в области {skills}. Сколько лет опыта у тебя?",
                    f"Отлично! {skills} сейчас очень востребована. Какой у тебя уровень опыта?",
                ],
                ConversationState.LOCATION_EXTRACT: [
                    f"Хорошо! Ты в {location}. Ты предпочитаешь офис, удалённую работу или оба варианта?",
                    f"Спасибо! В {location} ты хочешь работать в офисе или дома?",
                ],
                ConversationState.REMOTE_PREF_EXTRACT: [
                    f"Отлично! Итак, {remote_pref} работа. Сколько часов в неделю ты можешь работать?",
                    f"Понял! Сколько часов в неделю ты готов уделить работе?",
                ],
                ConversationState.RATE_EXTRACT: [
                    f"Спасибо! Какой минимальный размер оплаты тебе нужен? (Можешь пропустить, если не уверен)",
                    f"Понял. Какую ставку ты ищешь? (Опционально)",
                ],
                ConversationState.HOURS_EXTRACT: [
                    f"Хорошо! Сколько часов в неделю ты можешь работать?",
                    f"Спасибо! Какова твоя доступность по часам в неделю?",
                ],
                ConversationState.READY_TO_SEARCH: [
                    f"Отлично, {name}! Ищу подходящие вакансии по {skills}...",
                    f"Прекрасно! Ищу позиции {skills} в {location}...",
                ],
            },
            "armenian": {
                ConversationState.SKILLS_EXTRACT: [
                    f"Հասկացա! Դու փնտրում ես {skills} աշխատանք: Քանի տարի փորձ ունես?",
                    f"Հիանալի! {skills} շատ պահանջված է: Ո՞րն է քո փորձի մակարդակը:",
                ],
                ConversationState.LOCATION_EXTRACT: [
                    f"Լավ! Դու {location}-ում ես: Գրասենյակային, հեռավար, թե երկուսն էլ?",
                    f"Շնորհակալ! {location}-ում ո՞ր տեսակի աշխատանք ես ուզում:",
                ],
                ConversationState.REMOTE_PREF_EXTRACT: [
                    f"Հիանալի! Այսպես, {remote_pref} աշխատանք: Քանի ժամ շաբաթական կարող ես աշխատել?",
                    f"Հասկացա! Քանի ժամ շաբաթական ես հասանելի?",
                ],
                ConversationState.RATE_EXTRACT: [
                    f"Շնորհակալ! Ո՞րն է քո նվազագույն ժամային դրույքը: (Ընտրովի)",
                    f"Հասկացա: Ի՞նչ դրույք ես ուզում:",
                ],
                ConversationState.HOURS_EXTRACT: [
                    f"Լավ! Քանի ժամ շաբաթական կարող ես աշխատել?",
                    f"Շնորհակալ! Ո՞րն է քո հասանելիությունը:",
                    f"Ինչպե՞ս կարող ես բաշխել քո աշխատաժամը շաբաթվա ընթացքում:",
                ],
                ConversationState.READY_TO_SEARCH: [
                    f"Հիանալի, {name}! Փնտրում եմ {skills} աշխատանք...",
                    f"Կատարյալ! Փնտրում եմ պաշտոններ {location}-ում...",
                ],
            }
        }
        
        lang_templates = templates.get(language, templates["english"])
        questions = lang_templates.get(state, [])
        
        if not questions:
            return self.get_next_question(state, name, user_profile)
        
        # Return a random question from the list for variety
        return random.choice(questions)