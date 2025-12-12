import json
import re
import asyncio
from typing import List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
try:
    import pdfplumber
except ImportError:
    pdfplumber = None

# Import Models
from models import format_time

# Import New Architecture Components
from llm_gateway import LLMGateway
from agents.user_agent import UserContextAgent
from agents.discovery_agent import JobDiscoveryAgent
from agents.matching_agent import MatchingAgent
from cv_service import analyze_cv

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def start():
    with open("static/index.html") as f:
        return HTMLResponse(content=f.read())

@app.post("/upload_cv")
async def upload_cv(file: UploadFile = File(...)):
    print(f"📄 Received CV upload: {file.filename}")
    
    content_type = file.content_type
    filename = file.filename.lower()
    text = ""
    
    try:
        if filename.endswith(".pdf"):
            if not pdfplumber:
                return JSONResponse({"status": "error", "error": "PDF support not installed (pip install pdfplumber)"}, status_code=500)
            
            try:
                with pdfplumber.open(file.file) as pdf:
                    for page in pdf.pages:
                        extract = page.extract_text()
                        if extract:
                            text += extract + "\n"
            except Exception as e:
                print(f"❌ PDF reading error: {e}")
                return JSONResponse({"status": "error", "error": f"Invalid PDF file: {str(e)}"}, status_code=400)
                    
        elif filename.endswith(".txt") or content_type == "text/plain":
            content = await file.read()
            text = content.decode("utf-8")
            
        else:
            return JSONResponse({"status": "error", "error": "Only .pdf and .txt files are supported currently"}, status_code=400)
            
        if not text.strip():
             return JSONResponse({"status": "error", "error": "Could not read text from this file. If this is a scanned PDF (image), please convert it to text first."}, status_code=400)
             
        return {"status": "success", "text": text.strip()}
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)

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
                    cv_text = data.get("content", "")
                    await self.handle_cv_upload(cv_text)
                    return
            else:
                text = str(data)
                
            await self.process_input(text)
            
        except json.JSONDecodeError:
            await self.process_input(raw_message)

    async def handle_cv_upload(self, cv_text: str):
        """Process uploaded CV text and update agent state"""
        await self.send_message("📄 Analyzing your CV... this might take a moment.")
        
        try:
            # 1. Analyze with CV Service
            analysis = await analyze_cv(cv_text)
            cv_data = analysis.get('cv_data', {})
            skills = cv_data.get('skills', [])
            name = cv_data.get('name')
            experience = cv_data.get('experience', [])
            
            # 2. Update User Agent Profile
            # Create a synthetic "extraction" result to feed into the agent
            extracted_info = {
                "skills": skills,
                "experience_years": cv_data.get('total_experience_years'),
                "location": cv_data.get('location'),
                "cv_summary": cv_data.get('summary')
            }
            if name:
                extracted_info["name"] = name
                
            # Safely update profile
            for k, v in extracted_info.items():
                if v:
                    self.user_agent.user_profile[k] = v
                    
            # 3. Formulate response
            response = f"Thanks! I've analyzed your CV."
            if name:
                response += f" Nice to meet you, {name}!"
            
            if skills:
                top_skills = ", ".join(skills[:5])
                response += f"\n\nI see you have skills in: **{top_skills}**"
                if len(skills) > 5:
                    response += f" and {len(skills)-5} others."
            
            response += "\n\nIs this correct? Would you like me to start searching for jobs based on this?"
            
            # Send results to frontend (so UI can update state if needed)
            await self.websocket.send_json({
                "type": "cv_analysis",
                "skills": skills,
                "name": name
            })
            
            await self.send_message(response)
            
        except Exception as e:
            print(f"Error handling CV: {e}")
            await self.send_message("I had some trouble analyzing your CV, but I received the text. Let's continue chatting!")

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
        
        # Split query for multi-role search
        sub_queries = [q.strip() for q in re.split(r' and |,|&', query) if q.strip()]
        if not sub_queries:
            sub_queries = [query]
            
        all_jobs = []
        seen_ids = set()
        
        for sub_q in sub_queries:
             print(f"🔎 Searching for sub-query: {sub_q}")
             sub_results = await discovery_agent.search(query=sub_q, location=loc, remote_only=remote_only)
             for job in sub_results:
                 if job.job_id not in seen_ids:
                     # Tag the job with the query that found it for diversity logic
                     job.search_query = sub_q
                     all_jobs.append(job)
                     seen_ids.add(job.job_id)
                     
        jobs = all_jobs
        
        if not jobs:
            await self.send_message("I couldn't find any jobs right now. Try broadening your location or skills.")
            return

        self.found_jobs.extend([j for j in jobs if j.job_id not in {existing.job_id for existing in self.found_jobs}])
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
        # Includes both Single jobs and Pair jobs
        jobs_for_schedule = []
        jobs_for_schedule.extend(matches.get("raw_top_jobs", []))
        for p in matches.get("pairs", []):
            jobs_for_schedule.extend(p.jobs)
            
        # Deduplicate by ID
        seen_sched_ids = set()
        for job in jobs_for_schedule:
            if job.job_id in seen_sched_ids: continue
            seen_sched_ids.add(job.job_id)
            
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
