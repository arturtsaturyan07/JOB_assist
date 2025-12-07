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

def parse_time(raw: str) -> int:
    hour, minute = raw.split(":")
    return int(hour) * 60 + int(minute)

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
    def from_dict(cls, payload: Dict[str, str]) -> "TimeBlock":
        return cls(
            day=normalize_day(payload["day"]),
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
    company: str = ""
    description: str = ""
    apply_link: str = ""
    posted_date: str = ""

    @property
    def weekly_pay(self) -> float:
        return self.hourly_rate * self.hours_per_week

    @property
    def is_remote(self) -> bool:
        return "remote" in self.location.lower()

def build_busy_map(schedule: Dict[str, Sequence[Tuple[str, str]]]) -> Dict[str, List[Tuple[int, int]]]:
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
    preferred_locations: Optional[Sequence[str]] = None
    busy_map: Dict[str, List[Tuple[int, int]]] = field(init=False)

    def __post_init__(self) -> None:
        self.busy_map = build_busy_map(self.busy_schedule)
        if self.preferred_locations is None:
            self.preferred_locations = []

    @property
    def skill_set(self) -> set[str]:
        return {skill.lower() for skill in self.skills}

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

def summarize_job(job: Job) -> str:
    blocks = [f"{block.day} {format_time(block.start)}-{format_time(block.end)}" for block in job.schedule_blocks]
    schedule_str = ", ".join(blocks)
    return (
        f"{job.title} @ {job.location} | {job.hours_per_week}h/week | "
        f"{job.hourly_rate:.0f} AED/hr | Shifts: {schedule_str}"
    )
