"""
Market Intelligence Service for TwinWork AI

Provides market insights:
- Salary trends by role and location
- In-demand skills in Armenia
- Hiring seasons and patterns
- Career recommendations
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class SalaryData:
    """Salary information for a role"""
    role: str
    location: str
    currency: str
    min_salary: float
    max_salary: float
    median_salary: float
    period: str = "monthly"  # hourly, monthly, yearly
    sample_size: int = 0
    last_updated: str = ""


@dataclass
class SkillDemand:
    """Demand data for a skill"""
    skill: str
    demand_score: float  # 0-100
    growth_trend: str  # rising, stable, declining
    avg_salary_premium: float  # percentage increase
    related_roles: List[str] = field(default_factory=list)


class MarketIntelligence:
    """
    Market intelligence for the Armenian job market.
    
    Note: This uses curated data based on market research.
    In production, this would be updated from job posting analysis.
    """
    
    def __init__(self):
        # Armenian tech salary data (in AMD per month, updated for 2024)
        # Source: Market research, job postings analysis
        self.salary_data = {
            'armenia': {
                'software developer': SalaryData(
                    role='Software Developer',
                    location='Armenia',
                    currency='AMD',
                    min_salary=400000,
                    max_salary=1200000,
                    median_salary=700000,
                    period='monthly',
                    sample_size=500
                ),
                'senior software developer': SalaryData(
                    role='Senior Software Developer',
                    location='Armenia',
                    currency='AMD',
                    min_salary=800000,
                    max_salary=2000000,
                    median_salary=1200000,
                    period='monthly',
                    sample_size=200
                ),
                'python developer': SalaryData(
                    role='Python Developer',
                    location='Armenia',
                    currency='AMD',
                    min_salary=500000,
                    max_salary=1500000,
                    median_salary=850000,
                    period='monthly',
                    sample_size=150
                ),
                'frontend developer': SalaryData(
                    role='Frontend Developer',
                    location='Armenia',
                    currency='AMD',
                    min_salary=400000,
                    max_salary=1100000,
                    median_salary=650000,
                    period='monthly',
                    sample_size=180
                ),
                'data scientist': SalaryData(
                    role='Data Scientist',
                    location='Armenia',
                    currency='AMD',
                    min_salary=600000,
                    max_salary=1800000,
                    median_salary=1000000,
                    period='monthly',
                    sample_size=80
                ),
                'devops engineer': SalaryData(
                    role='DevOps Engineer',
                    location='Armenia',
                    currency='AMD',
                    min_salary=600000,
                    max_salary=1600000,
                    median_salary=950000,
                    period='monthly',
                    sample_size=100
                ),
                'qa engineer': SalaryData(
                    role='QA Engineer',
                    location='Armenia',
                    currency='AMD',
                    min_salary=300000,
                    max_salary=900000,
                    median_salary=550000,
                    period='monthly',
                    sample_size=120
                ),
                'product manager': SalaryData(
                    role='Product Manager',
                    location='Armenia',
                    currency='AMD',
                    min_salary=600000,
                    max_salary=1500000,
                    median_salary=900000,
                    period='monthly',
                    sample_size=60
                ),
                'ui/ux designer': SalaryData(
                    role='UI/UX Designer',
                    location='Armenia',
                    currency='AMD',
                    min_salary=350000,
                    max_salary=1000000,
                    median_salary=600000,
                    period='monthly',
                    sample_size=80
                ),
                'english teacher': SalaryData(
                    role='English Teacher',
                    location='Armenia',
                    currency='AMD',
                    min_salary=150000,
                    max_salary=500000,
                    median_salary=280000,
                    period='monthly',
                    sample_size=200
                ),
                'marketing manager': SalaryData(
                    role='Marketing Manager',
                    location='Armenia',
                    currency='AMD',
                    min_salary=400000,
                    max_salary=1000000,
                    median_salary=600000,
                    period='monthly',
                    sample_size=90
                ),
            }
        }
        
        # Skill demand data for Armenia
        self.skill_demand = {
            'python': SkillDemand(
                skill='Python',
                demand_score=95,
                growth_trend='rising',
                avg_salary_premium=15,
                related_roles=['Backend Developer', 'Data Scientist', 'ML Engineer']
            ),
            'javascript': SkillDemand(
                skill='JavaScript',
                demand_score=90,
                growth_trend='stable',
                avg_salary_premium=10,
                related_roles=['Frontend Developer', 'Full Stack Developer']
            ),
            'react': SkillDemand(
                skill='React',
                demand_score=88,
                growth_trend='rising',
                avg_salary_premium=12,
                related_roles=['Frontend Developer', 'Full Stack Developer']
            ),
            'typescript': SkillDemand(
                skill='TypeScript',
                demand_score=85,
                growth_trend='rising',
                avg_salary_premium=15,
                related_roles=['Frontend Developer', 'Full Stack Developer']
            ),
            'aws': SkillDemand(
                skill='AWS',
                demand_score=80,
                growth_trend='rising',
                avg_salary_premium=20,
                related_roles=['DevOps Engineer', 'Cloud Architect']
            ),
            'docker': SkillDemand(
                skill='Docker',
                demand_score=82,
                growth_trend='stable',
                avg_salary_premium=12,
                related_roles=['DevOps Engineer', 'Backend Developer']
            ),
            'kubernetes': SkillDemand(
                skill='Kubernetes',
                demand_score=75,
                growth_trend='rising',
                avg_salary_premium=18,
                related_roles=['DevOps Engineer', 'Cloud Architect']
            ),
            'sql': SkillDemand(
                skill='SQL',
                demand_score=85,
                growth_trend='stable',
                avg_salary_premium=8,
                related_roles=['Backend Developer', 'Data Analyst', 'DBA']
            ),
            'machine learning': SkillDemand(
                skill='Machine Learning',
                demand_score=70,
                growth_trend='rising',
                avg_salary_premium=25,
                related_roles=['ML Engineer', 'Data Scientist']
            ),
            'english': SkillDemand(
                skill='English',
                demand_score=95,
                growth_trend='stable',
                avg_salary_premium=20,
                related_roles=['All international roles']
            ),
        }
        
        # Hiring patterns
        self.hiring_seasons = {
            'high': ['September', 'October', 'January', 'February'],
            'medium': ['March', 'April', 'May', 'November'],
            'low': ['June', 'July', 'August', 'December']
        }
        
        # Top hiring companies in Armenia (tech)
        self.top_employers = [
            {'name': 'ServiceTitan', 'industry': 'Tech', 'size': 'Large', 'hires_per_year': 200},
            {'name': 'PicsArt', 'industry': 'Tech', 'size': 'Large', 'hires_per_year': 150},
            {'name': 'Synopsys', 'industry': 'Tech', 'size': 'Large', 'hires_per_year': 100},
            {'name': 'Krisp', 'industry': 'Tech', 'size': 'Medium', 'hires_per_year': 80},
            {'name': 'EPAM', 'industry': 'Tech', 'size': 'Large', 'hires_per_year': 150},
            {'name': 'DataArt', 'industry': 'Tech', 'size': 'Medium', 'hires_per_year': 60},
            {'name': 'Digitain', 'industry': 'Gaming', 'size': 'Large', 'hires_per_year': 100},
            {'name': 'BetConstruct', 'industry': 'Gaming', 'size': 'Large', 'hires_per_year': 120},
            {'name': 'SoftConstruct', 'industry': 'Gaming', 'size': 'Large', 'hires_per_year': 100},
            {'name': 'Renderforest', 'industry': 'Tech', 'size': 'Medium', 'hires_per_year': 50},
        ]
    
    def get_salary_trends(self, role: str, location: str = 'armenia') -> Dict[str, Any]:
        """
        Get salary information for a role.
        
        Args:
            role: Job title/role
            location: Country or city
        
        Returns:
            Salary data with trends
        """
        location_lower = location.lower()
        role_lower = role.lower()
        
        # Try exact match first
        if location_lower in self.salary_data:
            location_data = self.salary_data[location_lower]
            
            if role_lower in location_data:
                salary = location_data[role_lower]
                return {
                    'found': True,
                    'data': asdict(salary),
                    'in_usd': {
                        'min': round(salary.min_salary / 400, 2),  # AMD to USD
                        'max': round(salary.max_salary / 400, 2),
                        'median': round(salary.median_salary / 400, 2),
                    },
                    'comparison': self._get_salary_comparison(salary)
                }
            
            # Try partial match
            for key, salary in location_data.items():
                if role_lower in key or key in role_lower:
                    return {
                        'found': True,
                        'data': asdict(salary),
                        'in_usd': {
                            'min': round(salary.min_salary / 400, 2),
                            'max': round(salary.max_salary / 400, 2),
                            'median': round(salary.median_salary / 400, 2),
                        },
                        'comparison': self._get_salary_comparison(salary)
                    }
        
        return {
            'found': False,
            'message': f"No salary data available for '{role}' in '{location}'",
            'suggestion': 'Try searching for similar roles like "software developer" or "data scientist"'
        }
    
    def _get_salary_comparison(self, salary: SalaryData) -> Dict[str, str]:
        """Compare salary to market average"""
        # Compare to overall tech median in Armenia (~700,000 AMD)
        market_median = 700000
        
        if salary.median_salary > market_median * 1.2:
            level = 'above_average'
            message = 'This role pays 20%+ above the tech market average'
        elif salary.median_salary > market_median * 0.9:
            level = 'average'
            message = 'This role pays close to the tech market average'
        else:
            level = 'below_average'
            message = 'This role pays below the tech market average'
        
        return {'level': level, 'message': message}
    
    def get_hot_skills(self, industry: str = 'tech', top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Get most in-demand skills.
        
        Args:
            industry: Industry filter (currently only 'tech' supported)
            top_k: Number of skills to return
        
        Returns:
            List of skills with demand data
        """
        skills = sorted(
            self.skill_demand.values(),
            key=lambda s: s.demand_score,
            reverse=True
        )[:top_k]
        
        return [
            {
                'skill': s.skill,
                'demand_score': s.demand_score,
                'trend': s.growth_trend,
                'salary_premium': f"+{s.avg_salary_premium}%",
                'related_roles': s.related_roles
            }
            for s in skills
        ]
    
    def get_skill_demand(self, skill: str) -> Optional[Dict[str, Any]]:
        """Get demand data for a specific skill"""
        skill_lower = skill.lower()
        
        if skill_lower in self.skill_demand:
            demand = self.skill_demand[skill_lower]
            return asdict(demand)
        
        # Try partial match
        for key, demand in self.skill_demand.items():
            if skill_lower in key or key in skill_lower:
                return asdict(demand)
        
        return None
    
    def get_hiring_insights(self) -> Dict[str, Any]:
        """Get general hiring market insights"""
        current_month = datetime.now().strftime('%B')
        
        # Determine current hiring season
        if current_month in self.hiring_seasons['high']:
            season = 'high'
            season_message = '🔥 Great time to job search! Hiring activity is high.'
        elif current_month in self.hiring_seasons['medium']:
            season = 'medium'
            season_message = '📊 Average hiring activity. Good time for applications.'
        else:
            season = 'low'
            season_message = '🌴 Lower hiring activity. Focus on skill building and networking.'
        
        return {
            'current_month': current_month,
            'hiring_season': season,
            'season_message': season_message,
            'best_months_to_apply': self.hiring_seasons['high'],
            'top_employers': self.top_employers[:5],
            'market_trends': [
                '📈 Remote work opportunities increasing',
                '🔧 DevOps and Cloud skills in high demand',
                '🤖 AI/ML roles growing rapidly',
                '🌐 English proficiency essential for international companies',
                '💻 Full-stack developers highly sought after'
            ]
        }
    
    def get_career_recommendations(
        self, 
        current_skills: List[str], 
        experience_years: float,
        target_salary: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Get personalized career recommendations.
        
        Args:
            current_skills: User's current skills
            experience_years: Years of experience
            target_salary: Target monthly salary in AMD (optional)
        
        Returns:
            Career recommendations
        """
        recommendations = {
            'skills_to_learn': [],
            'roles_to_target': [],
            'salary_potential': {},
            'action_items': []
        }
        
        current_skills_lower = [s.lower() for s in current_skills]
        
        # Find skills to learn (high demand, not in current skills)
        for skill_name, demand in self.skill_demand.items():
            if skill_name not in current_skills_lower and demand.demand_score >= 75:
                recommendations['skills_to_learn'].append({
                    'skill': demand.skill,
                    'reason': f'High demand ({demand.demand_score}/100), {demand.growth_trend} trend',
                    'salary_premium': f'+{demand.avg_salary_premium}%'
                })
        
        recommendations['skills_to_learn'] = recommendations['skills_to_learn'][:5]
        
        # Suggest roles based on experience
        if experience_years < 2:
            recommendations['roles_to_target'] = [
                'Junior Developer',
                'QA Engineer',
                'Technical Support',
                'Junior Data Analyst'
            ]
            recommendations['action_items'].append('Build portfolio projects on GitHub')
            recommendations['action_items'].append('Consider internships at top companies')
        elif experience_years < 5:
            recommendations['roles_to_target'] = [
                'Mid-level Developer',
                'DevOps Engineer',
                'Data Analyst',
                'Technical Lead'
            ]
            recommendations['action_items'].append('Get cloud certifications (AWS, Azure)')
            recommendations['action_items'].append('Mentor junior developers')
        else:
            recommendations['roles_to_target'] = [
                'Senior Developer',
                'Tech Lead',
                'Engineering Manager',
                'Solutions Architect'
            ]
            recommendations['action_items'].append('Build leadership experience')
            recommendations['action_items'].append('Consider management track opportunities')
        
        # Salary potential
        if experience_years < 2:
            recommendations['salary_potential'] = {
                'current_range': '300,000 - 600,000 AMD',
                'with_growth': '500,000 - 900,000 AMD (1-2 years)',
                'tip': 'Focus on learning and building experience'
            }
        elif experience_years < 5:
            recommendations['salary_potential'] = {
                'current_range': '600,000 - 1,200,000 AMD',
                'with_growth': '900,000 - 1,500,000 AMD (1-2 years)',
                'tip': 'Specialize in high-demand areas like DevOps or ML'
            }
        else:
            recommendations['salary_potential'] = {
                'current_range': '1,000,000 - 2,000,000 AMD',
                'with_growth': '1,500,000 - 2,500,000+ AMD',
                'tip': 'Consider international remote opportunities for higher pay'
            }
        
        return recommendations
    
    def get_market_summary(self) -> Dict[str, Any]:
        """Get a complete market summary"""
        return {
            'salary_overview': {
                'tech_median': '700,000 AMD/month (~$1,750 USD)',
                'senior_tech_median': '1,200,000 AMD/month (~$3,000 USD)',
                'entry_level': '350,000 AMD/month (~$875 USD)'
            },
            'top_skills': self.get_hot_skills(top_k=5),
            'hiring': self.get_hiring_insights(),
            'top_companies': [c['name'] for c in self.top_employers[:5]],
            'market_outlook': 'Positive - Armenia\'s tech sector continues to grow with international companies expanding'
        }


# Convenience function
def get_market_intelligence() -> MarketIntelligence:
    """Get market intelligence instance"""
    return MarketIntelligence()

class SalaryPredictor:
    """
    AI-powered Salary Predictor.
    Uses statistical data where available, falls back to LLM for estimates.
    """
    def __init__(self):
        from llm_gateway import LLMGateway
        self.llm = LLMGateway()
        self.market_intel = MarketIntelligence()
        
    async def predict_salary(self, role: str, location: str, experience_years: int = 2) -> Dict[str, Any]:
        """
        Predict salary for a role/location.
        """
        # 1. Try statistical data
        stats = self.market_intel.get_salary_trends(role, location)
        if stats['found']:
            return {
                "source": "statistical_data",
                "currency": stats['data']['currency'],
                "min": stats['data']['min_salary'],
                "max": stats['data']['max_salary'],
                "median": stats['data']['median_salary'],
                "confidence": "high"
            }
            
        # 2. Fallback to LLM
        print(f"🤖 SalaryPredictor: Asking AI for '{role}' in '{location}'...")
        prompt = f"""
        Act as a compensation expert. Estimate the monthly salary range for a '{role}' in '{location}' 
        with {experience_years} years of experience.
        
        Return ONLY valid JSON:
        {{
            "currency": "ISO_CODE",
            "min": number,
            "max": number,
            "median": number,
            "confidence": "medium" (or "low")
        }}
        """
        
        try:
            response = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system_instruction="You are a data scientist specializing in global salary compensation.",
                json_mode=True
            )
            import json
            clean = response.replace('```json', '').replace('```', '').strip()
            return json.loads(clean)
        except Exception as e:
            print(f"Salary Prediction Error: {e}")
            return {"error": "Could not predict salary"}
