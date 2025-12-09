"""
CV Analysis Service for TwinWork AI

Provides CV/resume analysis:
- Extract skills from CV
- Extract experience timeline
- Match CV to jobs
- Suggest improvements
- Identify skill gaps
"""

import os
import re
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

from multi_model_service import MultiModelService, TaskType
from embedding_service import EmbeddingService, get_embedding_service
from models import Job


@dataclass
class Experience:
    """Work experience entry"""
    title: str
    company: str
    start_date: str
    end_date: str  # or "Present"
    description: str
    skills_used: List[str] = field(default_factory=list)


@dataclass
class Education:
    """Education entry"""
    degree: str
    institution: str
    field_of_study: str
    graduation_year: str


@dataclass
class CVData:
    """Extracted CV data"""
    raw_text: str
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""
    
    skills: List[str] = field(default_factory=list)
    experience: List[Experience] = field(default_factory=list)
    education: List[Education] = field(default_factory=list)
    
    languages: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    
    total_experience_years: float = 0.0
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['experience'] = [asdict(e) for e in self.experience]
        data['education'] = [asdict(e) for e in self.education]
        return data


@dataclass
class CVMatch:
    """CV match result for a job"""
    job_id: str
    job_title: str
    overall_score: float
    skill_match_score: float
    experience_match_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    recommendations: List[str]


