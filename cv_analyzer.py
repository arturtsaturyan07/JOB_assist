"""
CV Analysis Module for TwinWork AI

Extracts skills, experience, and career information from CVs.
Supports multiple formats: text, PDF (via text extraction)

Features:
- Extract skills from CV text
- Parse work experience timeline
- Detect missing skills for job matching
- Suggest improvements
- Calculate experience level
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class WorkExperience:
    """A work experience entry"""
    title: str = ""
    company: str = ""
    start_date: str = ""  # YYYY-MM or YYYY
    end_date: str = ""    # YYYY-MM or YYYY or "Present"
    description: str = ""
    skills: List[str] = field(default_factory=list)
    
    def duration_years(self) -> float:
        """Calculate duration in years"""
        try:
            start_parts = self.start_date.split('-')
            end_parts = self.end_date.replace('Present', str(datetime.now().year)).split('-')
            
            start_year = int(start_parts[0])
            end_year = int(end_parts[0])
            
            start_month = int(start_parts[1]) if len(start_parts) > 1 else 1
            end_month = int(end_parts[1]) if len(end_parts) > 1 else 12
            
            return (end_year - start_year) + (end_month - start_month) / 12.0
        except:
            return 0.0


@dataclass
class CVData:
    """Extracted CV information"""
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""
    
    skills: List[str] = field(default_factory=list)
    technical_skills: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    
    work_experience: List[WorkExperience] = field(default_factory=list)
    education: List[Dict[str, str]] = field(default_factory=list)  # degree, institution, year
    
    certifications: List[str] = field(default_factory=list)
    
    total_experience_years: float = 0.0
    experience_level: str = ""  # junior, mid, senior, lead
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['work_experience'] = [asdict(w) for w in self.work_experience]
        return data


class CVAnalyzer:
    """
    Extracts structured data from CVs without requiring paid APIs.
    
    Supports:
    - Text pasting (plain text CV)
    - LinkedIn profile text
    - Job posting text (for comparison)
    """
    
    # Common technical skills by category
    TECHNICAL_SKILLS = {
        'languages': {
            'programming': ['python', 'javascript', 'java', 'c++', 'c#', 'go', 'rust', 
                          'ruby', 'php', 'swift', 'kotlin', 'scala', 'typescript'],
            'web': ['html', 'css', 'react', 'angular', 'vue', 'node', 'express', 'django'],
            'data': ['sql', 'pandas', 'spark', 'hadoop', 'tensorflow', 'pytorch', 'r'],
            'devops': ['docker', 'kubernetes', 'aws', 'azure', 'terraform', 'jenkins'],
        },
        'frameworks': {
            'frontend': ['react', 'angular', 'vue', 'svelte', 'next.js', 'gatsby'],
            'backend': ['django', 'flask', 'fastapi', 'spring', 'rails', 'express'],
            'mobile': ['react native', 'flutter', 'ios', 'android'],
        },
        'tools': ['git', 'docker', 'kubernetes', 'jenkins', 'gitlab', 'github', 'jira', 'slack'],
        'databases': ['postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch'],
    }
    
    # Common job titles to extract experience
    JOB_TITLES = {
        'junior': ['junior', 'intern', 'entry level', 'associate'],
        'mid': ['mid-level', 'mid level', 'senior', 'lead'],
        'senior': ['senior', 'principal', 'staff', 'architect'],
        'lead': ['lead', 'head', 'manager', 'director', 'vp'],
    }
    
    # Language keywords
    LANGUAGES = {
        'english': ['english', 'native', 'fluent', 'c1', 'c2'],
        'russian': ['russian', 'русский'],
        'armenian': ['armenian', 'հայերեն'],
        'spanish': ['spanish', 'español'],
        'french': ['french', 'français'],
        'german': ['german', 'deutsch'],
        'chinese': ['chinese', 'mandarin'],
        'arabic': ['arabic'],
    }
    
    def __init__(self):
        pass
    
    def analyze_cv(self, cv_text: str) -> CVData:
        """
        Analyze CV text and extract structured data.
        
        Args:
            cv_text: Plain text CV content
            
        Returns:
            CVData with extracted information
        """
        cv_data = CVData()
        
        # Extract contact info
        cv_data.email = self._extract_email(cv_text)
        cv_data.phone = self._extract_phone(cv_text)
        cv_data.name = self._extract_name(cv_text)
        cv_data.location = self._extract_location(cv_text)
        cv_data.summary = self._extract_summary(cv_text)
        
        # Extract skills
        cv_data.skills = self._extract_skills(cv_text)
        cv_data.technical_skills = self._extract_technical_skills(cv_text)
        cv_data.languages = self._extract_languages(cv_text)
        
        # Extract work experience
        cv_data.work_experience = self._extract_work_experience(cv_text)
        
        # Extract education
        cv_data.education = self._extract_education(cv_text)
        
        # Extract certifications
        cv_data.certifications = self._extract_certifications(cv_text)
        
        # Calculate experience level
        cv_data.total_experience_years = sum(
            exp.duration_years() for exp in cv_data.work_experience
        )
        cv_data.experience_level = self._calculate_experience_level(cv_data.total_experience_years)
        
        return cv_data
    
    def _extract_email(self, text: str) -> str:
        """Extract email address"""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(pattern, text)
        return match.group(0) if match else ""
    
    def _extract_phone(self, text: str) -> str:
        """Extract phone number"""
        patterns = [
            r'\+\d{1,3}[-.\s]?\d{1,14}',  # International format
            r'\(\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4}',  # US format
            r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',  # Standard format
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return ""
    
    def _extract_name(self, text: str) -> str:
        """Extract person's name (usually at top of CV)"""
        lines = text.split('\n')
        # First non-empty line is usually the name
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line and len(line) < 100 and not any(c in line for c in ['@', '.com', '(']):
                return line
        return ""
    
    def _extract_location(self, text: str) -> str:
        """Extract location"""
        text_lower = text.lower()
        locations = [
            'yerevan', 'moscow', 'london', 'new york', 'san francisco', 'los angeles',
            'toronto', 'paris', 'berlin', 'sydney', 'tokyo', 'singapore',
            'dubai', 'chicago', 'remote', 'armenia', 'usa', 'uk', 'canada', 'australia'
        ]
        for loc in locations:
            if loc in text_lower:
                return loc.capitalize()
        return ""
    
    def _extract_summary(self, text: str) -> str:
        """Extract professional summary if present"""
        # Look for summary section
        summary_patterns = [
            r'(?:professional summary|summary|objective)(.*?)(?:experience|skills|education)',
            r'(?:about|about me)(.*?)(?:experience|skills|education)',
        ]
        for pattern in summary_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                summary = match.group(1).strip()
                return ' '.join(summary.split())[:200]  # First 200 chars
        return ""
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract soft skills"""
        soft_skills = [
            'leadership', 'communication', 'teamwork', 'problem solving',
            'project management', 'critical thinking', 'time management',
            'creativity', 'adaptability', 'analytical', 'strategic thinking',
            'negotiation', 'presentation', 'public speaking'
        ]
        
        text_lower = text.lower()
        found_skills = []
        for skill in soft_skills:
            if skill in text_lower:
                found_skills.append(skill.title())
        
        return found_skills
    
    def _extract_technical_skills(self, text: str) -> List[str]:
        """Extract technical skills"""
        text_lower = text.lower()
        found_skills = set()
        
        for category, skills_list in self.TECHNICAL_SKILLS['languages'].items():
            for skill in skills_list:
                if skill in text_lower:
                    found_skills.add(skill.title())
        
        for category, skills_list in self.TECHNICAL_SKILLS['frameworks'].items():
            for skill in skills_list:
                if skill.lower() in text_lower:
                    found_skills.add(skill.title())
        
        for skill in self.TECHNICAL_SKILLS['tools']:
            if skill in text_lower:
                found_skills.add(skill.title())
        
        for skill in self.TECHNICAL_SKILLS['databases']:
            if skill in text_lower:
                found_skills.add(skill.title())
        
        return list(found_skills)
    
    def _extract_languages(self, text: str) -> List[str]:
        """Extract spoken languages"""
        text_lower = text.lower()
        found_languages = []
        
        for lang, keywords in self.LANGUAGES.items():
            for keyword in keywords:
                if keyword in text_lower:
                    found_languages.append(lang.title())
                    break
        
        return found_languages
    
    def _extract_work_experience(self, text: str) -> List[WorkExperience]:
        """Extract work experience entries"""
        experiences = []
        
        # Look for experience section
        exp_match = re.search(
            r'(?:experience|work history|employment)(.*?)(?:education|skills|certifications|$)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if not exp_match:
            return []
        
        exp_section = exp_match.group(1)
        
        # Split by common delimiters
        entries = re.split(r'\n\n+', exp_section)
        
        for entry in entries:
            if not entry.strip():
                continue
            
            exp = WorkExperience()
            lines = entry.strip().split('\n')
            
            # First line usually has title and company
            first_line = lines[0].strip()
            
            # Try to extract title and company
            if '|' in first_line:
                parts = first_line.split('|')
                exp.title = parts[0].strip()
                exp.company = parts[1].strip()
            elif '-' in first_line and len(first_line) > 10:
                parts = first_line.split('-')
                exp.title = parts[0].strip()
                exp.company = parts[1].strip()
            else:
                exp.title = first_line
            
            # Look for dates
            dates_match = re.search(
                r'(\d{4}(?:-\d{2})?)\s*(?:to|-|–|until)\s*(\d{4}(?:-\d{2})?|present|current)',
                entry,
                re.IGNORECASE
            )
            if dates_match:
                exp.start_date = dates_match.group(1)
                exp.end_date = dates_match.group(2).capitalize()
            
            # Description is rest of the entry
            exp.description = '\n'.join(lines[1:]).strip()
            
            # Extract skills mentioned in this entry
            exp.skills = self._extract_technical_skills(entry)
            
            experiences.append(exp)
        
        return experiences
    
    def _extract_education(self, text: str) -> List[Dict[str, str]]:
        """Extract education entries"""
        education = []
        
        # Look for education section
        edu_match = re.search(
            r'(?:education|academic)(.*?)(?:experience|skills|certifications|$)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if not edu_match:
            return []
        
        edu_section = edu_match.group(1)
        entries = re.split(r'\n\n+', edu_section)
        
        for entry in entries:
            if not entry.strip():
                continue
            
            # Extract degree (Bachelor, Master, PhD, etc.)
            degree_match = re.search(
                r"(bachelor|master|phd|associate|diploma|certificate)'?s?\s+(?:degree\s+)?(?:in\s+)?([^,\n]*)",
                entry,
                re.IGNORECASE
            )
            
            if degree_match:
                degree = degree_match.group(1).title()
                field = degree_match.group(2).strip()
                
                # Extract year
                year_match = re.search(r'\b(\d{4})\b', entry)
                year = year_match.group(1) if year_match else ""
                
                education.append({
                    'degree': degree,
                    'field': field,
                    'year': year,
                    'institution': entry.split('\n')[0].strip()
                })
        
        return education
    
    def _extract_certifications(self, text: str) -> List[str]:
        """Extract certifications"""
        certs = []
        
        # Look for certifications section
        cert_match = re.search(
            r'(?:certifications?|licenses?|credentials?)(.*?)(?:education|experience|skills|$)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if not cert_match:
            return []
        
        cert_section = cert_match.group(1)
        
        # Split lines and extract cert names
        lines = cert_section.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) < 100:
                # Remove bullet points and dashes
                cert = re.sub(r'^[-•*]\s*', '', line)
                if cert:
                    certs.append(cert)
        
        return certs
    
    def _calculate_experience_level(self, years: float) -> str:
        """Calculate experience level based on years"""
        if years < 2:
            return "junior"
        elif years < 5:
            return "mid"
        elif years < 10:
            return "senior"
        else:
            return "lead"
    
    def find_missing_skills(self, cv_data: CVData, job_required_skills: List[str]) -> Dict[str, List[str]]:
        """
        Compare CV skills with job requirements.
        
        Returns:
            {
                'missing': skills not in CV,
                'have': skills in CV,
                'similar': skills that might match despite different names
            }
        """
        cv_all_skills = set(cv_data.skills + cv_data.technical_skills)
        cv_all_skills_lower = {s.lower() for s in cv_all_skills}
        
        job_skills_lower = {s.lower() for s in job_required_skills}
        
        have = [s for s in job_required_skills if s.lower() in cv_all_skills_lower]
        missing = [s for s in job_required_skills if s.lower() not in cv_all_skills_lower]
        
        return {
            'missing': missing,
            'have': have,
            'match_percentage': len(have) / len(job_required_skills) * 100 if job_required_skills else 0
        }
    
    def suggest_improvements(self, cv_data: CVData) -> List[str]:
        """Suggest CV improvements"""
        suggestions = []
        
        if not cv_data.name:
            suggestions.append("Add your name at the top of your CV")
        
        if not cv_data.email:
            suggestions.append("Add your email address")
        
        if not cv_data.phone:
            suggestions.append("Add your phone number")
        
        if not cv_data.location:
            suggestions.append("Add your location")
        
        if not cv_data.summary:
            suggestions.append("Add a professional summary")
        
        if not cv_data.work_experience:
            suggestions.append("Add your work experience")
        
        if not cv_data.education:
            suggestions.append("Add your education")
        
        if len(cv_data.technical_skills) < 5:
            suggestions.append("Add more technical skills")
        
        if not cv_data.languages:
            suggestions.append("List the languages you speak")
        
        if not cv_data.certifications:
            suggestions.append("Add any relevant certifications or licenses")
        
        return suggestions
