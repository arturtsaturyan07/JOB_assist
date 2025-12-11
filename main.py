import json
import asyncio
from typing import List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# Import Models
from models import format_time

# Import New Architecture Components
from llm_gateway import LLMGateway
from agents.user_agent import UserContextAgent
from agents.discovery_agent import JobDiscoveryAgent
from agents.matching_agent import MatchingAgent

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Initialization ---
print("🚀 Initializing TwinWork AI Agents...")

# 0. Infrastructure
llm_gateway = LLMGateway()

# 1. Agents
discovery_agent = JobDiscoveryAgent()
matching_agent = MatchingAgent()

# Note: UserContextAgent is stateful per session, so we init it in the WebSocket handler

print("✅ Agents Ready")

class ChatSession:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.user_id = str(id(websocket))
        
        # Initialize User Agent for this session
        self.user_agent = UserContextAgent(llm_gateway)
        
        self.found_jobs = []

    async def send_message(self, message: str, type: str = "text", options: List[str] = None):
        await self.websocket.send_json({
            "type": type,
            "message": message,
            "options": options
        })

    async def handle_message(self, raw_message: str):
        try:
            # Parse JSON if possible
            data = json.loads(raw_message)
            text = ""
            if isinstance(data, dict):
                text = data.get("text", data.get("message", ""))
                # Handle types directly if needed (e.g. feedback)
                if data.get("type") == "feedback":
                    # TODO: Implement feedback handling via Agent
                    return
                if data.get("type") == "cv_upload":
                    # TODO: Implement generic file/CV handling
                    await self.send_message("CV upload received (Parsing not yet connected to Agent).")
                    return
            else:
                text = str(data)
                
            await self.process_input(text)
            
        except json.JSONDecodeError:
            await self.process_input(raw_message)

    async def process_input(self, text: str):
        # 1. Delegate to User Agent
        response_text, ready_to_search = await self.user_agent.process_message(text)
        
        # 2. Send Agent Response
        if response_text:
            await self.send_message(response_text)
            
        # 3. Check for Search Trigger
        if ready_to_search:
            await self.perform_search()

    async def perform_search(self):
        profile = self.user_agent.user_profile
        name = profile.get("name", "there")
        
        await self.send_message(f"Searching for jobs matching your profile, {name}...")
        
        # 1. Discovery Agent
        # Construct query from job_role > skills > goals
        query = profile.get("job_role")
        
        if not query:
            skills = profile.get("skills", [])
            if skills:
                # Join top 2 skills to avoid overly specific long queries
                query = " ".join(skills[:2]) if isinstance(skills, list) else str(skills)
        
        if not query:
             query = profile.get("career_goals", "General")
            
        loc = profile.get("location", "Yerevan")
        remote_ok = profile.get("remote_ok", False) # Default to false if not specified
        remote_only = remote_ok and not profile.get("onsite_ok", True)
        
        jobs = await discovery_agent.search(query=query, location=loc, remote_only=remote_only)
        
        if not jobs:
            await self.send_message("I couldn't find any jobs right now. Try broadening your location or skills.")
            return

        self.found_jobs = jobs
        await self.send_message(f"Found {len(jobs)} jobs! Analyzing best matches...")

        # 2. Matching Agent
        matches = matching_agent.analyze_matches(profile, jobs)
        
        # 3. Present Results
        single_jobs_data = []
        for job in matches.get("raw_top_jobs", []):
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
        for match in matches.get("pairs", []):
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
                "score": int(getattr(match, 'score', 0) * 100),
                "grid": match.schedule_grid if hasattr(match, 'schedule_grid') else None
            })

        schedule_data = []
        # Basic schedule viz logic
        for job in matches.get("raw_top_jobs", []):
            if hasattr(job, "schedule_blocks") and job.schedule_blocks:
                 schedule_data.append({
                    "job_id": job.job_id,
                    "title": job.title,
                    "schedule": [
                        {"day": b.day, "start": format_time(b.start), "end": format_time(b.end)}
                        for b in job.schedule_blocks
                    ]
                })

        await self.websocket.send_json({
            "type": "jobs",
            "single_jobs": single_jobs_data,
            "pair_jobs": pair_jobs_data,
            "schedule_data": schedule_data
        })
        
        await self.send_message("Here are the best matches I found for you!")


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session = ChatSession(websocket)
    
    # Process initial empty message to trigger greeting
    await session.process_input("")
    
    try:
        while True:
            data = await websocket.receive_text()
            await session.handle_message(data)
    except WebSocketDisconnect:
        print(f"Client disconnected")

@app.get("/")
async def get():
    return HTMLResponse(open("static/index.html", "r", encoding="utf-8").read())
