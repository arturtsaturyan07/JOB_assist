import json
import os
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path

# Import refactored modules
from models import UserProfile, Job, MatchResult, summarize_job, TimeBlock
from matcher import JobMatcher
from llm_service import LLMService
from jsearch_service import JSearchService, LinkedInJobService
from adzuna_service import AdzunaService

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load API Keys
RAPIDAPI_KEY_FILE = "rapidapi_key.txt"
GEMINI_API_KEY_FILE = "gemini_api_key.txt"
ADZUNA_KEY_FILE = "azduna_api_key.txt"

def load_file_content(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return f.read().strip()
    return None

# Initialize Services
rapidapi_key = load_file_content(RAPIDAPI_KEY_FILE)
jsearch_service = JSearchService(rapidapi_key) if rapidapi_key else None
linkedin_service = LinkedInJobService(rapidapi_key) if rapidapi_key else None

# Initialize Adzuna Service
adzuna_key = load_file_content(ADZUNA_KEY_FILE)
adzuna_service = None
if adzuna_key:
    try:
        # Parse Adzuna key (format: "app_id:app_key")
        if ':' in adzuna_key:
            app_id, app_key = adzuna_key.split(':', 1)
            adzuna_service = AdzunaService(app_id, app_key, country="am")  # Armenia by default
    except Exception as e:
        print(f"Could not initialize Adzuna: {e}")

print(f"JSearch Service: {'✅ Enabled' if jsearch_service else '❌ Disabled'}")
print(f"LinkedIn Service: {'✅ Enabled' if linkedin_service else '❌ Disabled'}")
print(f"Adzuna Service: {'✅ Enabled' if adzuna_service else '❌ Disabled'}")

# Chat Session Management
class ChatSession:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.history = [] 
        self.user_profile_data = {}
        self.llm = LLMService()
        
    async def send_message(self, message: str, type: str = "text", options: List[str] = None):
        await self.websocket.send_json({
            "type": type,
            "message": message,
            "options": options
        })
        self.history.append({"role": "assistant", "content": message})

    async def process_input(self, text: str):
        text = text.strip()
        
        # Initial Greeting
        if not self.history and not text:
            await self.send_message("👋 Привет! Я Azduna - твой персональный помощник по поиску работы. Как тебя зовут?")
            return

        # Add user message to history
        self.history.append({"role": "user", "content": text})

        # Get response from LLM
        llm_result = await self.llm.get_response(self.history, self.user_profile_data)
        
        # Update user profile with extracted data
        extracted = llm_result.get("extracted_data", {})
        self.user_profile_data.update(extracted)
        
        # Send AI response
        ai_response = llm_result.get("response", "I didn't catch that.")
        await self.send_message(ai_response)

        # Check if ready to search
        if extracted.get("ready_to_search"):
            await self.perform_search()

    async def perform_search(self):
        # Get user's detected language for responses
        name = self.user_profile_data.get("name", "друг")
        
        await self.send_message(f"🔍 Отлично, {name}! Ищу лучшие вакансии для тебя из нескольких источников...")
        
        # Parse busy schedule
        busy_schedule = {}
        raw_schedule = self.user_profile_data.get("busy_schedule", {})
        if isinstance(raw_schedule, dict):
            for day, blocks in raw_schedule.items():
                busy_schedule[day] = [(b[0], b[1]) for b in blocks if len(b) == 2]

        # Create UserProfile object
        try:
            user = UserProfile(
                name=self.user_profile_data.get("name", "User"),
                age=25, # Default
                location=self.user_profile_data.get("location", ""),
                min_hourly_rate=float(self.user_profile_data.get("min_rate", 0)),
                max_hours_per_week=int(self.user_profile_data.get("max_hours", 40)),
                desired_hours_per_week=int(self.user_profile_data.get("desired_hours")) if self.user_profile_data.get("desired_hours") else None,
                remote_ok=self.user_profile_data.get("remote_ok", True),
                onsite_ok=self.user_profile_data.get("onsite_ok", True),
                skills=self.user_profile_data.get("skills", []),
                career_goals=self.user_profile_data.get("career_goals", ""),
                preferences={},
                busy_schedule=busy_schedule,
                preferred_locations=self.user_profile_data.get("preferred_locations", [])
            )
            
            # Build search query from skills, career goals, or default
            skills = user.skills if user.skills else []
            career_goals = self.user_profile_data.get("career_goals", "")
            
            # Primary query construction - get all career goals to search individually
            goals_list = []
            
            # Prefer career goals as they contain the actual roles
            if career_goals and career_goals.lower() not in ["general", "skip", "no"]:
                # Split multiple roles if comma-separated
                goals_list = [g.strip() for g in career_goals.split(',') if g.strip()]
            elif skills:
                # Fall back to skills
                goals_list = skills
            else:
                goals_list = ["Python Programmer"]  # Better default
            
            location = user.location if user.location else ""
            role_locations = self.user_profile_data.get("role_locations", {})
            remote_only = user.remote_ok and not user.onsite_ok
            
            print(f"=" * 60)
            print(f"🔍 Multi-Source Job Search:")
            print(f"   Career Goals: {goals_list}")
            print(f"   User Location: '{location}'")
            print(f"   Role-Specific Locations: {role_locations}")
            print(f"   Skills: {skills}")
            print(f"   Remote Only: {remote_only}")
            print(f"=" * 60)
            
            # Parallel search from multiple sources and multiple goals
            search_tasks = []
            
            # Search for each career goal individually to maximize results
            for goal in goals_list:
                # Build query with role/seniority
                query = goal
                
                # Add seniority level if not already in query and it's a technical role
                if ("senior" not in query.lower() and 
                    ("developer" in query.lower() or "engineer" in query.lower() or 
                     "programmer" in query.lower())):
                    query = f"Senior {query}"
                
                # Check if this role has a specific location preference
                goal_location = location
                for role_key, role_loc in role_locations.items():
                    if role_key.lower() in goal.lower():
                        goal_location = role_loc
                        break
                
                # JSearch (LinkedIn, Indeed, Glassdoor aggregator)
                if jsearch_service:
                    print(f"📡 Starting JSearch for '{query}' in {goal_location or 'any location'}...")
                    search_tasks.append(
                        jsearch_service.search_jobs(
                            query=query,
                            location="",  # JSearch doesn't filter by location well, we'll match later
                            remote_only=remote_only,
                            num_pages=2
                        )
                    )
                
                # Adzuna
                if adzuna_service:
                    print(f"📡 Starting Adzuna for '{query}'...")
                    search_tasks.append(
                        adzuna_service.search_jobs(
                            what=query,
                            where=location or "anywhere",
                            country="am"  # Armenia
                        )
                    )
            
            # Run all searches in parallel
            if search_tasks:
                results = await asyncio.gather(*search_tasks, return_exceptions=True)
            else:
                results = []
            
            # Aggregate results and filter out errors
            jobs_found = []
            source_counts = {}
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"❌ Search source {i} failed: {result}")
                    continue
                
                if isinstance(result, list):
                    jobs_found.extend(result)
                    source_name = ["JSearch", "Adzuna"][i] if i < 2 else f"Source{i}"
                    source_counts[source_name] = len(result)
                    print(f"✅ {source_name}: Found {len(result)} jobs")
            
            print(f"\n📊 Aggregated Results: {sum(source_counts.values())} total jobs from {len(source_counts)} sources")
            for source, count in source_counts.items():
                print(f"   - {source}: {count}")
            
            # Remove duplicates by job_id if present
            seen_ids = set()
            unique_jobs = []
            for job in jobs_found:
                if job.job_id not in seen_ids:
                    seen_ids.add(job.job_id)
                    unique_jobs.append(job)
            
            jobs_found = unique_jobs
            
            # If no jobs found with remote_only filter, try without it (second attempt)
            if not jobs_found and remote_only:
                print(f"\n⚠️ No remote jobs found. Retrying with all job types...")
                search_tasks = []
                
                if jsearch_service:
                    search_tasks.append(
                        jsearch_service.search_jobs(
                            query=query,
                            location="",
                            remote_only=False,
                            num_pages=3
                        )
                    )
                
                if adzuna_service:
                    search_tasks.append(
                        adzuna_service.search_jobs(
                            what=query,
                            where=location or "anywhere",
                            country="am"
                        )
                    )
                
                if search_tasks:
                    results = await asyncio.gather(*search_tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, list):
                            jobs_found.extend(result)
                
                print(f"✅ Found {len(jobs_found)} jobs (including non-remote)")
            
            if jobs_found:
                await self.send_message(f"🎉 Нашел {len(jobs_found)} вакансий! Вот лучшие рекомендации для тебя:")
                
                try:
                    # Match jobs using JobMatcher to get single and pair recommendations
                    from matcher import JobMatcher
                    matcher = JobMatcher(jobs_found)
                    
                    # Get single job matches
                    single_matches = matcher.match_single_jobs(user, limit=5)
                    print(f"✅ Found {len(single_matches)} single job matches")
                    
                    # Get job pair matches
                    pair_matches = matcher.match_job_pairs(user, limit=3)
                    print(f"✅ Found {len(pair_matches)} job pair matches")
                    
                    # Prepare job data for panel display
                    single_jobs_data = []
                    if single_matches:
                        for match in single_matches:
                            job = match.jobs[0]
                            single_jobs_data.append({
                                "title": job.title,
                                "company": job.company,
                                "location": job.location,
                                "hourly_rate": float(job.hourly_rate),
                                "hours_per_week": int(job.hours_per_week),
                                "weekly_pay": float(job.weekly_pay),
                                "apply_link": job.apply_link
                            })
                    else:
                        fallback_jobs = jobs_found[:5]
                        for job in fallback_jobs:
                            single_jobs_data.append({
                                "title": job.title,
                                "company": job.company,
                                "location": job.location,
                                "hourly_rate": float(job.hourly_rate),
                                "hours_per_week": int(job.hours_per_week),
                                "weekly_pay": float(job.weekly_pay),
                                "apply_link": job.apply_link
                            })
                    
                    pair_jobs_data = []
                    for match in pair_matches:
                        jobA, jobB = match.jobs[0], match.jobs[1]
                        pair_jobs_data.append({
                            "jobs": [
                                {
                                    "title": jobA.title,
                                    "company": jobA.company,
                                    "location": jobA.location,
                                    "hourly_rate": float(jobA.hourly_rate),
                                    "apply_link": jobA.apply_link
                                },
                                {
                                    "title": jobB.title,
                                    "company": jobB.company,
                                    "location": jobB.location,
                                    "hourly_rate": float(jobB.hourly_rate),
                                    "apply_link": jobB.apply_link
                                }
                            ],
                            "total_hours": int(match.total_hours),
                            "total_pay": float(match.total_pay)
                        })
                    
                    # Send jobs data to frontend
                    print(f"📤 Sending {len(single_jobs_data)} single jobs and {len(pair_jobs_data)} pair jobs to frontend")
                    await self.websocket.send_json({
                        "type": "jobs",
                        "single_jobs": single_jobs_data,
                        "pair_jobs": pair_jobs_data
                    })
                    
                    await self.send_message("✅ Check the job offers panel on the right for detailed information!")
                    
                except Exception as match_error:
                    print(f"❌ Error matching jobs: {match_error}")
                    import traceback
                    traceback.print_exc()
                    await self.send_message("Found jobs but had trouble organizing them. Showing best matches anyway!")
            else:
                await self.send_message("😔 К сожалению, по твоим критериям пока ничего не нашлось. Попробуем изменить параметры поиска?")
            
        except Exception as e:
            print(f"Search Error: {e}")
            import traceback
            traceback.print_exc()
            await self.send_message("Упс, что-то пошло не так при поиске. Давай попробуем еще раз!")

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session = ChatSession(websocket)
    
    # Initial greeting
    await session.process_input("")
    
    try:
        while True:
            data = await websocket.receive_text()
            await session.process_input(data)
    except WebSocketDisconnect:
        print("Client disconnected")

@app.get("/")
async def get():
    return HTMLResponse(open("static/index.html", "r").read())
