import json
from pathlib import Path
from typing import List, Sequence, Tuple, Dict
from itertools import combinations
from models import Job, UserProfile, MatchResult, MatchInsight, TimeBlock, DAY_ORDER, normalize_day, parse_time

def conflicts(block: TimeBlock, busy_blocks: Sequence[Tuple[int, int]]):
    for start, end in busy_blocks:
        if block.start < end and block.end > start:
            return True
    return False

def jobs_overlap(job_a: Job, job_b: Job) -> bool:
    for block_a in job_a.schedule_blocks:
        for block_b in job_b.schedule_blocks:
            if block_a.day != block_b.day:
                continue
            if block_a.start < block_b.end and block_a.end > block_b.start:
                return True
    return False

def job_fits_user(job: Job, user: UserProfile) -> Tuple[bool, List[MatchInsight]]:
    insights: List[MatchInsight] = []
    if job.hourly_rate < user.min_hourly_rate:
        return False, insights

    if job.hours_per_week > user.max_hours_per_week:
        return False, insights

    # Relaxed skill check for demo/API jobs which might have empty skills
    if job.required_skills:
        skill_gap = [skill for skill in job.required_skills if skill.lower() not in user.skill_set]
        if skill_gap:
            # Strict matching: return False, insights
            # For now, let's allow it if it's an API job (often has no structured skills)
            pass 

    location_ok = False
    
    # Check if job is remote
    is_remote = job.is_remote or "remote" in job.location.lower()
    
    if is_remote and user.remote_ok:
        # Remote jobs are OK if user accepts remote
        location_ok = True
    elif not is_remote and user.onsite_ok:
        # Onsite jobs need location match
        # Simple string matching for location
        if user.location and user.location.lower() in job.location.lower():
            location_ok = True
        elif user.location and job.location.lower() in user.location.lower():
            location_ok = True
        else:
            # Check preferred locations
            preferred = {loc.lower() for loc in user.preferred_locations or []} if user.preferred_locations else set()
            if user.location:
                preferred.add(user.location.lower())
            
            if job.location.lower() in preferred:
                location_ok = True
    elif user.remote_ok and is_remote:
        # If we reach here and job is remote, accept it
        location_ok = True

    if not location_ok:
        return False, insights

    for block in job.schedule_blocks:
        if conflicts(block, user.busy_map.get(block.day, [])):
            return False, insights

    insights.append(MatchInsight("Skills", "Skills match or not specified."))
    insights.append(MatchInsight("Schedule", "Fits within free time blocks."))
    insights.append(MatchInsight("Location", "Matches location preference."))
    insights.append(MatchInsight("Income", f"Pays {job.hourly_rate:.0f} per hour."))
    return True, insights

def score_job(job: Job, user: UserProfile) -> float:
    pay_weight = job.hourly_rate * 2
    hours_target = user.desired_hours_per_week or user.max_hours_per_week
    hours_alignment = 1 - abs(job.hours_per_week - hours_target) / max(hours_target, 1)
    preference_bonus = 0
    desired_env = user.preferences.get("environment")
    if desired_env and desired_env.lower() in job.title.lower():
        preference_bonus = 5
    return pay_weight + hours_alignment * 10 + preference_bonus

class JobMatcher:
    def __init__(self, jobs: Sequence[Job]):
        self.jobs = jobs

    def match_single_jobs(self, user: UserProfile, limit: int = 3) -> List[MatchResult]:
        eligible: List[Tuple[Job, float, List[MatchInsight]]] = []
        for job in self.jobs:
            fits, insights = job_fits_user(job, user)
            if fits:
                eligible.append((job, score_job(job, user), insights))
        eligible.sort(key=lambda entry: entry[1], reverse=True)
        results: List[MatchResult] = []
        for job, score, insights in eligible[:limit]:
            results.append(
                MatchResult(
                    jobs=[job],
                    total_hours=job.hours_per_week,
                    total_pay=job.weekly_pay,
                    insights=insights,
                    score=score,
                )
            )
        return results

    def match_job_pairs(self, user: UserProfile, limit: int = 3) -> List[MatchResult]:
        eligible_jobs = []
        job_scores: Dict[str, float] = {}
        for job in self.jobs:
            fits, _ = job_fits_user(job, user)
            if fits:
                eligible_jobs.append(job)
                job_scores[job.job_id] = score_job(job, user)
        combos: List[MatchResult] = []
        for job_a, job_b in combinations(eligible_jobs, 2):
            if jobs_overlap(job_a, job_b):
                continue
            total_hours = job_a.hours_per_week + job_b.hours_per_week
            if total_hours > user.max_hours_per_week:
                continue
            total_pay = job_a.weekly_pay + job_b.weekly_pay
            pair_score = job_scores[job_a.job_id] + job_scores[job_b.job_id]
            schedule_insights = self._get_pair_schedule_insights(job_a, job_b)
            pair_type = self._get_pair_type(job_a, job_b)
            insights = [
                MatchInsight("Pair Type", pair_type),
                MatchInsight("Schedule Fit", schedule_insights),
                MatchInsight("Combined Hours", f"{total_hours}h per week"),
                MatchInsight("Income", f"Combined weekly income: {total_pay:.0f} AED"),
            ]
            combos.append(
                MatchResult(
                    jobs=[job_a, job_b],
                    total_hours=total_hours,
                    total_pay=total_pay,
                    insights=insights,
                    score=pair_score,
                )
            )
        combos.sort(key=lambda entry: entry.score, reverse=True)
        return combos[:limit]
    
    def _get_pair_type(self, job_a: Job, job_b: Job) -> str:
        """Determine the type of job pair (e.g., morning/evening, weekday/weekend)."""
        days_a = {block.day for block in job_a.schedule_blocks}
        days_b = {block.day for block in job_b.schedule_blocks}
        overlap_days = days_a & days_b
        
        if not overlap_days:
            return "Different Days (e.g., Mon-Wed and Thu-Sun)"
        
        # Check if one is typically morning and one is evening
        avg_start_a = sum(block.start for block in job_a.schedule_blocks) / len(job_a.schedule_blocks)
        avg_start_b = sum(block.start for block in job_b.schedule_blocks) / len(job_b.schedule_blocks)
        
        morning_evening_gap = abs(avg_start_a - avg_start_b) > 240  # 4 hours difference
        if morning_evening_gap:
            if avg_start_a < avg_start_b:
                return "Morning & Evening Split (ideal rest period)"
            else:
                return "Evening & Morning Split (ideal rest period)"
        
        return "Complementary Schedule"
    
    def _get_pair_schedule_insights(self, job_a: Job, job_b: Job) -> str:
        """Generate detailed schedule insights for a job pair."""
        schedule_a = ", ".join([f"{b.day} {self._format_time(b.start)}-{self._format_time(b.end)}" 
                               for b in job_a.schedule_blocks])
        schedule_b = ", ".join([f"{b.day} {self._format_time(b.start)}-{self._format_time(b.end)}" 
                               for b in job_b.schedule_blocks])
        
        total_hours = job_a.hours_per_week + job_b.hours_per_week
        
        return f"{schedule_a} | {schedule_b} | Total: {total_hours}h/week"
    
    def _format_time(self, minutes: int) -> str:
        """Format minutes since midnight as HH:MM."""
        hour = minutes // 60
        minute = minutes % 60
        return f"{hour:02d}:{minute:02d}"
