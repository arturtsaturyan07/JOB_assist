import json
import os
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path

# Import refactored modules
from models import UserProfile, Job, MatchResult, summarize_job, TimeBlock, format_time
from matcher import JobMatcher
from conversation_engine import ConversationEngine, ConversationState
from jsearch_service import JSearchService, LinkedInJobService
from adzuna_service import AdzunaService

# Import TwinWork AI Services
from armenian_scrapers import ArmenianJobScraper
from memory_service import get_memory_service
from cv_service import CVService
from cv_service import CVService
from market_intelligence import get_market_intelligence
from llm_service import LLMService

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

# Initialize Adzuna
adzuna_key = load_file_content(ADZUNA_KEY_FILE)
adzuna_service = None
if adzuna_key:
    try:
        if ':' in adzuna_key:
            app_id, app_key = adzuna_key.split(':', 1)
            adzuna_service = AdzunaService(app_id, app_key, country="am")
    except Exception as e:
        print(f"Could not initialize Adzuna: {e}")

# Initialize TwinWork AI Services
armenian_scraper = ArmenianJobScraper()
memory_service = get_memory_service()
cv_service = CVService()
market_intelligence = get_market_intelligence()
llm_service = LLMService()

print(f"JSearch Service: {'✅ Enabled' if jsearch_service else '❌ Disabled'}")
print(f"Adzuna Service: {'✅ Enabled' if adzuna_service else '❌ Disabled'}")
print(f"Armenian Scraper: {'✅ Enabled' if armenian_scraper else '❌ Disabled'}")
print(f"Memory Service: {'✅ Enabled' if memory_service else '❌ Disabled'}")
print(f"CV Service: {'✅ Enabled' if cv_service else '❌ Disabled'}")
print(f"Market Intelligence: {'✅ Enabled' if market_intelligence else '❌ Disabled'}")

