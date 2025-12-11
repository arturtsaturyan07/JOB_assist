import asyncio
from agents.user_agent import UserContextAgent
from agents.discovery_agent import JobDiscoveryAgent
from agents.matching_agent import MatchingAgent
from llm_gateway import LLMGateway

async def test_all_agents():
    print("Starting Architecture Verification...")
    
    # 1. Infrastructure
    print("\n[1] Testing LLM Gateway...")
    gateway = LLMGateway()
    if gateway.gemini_avaliable or gateway.openai_client:
        print("   [OK] Gateway Active")
    else:
        print("   [FAIL] Gateway Inactive (Check API Keys)")
        
    # 2. User Agent
    print("\n[2] Testing User Agent...")
    user_agent = UserContextAgent(gateway)
    resp, ready = await user_agent.process_message("Hi, I'm Alex")
    print(f"   Response to 'Hi, I'm Alex': {resp}")
    
    if "Alex" in str(user_agent.user_profile) or "name" in user_agent.user_profile:
        print(f"   [OK] Name Extraction Worked: {user_agent.user_profile}")
    else:
        print(f"   [WARN] Name Extraction Uncertain: {user_agent.user_profile}")
        
    # Force profile for next steps
    user_agent.user_profile = {
        "name": "Alex",
        "skills": ["Python Developer"],
        "location": "Remote", 
        "remote_ok": True,
        "onsite_ok": False
    }
    
    # 3. Discovery Agent
    print("\n[3] Testing Discovery Agent...")
    discovery = JobDiscoveryAgent()
    jobs = []
    try:
        jobs = await discovery.search("Python", "Remote", True)
        print(f"   Found {len(jobs)} jobs via APIs")
    except Exception as e:
        print(f"   [WARN] Search Error (Expected if no API key): {e}")
        
    if not jobs:
        print("   [WARN] No jobs found, using mocks for matching test.")
        from models import Job
        jobs = [
            Job(job_id="1", title="Python Dev", company="TechCo", location="Remote", hourly_rate=50, hours_per_week=40),
            Job(job_id="2", title="Senior Python", company="BigCorp", location="Remote", hourly_rate=60, hours_per_week=40),
            Job(job_id="3", title="Java Dev", company="OldCorp", location="Remote", hourly_rate=45, hours_per_week=40)
        ]

    # 4. Matching Agent
    print("\n[4] Testing Matching Agent...")
    matcher = MatchingAgent()
    results = matcher.analyze_matches(user_agent.user_profile, jobs)
    
    print(f"   Single Matches: {len(results['single'])}")
    print(f"   Pair Matches: {len(results['pairs'])}")
    
    if len(results['single']) > 0:
        print("   [OK] Matching Logic Working")
    else:
        print("   [FAIL] Matching Logic Failed")

    print("\nVerification Complete!")

if __name__ == "__main__":
    asyncio.run(test_all_agents())
