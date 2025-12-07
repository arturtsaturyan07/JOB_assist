#!/usr/bin/env python3
"""Test multi-goal search through main.py"""

import asyncio
import json
from main import ChatSession

async def test_multi_goal_search():
    """Test that multiple career goals are all searched"""
    
    # Simulate a WebSocket session
    session = ChatSession()
    
    # Simulate messages
    test_messages = [
        "Hi, I'm Arthur",
        "I want English teacher and surgeon and lawyer positions",
        "I'm in Remote",
        "remote only",
        "$50 per hour",
        "40 hours per week",
        "search",
    ]
    
    print("=== Testing Multi-Goal Search ===\n")
    
    for msg in test_messages:
        print(f"User: {msg}")
        response = await session.process_message(msg)
        print(f"AI Response: {response.get('response', 'No response')[:100]}...")
        
        if response.get('extracted_data'):
            extracted = response['extracted_data']
            print(f"  -> Goals: {extracted.get('career_goals')}")
            print(f"  -> Ready: {extracted.get('ready_to_search')}")
        
        if response.get('jobs_found'):
            jobs = response.get('jobs_found', [])
            print(f"  -> Found {len(jobs)} jobs")
        
        print()

if __name__ == "__main__":
    asyncio.run(test_multi_goal_search())
