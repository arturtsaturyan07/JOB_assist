from typing import List, Tuple, Sequence
from models import Job, UserProfile, MatchResult
from itertools import combinations
# Import logic from original matcher but wrapped in Agent class
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matcher import JobMatcher as LegacyMatcher, score_job, job_fits_user

class MatchingAgent:
    """
    Agent 3: The "Analyst"
    Responsibility: Match user profile to jobs.
    Attributes:
        - uses 'matcher.py' logic but provides a cleaner agent interface.
    """
    def __init__(self):
        pass

    def analyze_matches(self, user_data: dict, jobs: List[Job]) -> dict:
        """
        Analyze jobs against user profile.
        Returns dictionary with 'single' and 'pair' matches.
        """
        if not jobs:
            return {"single": [], "pairs": [], "schedule": []}

        # Convert dict profile to UserProfile object
        profile = self._create_profile(user_data)
        
        matcher = LegacyMatcher(jobs)
        
        # 1. Single Matches
        single_matches = matcher.match_single_jobs(profile, limit=5)
        
        # 2. Pair Matches (TwinWork capability)
        pair_matches = matcher.match_job_pairs(profile, limit=3)
        
        return {
            "single": single_matches,
            "pairs": pair_matches,
            "raw_top_jobs": [m.jobs[0] for m in single_matches] if single_matches else jobs[:5]
        }

    def _create_profile(self, data: dict) -> UserProfile:
        # Reconstruct UserProfile from dict
        # Handle busy schedule parsing
        busy_schedule = {}
        raw_schedule = data.get("busy_schedule", {})
        if isinstance(raw_schedule, dict):
            for day, blocks in raw_schedule.items():
                busy_schedule[day] = [(b[0], b[1]) for b in blocks if len(b) == 2]

        return UserProfile(
            name=data.get("name", "User"),
            age=25,
            location=data.get("location", ""),
            min_hourly_rate=float(data.get("min_rate", 0)),
            max_hours_per_week=int(data.get("max_hours") or 70),  # Default to 70 to allow pairs
            desired_hours_per_week=int(data.get("desired_hours")) if data.get("desired_hours") else None,
            remote_ok=data.get("remote_ok", True),  # Default to True to be safe
            onsite_ok=data.get("onsite_ok", True),
            skills=data.get("skills", []),
            career_goals=data.get("career_goals", ""),
            preferences={},
            busy_schedule=busy_schedule,
            preferred_locations=data.get("preferred_locations", [])
        )
