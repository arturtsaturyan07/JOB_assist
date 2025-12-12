from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

DAY_ALIASES = {
    "mon": "Mon",
    "monday": "Mon",
    "tue": "Tue",
    "tuesday": "Tue",
    "wed": "Wed",
    "wednesday": "Wed",
    "thu": "Thu",
    "thursday": "Thu",
    "fri": "Fri",
    "friday": "Fri",
    "sat": "Sat",
    "saturday": "Sat",
    "sun": "Sun",
    "sunday": "Sun",
}

DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def normalize_day(raw: str) -> str:
    key = raw.strip().lower()
    if key not in DAY_ALIASES:
        raise ValueError(f"Unsupported day name: {raw}")
    return DAY_ALIASES[key]

def parse_time(raw: Union[str, int]) -> int:
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and ":" in raw:
        hour, minute = raw.split(":")
        return int(hour) * 60 + int(minute)
    if isinstance(raw, str) and raw.isdigit():
        return int(raw)
    return 0 # Fallback

def format_time(minutes: int) -> str:
    hour = minutes // 60
    minute = minutes % 60
    return f"{hour:02d}:{minute:02d}"

@dataclass(frozen=True)
class TimeBlock:
    day: str
    start: int
    end: int

    @classmethod
    def from_dict(cls, payload: Dict[str, Union[str, int]]) -> "TimeBlock":
        return cls(
            day=normalize_day(str(payload["day"])),
            start=parse_time(payload["start"]),
            end=parse_time(payload["end"]),
        )

    @property
    def duration_minutes(self) -> int:
        return self.end - self.start

@dataclass
class Job:
    job_id: str
    title: str
    location: str
    hourly_rate: float
    required_skills: Sequence[str]
    hours_per_week: int
    schedule_blocks: Sequence[TimeBlock]
    # Additional fields for real job data
    currency: str = "USD"  # Moved after defaults
    company: str = ""
    job_source: str = "" # e.g. "jsearch", "adzuna", "staff.am"
    search_query: str = "" # The query that found this job
    description: str = ""
    apply_link: str = ""
    posted_date: str = ""

    @property
    def weekly_pay(self) -> float:
        return self.hourly_rate * self.hours_per_week

    @property
    def is_remote(self) -> bool:
        return "remote" in self.location.lower()

def build_busy_map(schedule: Dict[str, Sequence[Tuple[Union[str, int], Union[str, int]]]]) -> Dict[str, List[Tuple[int, int]]]:
    busy: Dict[str, List[Tuple[int, int]]] = {day: [] for day in DAY_ORDER}
    for raw_day, blocks in schedule.items():
        day = normalize_day(raw_day)
        for start, end in blocks:
            busy[day].append((parse_time(start), parse_time(end)))
        busy[day].sort()
    return busy

@dataclass
class UserProfile:
    name: str
    age: int
    location: str
    min_hourly_rate: float
    max_hours_per_week: int
    desired_hours_per_week: Optional[int]
    remote_ok: bool
    onsite_ok: bool
    skills: Sequence[str]
    career_goals: str
    preferences: Dict[str, str]
    busy_schedule: Dict[str, Sequence[Tuple[str, str]]]
    currency: str = "USD" # Moved after defaults
    preferred_locations: Optional[Sequence[str]] = None
    # New TwinWork AI fields
    languages: Sequence[str] = field(default_factory=list)
    experience_years: int = 0
    education_level: str = ""
    study_commitments: Dict[str, Sequence[Tuple[str, str]]] = field(default_factory=dict)
    health_limitations: Optional[str] = None
    cv_data: Optional[Dict] = None
    user_id: str = ""
    # Computed fields
    busy_map: Dict[str, List[Tuple[int, int]]] = field(init=False)
    study_map: Dict[str, List[Tuple[int, int]]] = field(init=False)

    def __post_init__(self) -> None:
        self.busy_map = build_busy_map(self.busy_schedule)
        self.study_map = build_busy_map(self.study_commitments) if self.study_commitments else {}
        if self.preferred_locations is None:
            self.preferred_locations = []
        if not self.languages:
            self.languages = []

    @property
    def skill_set(self) -> set[str]:
        return {skill.lower() for skill in self.skills}
    
    @property
    def combined_busy_map(self) -> Dict[str, List[Tuple[int, int]]]:
        """Combine busy schedule and study commitments"""
        combined = {day: list(blocks) for day, blocks in self.busy_map.items()}
        for day, blocks in self.study_map.items():
            if day in combined:
                combined[day].extend(blocks)
                combined[day].sort()
            else:
                combined[day] = list(blocks)
        return combined
    
    @property
    def available_hours_per_week(self) -> int:
        """Calculate available hours after busy/study commitments"""
        total_busy_minutes = 0
        for day, blocks in self.combined_busy_map.items():
            for start, end in blocks:
                total_busy_minutes += (end - start)
        # Assume 12 waking hours per day (720 min) * 7 days = 5040 min
        available_minutes = 5040 - total_busy_minutes
        return max(0, available_minutes // 60)


@dataclass
class MatchInsight:
    title: str
    detail: str

@dataclass
class MatchResult:
    jobs: Sequence[Job]
    total_hours: int
    total_pay: float
    insights: Sequence[MatchInsight]
    score: float = 0.0

def summarize_job(job: Job) -> str:
    blocks = [f"{block.day} {format_time(block.start)}-{format_time(block.end)}" for block in job.schedule_blocks]
    schedule_str = ", ".join(blocks)
    return (
        f"{job.title} @ {job.location} | {job.hours_per_week}h/week | "
        f"{job.hourly_rate:.0f} AED/hr | Shifts: {schedule_str}"
    )
