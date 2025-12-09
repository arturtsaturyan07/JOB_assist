"""
Job Intelligence Service for TwinWork AI

Provides deep job description analysis:
- Extract structured data from ANY job posting
- Parse schedules from natural language
- Identify red flags and culture signals
- Support for Armenian, Russian, English job posts
"""

import re
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

from multi_model_service import MultiModelService, TaskType


@dataclass
class ParsedSchedule:
    """Parsed work schedule"""
    days: List[str] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""
    hours_per_week: int = 0
    is_flexible: bool = False
    shifts: List[str] = field(default_factory=list)  # ["morning", "evening", "night"]
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ParsedJob:
    """Fully parsed job posting"""
    title: str = ""
    company: str = ""
    location: str = ""
    is_remote: bool = False
    is_hybrid: bool = False
    
    required_skills: List[str] = field(default_factory=list)
    nice_to_have_skills: List[str] = field(default_factory=list)
    experience_years: int = 0
    education_required: str = ""
    
    schedule: ParsedSchedule = field(default_factory=ParsedSchedule)
    
    salary_min: float = 0.0
    salary_max: float = 0.0
    salary_currency: str = "USD"
    salary_period: str = "monthly"  # hourly, monthly, yearly
    
    employment_type: str = ""  # full-time, part-time, contract, internship
    
    responsibilities: List[str] = field(default_factory=list)
    benefits: List[str] = field(default_factory=list)
    
    red_flags: List[str] = field(default_factory=list)
    culture_signals: List[str] = field(default_factory=list)
    
    original_text: str = ""
    source: str = ""  # staff.am, linkedin, manual, etc.
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['schedule'] = self.schedule.to_dict()
        return data


