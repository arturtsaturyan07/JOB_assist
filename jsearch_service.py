import os
import re
import json
import hashlib
import random
import httpx
from typing import List, Dict, Any, Optional
from models import Job, TimeBlock

class JSearchService:
    """
    JSearch API service for job searching.
    Supports worldwide job search including Armenia, Russia, etc.
    Aggregates from LinkedIn, Indeed, Glassdoor, and more.
    """
    
    BASE_URL = "https://jsearch.p.rapidapi.com"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-rapidapi-host": "jsearch.p.rapidapi.com",
            "x-rapidapi-key": api_key
        }
    
    async def search_jobs(self, 
                          query: str,
                          location: str = "",
                          country: str = "",
                          remote_only: bool = False,
                          num_pages: int = 1) -> List[Job]:
        """
        Search for jobs using JSearch API.
        
        Args:
            query: Job title, skills, or keywords
            location: City or region (for reference/filtering)
            country: Country name or code (for reference/filtering)
            remote_only: Filter for remote jobs only
            num_pages: Number of pages to fetch (1 page = 10 jobs)
        
        Returns:
            List of Job objects
        """
        # JSearch works best when location is part of the query string for specific regions
        search_query = query.strip()
        
        # Only append location if it's not already there
        if location and location.lower() not in search_query.lower():
            search_query += f" in {location}"
        
        if location:
            # Also double check we didn't just add a duplicate
            pass
        
        # Removed auto-Senior injection to improve results for generic roles like "Taxi Driver" or "Junior dev"
        
        params = {
            "query": search_query,
            "page": "1",
            "num_pages": str(num_pages),
            "date_posted": "all"  # Options: all, today, 3days, week, month
        }
        
        if remote_only:
            params["remote_jobs_only"] = "true"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                print(f"📡 JSearch API Call:")
                print(f"   URL: {self.BASE_URL}/search")
                print(f"   Params: {params}")
                
                response = await client.get(
                    f"{self.BASE_URL}/search",
                    headers=self.headers,
                    params=params
                )
                
                print(f"   Status Code: {response.status_code}")
                response.raise_for_status()
                data = response.json()
                
                print(f"   API Status: {data.get('status')}")
                print(f"   Results count: {len(data.get('data', []))}")
                
                if data.get("status") == "OK":
                    jobs = self._parse_jobs(data.get("data", []))
                    print(f"   Parsed jobs: {len(jobs)}")
                    return jobs
                else:
                    print(f"JSearch API error response: {data}")
                    return []
                    
            except Exception as e:
                print(f"❌ JSearch API Error: {e}")
                import traceback
                traceback.print_exc()
                return []
    
    def _parse_jobs(self, results: List[Dict[str, Any]]) -> List[Job]:
        """Parse JSearch API results into Job objects."""
        jobs = []
        for item in results:
            try:
                # Extract salary info
                salary_min = item.get("job_min_salary")
                salary_max = item.get("job_max_salary")
                salary_period = item.get("job_salary_period")
                if salary_period:
                    salary_period = salary_period.lower()
                else:
                    salary_period = ""
                
                # Convert to hourly rate estimation
                hourly_rate = 0.0
                if salary_max:
                    if salary_period == "yearly" or salary_max > 50000:
                        hourly_rate = salary_max / 2000  # Annual to hourly
                    elif salary_period == "monthly" or (salary_max > 1000 and salary_max < 50000):
                        hourly_rate = salary_max / 160  # Monthly to hourly
                    elif salary_period == "hourly":
                        hourly_rate = salary_max
                    else:
                        hourly_rate = salary_max / 2000  # Default to annual conversion
                else:
                    # Better default based on job title
                    job_title = item.get("job_title", "").lower()
                    if any(role in job_title for role in ["physician", "doctor", "surgeon", "nurse", "pa "]):
                        hourly_rate = 45.0  # Healthcare jobs typically pay more
                    elif any(role in job_title for role in ["engineer", "developer", "architect"]):
                        hourly_rate = 40.0  # Tech jobs
                    elif any(role in job_title for role in ["teacher", "tutor", "instructor"]):
                        hourly_rate = 30.0  # Education
                    elif any(role in job_title for role in ["manager", "director", "executive", "lead"]):
                        hourly_rate = 35.0  # Management
                    else:
                        hourly_rate = 25.0  # Generic fallback
                
                # Extract location
                location_parts = []
                if item.get("job_city"):
                    location_parts.append(item["job_city"])
                if item.get("job_country"):
                    location_parts.append(item["job_country"])
                location = ", ".join(location_parts) if location_parts else "Remote"
                
                # Check if remote
                is_remote = item.get("job_is_remote", False)
                if is_remote:
                    location = f"Remote ({location})" if location != "Remote" else "Remote"
                
                # Infer schedule (Pass location for Remote detection)
                schedule_blocks = self._infer_schedule(item.get("job_title", ""), location)
                total_minutes = sum(b.end - b.start for b in schedule_blocks)
                
                # Special handling for flexible roles: suggest part-time hours to enable pairing
                if not schedule_blocks:  # Flexible schedule
                    # For drivers/flexible roles, suggest 25-35h to allow pairing with other jobs
                    if any(w in job_title.lower() for w in ['driver', 'courier', 'delivery', 'chauffeur']):
                        hours_per_week = 30  # Part-time driver enables pairing
                    else:
                        hours_per_week = 25  # Other flexible roles
                else:
                    hours_per_week = total_minutes // 60 if total_minutes > 0 else 40
                
                # Extract currency
                currency = item.get("job_salary_currency", "USD")
                if not currency and "UK" in location or "London" in location:
                    currency = "GBP"
                elif not currency and "Armenia" in location:
                    currency = "AMD"
                elif not currency:
                    currency = "USD"

                job = Job(
                    job_id=str(item.get("job_id", "")),
                    title=item.get("job_title", "Unknown Job"),
                    location=location,
                    hourly_rate=round(hourly_rate, 2),
                    currency=currency,
                    required_skills=[],  # JSearch doesn't provide structured skills
                    hours_per_week=hours_per_week,
                    schedule_blocks=schedule_blocks,
                    # Additional fields we can add to display
                    company=item.get("employer_name", ""),
                    description=item.get("job_description", "")[:500] if item.get("job_description") else "",
                    apply_link=item.get("job_apply_link") or item.get("job_google_link") or item.get("job_url") or "",
                    posted_date=item.get("job_posted_at_datetime_utc", "")
                )
                jobs.append(job)
                
            except Exception as e:
                print(f"Error parsing job item: {e}")
                continue
        
        return jobs
        
    def _infer_schedule(self, title: str, location: str = "") -> List[TimeBlock]:
        """Infer schedule blocks based on job title keywords"""
        title_lower = title.lower()
        loc_lower = (location or "").lower()
        
        # Remote = Flexible (No fixed blocks, pairs with anything)
        if "remote" in title_lower or "remote" in loc_lower:
            return []
            
        # Flexible Roles -> No fixed blocks (allows user to work whenever)
        if any(w in title_lower for w in ['driver', 'taxi', 'courier', 'delivery', 'uber', 'lyft', 'freelance', 'chauffeur', 'van driver', 'owner']):
            return []
            
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
        
        if any(w in title_lower for w in ['call center', 'support', 'operator', 'agent']):
            # Shifts
            if hash(title) % 2 == 0:
                # Morning: 08:00 - 14:00
                return [TimeBlock(day=d, start=480, end=840) for d in days]
            else:
                # Afternoon: 14:00 - 20:00
                return [TimeBlock(day=d, start=840, end=1200) for d in days]
                
        elif "part time" in title_lower or "part-time" in title_lower:
            return [TimeBlock(day=d, start=600, end=840) for d in days]
            
        # Default: 09:00 - 18:00 Mon-Fri
        return [TimeBlock(day=d, start=540, end=1080) for d in days]


