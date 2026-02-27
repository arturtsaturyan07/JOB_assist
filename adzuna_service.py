import os
import httpx
from typing import List, Optional, Dict, Any
from models import Job, TimeBlock

class AdzunaService:
    BASE_URL = "https://api.adzuna.com/v1/api/jobs"

    def __init__(self, app_id: str, app_key: str, country: str = "ae"):
        self.app_id = app_id
        self.app_key = app_key
        self.country = country

    async def search_jobs(self, 
                          what: str, 
                          where: str, 
                          country: str = None,
                          results_per_page: int = 10, 
                          content_type: str = "application/json") -> List[Job]:
        
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": what,
            "where": where,
            "results_per_page": results_per_page,
            "content-type": content_type
        }

        async with httpx.AsyncClient() as client:
            try:
                # Use provided country or default
                target_country = country if country else self.country
                
                # Construct the full URL: /v1/api/jobs/{country}/search/1
                url = f"{self.BASE_URL}/{target_country}/search/1"
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                return self._parse_jobs(data.get("results", []))
            except httpx.HTTPStatusError as e:
                print(f"Adzuna API HTTP Error: {e.response.status_code} - {e.response.text}")
                return []
            except Exception as e:
                print(f"Adzuna API Error: {type(e).__name__}: {e}")
                return []

    def _parse_jobs(self, results: List[Dict[str, Any]]) -> List[Job]:
        jobs = []
        for item in results:
            try:
                # Adzuna doesn't provide all fields we need for the demo logic (like schedule blocks),
                # so we will mock some of them or use defaults to ensure compatibility.
                
                # Extract salary (Adzuna gives min/max, we'll take average or max)
                salary_min = item.get("salary_min")
                salary_max = item.get("salary_max")
                hourly_rate = 0.0
                
                # Rough estimation if salary is annual (common in Adzuna)
                # Assuming 2000 hours/year for conversion if needed, but let's just use a placeholder if missing.
                if salary_max:
                    # Very rough heuristic: if > 1000, assume monthly or annual. 
                    # For demo purposes, let's just map it to a "score" or keep it as is if it looks like hourly.
                    # Let's assume the demo wants hourly.
                    if salary_max > 1000: 
                        hourly_rate = salary_max / 2000 # Annual to hourly
                    else:
                        hourly_rate = salary_max
                else:
                    hourly_rate = 20.0 # Default fallback

                job = Job(
                    job_id=str(item.get("id")),
                    title=item.get("title", "Unknown Job"),
                    company=item.get("company", {}).get("display_name", "") if isinstance(item.get("company"), dict) else "",
                    location=item.get("location", {}).get("display_name", "Unknown Location"),
                    hourly_rate=round(hourly_rate, 2),
                    required_skills=[], # Adzuna doesn't provide structured skills
                    hours_per_week=40, # Default
                    schedule_blocks=[], # Default empty, or we could generate random ones for the demo
                    apply_link=item.get("redirect_url", ""),  # Adzuna provides redirect_url for applications
                    description=item.get("description", ""),
                    job_source="adzuna"
                )
                jobs.append(job)
            except Exception as e:
                print(f"Error parsing job item: {e}")
                continue
        return jobs
