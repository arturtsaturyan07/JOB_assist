"""
RemoteOK API Service
Free API for remote job listings - no authentication required
API: https://remoteok.com/api
"""
import asyncio
import logging
from typing import List
import httpx
from models import Job
from schedule_inference import infer_schedule_from_title

logger = logging.getLogger(__name__)

class RemoteOKService:
    """RemoteOK API client for remote jobs"""
    
    def __init__(self):
        self.base_url = "https://remoteok.com/api"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    async def search_jobs(
        self,
        query: str = "",
        limit: int = 100
    ) -> List[Job]:
        """
        Search RemoteOK for remote jobs
        
        Args:
            query: Job title or keywords (optional, will filter results)
            limit: Maximum number of jobs to return
            
        Returns:
            List of Job objects
        """
        try:
            logger.info(f"🔍 Searching RemoteOK API for: {query or 'all remote jobs'}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, headers=self.headers)
                response.raise_for_status()
                
                data = response.json()
                
                # First item is metadata, skip it
                if isinstance(data, list) and len(data) > 0:
                    jobs_data = data[1:] if data[0].get('id') == 'legal' else data
                else:
                    jobs_data = []
                
                jobs = []
                query_lower = query.lower() if query else ""
                
                for job_data in jobs_data[:limit * 2]:  # Get more to filter
                    try:
                        # Filter by query if provided
                        if query_lower:
                            title = job_data.get('position', '').lower()
                            tags = ' '.join(job_data.get('tags', [])).lower()
                            if query_lower not in title and query_lower not in tags:
                                continue
                        
                        job = self._parse_job(job_data)
                        if job:
                            jobs.append(job)
                            
                        if len(jobs) >= limit:
                            break
                            
                    except Exception as e:
                        logger.debug(f"Error parsing RemoteOK job: {e}")
                        continue
                
                logger.info(f"✅ RemoteOK returned {len(jobs)} remote jobs")
                return jobs
                
        except Exception as e:
            logger.error(f"❌ RemoteOK API error: {e}")
            return []
    
    def _parse_job(self, data: dict) -> Job:
        """Parse RemoteOK job data to Job object"""
        try:
            # Extract salary
            salary_min = data.get('salary_min', 0)
            salary_max = data.get('salary_max', 0)
            hourly_rate = 30.0  # Default for remote jobs
            
            if salary_min or salary_max:
                annual_salary = salary_max or salary_min
                hourly_rate = annual_salary / 2000 if annual_salary > 1000 else annual_salary
            
            # Build apply link
            slug = data.get('slug', '')
            apply_link = f"https://remoteok.com/remote-jobs/{slug}" if slug else data.get('url', '')
            
            # Get title
            title = data.get('position', 'Remote Position')
            
            # Infer schedule (remote jobs typically flexible)
            schedule_blocks, hours_per_week = infer_schedule_from_title(title, "Remote")
            
            job = Job(
                job_id=f"remoteok_{data.get('id', hash(apply_link))}",
                title=title,
                company=data.get('company', ''),
                location="Remote",
                hourly_rate=hourly_rate,
                required_skills=data.get('tags', [])[:5],  # Limit to 5 tags
                hours_per_week=hours_per_week,
                schedule_blocks=schedule_blocks,
                apply_link=apply_link,
                description=data.get('description', '')[:500],
                job_source="remoteok",
                posted_date=data.get('date', '')
            )
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing RemoteOK job: {e}")
            return None