class CVService:
    """
    CV analysis and matching service.
    
    Supports:
    - Text extraction from pasted CV
    - Skill extraction
    - Experience parsing
    - Job matching
    - Improvement suggestions
    """
    
    def __init__(self):
        self.llm = MultiModelService()
        self.embeddings = get_embedding_service()
        
        # Common skills to look for
        self.skill_categories = {
            'programming': [
                'python', 'javascript', 'java', 'c++', 'c#', 'go', 'rust',
                'ruby', 'php', 'swift', 'kotlin', 'scala', 'typescript'
            ],
            'web': [
                'html', 'css', 'react', 'angular', 'vue', 'node.js',
                'django', 'flask', 'fastapi', 'express', 'next.js'
            ],
            'data': [
                'sql', 'postgresql', 'mysql', 'mongodb', 'redis',
                'pandas', 'numpy', 'tensorflow', 'pytorch', 'spark'
            ],
            'cloud': [
                'aws', 'azure', 'gcp', 'docker', 'kubernetes',
                'terraform', 'ansible', 'jenkins', 'ci/cd'
            ],
            'soft': [
                'leadership', 'communication', 'teamwork', 'problem-solving',
                'project management', 'agile', 'scrum'
            ]
        }
    
    async def parse_cv(self, cv_text: str) -> CVData:
        """
        Parse CV text and extract structured data.
        
        Args:
            cv_text: Raw CV text (pasted or extracted from file)
        
        Returns:
            CVData with extracted information
        """
        print("📄 Parsing CV...")
        
        # Try LLM extraction first
        try:
            llm_result = await self._llm_parse(cv_text)
        except Exception as e:
            print(f"⚠️ LLM CV parsing failed: {e}")
            llm_result = {}
        
        # Always do rule-based as backup
        rule_result = self._rule_based_parse(cv_text)
        
        # Merge results
        merged = self._merge_results(llm_result, rule_result)
        
        # Create CVData
        cv_data = CVData(
            raw_text=cv_text,
            name=merged.get('name', ''),
            email=merged.get('email', ''),
            phone=merged.get('phone', ''),
            location=merged.get('location', ''),
            summary=merged.get('summary', ''),
            skills=merged.get('skills', []),
            experience=self._parse_experience(merged.get('experience', [])),
            education=self._parse_education(merged.get('education', [])),
            languages=merged.get('languages', []),
            certifications=merged.get('certifications', []),
            total_experience_years=merged.get('total_experience_years', 0.0)
        )
        
        print(f"✅ CV parsed: {len(cv_data.skills)} skills, {len(cv_data.experience)} positions")
        
        return cv_data
    
    async def _llm_parse(self, cv_text: str) -> Dict[str, Any]:
        """Use LLM to parse CV"""
        system_prompt = """You are an expert CV parser. Extract ALL information from this CV/resume.
        
        Return valid JSON with these fields:
        {
            "name": "Full name",
            "email": "email@example.com",
            "phone": "+1234567890",
            "location": "City, Country",
            "summary": "Professional summary if present",
            "skills": ["skill1", "skill2", ...],
            "experience": [
                {
                    "title": "Job Title",
                    "company": "Company Name",
                    "start_date": "Jan 2020",
                    "end_date": "Present",
                    "description": "Brief description",
                    "skills_used": ["skill1"]
                }
            ],
            "education": [
                {
                    "degree": "Bachelor's/Master's/etc",
                    "institution": "University Name",
                    "field_of_study": "Computer Science",
                    "graduation_year": "2020"
                }
            ],
            "languages": ["English", "Russian", "Armenian"],
            "certifications": ["AWS Certified", "PMP"],
            "total_experience_years": 5.0
        }
        
        Important:
        - Extract ALL skills mentioned, including from job descriptions
        - Calculate total experience years from employment history
        - If info is not present, use empty string/array
        """
        
        result = await self.llm.process(
            TaskType.CV_ANALYSIS,
            cv_text[:4000],  # Limit length
            system_prompt
        )
        
        return result
    
    def _rule_based_parse(self, text: str) -> Dict[str, Any]:
        """Rule-based CV parsing"""
        result = {}
        text_lower = text.lower()
        
        # Email extraction
        email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
        if email_match:
            result['email'] = email_match.group(0)
        
        # Phone extraction
        phone_match = re.search(r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}', text)
        if phone_match:
            result['phone'] = phone_match.group(0)
        
        # Name extraction (usually first line or after "Name:")
        lines = text.strip().split('\n')
        if lines:
            first_line = lines[0].strip()
            # Check if it looks like a name (2-4 words, capitalized)
            words = first_line.split()
            if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
                result['name'] = first_line
        
        # Skills extraction
        skills = []
        for category, skill_list in self.skill_categories.items():
            for skill in skill_list:
                if re.search(rf'\b{re.escape(skill)}\b', text_lower):
                    skills.append(skill.title())
        result['skills'] = list(set(skills))
        
        # Experience years extraction
        exp_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?experience', text_lower)
        if exp_match:
            result['total_experience_years'] = float(exp_match.group(1))
        
        # Languages
        languages = []
        lang_keywords = ['english', 'russian', 'armenian', 'french', 'german', 'spanish', 'chinese']
        for lang in lang_keywords:
            if lang in text_lower:
                languages.append(lang.title())
        result['languages'] = languages
        
        return result
    
    def _merge_results(self, llm_result: Dict, rule_result: Dict) -> Dict:
        """Merge LLM and rule-based results"""
        merged = rule_result.copy()
        
        for key, value in llm_result.items():
            if value and (isinstance(value, (str, int, float)) or (isinstance(value, list) and len(value) > 0)):
                merged[key] = value
        
        # Combine skills from both
        if 'skills' in llm_result and 'skills' in rule_result:
            combined_skills = list(set(llm_result['skills'] + rule_result['skills']))
            merged['skills'] = combined_skills
        
        return merged
    
    def _parse_experience(self, exp_list: List) -> List[Experience]:
        """Parse experience list into Experience objects"""
        experiences = []
        for exp in exp_list:
            if isinstance(exp, dict):
                experiences.append(Experience(
                    title=exp.get('title', ''),
                    company=exp.get('company', ''),
                    start_date=exp.get('start_date', ''),
                    end_date=exp.get('end_date', ''),
                    description=exp.get('description', ''),
                    skills_used=exp.get('skills_used', [])
                ))
        return experiences
    
    def _parse_education(self, edu_list: List) -> List[Education]:
        """Parse education list into Education objects"""
        educations = []
        for edu in edu_list:
            if isinstance(edu, dict):
                educations.append(Education(
                    degree=edu.get('degree', ''),
                    institution=edu.get('institution', ''),
                    field_of_study=edu.get('field_of_study', ''),
                    graduation_year=edu.get('graduation_year', '')
                ))
        return educations
    
    def match_to_jobs(self, cv: CVData, jobs: List[Job], top_k: int = 5) -> List[CVMatch]:
        """
        Match CV to jobs and return top matches.
        
        Args:
            cv: Parsed CV data
            jobs: List of jobs to match against
            top_k: Number of top matches to return
        
        Returns:
            List of CVMatch objects sorted by score
        """
        matches = []
        
        for job in jobs:
            # Skill matching
            skill_match = self.embeddings.match_skills(cv.skills, list(job.required_skills))
            missing_skills = self.embeddings.get_skill_gap(cv.skills, list(job.required_skills))
            
            # Experience matching (simple: check if cv has enough years)
            # This is a simplified version
            exp_match_score = min(1.0, cv.total_experience_years / 3.0) if cv.total_experience_years else 0.5
            
            # Overall score
            overall_score = skill_match.score * 0.6 + exp_match_score * 0.4
            
            # Generate recommendations
            recommendations = []
            if missing_skills:
                recommendations.append(f"Consider learning: {', '.join(missing_skills[:3])}")
            if cv.total_experience_years < 2:
                recommendations.append("Build experience through internships or personal projects")
            
            matches.append(CVMatch(
                job_id=job.job_id,
                job_title=job.title,
                overall_score=overall_score,
                skill_match_score=skill_match.score,
                experience_match_score=exp_match_score,
                matched_skills=skill_match.matched_items,
                missing_skills=missing_skills,
                recommendations=recommendations
            ))
        
        # Sort by overall score
        matches.sort(key=lambda m: m.overall_score, reverse=True)
        
        return matches[:top_k]
    
    async def suggest_improvements(self, cv: CVData, target_role: str = "") -> List[str]:
        """
        Suggest improvements for the CV.
        
        Args:
            cv: Parsed CV data
            target_role: Optional target role for specific suggestions
        
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Check for missing critical sections
        if not cv.summary:
            suggestions.append("📝 Add a professional summary at the top of your CV")
        
        if len(cv.skills) < 5:
            suggestions.append("🎯 Add more specific technical skills - aim for at least 10-15")
        
        if not cv.experience:
            suggestions.append("💼 Add your work experience section with dates and descriptions")
        
        if not cv.education:
            suggestions.append("🎓 Add your education details")
        
        if not cv.languages:
            suggestions.append("🌐 Mention your language skills (especially English, Russian, Armenian)")
        
        # Target role specific suggestions
        if target_role:
            role_lower = target_role.lower()
            
            if 'developer' in role_lower or 'engineer' in role_lower:
                tech_skills = ['python', 'javascript', 'git', 'sql']
                missing_tech = [s for s in tech_skills if s not in [sk.lower() for sk in cv.skills]]
                if missing_tech:
                    suggestions.append(f"💻 For {target_role} roles, consider adding: {', '.join(missing_tech)}")
            
            if 'senior' in role_lower:
                if cv.total_experience_years < 5:
                    suggestions.append("⏳ Senior roles typically require 5+ years of experience")
                suggestions.append("👥 Highlight leadership and mentoring experience")
        
        # General improvements
        if len(cv.skills) > 0:
            # Check for trending skills
            trending = ['docker', 'kubernetes', 'aws', 'react', 'python']
            missing_trending = [s for s in trending if s not in [sk.lower() for sk in cv.skills]]
            if missing_trending:
                suggestions.append(f"📈 High-demand skills to consider: {', '.join(missing_trending[:3])}")
        
        # LLM-based suggestions
        try:
            llm_suggestions = await self._get_llm_suggestions(cv, target_role)
            suggestions.extend(llm_suggestions)
        except:
            pass
        
        return suggestions[:10]  # Limit to 10 suggestions
    
    async def _get_llm_suggestions(self, cv: CVData, target_role: str) -> List[str]:
        """Get LLM-powered improvement suggestions"""
        prompt = f"""Analyze this CV and provide 3 specific improvement suggestions.