class JobIntelligenceService:
    """
    Deep job analysis service using LLM + rule-based extraction.
    
    Designed to extract maximum information from any job posting,
    including Armenian/Russian language posts.
    """
    
    def __init__(self):
        self.llm = MultiModelService()
        
        # Red flag keywords (multilingual)
        self.red_flags = {
            'en': [
                'unpaid overtime', 'unlimited pto', 'fast-paced',
                'wear many hats', 'hustle culture', 'work hard play hard',
                'competitive salary', 'salary negotiable', 'exposure',
                'paid in equity', 'startup mentality', 'family environment',
                'entry-level with 5 years experience', 'ninja', 'rockstar'
            ],
            'ru': [
                'неоплачиваемые переработки', 'ненормированный график',
                'многозадачность', 'стрессоустойчивость обязательна',
                'молодой коллектив', 'зп по результатам собеседования'
            ],
            'am': [
                'անվdelays աdelays',  # placeholder for Armenian
            ]
        }
        
        # Positive culture signals (multilingual)
        self.culture_signals = {
            'en': [
                'work-life balance', 'flexible hours', 'remote-friendly',
                'professional development', 'mentorship program',
                'health insurance', 'paid parental leave', '401k matching',
                'unlimited sick days', 'mental health support',
                'diversity and inclusion', 'transparent salary'
            ],
            'ru': [
                'баланс работы и жизни', 'гибкий график', 'удаленная работа',
                'профессиональное развитие', 'медицинская страховка',
                'оплачиваемый отпуск', 'корпоративное обучение'
            ]
        }
        
        # Skill categories for better matching
        self.skill_categories = {
            'programming': [
                'python', 'javascript', 'typescript', 'java', 'c++', 'c#',
                'go', 'rust', 'ruby', 'php', 'swift', 'kotlin', 'scala'
            ],
            'frontend': [
                'react', 'angular', 'vue', 'svelte', 'html', 'css', 'sass',
                'tailwind', 'bootstrap', 'jquery', 'webpack', 'vite'
            ],
            'backend': [
                'node', 'express', 'django', 'flask', 'fastapi', 'spring',
                'rails', 'laravel', 'asp.net', 'graphql', 'rest api'
            ],
            'database': [
                'sql', 'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
                'cassandra', 'dynamodb', 'firebase', 'supabase'
            ],
            'devops': [
                'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'terraform',
                'ansible', 'jenkins', 'github actions', 'gitlab ci', 'linux'
            ],
            'data': [
                'pandas', 'numpy', 'tensorflow', 'pytorch', 'scikit-learn',
                'spark', 'hadoop', 'airflow', 'tableau', 'power bi'
            ],
            'design': [
                'figma', 'sketch', 'adobe xd', 'photoshop', 'illustrator',
                'ui/ux', 'user research', 'prototyping', 'wireframing'
            ]
        }
    
    async def analyze_job(self, job_text: str, source: str = "manual") -> ParsedJob:
        """
        Analyze a job posting and extract structured data.
        
        Args:
            job_text: Raw job posting text
            source: Where the job came from (staff.am, linkedin, etc.)
        
        Returns:
            ParsedJob with all extracted information
        """
        # Try LLM extraction first
        try:
            llm_result = await self._llm_extraction(job_text)
        except Exception as e:
            print(f"⚠️ LLM extraction failed: {e}")
            llm_result = {}
        
        # Always do rule-based extraction as backup/supplement
        rule_result = self._rule_based_extraction(job_text)
        
        # Merge results (LLM takes priority where available)
        merged = self._merge_extractions(llm_result, rule_result)
        
        # Create ParsedJob
        parsed = ParsedJob(
            title=merged.get('title', ''),
            company=merged.get('company', ''),
            location=merged.get('location', ''),
            is_remote='remote' in merged.get('location', '').lower() or merged.get('is_remote', False),
            is_hybrid=merged.get('is_hybrid', False),
            required_skills=merged.get('required_skills', []),
            nice_to_have_skills=merged.get('nice_to_have_skills', []),
            experience_years=merged.get('experience_years', 0),
            education_required=merged.get('education_required', ''),
            schedule=self._parse_schedule(merged.get('schedule', {})),
            salary_min=merged.get('salary_min', 0),
            salary_max=merged.get('salary_max', 0),
            salary_currency=merged.get('salary_currency', 'USD'),
            salary_period=merged.get('salary_period', 'monthly'),
            employment_type=merged.get('employment_type', ''),
            responsibilities=merged.get('responsibilities', []),
            benefits=merged.get('benefits', []),
            red_flags=merged.get('red_flags', []),
            culture_signals=merged.get('culture_signals', []),
            original_text=job_text,
            source=source
        )
        
        return parsed
    
    async def _llm_extraction(self, job_text: str) -> Dict[str, Any]:
        """Use LLM for intelligent extraction"""
        system_prompt = """You are an expert job posting analyzer. Extract ALL information from this job posting.
        
        Return valid JSON with these exact fields:
        {
            "title": "Exact job title",
            "company": "Company name",
            "location": "City, Country or 'Remote'",
            "is_remote": true/false,
            "is_hybrid": true/false,
            "required_skills": ["skill1", "skill2"],
            "nice_to_have_skills": ["skill1"],
            "experience_years": 0,
            "education_required": "Bachelor's/Master's/etc or empty",
            "schedule": {
                "days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
                "start_time": "09:00",
                "end_time": "18:00",
                "is_flexible": false
            },
            "salary_min": 0,
            "salary_max": 0,
            "salary_currency": "USD/AMD/RUB/EUR",
            "salary_period": "hourly/monthly/yearly",
            "employment_type": "full-time/part-time/contract/internship",
            "responsibilities": ["resp1", "resp2"],
            "benefits": ["benefit1", "benefit2"],
            "red_flags": ["any concerning aspects"],
            "culture_signals": ["positive culture indicators"]
        }
        
        Important:
        - If info is not present, use empty string/array/0
        - Detect language (English/Russian/Armenian) and extract correctly
        - Convert all currencies to their code (AMD, USD, RUB, EUR)
        - Red flags: unpaid overtime, vague job description, unrealistic requirements
        - Culture signals: work-life balance, growth, benefits
        """
        
        result = await self.llm.process(
            TaskType.JOB_ANALYSIS,
            job_text,
            system_prompt,
            use_cache=True
        )
        
        return result.get('job_data', result)
    
    def _rule_based_extraction(self, text: str) -> Dict[str, Any]:
        """Extract job info using regex patterns"""
        text_lower = text.lower()
        result = {}
        
        # Title extraction
        result['title'] = self._extract_title(text)
        
        # Skills extraction
        result['required_skills'] = self._extract_skills(text_lower)
        
        # Experience extraction
        result['experience_years'] = self._extract_experience(text_lower)
        
        # Salary extraction
        salary_info = self._extract_salary(text)
        result.update(salary_info)
        
        # Schedule extraction
        result['schedule'] = self._extract_schedule_from_text(text_lower)
        
        # Employment type
        result['employment_type'] = self._extract_employment_type(text_lower)
        
        # Location
        result['location'] = self._extract_location(text)
        result['is_remote'] = 'remote' in text_lower or 'удаленн' in text_lower
        result['is_hybrid'] = 'hybrid' in text_lower or 'гибрид' in text_lower
        
        # Red flags
        result['red_flags'] = self._detect_red_flags(text_lower)
        
        # Culture signals
        result['culture_signals'] = self._detect_culture_signals(text_lower)
        
        return result
    
    def _extract_title(self, text: str) -> str:
        """Extract job title from text"""
        # Common patterns
        patterns = [
            r"(?:position|role|title|job)[\s:]+([A-Za-z\s]+(?:Developer|Engineer|Manager|Designer|Analyst|Specialist|Teacher|Doctor|Nurse))",
            r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Developer|Engineer|Manager|Designer|Analyst)))",
            r"(?:looking for|hiring|seeking)[\sa]+([A-Za-z\s]+(?:Developer|Engineer|Manager|Designer))",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip().title()
        
        return ""
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from job text"""
        found_skills = []
        
        for category, skills in self.skill_categories.items():
            for skill in skills:
                # Use word boundary for accurate matching
                if re.search(rf'\b{re.escape(skill)}\b', text, re.IGNORECASE):
                    found_skills.append(skill.title())
        
        return list(set(found_skills))
    
    def _extract_experience(self, text: str) -> int:
        """Extract years of experience required"""
        patterns = [
            r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)',
            r'experience[\s:]+(\d+)\+?\s*(?:years?|yrs?)',
            r'(\d+)\+?\s*лет\s*(?:опыта)?',  # Russian
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return 0
    
    def _extract_salary(self, text: str) -> Dict[str, Any]:
        """Extract salary information"""
        result = {
            'salary_min': 0,
            'salary_max': 0,
            'salary_currency': 'USD',
            'salary_period': 'monthly'
        }
        
        # Currency detection
        if 'amd' in text.lower() or '֏' in text or 'դdelays' in text:
            result['salary_currency'] = 'AMD'
        elif 'rub' in text.lower() or '₽' in text or 'руб' in text.lower():
            result['salary_currency'] = 'RUB'
        elif 'eur' in text.lower() or '€' in text:
            result['salary_currency'] = 'EUR'
        elif 'gbp' in text.lower() or '£' in text:
            result['salary_currency'] = 'GBP'
        
        # Period detection
        if 'hour' in text.lower() or '/hr' in text.lower() or 'в час' in text.lower():
            result['salary_period'] = 'hourly'
        elif 'year' in text.lower() or 'annual' in text.lower() or 'в год' in text.lower():
            result['salary_period'] = 'yearly'
        
        # Salary range patterns
        range_patterns = [
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*[-–to]+\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d{1,3}(?:,\d{3})*)\s*[-–to]+\s*(\d{1,3}(?:,\d{3})*)\s*(?:amd|usd|eur|rub|gbp)',
            r'(?:salary|зп|оклад)[\s:]+(\d{1,3}(?:,\d{3})*)\s*[-–to]+\s*(\d{1,3}(?:,\d{3})*)',
        ]
        
        for pattern in range_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['salary_min'] = float(match.group(1).replace(',', ''))
                result['salary_max'] = float(match.group(2).replace(',', ''))
                break
        
        # Single salary patterns
        if result['salary_min'] == 0:
            single_patterns = [
                r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                r'(\d{1,3}(?:,\d{3})*)\s*(?:amd|usd|eur|rub)',
            ]
            for pattern in single_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    salary = float(match.group(1).replace(',', ''))
                    result['salary_min'] = salary
                    result['salary_max'] = salary
                    break
        
        return result
    
    def _extract_schedule_from_text(self, text: str) -> Dict[str, Any]:
        """Extract work schedule from text"""
        schedule = {
            'days': [],
            'start_time': '',
            'end_time': '',
            'is_flexible': False
        }
        
        # Flexible schedule
        if any(word in text for word in ['flexible', 'гибкий', 'свободный график']):
            schedule['is_flexible'] = True
        
        # Day patterns
        if 'mon-fri' in text or 'monday-friday' in text or 'пн-пт' in text:
            schedule['days'] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
        elif 'weekdays' in text or 'будни' in text:
            schedule['days'] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
        elif 'weekends' in text or 'выходные' in text:
            schedule['days'] = ['Sat', 'Sun']
        
        # Time patterns
        time_pattern = r'(\d{1,2}):?(\d{2})?\s*(am|pm)?\s*[-–to]+\s*(\d{1,2}):?(\d{2})?\s*(am|pm)?'
        match = re.search(time_pattern, text)
        if match:
            start_hour = int(match.group(1))
            end_hour = int(match.group(4))
            
            # Handle AM/PM
            if match.group(3) and 'pm' in match.group(3).lower() and start_hour < 12:
                start_hour += 12
            if match.group(6) and 'pm' in match.group(6).lower() and end_hour < 12:
                end_hour += 12
            
            schedule['start_time'] = f"{start_hour:02d}:00"
            schedule['end_time'] = f"{end_hour:02d}:00"
        
        # Default schedule if none found and it's full-time
        if not schedule['days'] and 'full-time' in text:
            schedule['days'] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
            if not schedule['start_time']:
                schedule['start_time'] = '09:00'
                schedule['end_time'] = '18:00'
        
        return schedule
    
    def _extract_employment_type(self, text: str) -> str:
        """Extract employment type"""
        if 'full-time' in text or 'full time' in text or 'полная занятость' in text:
            return 'full-time'
        elif 'part-time' in text or 'part time' in text or 'частичная занятость' in text:
            return 'part-time'
        elif 'contract' in text or 'contractor' in text or 'контракт' in text:
            return 'contract'
        elif 'intern' in text or 'стажер' in text or 'стажировка' in text:
            return 'internship'
        elif 'freelance' in text or 'фриланс' in text:
            return 'freelance'
        return ''
    
    def _extract_location(self, text: str) -> str:
        """Extract job location"""
        # Common cities
        cities = [
            'Yerevan', 'Moscow', 'London', 'Dubai', 'New York', 'San Francisco',
            'Los Angeles', 'Berlin', 'Paris', 'Toronto', 'Sydney', 'Singapore',
            'Ереван', 'Москва', 'Лондон', 'Дubай', 'Берлин', 'Париж'
        ]
        
        for city in cities:
            if city.lower() in text.lower():
                return city
        
        # Check for remote
        if 'remote' in text.lower() or 'удаленн' in text.lower():
            return 'Remote'
        
        return ''
    
    def _detect_red_flags(self, text: str) -> List[str]:
        """Detect red flags in job posting"""
        found = []
        for lang, flags in self.red_flags.items():
            for flag in flags:
                if flag in text:
                    found.append(flag)
        return found
    
    def _detect_culture_signals(self, text: str) -> List[str]:
        """Detect positive culture signals"""
        found = []
        for lang, signals in self.culture_signals.items():
            for signal in signals:
                if signal in text:
                    found.append(signal)
        return found
    
    def _parse_schedule(self, schedule_dict: Dict) -> ParsedSchedule:
        """Convert schedule dict to ParsedSchedule"""
        return ParsedSchedule(
            days=schedule_dict.get('days', []),
            start_time=schedule_dict.get('start_time', schedule_dict.get('start', '')),
            end_time=schedule_dict.get('end_time', schedule_dict.get('end', '')),
            is_flexible=schedule_dict.get('is_flexible', False),
            hours_per_week=self._calculate_weekly_hours(schedule_dict)
        )
    
    def _calculate_weekly_hours(self, schedule: Dict) -> int:
        """Calculate hours per week from schedule"""
        days = schedule.get('days', [])
        start = schedule.get('start_time', schedule.get('start', ''))
        end = schedule.get('end_time', schedule.get('end', ''))
        
        if not days or not start or not end:
            return 40  # Default
        
        try:
            start_hour = int(start.split(':')[0])
            end_hour = int(end.split(':')[0])
            hours_per_day = end_hour - start_hour
            return hours_per_day * len(days)
        except:
            return 40
    
    def _merge_extractions(self, llm_result: Dict, rule_result: Dict) -> Dict:
        """Merge LLM and rule-based extractions, preferring LLM where available"""
        merged = rule_result.copy()
        
        for key, value in llm_result.items():
            # LLM takes priority if it has a non-empty value
            if value and (isinstance(value, (str, int, float, bool)) or (isinstance(value, list) and len(value) > 0)):
                merged[key] = value
            elif isinstance(value, dict) and any(v for v in value.values()):
                merged[key] = value
        
        return merged


# Convenience function
async def analyze_job_posting(text: str, source: str = "manual") -> Dict[str, Any]:
    """Convenience function to analyze a job posting"""
    service = JobIntelligenceService()
    parsed = await service.analyze_job(text, source)
    return parsed.to_dict()
