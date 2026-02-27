import asyncio
import os
import logging
from typing import List, Dict, Any, Optional
from models import Job
# Import existing services (assuming these files still exist in root)
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Lazy imports to avoid circular deps or failures if files missing
from adzuna_service import AdzunaService
from armenian_scrapers import ArmenianJobScraper
from linkedin_scraper import LinkedInScraper

# Import new free job sources
from indeed_scraper import IndeedScraper
from remoteok_service import RemoteOKService
from themuse_service import TheMuseService
from usajobs_service import USAJobsService

logger = logging.getLogger(__name__)

class JobDiscoveryAgent:
    """
    Agent 2: The "Researcher"
    Responsibility: Find jobs from multiple sources based on criteria.
    """
    def __init__(self):
        self.rapidapi_key = self._load_key("rapidapi_key.txt")
        self.adzuna_key = self._load_key("adzuna_api_key.txt")
        self.usajobs_key = self._load_key("usajobs_api_key.txt")
        self.usajobs_email = self._load_key("usajobs_email.txt")
        
        # JSearch DISABLED - requires paid subscription
        self.jsearch = None
        logger.info("[DiscoveryAgent] JSearch disabled - requires paid subscription")
        
        # LinkedIn Scraper (Selenium-based, no API key needed)
        self.linkedin_scraper = LinkedInScraper()
        logger.info("[DiscoveryAgent] LinkedIn Scraper initialized (headless mode)")
        
        # Indeed Scraper (FREE - Selenium-based, no API key needed)
        self.indeed_scraper = IndeedScraper()
        logger.info("[DiscoveryAgent] Indeed Scraper initialized (headless mode)")
        
        # RemoteOK API (FREE - no API key needed)
        self.remoteok = RemoteOKService()
        logger.info("[DiscoveryAgent] RemoteOK API initialized (free, no key needed)")
        
        # The Muse API (FREE - 500 requests/day, no key required)
        self.themuse = TheMuseService()
        logger.info("[DiscoveryAgent] The Muse API initialized (free tier)")
        
        # USAJobs API (FREE - unlimited, requires free API key)
        self.usajobs = None
        if self.usajobs_key:
            self.usajobs = USAJobsService(self.usajobs_key, self.usajobs_email)
            logger.info("[DiscoveryAgent] USAJobs API initialized (free, unlimited)")
        else:
            logger.info("[DiscoveryAgent] USAJobs API not configured (get free key at https://developer.usajobs.gov/)")
        
        # Adzuna API (DISABLED - connection timeouts)
        # To re-enable: uncomment the code below
        self.adzuna = None
        # if self.adzuna_key and ':' in self.adzuna_key:
        #      app_id, app_key = self.adzuna_key.split(':', 1)
        #      try:
        #         # Default to Germany (de) for better job coverage
        #         self.adzuna = AdzunaService(app_id, app_key, country="de")
        #      except: pass
        
        if self.adzuna:
            logger.info("[DiscoveryAgent] Adzuna API initialized")
        else:
            logger.info("[DiscoveryAgent] Adzuna API disabled (connection timeouts)")
             
        self.armenian = ArmenianJobScraper()

    def _load_key(self, filename: str) -> Optional[str]:
        # Helper to find key files in parent dir
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), filename)
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return f.read().strip()
            # Try current dir as fallback
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    return f.read().strip()
        except:
            pass
        return None

    async def search(self, query: str, location: str = "Yerevan", remote_only: bool = False) -> List[Job]:
        """
        Aggregated search from all providers.
        
        Args:
            query: Job title, skills, or keywords
            location: Location to search (can be broad like "Europe" or specific like "Germany")
            remote_only: Filter for remote jobs only
            
        Returns:
            List of Job objects from all available providers
        """
        tasks = []
        
        # Support multi-location search (e.g. "London, US")
        locations = [l.strip() for l in location.split(",") if l.strip()] if location else ["Yerevan"]
        
        for loc in locations:
            logger.info(f"[DiscoveryAgent] Searching for '{query}' in '{loc}'...")
            
            # 1. JSearch (DISABLED - requires paid subscription)
            if self.jsearch:
                try:
                    jobs_task = self.jsearch.search_jobs(
                        query=query,
                        location=loc,
                        remote_only=remote_only,
                        num_pages=10
                    )
                    tasks.append(("jsearch", jobs_task))
                except Exception as e:
                    logger.error(f"[DiscoveryAgent] JSearch error: {e}")
                
            # 2. LinkedIn Scraper (Selenium-based, headless mode with anti-detection)
            if self.linkedin_scraper:
                try:
                    logger.info(f"[DiscoveryAgent] Adding LinkedIn Scraper: query='{query}', location='{loc}'")
                    tasks.append(("linkedin_scraper", self.linkedin_scraper.search_jobs(query, loc, results_per_page=100)))
                except Exception as e:
                    logger.error(f"[DiscoveryAgent] LinkedIn Scraper error: {e}")
            
            # 3. Indeed Scraper (FREE - Selenium-based, headless mode)
            if self.indeed_scraper:
                try:
                    logger.info(f"[DiscoveryAgent] Adding Indeed Scraper: query='{query}', location='{loc}'")
                    tasks.append(("indeed_scraper", self.indeed_scraper.search_jobs(query, loc, results_per_page=100)))
                except Exception as e:
                    logger.error(f"[DiscoveryAgent] Indeed Scraper error: {e}")
            
            # 4. RemoteOK API (FREE - for remote jobs)
            if self.remoteok:
                try:
                    logger.info(f"[DiscoveryAgent] Adding RemoteOK API: query='{query}'")
                    tasks.append(("remoteok", self.remoteok.search_jobs(query, limit=100)))
                except Exception as e:
                    logger.error(f"[DiscoveryAgent] RemoteOK error: {e}")
            
            # 5. The Muse API (FREE - 500 requests/day)
            if self.themuse:
                try:
                    logger.info(f"[DiscoveryAgent] Adding The Muse API: query='{query}', location='{loc}'")
                    tasks.append(("themuse", self.themuse.search_jobs(query, loc, limit=100)))
                except Exception as e:
                    logger.error(f"[DiscoveryAgent] The Muse error: {e}")
            
            # 6. USAJobs API (FREE - US federal government jobs)
            if self.usajobs and ('us' in loc.lower() or 'america' in loc.lower() or 'usa' in loc.lower()):
                try:
                    logger.info(f"[DiscoveryAgent] Adding USAJobs API: query='{query}', location='{loc}'")
                    tasks.append(("usajobs", self.usajobs.search_jobs(query, loc, limit=100)))
                except Exception as e:
                    logger.error(f"[DiscoveryAgent] USAJobs error: {e}")
            
            # 7. Adzuna with smart country detection (DISABLED - connection timeouts)
            if self.adzuna:
                try:
                    country_code = self._get_adzuna_country_code(loc)
                    logger.info(f"[DiscoveryAgent] Adding Adzuna search: query='{query}', location='{loc}', country_code='{country_code}'")
                    tasks.append(("adzuna", self.adzuna.search_jobs(query, loc, country=country_code)))
                except Exception as e:
                    logger.error(f"[DiscoveryAgent] Adzuna error: {e}")
                
            # 8. Armenian Scrapers - ONLY search for Armenian locations
            is_armenian_location = any(
                armenian_keyword in loc.lower() 
                for armenian_keyword in ['armenia', 'yerevan', 'gyumri', 'vanadzor', 'gavar', 'dilijan', 'am']
            )
            
            if is_armenian_location and self.armenian:
                try:
                    logger.info(f"[DiscoveryAgent] Adding Armenian Scrapers: query='{query}', location='{loc}'")
                    tasks.append(("armenian", self.armenian.search_all(query, loc)))
                except Exception as e:
                    logger.error(f"[DiscoveryAgent] Armenian scraper error: {e}")

        if not tasks:
            logger.warning("[DiscoveryAgent] No search services configured!")
            return []

        # Execute all tasks and handle exceptions gracefully
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        jobs = []
        for i, res in enumerate(results):
            service_name = tasks[i][0] if i < len(tasks) else "unknown"
            
            if isinstance(res, list):
                jobs.extend(res)
                logger.info(f"[DiscoveryAgent] {service_name} returned {len(res)} jobs")
            elif isinstance(res, Exception):
                logger.error(f"[DiscoveryAgent] {service_name} error: {res}")

        # Deduplicate by Job ID
        unique_map = {j.job_id: j for j in jobs}
        deduplicated_jobs = list(unique_map.values())
        
        # FILTER: Only show jobs with apply links
        jobs_with_apply = [j for j in deduplicated_jobs if j.apply_link and j.apply_link.strip()]
        
        logger.info(f"[DiscoveryAgent] Total unique jobs found: {len(deduplicated_jobs)}")
        logger.info(f"[DiscoveryAgent] Jobs with apply links: {len(jobs_with_apply)}")
        
        if len(jobs_with_apply) < len(deduplicated_jobs):
            skipped = len(deduplicated_jobs) - len(jobs_with_apply)
            logger.info(f"[DiscoveryAgent] Skipped {skipped} jobs without apply links")
        
        return jobs_with_apply
    
    def _get_adzuna_country_code(self, location: str) -> str:
        """
        Map location string to Adzuna country code.
        
        Adzuna supported countries:
        - de (Germany), gb (UK), us (USA), fr (France), nl (Netherlands),
        - at (Austria), ch (Switzerland), au (Australia), ca (Canada), etc.
        """
        loc_lower = location.lower() if location else ""
        
        # Country/city to Adzuna country code mapping
        country_map = {
            # Germany
            'germany': 'de', 'deutschland': 'de', 'berlin': 'de', 'munich': 'de', 
            'hamburg': 'de', 'frankfurt': 'de', 'cologne': 'de', 'stuttgart': 'de',
            # UK
            'uk': 'gb', 'united kingdom': 'gb', 'britain': 'gb', 'england': 'gb',
            'london': 'gb', 'manchester': 'gb', 'birmingham': 'gb', 'edinburgh': 'gb',
            # USA
            'usa': 'us', 'united states': 'us', 'america': 'us', 'new york': 'us',
            'los angeles': 'us', 'chicago': 'us', 'san francisco': 'us', 'boston': 'us',
            # France
            'france': 'fr', 'paris': 'fr', 'lyon': 'fr', 'marseille': 'fr',
            # Netherlands
            'netherlands': 'nl', 'holland': 'nl', 'amsterdam': 'nl', 'rotterdam': 'nl',
            # Austria
            'austria': 'at', 'vienna': 'at', 'wien': 'at',
            # Switzerland
            'switzerland': 'ch', 'zurich': 'ch', 'geneva': 'ch',
            # Australia
            'australia': 'au', 'sydney': 'au', 'melbourne': 'au',
            # Canada
            'canada': 'ca', 'toronto': 'ca', 'vancouver': 'ca', 'montreal': 'ca',
            # Poland
            'poland': 'pl', 'warsaw': 'pl', 'krakow': 'pl',
            # Italy
            'italy': 'it', 'rome': 'it', 'milan': 'it',
            # Spain
            'spain': 'es', 'madrid': 'es', 'barcelona': 'es',
        }
        
        # Check for matches
        for key, code in country_map.items():
            if key in loc_lower:
                return code
        
        # Default to Germany (good coverage)
        return 'de'
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of all search services.
        
        Returns:
            Dictionary with health metrics for each service
        """
        health = {}
        
        # Get JSearch health from ResilientJSearchService
        if self.jsearch:
            health.update(self.jsearch.get_health_status())
        
        # Add other services status (basic info)
        health["linkedin_api"] = {
            "is_available": self.linkedin is not None,
            "configured": self.linkedin is not None,
            "status": "deprecated - use linkedin_scraper instead"
        }
        
        health["linkedin_scraper"] = {
            "is_available": self.linkedin_scraper is not None,
            "configured": self.linkedin_scraper is not None,
            "status": "active - Headless Selenium scraper with anti-detection"
        }
        
        health["indeed_scraper"] = {
            "is_available": self.indeed_scraper is not None,
            "configured": self.indeed_scraper is not None,
            "status": "active - FREE Selenium scraper (no API key needed)"
        }
        
        health["remoteok"] = {
            "is_available": self.remoteok is not None,
            "configured": self.remoteok is not None,
            "status": "active - FREE API for remote jobs (no key needed)"
        }
        
        health["themuse"] = {
            "is_available": self.themuse is not None,
            "configured": self.themuse is not None,
            "status": "active - FREE API (500 requests/day, no key needed)"
        }
        
        health["usajobs"] = {
            "is_available": self.usajobs is not None,
            "configured": self.usajobs is not None,
            "status": "active - FREE API for US federal jobs" if self.usajobs else "inactive - get free key at https://developer.usajobs.gov/"
        }
        
        health["adzuna"] = {
            "is_available": self.adzuna is not None,
            "configured": self.adzuna is not None
        }
        
        health["armenian_scrapers"] = {
            "is_available": self.armenian is not None,
            "configured": self.armenian is not None
        }
        
        return health
