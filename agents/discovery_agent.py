import asyncio
import os
from typing import List, Dict, Any, Optional
from models import Job
# Import existing services (assuming these files still exist in root)
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Lazy imports to avoid circular deps or failures if files missing
from jsearch_service import JSearchService
from adzuna_service import AdzunaService
from armenian_scrapers import ArmenianJobScraper

class JobDiscoveryAgent:
    """
    Agent 2: The "Researcher"
    Responsibility: Find jobs from multiple sources based on criteria.
    """
    def __init__(self):
        self.rapidapi_key = self._load_key("rapidapi_key.txt")
        self.adzuna_key = self._load_key("adzuna_api_key.txt")
        
        self.jsearch = JSearchService(self.rapidapi_key) if self.rapidapi_key else None
        
        self.adzuna = None
        if self.adzuna_key and ':' in self.adzuna_key:
             app_id, app_key = self.adzuna_key.split(':', 1)
             try:
                self.adzuna = AdzunaService(app_id, app_key, country="am")
             except: pass
             
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
        """
        tasks = []
        # Support multi-location search (e.g. "London, US")
        locations = [l.strip() for l in location.split(",") if l.strip()] if location else ["Yerevan"]
        
        for loc in locations:
            print(f"[DiscoveryAgent] Searching for '{query}' in '{loc}'...")
            
            # 1. JSearch
            if self.jsearch:
                tasks.append(self.jsearch.search_jobs(query, loc, remote_only=remote_only, num_pages=1))
                
            # 2. Adzuna
            if self.adzuna:
                tasks.append(self.adzuna.search_jobs(query, loc))
                
            # 3. Armenian Scrapers (Trigger for any known Armenian city or generic "Armenia")
            loc_lower = loc.lower()
            armenian_locations = ["armenia", "yerevan", "gyumri", "vanadzor", "dilijan", "abovyan", "hrazdan", "vagharshapat"]
            if any(place in loc_lower for place in armenian_locations):
                tasks.append(self.armenian.search_all(query, loc))

        if not tasks:
            print("[DiscoveryAgent] No search services configured!")
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        jobs = []
        for res in results:
            if isinstance(res, list):
                jobs.extend(res)
            elif isinstance(res, Exception):
                print(f"[DiscoveryAgent] Search error: {res}")

        # Deduplicate by Job ID
        unique_map = {j.job_id: j for j in jobs}
        return list(unique_map.values())
