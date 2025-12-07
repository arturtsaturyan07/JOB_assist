#!/usr/bin/env python3
"""
Test parallel search from multiple job sources
"""
import asyncio
import sys
import os
import io

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add current dir to path
sys.path.insert(0, os.path.dirname(__file__))

from jsearch_service import JSearchService
from adzuna_service import AdzunaService

async def test_parallel_search():
    # Load API keys
    with open("rapidapi_key.txt", "r") as f:
        rapidapi_key = f.read().strip()
    
    jsearch = JSearchService(rapidapi_key)
    
    # Test different queries
    queries = [
        "Python Developer",
        "Senior Python Engineer",
        "English Teacher"
    ]
    
    print("=" * 70)
    print("PARALLEL JOB SEARCH - EXTENDED RESULTS")
    print("=" * 70)
    
    for query in queries:
        print(f"\n\n{'=' * 70}")
        print(f"Searching for: {query}")
        print('=' * 70)
        
        # Simulate parallel searches by doing multiple pages
        search_tasks = [
            jsearch.search_jobs(query=query, location="", remote_only=False, num_pages=2),
            jsearch.search_jobs(query=f"Senior {query}", location="", remote_only=False, num_pages=2),
        ]
        
        print("\nRunning parallel searches...")
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Process results
        all_jobs = []
        source_names = [query, f"Senior {query}"]
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Search {i+1} failed: {result}")
                continue
            
            if isinstance(result, list):
                all_jobs.extend(result)
                print(f"✅ Variant {i+1} ({source_names[i]}): Found {len(result)} jobs")
        
        # Remove duplicates
        seen_ids = set()
        unique_jobs = []
        for job in all_jobs:
            if job.job_id not in seen_ids:
                seen_ids.add(job.job_id)
                unique_jobs.append(job)
        
        print(f"\n📊 Total unique jobs: {len(unique_jobs)}\n")
        
        for i, job in enumerate(unique_jobs[:5], 1):
            print(f"{i}. {job.title}")
            print(f"   Company: {job.company}")
            print(f"   Location: {job.location}")
            print(f"   Rate: ${job.hourly_rate}/hr")
            print()

if __name__ == "__main__":
    asyncio.run(test_parallel_search())
