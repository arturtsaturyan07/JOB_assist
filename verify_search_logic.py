import asyncio
import re
from agents.discovery_agent import JobDiscoveryAgent
from agents.matching_agent import MatchingAgent

async def test_logic():
    print("🚀 Starting Logic Verification...")
    
    # 1. Simulate User Profile
    user_profile = {
        "name": "Arthur",
        "job_role": "Call Center and Driver",
        "location": "Yerevan",
        "skills": ["Driving", "Communication"],
        "min_rate": 0,
        "max_hours": 70, # High max to allow pairs
    }
    print(f"👤 Profile: {user_profile}")
    
    # 2. Simulate Search (Main.py logic)
    discovery = JobDiscoveryAgent()
    query = user_profile["job_role"]
    loc = user_profile["location"]
    
    sub_queries = [q.strip() for q in re.split(r' and |,|&', query) if q.strip()]
    print(f"🔍 Sub-queries: {sub_queries}")
    
    all_jobs = []
    seen_ids = set()
    
    for sub_q in sub_queries:
        print(f"  > Searching '{sub_q}' in '{loc}'...")
        jobs = await discovery.search(sub_q, loc)
        print(f"    Found {len(jobs)} raw jobs.")
        for j in jobs:
            if j.job_id not in seen_ids:
                all_jobs.append(j)
                seen_ids.add(j.job_id)
                print(f"      - [{j.job_source or 'JSearch'}] {j.title}: {len(j.schedule_blocks)} blocks ({j.hours_per_week}h)")
                # Print first block to check schedule
                if j.schedule_blocks:
                    b = j.schedule_blocks[0]
                    print(f"        Block 1: {b.day} {b.start//60}:{b.start%60:02d}-{b.end//60}:{b.end%60:02d}")

    print(f"\n📊 Total Unique Jobs: {len(all_jobs)}")
    
    # 3. Simulate Matching
    matcher = MatchingAgent()
    results = matcher.analyze_matches(user_profile, all_jobs)
    
    print("\n🧩 Single Matches:")
    for m in results["single"]:
        j = m.jobs[0]
        print(f"  - {j.title} (Score: {m.score})")
        
    print("\n🤝 Pair Matches:")
    if not results["pairs"]:
        print("  (None found)")
    for m in results["pairs"]:
        j1 = m.jobs[0]
        j2 = m.jobs[1]
        print(f"  - {j1.title} + {j2.title} (Score: {m.score})")

if __name__ == "__main__":
    asyncio.run(test_logic())
