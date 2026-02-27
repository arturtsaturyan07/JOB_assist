"""
Schedule Inference Helper
Infers work schedules based on job titles and types
Used by job scrapers that don't provide schedule information
"""
from typing import List, Tuple
from models import TimeBlock

def infer_schedule_from_title(title: str, location: str = "") -> Tuple[List[TimeBlock], int]:
    """
    Infer schedule blocks and hours per week based on job title keywords
    
    Returns:
        Tuple of (schedule_blocks, hours_per_week)
    """
    title_lower = title.lower()
    loc_lower = (location or "").lower()
    
    # Remote = Flexible (no fixed schedule)
    if "remote" in title_lower or "remote" in loc_lower:
        return [], 40
    
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    
    # Driver/Taxi/Delivery - Evening shifts (18:00-23:00, 5h/day = 25h/week)
    if any(w in title_lower for w in ['driver', 'taxi', 'courier', 'delivery', 'uber', 'lyft']):
        blocks = [TimeBlock(day=d, start=1080, end=1380) for d in days]  # 18:00-23:00
        return blocks, 25
    
    # Call Center/Support - Split into morning and afternoon shifts
    if any(w in title_lower for w in ['call center', 'support', 'operator', 'agent', 'customer service', 'helpdesk']):
        # Use hash to deterministically assign shift
        if hash(title) % 2 == 0:
            # Morning: 08:00-14:00 (6h/day = 30h/week)
            blocks = [TimeBlock(day=d, start=480, end=840) for d in days]
            return blocks, 30
        else:
            # Afternoon: 14:00-20:00 (6h/day = 30h/week)
            blocks = [TimeBlock(day=d, start=840, end=1200) for d in days]
            return blocks, 30
    
    # Part-time - Short shifts (10:00-14:00, 4h/day = 20h/week)
    if "part time" in title_lower or "part-time" in title_lower or "parttime" in title_lower:
        blocks = [TimeBlock(day=d, start=600, end=840) for d in days]
        return blocks, 20
    
    # Night shift
    if "night" in title_lower or "overnight" in title_lower or "graveyard" in title_lower:
        blocks = [TimeBlock(day=d, start=1320, end=480) for d in days]  # 22:00-08:00 (crosses midnight)
        return blocks, 40
    
    # Weekend only
    if "weekend" in title_lower:
        weekend_days = ['Sat', 'Sun']
        blocks = [TimeBlock(day=d, start=540, end=1080) for d in weekend_days]  # 09:00-18:00
        return blocks, 18
    
    # Default: Standard 9-5 office hours (09:00-18:00, 9h/day = 45h/week)
    blocks = [TimeBlock(day=d, start=540, end=1080) for d in days]
    return blocks, 45
