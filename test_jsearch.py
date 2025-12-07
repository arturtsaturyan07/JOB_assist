#!/usr/bin/env python3
"""
Test script to verify JSearch API is working and returning results
"""
import asyncio
import sys
import os

# Add current dir to path
sys.path.insert(0, os.path.dirname(__file__))

from jsearch_service import JSearchService

async def test_jsearch():
    # Load API key
    with open("rapidapi_key.txt", "r") as f:
        api_key = f.read().strip()
    
    service = JSearchService(api_key)
    
    print("=" * 60)
    print("Testing JSearch API")
    print("=" * 60)
    
    # Test 1: Simple query for Python programmer
    print("\n✅ Test 1: Python Programmer in Armenia")
    jobs = await service.search_jobs(
        query="Senior Python Programmer",
        location="Armenia",
        num_pages=2
    )
    print(f"Result: Found {len(jobs)} jobs")
    if jobs:
        for i, job in enumerate(jobs[:3], 1):
            print(f"  {i}. {job.title}")
            print(f"     Company: {job.company}")
            print(f"     Location: {job.location}")
            print(f"     Rate: ${job.hourly_rate}/hr")
    
    # Test 2: Broader search without location
    print("\n✅ Test 2: Senior Python Programmer (no location)")
    jobs = await service.search_jobs(
        query="Senior Python Programmer",
        location="",
        num_pages=2
    )
    print(f"Result: Found {len(jobs)} jobs")
    if jobs:
        for i, job in enumerate(jobs[:3], 1):
            print(f"  {i}. {job.title}")
            print(f"     Company: {job.company}")
            print(f"     Location: {job.location}")
            print(f"     Rate: ${job.hourly_rate}/hr")
    
    # Test 3: Simple "Programmer" query
    print("\n✅ Test 3: Python Developer (broad search)")
    jobs = await service.search_jobs(
        query="Python Developer",
        location="",
        num_pages=2
    )
    print(f"Result: Found {len(jobs)} jobs")
    if jobs:
        for i, job in enumerate(jobs[:3], 1):
            print(f"  {i}. {job.title}")
            print(f"     Company: {job.company}")
            print(f"     Location: {job.location}")
            print(f"     Rate: ${job.hourly_rate}/hr")
    
    # Test 4: Remote only
    print("\n✅ Test 4: Remote Python jobs")
    jobs = await service.search_jobs(
        query="Python Developer",
        location="",
        remote_only=True,
        num_pages=2
    )
    print(f"Result: Found {len(jobs)} jobs")
    if jobs:
        for i, job in enumerate(jobs[:3], 1):
            print(f"  {i}. {job.title}")
            print(f"     Company: {job.company}")
            print(f"     Location: {job.location}")
            print(f"     Rate: ${job.hourly_rate}/hr")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_jsearch())
