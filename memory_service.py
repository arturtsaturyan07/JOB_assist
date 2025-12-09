"""
Memory Service for TwinWork AI

Provides persistent user memory for personalization:
- Track liked/disliked jobs
- Remember rejected job types
- Track applied and saved jobs
- Learn preferences from feedback
- Personalize future suggestions
"""

import os
import json
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class JobFeedback:
    """User feedback on a job"""
    job_id: str
    job_title: str
    action: str  # liked, disliked, applied, saved, rejected
    timestamp: str
    reason: Optional[str] = None


@dataclass
class UserMemory:
    """Persistent memory for a user"""
    user_id: str
    name: str = ""
    
    # Job interactions
    liked_jobs: List[str] = field(default_factory=list)
    disliked_jobs: List[str] = field(default_factory=list)
    applied_jobs: List[str] = field(default_factory=list)
    saved_jobs: List[str] = field(default_factory=list)
    
    # Learned preferences
    rejected_job_types: List[str] = field(default_factory=list)  # e.g., "night shifts", "sales"
    preferred_companies: List[str] = field(default_factory=list)
    avoided_companies: List[str] = field(default_factory=list)
    
    # Skills and career
    confirmed_skills: List[str] = field(default_factory=list)
    desired_skills: List[str] = field(default_factory=list)  # Skills they want to learn
    career_interests: List[str] = field(default_factory=list)
    
    # Work preferences learned from feedback
    prefers_remote: Optional[bool] = None
    prefers_startup: Optional[bool] = None
    prefers_large_company: Optional[bool] = None
    salary_expectations: Optional[float] = None
    
    # Search history
    search_queries: List[str] = field(default_factory=list)
    
    # Feedback history
    feedback_history: List[Dict] = field(default_factory=list)
    
    # Timestamps
    created_at: str = ""
    last_active: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UserMemory':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class MemoryService:
    """
    Persistent memory service for user personalization.
    
    Stores data in JSON files, one per user.
    """
    
    def __init__(self, storage_dir: str = "user_memories"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self._memory_cache: Dict[str, UserMemory] = {}
    
    def _get_memory_path(self, user_id: str) -> Path:
        """Get file path for user memory"""
        return self.storage_dir / f"{user_id}.json"
    
    def get_memory(self, user_id: str) -> UserMemory:
        """Get or create user memory"""
        # Check cache
        if user_id in self._memory_cache:
            return self._memory_cache[user_id]
        
        # Try to load from file
        file_path = self._get_memory_path(user_id)
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    memory = UserMemory.from_dict(data)
                    self._memory_cache[user_id] = memory
                    return memory
            except Exception as e:
                print(f"⚠️ Could not load memory for {user_id}: {e}")
        
        # Create new memory
        memory = UserMemory(
            user_id=user_id,
            created_at=datetime.now().isoformat(),
            last_active=datetime.now().isoformat()
        )
        self._memory_cache[user_id] = memory
        return memory
    
    def save_memory(self, user_id: str):
        """Save user memory to file"""
        if user_id not in self._memory_cache:
            return
        
        memory = self._memory_cache[user_id]
        memory.last_active = datetime.now().isoformat()
        
        file_path = self._get_memory_path(user_id)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(memory.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save memory for {user_id}: {e}")
    
    def record_feedback(
        self, 
        user_id: str, 
        job_id: str, 
        job_title: str,
        action: str,
        reason: Optional[str] = None
    ):
        """
        Record user feedback on a job.
        
        Actions: liked, disliked, applied, saved, rejected
        """
        memory = self.get_memory(user_id)
        
        # Create feedback record
        feedback = JobFeedback(
            job_id=job_id,
            job_title=job_title,
            action=action,
            timestamp=datetime.now().isoformat(),
            reason=reason
        )
        memory.feedback_history.append(asdict(feedback))
        
        # Update appropriate lists
        if action == 'liked':
            if job_id not in memory.liked_jobs:
                memory.liked_jobs.append(job_id)
            if job_id in memory.disliked_jobs:
                memory.disliked_jobs.remove(job_id)
        
        elif action == 'disliked':
            if job_id not in memory.disliked_jobs:
                memory.disliked_jobs.append(job_id)
            if job_id in memory.liked_jobs:
                memory.liked_jobs.remove(job_id)
        
        elif action == 'applied':
            if job_id not in memory.applied_jobs:
                memory.applied_jobs.append(job_id)
        
        elif action == 'saved':
            if job_id not in memory.saved_jobs:
                memory.saved_jobs.append(job_id)
        
        elif action == 'rejected':
            # Learn from rejection reason
            if reason:
                self._learn_from_rejection(memory, reason)
        
        # Learn preferences from action
        self._learn_from_feedback(memory, job_title, action)
        
        # Save immediately
        self.save_memory(user_id)
    
    def _learn_from_feedback(self, memory: UserMemory, job_title: str, action: str):
        """Learn preferences from user feedback"""
        job_title_lower = job_title.lower()
        
        # Learn remote preference
        if 'remote' in job_title_lower:
            if action == 'liked' or action == 'applied':
                memory.prefers_remote = True
            elif action == 'disliked':
                memory.prefers_remote = False
        
        # Learn company size preference
        startup_keywords = ['startup', 'early-stage', 'seed', 'series a']
        if any(kw in job_title_lower for kw in startup_keywords):
            if action == 'liked' or action == 'applied':
                memory.prefers_startup = True
            elif action == 'disliked':
                memory.prefers_startup = False
    
    def _learn_from_rejection(self, memory: UserMemory, reason: str):
        """Learn from rejection reasons"""
        reason_lower = reason.lower()
        
        # Common rejection patterns
        rejection_patterns = {
            'night shift': 'night shifts',
            'weekend': 'weekend work',
            'travel': 'travel required',
            'sales': 'sales roles',
            'call center': 'call center',
            'commission': 'commission-based',
            'low pay': 'low salary',
            'unpaid': 'unpaid work'
        }
        
        for pattern, category in rejection_patterns.items():
            if pattern in reason_lower:
                if category not in memory.rejected_job_types:
                    memory.rejected_job_types.append(category)
    
    def record_search(self, user_id: str, query: str):
        """Record a search query"""
        memory = self.get_memory(user_id)
        
        # Keep last 20 searches
        memory.search_queries.append(query)
        if len(memory.search_queries) > 20:
            memory.search_queries = memory.search_queries[-20:]
        
        self.save_memory(user_id)
    
    def add_confirmed_skill(self, user_id: str, skill: str):
        """Add a confirmed skill"""
        memory = self.get_memory(user_id)
        skill_lower = skill.lower()
        
        if skill_lower not in [s.lower() for s in memory.confirmed_skills]:
            memory.confirmed_skills.append(skill)
        
        self.save_memory(user_id)
    
    def add_desired_skill(self, user_id: str, skill: str):
        """Add a skill the user wants to learn"""
        memory = self.get_memory(user_id)
        skill_lower = skill.lower()
        
        if skill_lower not in [s.lower() for s in memory.desired_skills]:
            memory.desired_skills.append(skill)
        
        self.save_memory(user_id)
    
    def get_personalized_filters(self, user_id: str) -> Dict[str, Any]:
        """
        Get learned filters for job search.
        
        Returns filters to apply based on user's history.
        """
        memory = self.get_memory(user_id)
        
        filters = {
            'exclude_job_types': memory.rejected_job_types,
            'exclude_job_ids': memory.disliked_jobs,
            'preferred_companies': memory.preferred_companies,
            'avoid_companies': memory.avoided_companies,
        }
        
        # Add preference filters if learned
        if memory.prefers_remote is not None:
            filters['prefer_remote'] = memory.prefers_remote
        
        if memory.prefers_startup is not None:
            filters['prefer_startup'] = memory.prefers_startup
        
        if memory.salary_expectations:
            filters['min_salary'] = memory.salary_expectations
        
        return filters
    
    def get_job_suggestions(self, user_id: str) -> Dict[str, Any]:
        """
        Get personalized job search suggestions.
        
        Based on search history, likes, and career interests.
        """
        memory = self.get_memory(user_id)
        
        suggestions = {
            'recent_searches': memory.search_queries[-5:] if memory.search_queries else [],
            'career_interests': memory.career_interests,
            'skills_to_highlight': memory.confirmed_skills,
            'skills_to_develop': memory.desired_skills,
        }
        
        # Analyze liked jobs for patterns
        if memory.feedback_history:
            liked_titles = [
                f['job_title'] for f in memory.feedback_history 
                if f.get('action') == 'liked'
            ]
            if liked_titles:
                suggestions['liked_job_types'] = liked_titles[-5:]
        
        return suggestions
    
    def get_job_status(self, user_id: str, job_id: str) -> Optional[str]:
        """Get the user's status for a specific job"""
        memory = self.get_memory(user_id)
        
        if job_id in memory.applied_jobs:
            return 'applied'
        elif job_id in memory.saved_jobs:
            return 'saved'
        elif job_id in memory.liked_jobs:
            return 'liked'
        elif job_id in memory.disliked_jobs:
            return 'disliked'
        
        return None
    
    def update_user_name(self, user_id: str, name: str):
        """Update user's name"""
        memory = self.get_memory(user_id)
        memory.name = name
        self.save_memory(user_id)
    
    def get_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user activity statistics"""
        memory = self.get_memory(user_id)
        
        return {
            'total_liked': len(memory.liked_jobs),
            'total_disliked': len(memory.disliked_jobs),
            'total_applied': len(memory.applied_jobs),
            'total_saved': len(memory.saved_jobs),
            'total_searches': len(memory.search_queries),
            'confirmed_skills': len(memory.confirmed_skills),
            'member_since': memory.created_at,
            'last_active': memory.last_active
        }
    
    def clear_memory(self, user_id: str):
        """Clear all memory for a user"""
        if user_id in self._memory_cache:
            del self._memory_cache[user_id]
        
        file_path = self._get_memory_path(user_id)
        if file_path.exists():
            file_path.unlink()


# Global instance
_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """Get or create the memory service singleton"""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service