CV Summary:
- Skills: {', '.join(cv.skills[:15])}
- Experience: {cv.total_experience_years} years
- Education: {[e.degree for e in cv.education]}
{"- Target role: " + target_role if target_role else ""}

Return JSON:
{{"suggestions": ["suggestion 1", "suggestion 2", "suggestion 3"]}}
"""
        
        result = await self.llm.process(TaskType.CV_ANALYSIS, prompt)
        return result.get('suggestions', [])
    
    def get_skill_summary(self, cv: CVData) -> Dict[str, List[str]]:
        """Categorize CV skills by type"""
        summary = {
            'programming': [],
            'web': [],
            'data': [],
            'cloud': [],
            'soft': [],
            'other': []
        }
        
        cv_skills_lower = [s.lower() for s in cv.skills]
        
        for skill in cv.skills:
            skill_lower = skill.lower()
            categorized = False
            
            for category, category_skills in self.skill_categories.items():
                if skill_lower in category_skills:
                    summary[category].append(skill)
                    categorized = True
                    break
            
            if not categorized:
                summary['other'].append(skill)
        
        return summary


# Convenience function
async def analyze_cv(cv_text: str) -> Dict[str, Any]:
    """Analyze a CV and return structured data"""
    service = CVService()
    cv_data = await service.parse_cv(cv_text)
    suggestions = await service.suggest_improvements(cv_data)
    
    return {
        'cv_data': cv_data.to_dict(),
        'suggestions': suggestions,
        'skill_summary': service.get_skill_summary(cv_data)
    }
