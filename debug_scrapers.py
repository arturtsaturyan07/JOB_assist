import asyncio
from agents.discovery_agent import JobDiscoveryAgent

async def test_search():
    agent = JobDiscoveryAgent()
    print("🚀 Starting Search Test for 'Math Teacher' in 'Yerevan'...")
    
    # We want to see deeper logs, so we trust the agent's print statements 
    # but we will also inspect the return values.
    
    # Mocking or Ensure keys are loaded? 
    # The agent loads keys internally.
    
    jobs = await agent.search("Math Teacher", "Yerevan")
    
    print(f"\n✅ Total Jobs Found: {len(jobs)}")
    
    by_source = {}
    for job in jobs:
        src = job.job_source or "unknown"
        by_source[src] = by_source.get(src, 0) + 1
        print(f"- [{src}] {job.title} @ {job.company} ({job.location})")
        
    print("\n📊 Breakdown by Source:")
    for src, count in by_source.items():
        print(f"  {src}: {count}")

if __name__ == "__main__":
    asyncio.run(test_search())
