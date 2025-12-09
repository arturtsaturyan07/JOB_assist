"""
Market Intelligence Module for TwinWork AI

Provides insights about the job market:
- Salary trends for different roles and locations
- In-demand skills
- Hiring seasons
- Career growth recommendations
- Employability score

Uses no external APIs - works with local data.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta


@dataclass
class SalaryData:
    """Salary information for a role"""
    role: str
    location: str
    min_salary: float = 0
    max_salary: float = 0
    median_salary: float = 0
    currency: str = "USD"
    period: str = "monthly"  # monthly, yearly, hourly


@dataclass
class MarketInsight:
    """Market insight data"""
    skill: str
    demand_level: str  # high, medium, low
    trend: str  # rising, stable, declining
    hiring_months: List[int] = field(default_factory=list)  # months where hiring peaks


@dataclass
class EmployabilityScore:
    """User employability assessment"""
    overall_score: float  # 0-100
    skill_match: float  # 0-100
    experience_match: float  # 0-100
    location_advantage: float  # 0-100
    language_advantage: float  # 0-100
    recommendations: List[str] = field(default_factory=list)


class MarketIntelligenceService:
    """
    Provides market intelligence without requiring external APIs.
    
    Works with:
    - Crowdsourced salary data (can be built from job postings)
    - Skill demand patterns (from job postings)
    - Seasonal hiring patterns
    """
    
    def __init__(self):
        # Base market data (in-memory, can be extended)
        self.skill_demand = self._init_skill_demand()
        self.salary_ranges = self._init_salary_ranges()
        self.hiring_seasons = self._init_hiring_seasons()
        self.cost_of_living = self._init_cost_of_living()
    
    def _init_skill_demand(self) -> Dict[str, MarketInsight]:
        """Initialize skill demand data"""
        skills = {
            'python': MarketInsight('Python', 'high', 'rising', [1,2,3,9,10]),
            'javascript': MarketInsight('JavaScript', 'high', 'stable', [1,2,3,9,10]),
            'typescript': MarketInsight('TypeScript', 'high', 'rising', [2,3,9,10]),
            'react': MarketInsight('React', 'high', 'rising', [1,2,3,9,10]),
            'aws': MarketInsight('AWS', 'high', 'rising', [1,2,9,10,11]),
            'docker': MarketInsight('Docker', 'medium', 'rising', [2,3,9,10]),
            'kubernetes': MarketInsight('Kubernetes', 'medium', 'rising', [2,3,9,10]),
            'sql': MarketInsight('SQL', 'high', 'stable', [1,2,3,9,10,11]),
            'java': MarketInsight('Java', 'high', 'stable', [1,2,3,9,10]),
            'golang': MarketInsight('Go', 'medium', 'rising', [2,3,9,10]),
            'rust': MarketInsight('Rust', 'medium', 'rising', [3,9,10]),
            'machine learning': MarketInsight('Machine Learning', 'high', 'rising', [1,2,3,9,10]),
            'data science': MarketInsight('Data Science', 'high', 'rising', [1,2,3,9,10]),
            'devops': MarketInsight('DevOps', 'high', 'rising', [2,3,9,10]),
            'leadership': MarketInsight('Leadership', 'high', 'stable', [1,2,9,10]),
            'communication': MarketInsight('Communication', 'high', 'stable', [1,2,3,9,10]),
        }
        return {k.lower(): v for k, v in skills.items()}
    
    def _init_salary_ranges(self) -> Dict[str, List[SalaryData]]:
        """Initialize salary range data by role and location"""
        return {
            'python developer': [
                SalaryData('Python Developer', 'Yerevan', 1500, 3000, 2200, 'AMD', 'monthly'),
                SalaryData('Python Developer', 'Remote', 2000, 5000, 3500, 'USD', 'monthly'),
                SalaryData('Python Developer', 'USA', 5000, 12000, 8500, 'USD', 'monthly'),
            ],
            'javascript developer': [
                SalaryData('JavaScript Developer', 'Yerevan', 1500, 3000, 2200, 'AMD', 'monthly'),
                SalaryData('JavaScript Developer', 'Remote', 2000, 5000, 3500, 'USD', 'monthly'),
                SalaryData('JavaScript Developer', 'USA', 5000, 12000, 8500, 'USD', 'monthly'),
            ],
            'data scientist': [
                SalaryData('Data Scientist', 'Yerevan', 2000, 4000, 3000, 'AMD', 'monthly'),
                SalaryData('Data Scientist', 'Remote', 3000, 7000, 5000, 'USD', 'monthly'),
                SalaryData('Data Scientist', 'USA', 7000, 15000, 11000, 'USD', 'monthly'),
            ],
            'devops engineer': [
                SalaryData('DevOps Engineer', 'Yerevan', 1800, 3500, 2600, 'AMD', 'monthly'),
                SalaryData('DevOps Engineer', 'Remote', 2500, 5500, 4000, 'USD', 'monthly'),
                SalaryData('DevOps Engineer', 'USA', 6000, 13000, 9500, 'USD', 'monthly'),
            ],
            'teacher': [
                SalaryData('Teacher', 'Yerevan', 300, 1200, 700, 'AMD', 'monthly'),
                SalaryData('Teacher', 'Remote', 500, 2000, 1200, 'USD', 'monthly'),
            ],
            'driver': [
                SalaryData('Driver', 'Yerevan', 400, 1500, 900, 'AMD', 'monthly'),
                SalaryData('Driver', 'USA', 2000, 4000, 3000, 'USD', 'monthly'),
            ]
        }
    
    def _init_hiring_seasons(self) -> Dict[str, List[int]]:
        """Initialize hiring season data (months)"""
        return {
            'tech': [1, 3, 9, 10],  # Jan, Mar, Sep, Oct
            'finance': [1, 2, 9, 10],  # Jan, Feb, Sep, Oct
            'sales': [1, 2, 9, 10],
            'education': [7, 8, 9],  # Jul, Aug, Sep
            'retail': [11, 12],  # Nov, Dec (holiday season)
            'general': [1, 9],  # Traditional hiring months
        }
    
    def _init_cost_of_living(self) -> Dict[str, float]:
        """Cost of living index by location (Yerevan = 100)"""
        return {
            'yerevan': 100,
            'moscow': 110,
            'london': 180,
            'new york': 200,
            'san francisco': 220,
            'los angeles': 180,
            'toronto': 150,
            'paris': 170,
            'berlin': 130,
            'sydney': 160,
            'tokyo': 150,
            'singapore': 140,
            'dubai': 120,
            'remote': 50,  # No location overhead
        }
    
    def get_salary_estimate(self, role: str, location: str) -> Optional[SalaryData]:
        """Get salary estimate for a role in a location"""
        role_lower = role.lower()
        
        # Try exact match
        if role_lower in self.salary_ranges:
            for salary_data in self.salary_ranges[role_lower]:
                if location.lower() in salary_data.location.lower():
                    return salary_data
            # Return first result if location doesn't match exactly
            return self.salary_ranges[role_lower][0]
        
        # Try partial match
        for role_key in self.salary_ranges.keys():
            if role_lower in role_key or role_key in role_lower:
                for salary_data in self.salary_ranges[role_key]:
                    if location.lower() in salary_data.location.lower():
                        return salary_data
                return self.salary_ranges[role_key][0]
        
        return None
    
    def get_skill_demand(self, skill: str) -> Optional[MarketInsight]:
        """Get market demand for a skill"""
        skill_lower = skill.lower()
        if skill_lower in self.skill_demand:
            return self.skill_demand[skill_lower]
        
        # Partial match
        for skill_key in self.skill_demand.keys():
            if skill_lower in skill_key or skill_key in skill_lower:
                return self.skill_demand[skill_key]
        
        return None
    
    def get_top_skills(self, field: str = 'tech', count: int = 5) -> List[MarketInsight]:
        """Get top in-demand skills for a field"""
        all_insights = list(self.skill_demand.values())
        
        # Filter by trend and demand
        high_demand = [s for s in all_insights if s.demand_level == 'high']
        high_demand.sort(key=lambda x: (x.trend == 'rising', x.skill))
        
        return high_demand[:count]
    
    def get_hiring_season(self, field: str = 'tech') -> List[int]:
        """Get peak hiring months for a field"""
        return self.hiring_seasons.get(field, self.hiring_seasons['general'])
    
    def is_hiring_season(self, field: str = 'tech', month: Optional[int] = None) -> bool:
        """Check if current/given month is hiring season"""
        if month is None:
            month = datetime.now().month
        
        season = self.get_hiring_season(field)
        return month in season
    
    def calculate_adjusted_salary(self, base_salary: float, from_location: str, to_location: str, 
                                 currency_from: str = 'USD', currency_to: str = 'USD') -> float:
        """
        Adjust salary based on cost of living differences.
        
        Example: What would a $5000/month salary in USA be in Armenia?
        """
        from_col = self.cost_of_living.get(from_location.lower(), 100)
        to_col = self.cost_of_living.get(to_location.lower(), 100)
        
        # Adjust for CoL difference
        adjusted = base_salary * (to_col / from_col)
        
        return adjusted
    
    def calculate_employability_score(self, 
                                     cv_skills: List[str],
                                     job_required_skills: List[str],
                                     experience_years: float,
                                     job_years_required: int,
                                     user_location: str,
                                     job_location: str,
                                     languages: List[str],
                                     job_languages: List[str]) -> EmployabilityScore:
        """
        Calculate employability score for a specific job.
        
        Returns score out of 100 with breakdown.
        """
        score = EmployabilityScore(0, 0, 0, 0, 0)
        recommendations = []
        
        # Skill match (40 points)
        if job_required_skills:
            cv_skills_lower = {s.lower() for s in cv_skills}
            job_skills_lower = {s.lower() for s in job_required_skills}
            matched = len(cv_skills_lower & job_skills_lower)
            skill_match = (matched / len(job_skills_lower)) * 100 if job_skills_lower else 0
            score.skill_match = min(100, skill_match)
        else:
            score.skill_match = 100
        
        # Experience match (30 points)
        if experience_years >= job_years_required:
            score.experience_match = 100
        else:
            years_short = job_years_required - experience_years
            score.experience_match = max(20, 100 - (years_short * 20))
            recommendations.append(f"You're {years_short:.1f} years short on experience")
        
        # Location advantage (15 points)
        if user_location.lower() == job_location.lower():
            score.location_advantage = 100
        elif user_location.lower() == 'remote' or job_location.lower() == 'remote':
            score.location_advantage = 90
        else:
            score.location_advantage = 50
            recommendations.append(f"Location mismatch: {user_location} vs {job_location}")
        
        # Language advantage (15 points)
        if job_languages:
            user_langs_lower = {l.lower() for l in languages}
            job_langs_lower = {l.lower() for l in job_languages}
            matched_langs = len(user_langs_lower & job_langs_lower)
            score.language_advantage = (matched_langs / len(job_langs_lower)) * 100 if job_langs_lower else 50
        else:
            score.language_advantage = 100
        
        # Calculate weighted overall score
        score.overall_score = (
            score.skill_match * 0.40 +
            score.experience_match * 0.30 +
            score.location_advantage * 0.15 +
            score.language_advantage * 0.15
        )
        
        score.recommendations = recommendations
        
        return score
    
    def get_career_recommendations(self, 
                                 current_role: str,
                                 current_skills: List[str],
                                 experience_years: float,
                                 interests: List[str]) -> List[str]:
        """Get recommendations to increase employability"""
        recommendations = []
        
        # Skill recommendations
        top_skills = self.get_top_skills('tech', 10)
        missing_top_skills = [s.skill for s in top_skills 
                             if s.skill.lower() not in [sk.lower() for sk in current_skills]]
        
        if missing_top_skills:
            recommendations.append(f"Learn these in-demand skills: {', '.join(missing_top_skills[:3])}")
        
        # Experience recommendations
        if experience_years < 2:
            recommendations.append("Build more work experience - junior roles are competitive")
            recommendations.append("Consider internships or entry-level positions to gain experience")
        elif experience_years < 5:
            recommendations.append("You're at mid-level - target mid-level positions for better salaries")
        
        # General recommendations
        recommendations.append("Build a strong portfolio on GitHub to showcase your skills")
        recommendations.append("Get relevant certifications to stand out")
        recommendations.append("Network with professionals in your field")
        
        return recommendations
    
    def analyze_job_market(self, skill: str, location: str = 'Remote') -> Dict[str, Any]:
        """Get comprehensive market analysis for a skill/location combo"""
        skill_insight = self.get_skill_demand(skill)
        salary = self.get_salary_estimate(skill, location)
        
        return {
            'skill': skill,
            'location': location,
            'demand': skill_insight.demand_level if skill_insight else 'unknown',
            'trend': skill_insight.trend if skill_insight else 'unknown',
            'peak_hiring_months': skill_insight.hiring_months if skill_insight else [],
            'current_month_hiring': self.is_hiring_season('tech'),
            'salary': salary.to_dict() if salary else None,
            'recommendations': [
                f"Demand is {skill_insight.demand_level}" if skill_insight else "Skill data not available",
                f"Hiring peaks in months: {','.join(map(str, skill_insight.hiring_months))}" if skill_insight else "",
            ]
        }
