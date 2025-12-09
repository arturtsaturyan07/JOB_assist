import os
import json
import re
import google.generativeai as genai
import httpx
from typing import Dict, Any, List, Optional

class LLMService:
    """
    LLM Service with Double Fallback: OpenAI -> Gemini -> Regex.
    """
    
    def __init__(self, gemini_key_file: str = "gemini_api_key.txt", openai_key_file: str = "openai_api_key.txt"):
        self.gemini_key = self._load_key(gemini_key_file)
        self.openai_key = self._load_key(openai_key_file)
        
        self.provider = "none"
        self.use_fallback_regex = False

        # 1. Try OpenAI First (User Preference)
        if self.openai_key:
            self.provider = "openai"
            self.openai_model = "gpt-4o-mini" # Cost effective
        # 2. Try Gemini Second
        elif self.gemini_key:
            try:
                genai.configure(api_key=self.gemini_key)
                self.provider = "gemini"
                self.gemini_model = "gemini-2.0-flash"
            except Exception as e:
                print(f"Warning: Gemini config failed: {e}")
                
        if self.provider == "none":
            print("Warning: No API keys found. Using pure regex fallback.")
            self.use_fallback_regex = True

    def _load_key(self, filepath: str) -> Optional[str]:
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                content = f.read().strip()
                return content if content else None
        return None

    async def chat(self, user_message: str, system_context: str = "") -> str:
        """
        Generate a conversational response (OpenAI -> Gemini -> Fallback)
        """
        if self.use_fallback_regex:
            return "I'm having trouble connecting to my AI brain. Could you rephrase that simply?"

        prompt = f"""
        You are TwinWork AI, a helpful and friendly job assistant.
        
        CONTEXT: {system_context}
        
        USER SAYS: "{user_message}"
        
        INSTRUCTIONS:
        - Answer naturally and helpfuly.
        - Keep it brief (max 2-3 sentences).
        - If the user asks "do you understand me", say "Yes, I understand you perfectly!"
        - If confused, guide them back to job search.
        """

        try:
            if self.provider == "openai":
                return await self._call_openai(prompt)
            elif self.provider == "gemini":
                return await self._call_gemini(prompt)
        except Exception as e:
            print(f"LLM Chat Error ({self.provider}): {e}")
            return "Sorry, I didn't quite catch that. Could you rephrase?"

    async def _call_openai(self, prompt: str) -> str:
        timeout = httpx.Timeout(10.0, connect=5.0)
        payload = {
            "model": self.openai_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json; charset=utf-8"
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    content=body
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                try:
                    print(f"OpenAI Error: {e}")
                except UnicodeEncodeError:
                    print(f"OpenAI Error: {str(e).encode('ascii', 'ignore').decode('ascii')}")
                raise e

    async def _call_gemini(self, prompt: str) -> str:
        model = genai.GenerativeModel(self.gemini_model)
        response = await model.generate_content_async(prompt)
        return response.text

    def _extract_with_regex(self, text: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback: Extract user info using regex patterns."""
        # [Existing Regex Logic Removed for Brevity - Keeping Core Wrapper]
        # In a real implementation, we would keep the regex logic here
        # For now, assuming caller handles fallback or we re-implement it briefly?
        # WAIT: I should not delete the regex logic if I can avoid it.
        # But replacing the WHOLE file deletes it.
        # I should use `replacement_chunks` instead or handle it carefully.
        # I will return a placeholder here if I can't keep the code, BUT
        # The user wants "normal chat". This class handles normal chat.
        # The regex part handles extraction.
        # I will keep the regex method mostly intact by NOT deleting it, 
        # checking the previous content to see where it was.
        # Since I'm using `replace_file_content` on the whole file or large chunk,
        # I must be careful.
        # I'll use `replace_file_content` just for the TOP part (Init + Chat)
        # and keep the extraction logic below.
        return {} # Placeholder - DO NOT USE THIS implementation for extraction

    # ... (rest of regex methods) ...


    def _extract_with_regex(self, text: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback: Extract user info using regex patterns."""
        text_lower = text.lower()
        
        extracted = {}
        
        # Name extraction - supports English, Russian, and Armenian
        name_patterns = [
            # English patterns
            r"i\s+am\s+(\w+)",  # I am Arthur
            r"i'm\s+(\w+)",    # I'm Arthur  
            r"my\s+name\s+is\s+(\w+)",  # My name is Arthur
            r"call\s+me\s+(\w+)",  # Call me Arthur
            # Russian patterns
            r"я\s+(\w+)",  # Russian: я [name] (I [name] - casual form)
            r"меня\s+зовут\s+(\w+)",  # Russian: меня зовут [name] (They call me [name])
            r"мое\s+имя\s+(\w+)",  # Russian: мое имя [name] (My name is [name])
            # Armenian patterns
            r"ես\s+եմ\s+(\w+)",  # Armenian: ես եմ [name] (I am [name])
            r"ես\s+(\w+)",  # Armenian: ես [name] (I [name] - casual form)
            r"իմ\s+անունը\s+(\w+)",  # Armenian: իմ անունը [name] (My name is [name])
            r"ինձ\s+անվանեք\s+(\w+)",  # Armenian: ինձ անվանեք [name] (Call me [name])
            # Bare word (any language)
            r"^(\w+)$",  # Just a single word (name)
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE | re.UNICODE)
            if match:
                name = match.group(1).capitalize()
                if name not in ['A', 'The', 'And', 'Or', 'But', 'As', 'In', 'Yes', 'No', 'Remote', 'Both', 'Skip', 'Any', 'Hi', 'Hello']:
                    extracted['name'] = name
                    break
        
        # Skills/career goals extraction - extract ALL mentioned jobs/roles
        # Match patterns like "english teacher", "python developer", "surgeon", etc.
        
        skills = []
        career_goals = []
        
        # List of known roles
        roles = [
            'teacher', 'tutor', 'developer', 'engineer', 'programmer', 'designer',
            'surgeon', 'doctor', 'nurse', 'lawyer', 'accountant', 'manager',
            'analyst', 'architect', 'consultant', 'scientist', 'researcher',
            'driver', 'chef', 'plumber', 'electrician', 'mechanic', 'painter',
            'carpenter', 'cleaner', 'security', 'guard', 'photographer', 'writer',
            'editor', 'journalist', 'translator', 'interpreter', 'recruiter',
            'hr', 'marketing', 'sales', 'ceo', 'cto', 'director', 'supervisor',
        ]
        
        # List of known skills/domains
        domains = [
            'python', 'javascript', 'java', 'c\\+\\+', 'go', 'rust', 'english',
            'spanish', 'french', 'german', 'data', 'ai', 'ml', 'web', 'mobile',
            'cloud', 'devops', 'security', 'frontend', 'backend', 'fullstack',
        ]
        
        # Split by common separators (and, or, &, ,)
        job_phrases = re.split(r'\s+(?:and|or|&|,)\s+', text_lower)
        
        for phrase in job_phrases:
            phrase = phrase.strip()
            
            # Try to match "[domain] [role]" pattern
            for domain in domains:
                for role in roles:
                    pattern = rf'{domain}\s+{role}'
                    if re.search(pattern, phrase, re.IGNORECASE):
                        domain_name = domain.replace('\\', '').capitalize()
                        role_name = role.capitalize()
                        
                        # Add to skills
                        if domain_name not in skills:
                            skills.append(domain_name)
                        
                        # Add to career goals
                        goal = f"{domain_name} {role_name}"
                        if goal not in career_goals:
                            career_goals.append(goal)
            
            # Also match standalone roles
            for role in roles:
                if re.search(rf'\b{role}\b', phrase, re.IGNORECASE):
                    role_name = role.capitalize()
                    if role_name not in career_goals:
                        career_goals.append(role_name)
        
        if skills:
            extracted['skills'] = skills
        if career_goals:
            extracted['career_goals'] = ', '.join(career_goals)
        elif skills:
            extracted['career_goals'] = ', '.join(skills)
        
        # Location extraction
        # Location extraction - comprehensive city list
        locations = [
            'yerevan', 'moscow', 'london', 'dubai', 'new york', 'chicago', 'san francisco',
            'los angeles', 'toronto', 'paris', 'berlin', 'sydney', 'tokyo', 'singapore',
            'remote', 'armenia', 'usa', 'uk', 'canada', 'australia'
        ]
        
        # Check for role-specific locations (e.g., "teacher: remote, doctor: london")
        # First, split by comma to separate role statements
        role_locations = {}
        # Split by comma or "for" to separate role specifications
        segments = re.split(r',|(?=for\s)', text_lower)
        
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue
            # Remove "for" prefix if present
            segment = re.sub(r'^for\s+', '', segment)
            
            # Find which role is mentioned in this segment
            for role in ['doctor', 'surgeon', 'nurse', 'teacher', 'developer', 'engineer', 'lawyer', 'accountant']:
                if role in segment:
                    # Find the location in this segment
                    for loc in locations:
                        if loc in segment:
                            role_locations[role] = loc.capitalize()
                            break
                    break  # Found role in this segment, move to next segment
        
        # Extract general/default location (any location mentioned)
        for loc in locations:
            if loc in text_lower and loc not in ['doctor', 'surgeon', 'nurse', 'teacher', 'developer', 'engineer', 'lawyer', 'accountant']:
                extracted['location'] = loc.capitalize()
                break
        
        # Store role-specific locations if found
        if role_locations:
            extracted['role_locations'] = role_locations

        # Remote/Onsite preference
        if 'remote' in text_lower:
            extracted['remote_ok'] = True
        if 'office' in text_lower or 'onsite' in text_lower or 'in-office' in text_lower or 'in office' in text_lower:
            extracted['onsite_ok'] = True
        # Handle "both" - means both remote and onsite are OK
        if 'both' in text_lower:
            extracted['remote_ok'] = True
            extracted['onsite_ok'] = True
        
        # Extract hours per week first - look for "X hours per week", "X hrs/week", etc.
        hours_match = re.search(r'(\d+)\s*(?:hours?|hrs?)\s*(?:per\s*week|\/week|\/wk|/w)?', text_lower)
        if hours_match:
            try:
                hours = int(hours_match.group(1))
                # Make sure this is actually about weekly hours, not salary
                if 'week' in text_lower or '/w' in text_lower or 'hr' in text_lower:
                    extracted['max_hours'] = hours
            except:
                pass
        
        # Extract hourly rate - look for "$X", "X per hour", "X/hr", etc.
        # Be more specific: look for $ symbol or explicit "per hour" / "/hr" patterns
        rate_patterns = [
            r'\$(\d+(?:\.\d{2})?)',  # $50
            r'(\d+(?:\.\d{2})?)\s*(?:per|\/)\s*(?:hour|hr|h)',  # 50 per hour, 50/hr
        ]
        for pattern in rate_patterns:
            rate_match = re.search(pattern, text_lower)
            if rate_match:
                try:
                    rate = float(rate_match.group(1))
                    extracted['min_rate'] = rate
                    break  # Found a rate, don't need to try other patterns
                except:
                    pass
        
        # Handle "skip", "any", "flexible", "doesn't matter" for hourly rate
        if not extracted.get('min_rate'):
            skip_keywords = ['skip', 'any', 'flexible', "doesn't matter", 'whatever', 'no preference', 'Ð¿Ñ€Ð¾Ð¿ÑƒÑÑ‚Ð¸Ñ‚ÑŒ', 'Ð»ÑŽÐ±Ð¾Ð¹']
            if any(kw in text_lower for kw in skip_keywords):
                extracted['min_rate'] = 0  # 0 means flexible/no minimum
        
        # Handle "skip", "no limit", etc. for hours per week
        if not extracted.get('max_hours'):
            skip_keywords = ['skip', 'no limit', 'any', 'flexible', 'whatever', 'Ð¿Ñ€Ð¾Ð¿ÑƒÑÑ‚Ð¸Ñ‚ÑŒ', 'Ð½ÐµÑ‚ Ð»Ð¸Ð¼Ð¸Ñ‚Ð°']
            if any(kw in text_lower for kw in skip_keywords):
                extracted['max_hours'] = 999  # 999 means no limit
        
        # Extract number of offers - look for "5 offers", "10 jobs", "show me 20", etc.
        # Only extract if it has explicit keywords to avoid confusion with rates/hours
        offers_patterns = [
            r'(?:show\s+)?(\d+)\s*(?:offers?|jobs?|vacancies?|positions?)',
            r'(\d+)\s*(?:offers?|opportunities?)',
        ]
        for pattern in offers_patterns:
            offers_match = re.search(pattern, text_lower)
            if offers_match:
                try:
                    num_offers = int(offers_match.group(1))
                    if 1 <= num_offers <= 100:  # Reasonable range
                        extracted['num_offers'] = num_offers
                        break
                except:
                    pass
        
        # Fallback: If the entire input is just a number (e.g., user replies "2" to "How many offers?")
        # and we haven't extracted an explicit rate or hours already, treat it as num_offers
        if not extracted.get('num_offers') and not extracted.get('min_rate') and not extracted.get('max_hours'):
            bare_number_match = re.match(r'^(\d+)$', text_lower.strip())
            if bare_number_match:
                try:
                    num = int(bare_number_match.group(1))
                    if 1 <= num <= 100:  # Reasonable range for offers
                        extracted['num_offers'] = num
                except:
                    pass
        
        return extracted

    async def get_response(self, history: List[Dict[str, str]], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        if self.use_fallback or not self.model_name:
            return self._fallback_response(history, user_profile)

        # Construct prompt with friendly personality
        system_prompt = """
        You are Azduna - a super friendly, warm, and helpful AI job assistant! ðŸŒŸ
        Think of yourself as a supportive friend who genuinely wants to help find the perfect job.
        
        YOUR PERSONALITY:
        - Be warm, encouraging, and use casual friendly language
        - Use emojis naturally (but not excessively!) 
        - Celebrate small wins with the user
        - Be understanding if they seem frustrated
        - Show genuine interest in their goals
        - Feel free to chat naturally
        - Use their name when addressing them
        - DON'T sound like a robot or form!
        - DO sound like a friendly recruiter having a casual chat
        
        REQUIRED INFORMATION TO COLLECT:
        1. Name - Be warm when greeting!
        2. Location (City) - Show interest in their city
        3. Minimum Hourly Rate - Be supportive (can be any currency, or "skip"/"any" = 0)
        4. Maximum Hours Per Week
        5. Desired Hours Per Week (can skip)
        6. Remote Work Preference
        7. Onsite Work Preference  
        8. Skills - Be enthusiastic about their skills!
        9. Career Goals - Show genuine interest (can skip = "General")
        10. Busy Schedule (or "no")
        11. Preferred Locations (or "no")
        12. Country Code - Default "am" (Armenia). If UAE/Dubai â†’ "ae", London/UK â†’ "gb", etc.

        CURRENT USER DATA:
        {user_data}
        
        **MULTILINGUAL SUPPORT** (CRITICAL):
        - Understand: English, Russian (Ð ÑƒÑÑÐºÐ¸Ð¹), Armenian (Õ€Õ¡ÕµÕ¥Ö€Õ¥Õ¶)
        - ALWAYS respond in the SAME language as the user!
        - If they switch languages, switch with them!
        
        **FLEXIBILITY**:
        - "no", "Ð½ÐµÑ‚", "skip", "Ð¿Ñ€Ð¾Ð¿ÑƒÑÑ‚Ð¸Ñ‚ÑŒ" = move on gracefully
        - Accept casual: "whatever", "doesn't matter", "Ð»ÑŽÐ±Ð°Ñ"
        - If both remote AND onsite are "no" â†’ ask about hybrid
        
        **COMPLETION**:
        When you have ALL info, set "ready_to_search": true and say something excited!
        
        BUSY SCHEDULE FORMAT: {"Mon": [["09:00", "12:00"]]} or {} if none

        OUTPUT FORMAT (JSON only - MUST BE VALID JSON):
        {
            "response": "Your friendly response in user's language",
            "extracted_data": {
                "name": "...",
                "location": "...",
                "min_rate": 0.0,
                "max_hours": 0,
                "desired_hours": 0,
                "remote_ok": true,
                "onsite_ok": true,
                "skills": ["..."],
                "career_goals": "...",
                "busy_schedule": {},
                "preferred_locations": [],
                "country_code": "am",
                "ready_to_search": false
            }
        }
        Only include fields you've newly extracted or updated.
        """

        formatted_prompt = system_prompt.replace("{user_data}", json.dumps(user_profile, indent=2, ensure_ascii=False))
        
        # Build chat history for context
        full_prompt = formatted_prompt + "\n\nChat History:\n"
        for msg in history:
            full_prompt += f"{msg['role'].upper()}: {msg['content']}\n"
        full_prompt += "\nAI (respond with ONLY valid JSON):"

        # List of models to try in order
        models_to_try = [self.model_name, "gemini-2.5-flash", "gemini-2.0-pro-exp", "gemini-flash-latest"]
        
        last_error = None
        for model_name in models_to_try:
            try:
                print(f"[*] Trying model: {model_name}")
                model = genai.GenerativeModel(model_name)
                
                # Use JSON mode for structured output
                config = genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.7
                )

                response = model.generate_content(full_prompt, generation_config=config)
                
                # Clean up response
                text = response.text.strip()
                if not text:
                    print(f"Empty response from {model_name}")
                    last_error = "Empty response"
                    continue
                    
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                
                text = text.strip()
                
                # Try to parse JSON
                result = json.loads(text)
                print(f"[OK] Success with {model_name}")
                return result
                
            except json.JSONDecodeError as e:
                print(f"[ERROR] JSON Parse Error with {model_name}: {e}")
                print(f"   Response text: {text[:200]}")
                last_error = f"JSON Parse Error: {e}"
                continue
            except Exception as e:
                print(f"[ERROR] Error with {model_name}: {type(e).__name__}: {str(e)[:100]}")
                last_error = e
                continue
        
        print(f"All models failed. Using fallback. Last error: {last_error}")
        return self._fallback_response(history, user_profile)

    def _fallback_response(self, history: List[Dict[str, str]], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback response using regex extraction."""
        print("Using fallback extraction mode...")
        
        # Get last user message
        last_user_msg = ""
        for msg in reversed(history):
            if msg['role'] == 'user':
                last_user_msg = msg['content']
                break
        
        # Extract data from user message
        extracted = self._extract_with_regex(last_user_msg, user_profile)
        
        # Don't re-extract name if we already have one
        if 'name' in user_profile and 'name' in extracted:
            extracted.pop('name')
        
        # Merge with existing profile
        merged_profile = {**user_profile, **extracted}
        
        # Generate friendly response based on what we have
        name = extracted.get('name', merged_profile.get('name', 'Ð´Ñ€ÑƒÐ³'))
        
        # Check what info we're still missing - expanded list
        has_name = 'name' in merged_profile
        has_skills = 'skills' in merged_profile or 'career_goals' in merged_profile
        has_location = 'location' in merged_profile
        has_remote_pref = 'remote_ok' in merged_profile or 'onsite_ok' in merged_profile
        has_min_rate = 'min_rate' in merged_profile
        has_max_hours = 'max_hours' in merged_profile
        has_num_offers = 'num_offers' in merged_profile
        
        response = ""
        ready_to_search = False
        
        # Progressive conversation flow - ask for more details
        if not has_name:
            response = "Hi there! What's your name?"
        elif not has_skills:
            response = f"Nice to meet you, {name}! What kind of jobs are you looking for? (e.g., Python developer, English teacher, surgeon)"
        elif not has_location:
            response = f"Great! So you're interested in {extracted.get('career_goals', 'these roles')}!\nWhere are you located? (or 'remote' if you work remotely)"
        elif not has_remote_pref:
            response = f"Perfect! {extracted.get('location', 'Your location')} noted!\nAre you open to remote work, office work, or both?"
        elif not has_min_rate:
            response = f"Awesome!\nWhat's your minimum hourly rate? (or 'any' / 'skip' if you're flexible)"
        elif not has_max_hours:
            response = f"Got it!\nHow many hours per week can you work? (or 'no limit' / 'skip')"
        elif not has_num_offers:
            response = f"Perfect!\nHow many job offers would you like to see? (5, 10, 20, or more?)"
        else:
            # We have enough info to search!
            response = f"Excellent, {name}! I have all the details. Let me find the best opportunities for you!"
            ready_to_search = True
        
        # Auto-trigger search if we have the essentials and user seems ready
        if has_name and has_skills and has_location and has_remote_pref and has_min_rate and has_max_hours:
            # Check if they explicitly said "search", "find", "show", etc.
            if any(word in last_user_msg.lower() for word in ['search', 'find', 'show', 'look', 'begin', 'start', 'go']):
                ready_to_search = True
            # Or if they provided number of offers
            elif has_num_offers or any(word in last_user_msg.lower() for word in ['offers', 'jobs', 'positions', 'vacancies']):
                ready_to_search = True
        
        extracted['ready_to_search'] = ready_to_search
        
        return {
            "response": response,
            "extracted_data": extracted
        }