class LinkedInJobService:
    """
    LinkedIn Job Search API service.
    Direct LinkedIn job search through RapidAPI.
    """
    
    BASE_URL = "https://linkedin-job-search-api.p.rapidapi.com"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-rapidapi-host": "linkedin-job-search-api.p.rapidapi.com",
            "x-rapidapi-key": api_key
        }
    
    async def search_jobs(self, 
                          keywords: str,
                          location: str = "",
                          limit: int = 10) -> List[Job]:
        """Search LinkedIn jobs."""
        
        params = {
            "keywords": keywords,
            "locationId": "",
            "datePosted": "anyTime",
            "sort": "mostRelevant"
        }
        
        if location:
            params["keywords"] = f"{keywords} {location}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/active-jb-7d",
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                return self._parse_jobs(data[:limit] if isinstance(data, list) else [])
                
            except Exception as e:
                print(f"LinkedIn API Error: {e}")
                return []
    
    def _parse_jobs(self, results: List[Dict[str, Any]]) -> List[Job]:
        """Parse LinkedIn API results into Job objects."""
        jobs = []
        for item in results:
            try:
                job = Job(
                    job_id=str(item.get("id", "")),
                    title=item.get("title", "Unknown Job"),
                    location=item.get("location", "Unknown"),
                    hourly_rate=25.0,  # LinkedIn doesn't always provide salary
                    required_skills=[],
                    hours_per_week=40,
                    schedule_blocks=[],
                    company=item.get("company", {}).get("name", ""),
                    description="",
                    apply_link=item.get("url", ""),
                    posted_date=item.get("postedDate", "")
                )
                jobs.append(job)
            except Exception as e:
                print(f"Error parsing LinkedIn job: {e}")
                continue
        return jobs
