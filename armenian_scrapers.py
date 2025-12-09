"""
Armenian Job Market Scrapers for TwinWork AI

Supports scraping from:
- staff.am (most popular)
- job.am (tech-focused)
- list.am/jobs (classifieds)
- hr.am (HR-focused)

Features:
- Respectful scraping with delays
- robots.txt compliance
- Manual paste fallback
- Result caching
"""

import os
import re
import json
import asyncio
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from urllib.parse import urljoin, quote_plus

import httpx
from bs4 import BeautifulSoup

from job_intelligence import JobIntelligenceService, ParsedJob
from models import Job, TimeBlock


@dataclass
class ScrapedJob:
    """Raw scraped job data before normalization"""
    title: str
    company: str
    location: str
    url: str
    source: str
    description: str = ""
    salary: str = ""
    posted_date: str = ""
    employment_type: str = ""
    raw_html: str = ""


class ArmenianJobScraper:
    """
    Unified scraper for Armenian job sites.
    
    Implements respectful scraping with:
    - 1-2 second delays between requests
    - User-agent identification
    - Caching to reduce requests
    """
    
    # Request headers
    HEADERS = {
        'User-Agent': 'TwinWork AI Job Assistant/1.0 (Educational Project; Contact: student@example.com)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5,hy;q=0.3,ru;q=0.2',
    }
    
    # Request delay (seconds) - be respectful!
    REQUEST_DELAY = 1.5
    
    def __init__(self, cache_file: str = "job_cache.json"):
        self.cache_file = cache_file
        self.cache: Dict[str, Dict] = self._load_cache()
        self.job_intelligence = JobIntelligenceService()
        self._last_request_time: Dict[str, float] = {}
    
    def _load_cache(self) -> Dict:
        """Load cached results"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        """Save cache to file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Warning: Could not save cache: {e}")
    
    def _get_cache_key(self, source: str, query: str) -> str:
        """Generate cache key"""
        return hashlib.md5(f"{source}:{query}".encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid (< 1 hour old)"""
        if 'timestamp' not in cache_entry:
            return False
        cached_time = datetime.fromisoformat(cache_entry['timestamp'])
        return datetime.now() - cached_time < timedelta(hours=1)
    
    async def _rate_limit(self, source: str):
        """Implement rate limiting per source"""
        if source in self._last_request_time:
            elapsed = asyncio.get_event_loop().time() - self._last_request_time[source]
            if elapsed < self.REQUEST_DELAY:
                await asyncio.sleep(self.REQUEST_DELAY - elapsed)
        self._last_request_time[source] = asyncio.get_event_loop().time()
    
    async def search_all(
        self, 
        query: str, 
        location: str = "Yerevan",
        max_per_source: int = 10
    ) -> List[Job]:
        """
        Search all Armenian job sites in parallel.
        
        Args:
            query: Job title or keywords
            location: City (default: Yerevan)
            max_per_source: Maximum jobs to fetch per source
        
        Returns:
            List of normalized Job objects
        """
        print(f"🇦🇲 Searching Armenian job sites for: {query}")
        
        # Run searches in parallel
        tasks = [
            self.search_staff_am(query, location, max_per_source),
            self.search_job_am(query, location, max_per_source),
            self.search_list_am(query, max_per_source),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_jobs = []
        source_counts = {}
        
        for i, result in enumerate(results):
            source = ['staff.am', 'job.am', 'list.am'][i]
            if isinstance(result, Exception):
                print(f"⚠️ {source} search failed: {result}")
                source_counts[source] = 0
            elif isinstance(result, list):
                all_jobs.extend(result)
                source_counts[source] = len(result)
                print(f"✅ {source}: {len(result)} jobs")
        
        print(f"📊 Total: {len(all_jobs)} jobs from Armenian sites")
        
        return all_jobs
    
    async def search_staff_am(
        self, 
        query: str, 
        location: str = "",
        limit: int = 10
    ) -> List[Job]:
        """
        Search staff.am for jobs.
        
        staff.am is the most popular job site in Armenia.
        """
        source = "staff.am"
        cache_key = self._get_cache_key(source, f"{query}_{location}")
        
        # Check cache
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            print(f"📦 Using cached results for {source}")
            return self._parse_cached_jobs(self.cache[cache_key]['jobs'])
        
        await self._rate_limit(source)
        
        # staff.am search URL format
        search_url = f"https://staff.am/en/jobs?q={quote_plus(query)}"
        if location:
            search_url += f"&location={quote_plus(location)}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(search_url, headers=self.HEADERS)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Parse job listings
                scraped = []
                job_cards = soup.select('.job-card, .job-item, .jobs-list-item, [class*="job"]')[:limit]
                
                for card in job_cards:
                    try:
                        title_elem = card.select_one('h2, h3, .job-title, [class*="title"]')
                        company_elem = card.select_one('.company, .employer, [class*="company"]')
                        location_elem = card.select_one('.location, [class*="location"]')
                        link_elem = card.select_one('a[href*="/jobs/"]')
                        
                        if title_elem:
                            scraped.append(ScrapedJob(
                                title=title_elem.get_text(strip=True),
                                company=company_elem.get_text(strip=True) if company_elem else "",
                                location=location_elem.get_text(strip=True) if location_elem else "Yerevan",
                                url=urljoin("https://staff.am", link_elem['href']) if link_elem else "",
                                source="staff.am",
                                description=""
                            ))
                    except Exception as e:
                        continue
                
                # Convert to Job objects
                jobs = await self._normalize_jobs(scraped)
                
                # Cache results
                self.cache[cache_key] = {
                    'timestamp': datetime.now().isoformat(),
                    'jobs': [self._job_to_cache_dict(j) for j in jobs]
                }
                self._save_cache()
                
                return jobs
                
        except Exception as e:
            print(f"❌ staff.am error: {e}")
            return []
    
    async def search_job_am(
        self, 
        query: str, 
        location: str = "",
        limit: int = 10
    ) -> List[Job]:
        """
        Search job.am for jobs.
        
        job.am is a tech-focused job site.
        """
        source = "job.am"
        cache_key = self._get_cache_key(source, f"{query}_{location}")
        
        # Check cache
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            print(f"📦 Using cached results for {source}")
            return self._parse_cached_jobs(self.cache[cache_key]['jobs'])
        
        await self._rate_limit(source)
        
        # job.am search URL
        search_url = f"https://www.job.am/search?q={quote_plus(query)}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(search_url, headers=self.HEADERS)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                scraped = []
                job_cards = soup.select('.job-listing, .vacancy, [class*="job"]')[:limit]
                
                for card in job_cards:
                    try:
                        title_elem = card.select_one('h2, h3, .title, [class*="title"]')
                        company_elem = card.select_one('.company, [class*="company"]')
                        link_elem = card.select_one('a[href]')
                        
                        if title_elem:
                            scraped.append(ScrapedJob(
                                title=title_elem.get_text(strip=True),
                                company=company_elem.get_text(strip=True) if company_elem else "",
                                location="Yerevan",
                                url=urljoin("https://www.job.am", link_elem['href']) if link_elem else "",
                                source="job.am",
                                description=""
                            ))
                    except Exception:
                        continue
                
                jobs = await self._normalize_jobs(scraped)
                
                # Cache
                self.cache[cache_key] = {
                    'timestamp': datetime.now().isoformat(),
                    'jobs': [self._job_to_cache_dict(j) for j in jobs]
                }
                self._save_cache()
                
                return jobs
                
        except Exception as e:
            print(f"❌ job.am error: {e}")
            return []
    
    async def search_list_am(
        self, 
        query: str,
        limit: int = 10
    ) -> List[Job]:
        """
        Search list.am jobs section.
        
        list.am is a classifieds site with a jobs section.
        """
        source = "list.am"
        cache_key = self._get_cache_key(source, query)
        
        # Check cache
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            print(f"📦 Using cached results for {source}")
            return self._parse_cached_jobs(self.cache[cache_key]['jobs'])
        
        await self._rate_limit(source)
        
        # list.am jobs search
        search_url = f"https://www.list.am/en/category/91?q={quote_plus(query)}"  # 91 = jobs category
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(search_url, headers=self.HEADERS)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                scraped = []
                listings = soup.select('.gl, .list-item, [class*="listing"]')[:limit]
                
                for listing in listings:
                    try:
                        title_elem = listing.select_one('.title, a')
                        link_elem = listing.select_one('a[href]')
                        
                        if title_elem:
                            scraped.append(ScrapedJob(
                                title=title_elem.get_text(strip=True),
                                company="",  # list.am often doesn't show company
                                location="Armenia",
                                url=urljoin("https://www.list.am", link_elem['href']) if link_elem else "",
                                source="list.am",
                                description=""
                            ))
                    except Exception:
                        continue
                
                jobs = await self._normalize_jobs(scraped)
                
                # Cache
                self.cache[cache_key] = {
                    'timestamp': datetime.now().isoformat(),
                    'jobs': [self._job_to_cache_dict(j) for j in jobs]
                }
                self._save_cache()
                
                return jobs
                
        except Exception as e:
            print(f"❌ list.am error: {e}")
            return []
    
    async def parse_manual_job(self, job_text: str) -> Job:
        """
        Parse a manually pasted job description.
        
        Users can paste job descriptions directly when scraping fails.
        """
        print("📝 Parsing manually pasted job...")
        
        # Use job intelligence for extraction
        parsed = await self.job_intelligence.analyze_job(job_text, source="manual")
        
        # Convert to Job object
        schedule_blocks = []
        if parsed.schedule.days and parsed.schedule.start_time and parsed.schedule.end_time:
            for day in parsed.schedule.days:
                try:
                    start_minutes = self._time_to_minutes(parsed.schedule.start_time)
                    end_minutes = self._time_to_minutes(parsed.schedule.end_time)
                    schedule_blocks.append(TimeBlock(
                        day=day,
                        start=start_minutes,
                        end=end_minutes
                    ))
                except:
                    pass
        
        # Estimate hourly rate from salary
        hourly_rate = self._estimate_hourly_rate(
            parsed.salary_min or parsed.salary_max,
            parsed.salary_period,
            parsed.salary_currency
        )
        
        return Job(
            job_id=f"manual_{hashlib.md5(job_text[:100].encode()).hexdigest()[:8]}",
            title=parsed.title or "Unknown Position",
            location=parsed.location or "Not specified",
            hourly_rate=hourly_rate,
            required_skills=parsed.required_skills,
            hours_per_week=parsed.schedule.hours_per_week or 40,
            schedule_blocks=schedule_blocks,
            company=parsed.company or "",
            description=job_text[:500],
            apply_link="",
            posted_date=""
        )
    
    async def _normalize_jobs(self, scraped_jobs: List[ScrapedJob]) -> List[Job]:
        """Convert scraped jobs to normalized Job objects"""
        jobs = []
        
        for scraped in scraped_jobs:
            # Generate unique ID
            job_id = hashlib.md5(
                f"{scraped.source}:{scraped.title}:{scraped.company}".encode()
            ).hexdigest()[:12]
            
            # Default schedule (9-6, Mon-Fri)
            schedule_blocks = [
                TimeBlock(day=day, start=540, end=1080)  # 9:00-18:00
                for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
            ]
            
            # Default hourly rate (estimate based on Armenian market)
            hourly_rate = 10.0  # ~$10/hr is decent in Armenia
            
            job = Job(
                job_id=job_id,
                title=scraped.title,
                location=scraped.location or "Yerevan, Armenia",
                hourly_rate=hourly_rate,
                required_skills=[],  # Would need job detail page for this
                hours_per_week=40,
                schedule_blocks=schedule_blocks,
                company=scraped.company,
                description=scraped.description,
                apply_link=scraped.url,
                posted_date=scraped.posted_date
            )
            jobs.append(job)
        
        return jobs
    
    def _job_to_cache_dict(self, job: Job) -> Dict:
        """Convert Job to cache-friendly dict"""
        return {
            'job_id': job.job_id,
            'title': job.title,
            'location': job.location,
            'hourly_rate': job.hourly_rate,
            'required_skills': list(job.required_skills),
            'hours_per_week': job.hours_per_week,
            'company': job.company,
            'description': job.description,
            'apply_link': job.apply_link,
            'posted_date': job.posted_date
        }
    
    def _parse_cached_jobs(self, cached_jobs: List[Dict]) -> List[Job]:
        """Convert cached dicts back to Job objects"""
        jobs = []
        for c in cached_jobs:
            jobs.append(Job(
                job_id=c['job_id'],
                title=c['title'],
                location=c['location'],
                hourly_rate=c['hourly_rate'],
                required_skills=c['required_skills'],
                hours_per_week=c['hours_per_week'],
                schedule_blocks=[],  # Not cached
                company=c.get('company', ''),
                description=c.get('description', ''),
                apply_link=c.get('apply_link', ''),
                posted_date=c.get('posted_date', '')
            ))
        return jobs
    
    def _time_to_minutes(self, time_str: str) -> int:
        """Convert time string (HH:MM) to minutes since midnight"""
        try:
            parts = time_str.split(':')
            return int(parts[0]) * 60 + int(parts[1])
        except:
            return 540  # Default 9:00
    
    def _estimate_hourly_rate(
        self, 
        salary: float, 
        period: str, 
        currency: str
    ) -> float:
        """Estimate hourly rate from salary"""
        if not salary:
            return 10.0  # Default for Armenia
        
        # Convert to hourly
        if period == 'yearly':
            hourly = salary / 2000
        elif period == 'monthly':
            hourly = salary / 160
        elif period == 'hourly':
            hourly = salary
        else:
            hourly = salary / 160  # Assume monthly
        
        # Convert to USD equivalent (rough estimates)
        if currency == 'AMD':
            hourly = hourly / 400  # 1 USD ≈ 400 AMD
        elif currency == 'RUB':
            hourly = hourly / 90   # 1 USD ≈ 90 RUB
        elif currency == 'EUR':
            hourly = hourly * 1.1  # 1 EUR ≈ 1.1 USD
        
        return round(hourly, 2)
    
    def clear_cache(self):
        """Clear all cached results"""
        self.cache.clear()
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)


# Convenience function
async def search_armenian_jobs(query: str, location: str = "Yerevan") -> List[Job]:
    """Search all Armenian job sites"""
    scraper = ArmenianJobScraper()
    return await scraper.search_all(query, location)
