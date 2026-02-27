"""
The Muse API Service
Free tier: 500 requests/day
API: https://www.themuse.com/developers/api/v2
"""
import asyncio
import logging
from typing import List, Optional
import httpx
from models import Job
from schedule_inference import infer_schedule_from_title

logger = logging.getLogger(__name__)

class TheMuseService:
    """The Muse API client for quality job listings"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://www.themuse.com/api/public/jobs"
        self.api_key = api_key  # Optional - works without key but with rate limits
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    async def search_jobs(
        self,
        query: str = "",
        location: str = "",
        limit: int = 100
    ) -> List[Job]:
        """
        Search The Muse for jobs
        
        Args:
            query: Job title or keywords
            location: Location to search
            limit: Maximum number of jobs (max 100 per request)
            
        Returns:
            List of Job objects
        """
        try:
            logger.info(f"🔍 Searching The Muse API for: {query}")
            
            params = {
                'page': 0,
                'descending': 'true'
            }
            
            if query:
                params['category'] = query
            
            if location:
                params['location'] = location
            
            if self.api_key:
                params['api_key'] = self.api_key
            
            jobs = []
            pages_to_fetch = min(5, (limit // 20) + 1)  # 20 results per page
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                for page in range(pages_to_fetch):
                    params['page'] = page
                    
                    response = await client.get(
                        self.base_url,
                        params=params,
                        headers=self.headers
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    results = data.get('results', [])
                    
                    if not results:
                        break
                    
                    for job_data in results:
                        try:
                            job = self._parse_job(job_data)
                            if job:
                                jobs.append(job)
                                
                            if len(jobs) >= limit:
                                break
                                
                        except Exception as e:
                            logger.debug(f"Error parsing Muse job: {e}")
                            continue
                    
                    if len(jobs) >= limit:
                        break
                    
                    # Rate limiting
                    await asyncio.sleep(0.5)
            
            logger.info(f"✅ The Muse returned {len(jobs)} jobs")
            return jobs
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("⚠️ The Muse API rate limit exceeded (500 requests/day)")
            else:
                logger.error(f"❌ The Muse API error: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ The Muse API error: {e}")
            return []
    
    def _parse_job(self, data: dict) -> Optional[Job]:
        """Parse The Muse job data to Job object"""
        try:
            # Extract locations
            locations = data.get('locations', [])
            location_str = locations[0].get('name', 'Remote') if locations else 'Remote'
            
            # Extract company
            company_data = data.get('company', {})
            company_name = company_data.get('name', '')
            
            # Build apply link
            refs = data.get('refs', {})
            apply_link = refs.get('landing_page', '')
            
            # Categories as skills
            categories = data.get('categories', [])
            skills = [cat.get('name', '') for cat in categories[:5]]
            
            # Get title
            title = data.get('name', 'Position')
            
            # Infer schedule from title
            schedule_blocks, hours_per_week = infer_schedule_from_title(title, location_str)
            
            job = Job(
                job_id=f"muse_{data.get('id', hash(apply_link))}",
                title=title,
                company=company_name,
                location=location_str,
                hourly_rate=30.0,  # Default - Muse doesn't provide salary in API
                required_skills=skills,
                hours_per_week=hours_per_week,
                schedule_blocks=schedule_blocks,
                apply_link=apply_link,
                description=data.get('contents', '')[:500],
                job_source="themuse",
                posted_date=data.get('publication_date', '')
            )
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing Muse job: {e}")
            return None
