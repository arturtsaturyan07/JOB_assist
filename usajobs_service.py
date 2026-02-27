"""
USAJobs API Service
Free API for US Federal Government jobs - no rate limits
API: https://developer.usajobs.gov/
Requires free API key from https://developer.usajobs.gov/APIRequest/Index
"""
import asyncio
import logging
from typing import List, Optional
import httpx
from models import Job

logger = logging.getLogger(__name__)

class USAJobsService:
    """USAJobs API client for US federal government jobs"""
    
    def __init__(self, api_key: Optional[str] = None, email: Optional[str] = None):
        self.base_url = "https://data.usajobs.gov/api/search"
        self.api_key = api_key
        self.email = email
        
        if not api_key:
            logger.warning("⚠️ USAJobs API key not provided - service will be inactive")
            logger.info("ℹ️ Get free API key at: https://developer.usajobs.gov/APIRequest/Index")
    
    async def search_jobs(
        self,
        query: str = "",
        location: str = "",
        limit: int = 100
    ) -> List[Job]:
        """
        Search USAJobs for federal government positions
        
        Args:
            query: Job title or keywords
            location: US location (city, state, or zip code)
            limit: Maximum number of jobs (max 500 per request)
            
        Returns:
            List of Job objects
        """
        if not self.api_key:
            logger.info("ℹ️ USAJobs API key not configured - skipping")
            return []
        
        try:
            logger.info(f"🔍 Searching USAJobs API for: {query}")
            
            headers = {
                'Host': 'data.usajobs.gov',
                'User-Agent': self.email or 'job-search-app@example.com',
                'Authorization-Key': self.api_key
            }
            
            params = {
                'ResultsPerPage': min(limit, 500)
            }
            
            if query:
                params['Keyword'] = query
            
            if location:
                params['LocationName'] = location
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.base_url,
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                search_result = data.get('SearchResult', {})
                results = search_result.get('SearchResultItems', [])
                
                jobs = []
                for item in results:
                    try:
                        job_data = item.get('MatchedObjectDescriptor', {})
                        job = self._parse_job(job_data)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        logger.debug(f"Error parsing USAJobs job: {e}")
                        continue
                
                logger.info(f"✅ USAJobs returned {len(jobs)} federal jobs")
                return jobs
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ USAJobs API error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"❌ USAJobs API error: {e}")
            return []
    
    def _parse_job(self, data: dict) -> Optional[Job]:
        """Parse USAJobs job data to Job object"""
        try:
            # Extract salary
            salary_min = data.get('PositionRemuneration', [{}])[0].get('MinimumRange', 0)
            salary_max = data.get('PositionRemuneration', [{}])[0].get('MaximumRange', 0)
            
            hourly_rate = 25.0
            if salary_min or salary_max:
                annual_salary = salary_max or salary_min
                hourly_rate = annual_salary / 2000 if annual_salary > 1000 else annual_salary
            
            # Extract locations
            locations = data.get('PositionLocation', [])
            location_str = locations[0].get('LocationName', 'USA') if locations else 'USA'
            
            # Apply link
            apply_link = data.get('PositionURI', '')
            
            # Organization as company
            org_name = data.get('OrganizationName', 'US Federal Government')
            
            job = Job(
                job_id=f"usajobs_{data.get('PositionID', hash(apply_link))}",
                title=data.get('PositionTitle', 'Federal Position'),
                company=org_name,
                location=location_str,
                hourly_rate=hourly_rate,
                required_skills=[],
                hours_per_week=40,
                schedule_blocks=[],
                apply_link=apply_link,
                description=data.get('UserArea', {}).get('Details', {}).get('JobSummary', '')[:500],
                job_source="usajobs",
                posted_date=data.get('PublicationStartDate', '')
            )
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing USAJobs job: {e}")
            return None