# Chat Session Management
class ChatSession:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.history = [] 
        self.user_profile_data = {}
        self.conversation_engine = ConversationEngine(llm_service)
        self.user_id = str(id(websocket)) # Simple session ID
        self.found_jobs = [] # Store found jobs for reference
        
    async def send_message(self, message: str, type: str = "text", options: List[str] = None):
        await self.websocket.send_json({
            "type": type,
            "message": message,
            "options": options
        })
        self.history.append({"role": "assistant", "content": message})

    async def handle_message(self, raw_message: str):
        """Handle incoming WebSocket messages (text or JSON)"""
        try:
            # Try to parse as JSON for special commands
            data = json.loads(raw_message)
            
            # If data is not a dictionary (e.g. just a number "10"), treat as text
            if not isinstance(data, dict):
                await self.process_input(str(data))
                return

            if data.get("type") == "feedback":
                await self.handle_feedback(data)
                return
            
            if data.get("type") == "cv_upload":
                await self.handle_cv_upload(data)
                return
            
            # Regular text message
            text = data.get("text", data.get("message", ""))
            await self.process_input(text)
            
        except json.JSONDecodeError:
            # Plain text message
            await self.process_input(raw_message)

    async def handle_feedback(self, data: dict):
        """Handle job feedback (like, save, apply, etc.)"""
        job_id = data.get("job_id", "")
        action = data.get("action", "")
        
        # Find job title
        job_title = "Job"
        for job in self.found_jobs:
            if job.job_id == job_id:
                job_title = job.title
                break
        
        if memory_service:
            memory_service.record_feedback(self.user_id, job_id, job_title, action)
        
        # Send confirmation
        if action == "liked":
            await self.websocket.send_json({"type": "feedback_ack", "message": f"❤️ Saved to favorites"})
        elif action == "saved":
            await self.websocket.send_json({"type": "feedback_ack", "message": f"🔖 Job saved"})

    async def handle_cv_upload(self, data: dict):
        """Handle CV upload and analysis"""
        if not cv_service:
            await self.send_message("⚠️ CV analysis service is not available")
            return
        
        cv_text = data.get("content", "")
        if not cv_text:
            await self.send_message("Please paste your CV content")
            return
        
        await self.send_message("📄 Analyzing your CV...")
        
        try:
            cv_data = await cv_service.parse_cv(cv_text)
            suggestions = await cv_service.suggest_improvements(cv_data)
            
            # Update user profile with CV data
            if cv_data.skills:
                self.user_profile_data["skills"] = cv_data.skills
            if cv_data.languages:
                self.user_profile_data["languages"] = cv_data.languages
            if cv_data.name and not self.user_profile_data.get("name"):
                self.user_profile_data["name"] = cv_data.name
                self.conversation_engine.current_state = ConversationState.SKILLS_EXTRACT # Advance state
            if cv_data.location:
                self.user_profile_data["location"] = cv_data.location
            
            # Store CV data
            self.user_profile_data["cv_data"] = cv_data.to_dict()
            
            # Send results
            await self.websocket.send_json({
                "type": "cv_analysis",
                "skills": cv_data.skills,
                "experience_years": cv_data.total_experience_years,
                "suggestions": suggestions
            })
            
            skills_str = ", ".join(cv_data.skills[:10])
            await self.send_message(f"✅ Found {len(cv_data.skills)} skills in your CV:\n{skills_str}")
            
            if suggestions:
                await self.send_message("💡 **Improvement suggestions:**\n" + "\n".join(f"• {s}" for s in suggestions[:5]))
            
            # Advance conversation if needed
            if self.conversation_engine.current_state == ConversationState.SKILLS_EXTRACT:
                await self.process_input("My skills are " + skills_str)

        except Exception as e:
            await self.send_message(f"⚠️ Could not analyze CV: {str(e)}")

    async def process_input(self, text: str):
        text = text.strip()
        
        # Initial Greeting
        if not self.history and not text:
            # Check memory for existing user
            if memory_service:
                user_mem = memory_service.get_memory(self.user_id)
                if user_mem and user_mem.name:
                    name = user_mem.name
                    self.user_profile_data["name"] = name
                    await self.send_message(f"Hey {name}! Welcome back. Ready to continue your search?")
                    return

            initial_msg = self.conversation_engine.get_next_question(ConversationState.GREETING)
            await self.send_message(initial_msg)
            return

        # Add user message to history
        self.history.append({"role": "user", "content": text})

        # Get response from conversation engine
        extraction_result, ai_response = await self.conversation_engine.process_user_input(text, self.user_profile_data)
        
        # Update user profile
        self.user_profile_data.update(extraction_result.extracted)
        
        # Update memory
        if memory_service and extraction_result.extracted.get("name"):
             memory_service.update_user_name(self.user_id, extraction_result.extracted["name"])
        
        # Send AI response
        await self.send_message(ai_response)

        # Check if ready to search
        if self.conversation_engine.current_state == ConversationState.READY_TO_SEARCH:
            await self.perform_search()

    async def perform_search(self):
        # Get user's detected language for responses
        name = self.user_profile_data.get("name", "friend")
        
        await self.send_message(f"Got it, {name}! Let me search for jobs that match your profile...")
        
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
                age=25, 
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
            
            # Primary query construction
            goals_list = []
            career_goals = self.user_profile_data.get("career_goals", "")
            skills = user.skills if user.skills else []
            
            if career_goals and career_goals.lower() not in ["general", "skip", "no"]:
                goals_list = [g.strip() for g in career_goals.split(',') if g.strip()]
            elif skills:
                goals_list = skills
            else:
                goals_list = ["Job"] 
            
            location = user.location if user.location else ""
            remote_only = user.remote_ok and not user.onsite_ok
            
            print(f"=" * 60)
            print(f"🔍 TwinWork AI Multi-Source Search:")
            print(f"   Goals: {goals_list}")
            print(f"   Location: '{location}'")
            print(f"   Remote Only: {remote_only}")
            print(f"=" * 60)
            
            search_tasks = []
            
            for goal in goals_list:
                query = goal
                
                # JSearch
                if jsearch_service:
                    print(f"📡 JSearch: '{query}'...")
                    search_tasks.append(
                        jsearch_service.search_jobs(
                            query=query,
                            location="", 
                            remote_only=remote_only,
                            num_pages=2
                        )
                    )
                
                # Adzuna
                if adzuna_service:
                    print(f"📡 Adzuna: '{query}'...")
                    search_tasks.append(
                        adzuna_service.search_jobs(
                            what=query,
                            where=location or "anywhere",
                            country="am"
                        )
                    )

                # Armenian Job Sites
                if armenian_scraper:
                    print(f"🇦🇲 Armenian Sites: '{query}'...")
                    search_tasks.append(
                        armenian_scraper.search_all(
                            query=query,
                            location=location or "Yerevan"
                        )
                    )
            
            # Run searches
            if search_tasks:
                results = await asyncio.gather(*search_tasks, return_exceptions=True)
            else:
                results = []
            
            # Aggregate results
            jobs_found = []
            for result in results:
                if isinstance(result, list):
                    jobs_found.extend(result)
            
            # Deduplicate
            seen = set()
            unique_jobs = []
            for job in jobs_found:
                if job.job_id not in seen:
                    seen.add(job.job_id)
                    unique_jobs.append(job)
            jobs_found = unique_jobs

            if jobs_found:
                # Store for feedback
                self.found_jobs = jobs_found
                
                if memory_service:
                    for goal in goals_list:
                         memory_service.record_search(self.user_id, goal)

                await self.send_message(f"🎉 Found {len(jobs_found)} jobs! Analyzing for schedule matches...")
                
                try:
                    # Match jobs
                    from matcher import JobMatcher
                    matcher = JobMatcher(jobs_found)
                    
                    # Single matches
                    single_matches = matcher.match_single_jobs(user, limit=5)
                    
                    # Pair matches
                    pair_matches = matcher.match_job_pairs(user, limit=3)
                    
                    # Format for frontend
                    single_jobs_data = []
                    
                    # Use raw jobs if no matches (fallback)
                    display_jobs = [m.jobs[0] for m in single_matches] if single_matches else jobs_found[:5]
                    
                    for job in display_jobs:
                         single_jobs_data.append({
                            "title": job.title,
                            "company": job.company,
                            "location": job.location,
                            "hourly_rate": float(job.hourly_rate) if job.hourly_rate else 0,
                            "hours_per_week": int(job.hours_per_week) if job.hours_per_week else 0,
                            "apply_link": job.apply_link,
                            "job_id": job.job_id
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
                                    "hourly_rate": float(jobA.hourly_rate) if jobA.hourly_rate else 0,
                                    "apply_link": jobA.apply_link,
                                    "job_id": jobA.job_id
                                },
                                {
                                    "title": jobB.title,
                                    "company": jobB.company,
                                    "location": jobB.location,
                                    "hourly_rate": float(jobB.hourly_rate) if jobB.hourly_rate else 0,
                                    "apply_link": jobB.apply_link,
                                    "job_id": jobB.job_id
                                }
                            ],
                            "total_hours": int(match.total_hours),
                            "total_pay": float(match.total_pay),
                            "score": int(match.score * 100),
                            "grid": match.schedule_grid if hasattr(match, 'schedule_grid') else None
                        })
                    
                    # Schedule data for grid view (using first 5 single jobs)
                    schedule_data = []
                    for job in display_jobs[:5]:
                        blocks = getattr(job, "schedule_blocks", None)
                        if blocks:
                            schedule_data.append({
                                "job_id": job.job_id,
                                "title": job.title,
                                "schedule": [
                                    {
                                        "day": block.day,
                                        "start": format_time(block.start),
                                        "end": format_time(block.end),
                                    }
                                    for block in blocks
                                ],
                            })

                    # Send to frontend
                    await self.websocket.send_json({
                        "type": "jobs",
                        "single_jobs": single_jobs_data,
                        "pair_jobs": pair_jobs_data,
                        "schedule_data": schedule_data
                    })
                    
                    await self.send_message("✅ Check the panels! You can switch between **Single Jobs**, **Job Pairs**, and **Schedule View** using the tabs.")
                    
                except Exception as match_error:
                    print(f"❌ Matching Error: {match_error}")
                    import traceback
                    traceback.print_exc()
                    await self.send_message("Found jobs, but had trouble with the schedule analysis. Showing raw results.")
            else:
                await self.send_message("😔 No jobs found matching your criteria. Try broader keywords?")
            
        except Exception as e:
            print(f"Search Error: {e}")
            import traceback
            traceback.print_exc()
            await self.send_message("Oops, something went wrong during the search.")

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session = ChatSession(websocket)
    
    # Process initial greeting
    await session.process_input("")
    
    try:
        while True:
            data = await websocket.receive_text()
            await session.handle_message(data) # Use handle_message for JSON support
    except WebSocketDisconnect:
        print(f"Client disconnected")

@app.get("/")
async def get():
    return HTMLResponse(open("static/index.html", "r", encoding="utf-8").read())
