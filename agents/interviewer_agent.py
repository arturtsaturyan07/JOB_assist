from typing import Dict, Any, List
from resilience.resilient_llm_gateway import ResilientLLMGateway
import json

class InterviewerAgent:
    """
    Agent for conducting mock interviews based on job descriptions.
    """
    def __init__(self):
        self.llm = ResilientLLMGateway()

    async def generate_questions(self, job_title: str, job_description: str) -> List[str]:
        """Generate 3 technical/behavioral questions for the role."""
        print(f"🎤 Interviewer: Generating questions for {job_title}")
        
        prompt = f"""
        You are a hiring manager for a '{job_title}' role.
        Job Description: {job_description[:500]}...
        
        Generate 3 specific interview questions (1 technical, 1 behavioral, 1 situational).
        Target questions directly at this role.
        
        Return JSON list of strings:
        ["Question 1", "Question 2", "Question 3"]
        """
        
        try:
            response = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system_instruction="You are a tough but fair hiring manager.",
                json_mode=True
            )
            clean = response.replace('```json', '').replace('```', '').strip()
            data = json.loads(clean)
            
            # Handle {"questions": [...]} format
            if isinstance(data, dict):
                for key in ["questions", "interview_questions", "list"]:
                    if key in data and isinstance(data[key], list):
                        return data[key]
                # Fallback: values() if it looks like a list
                return list(data.values())[0] if data else []
            
            return data if isinstance(data, list) else []
        except Exception as e:
            print(f"Error generating questions: {e}")
            return ["Tell me about yourself.", "Why do you want this job?", "What are your strengths?"]

    async def review_answer(self, question: str, answer: str) -> Dict[str, Any]:
        """Review the user's answer and provide feedback."""
        prompt = f"""
        I asked the candidate: "{question}"
        They answered: "{answer}"
        
        Evaluate this answer.
        1. Rate it 1-10.
        2. Identify 1 strength.
        3. Identify 1 weakness.
        4. Provide an improved version.
        
        Return JSON:
        {{
            "rating": 7,
            "strength": "Good enthusiasm",
            "weakness": "Lack of specific examples",
            "feedback": "Try to use the STAR method...",
            "improved_answer": "..."
        }}
        """
        try:
            response = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system_instruction="You are an interview coach.",
                json_mode=True
            )
            clean = response.replace('```json', '').replace('```', '').strip()
            return json.loads(clean)
        except Exception as e:
            return {"feedback": "Could not analyze answer. Please try again."}
