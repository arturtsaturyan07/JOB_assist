#!/usr/bin/env python3
"""Test improved features: role-specific locations, better rate defaults"""

from llm_service import LLMService

llm = LLMService()

print("=== Test 1: Role-Specific Locations ===")
test1 = "remote, but for doctor i wanna work in chicago, and teacher in new york"
result1 = llm._extract_with_regex(test1, {})
print(f"Input: {test1}")
print(f"Location: {result1.get('location')}")
print(f"Role Locations: {result1.get('role_locations')}")
print()

print("=== Test 2: Multiple Career Goals ===")
test2 = "doctor and teacher"
result2 = llm._extract_with_regex(test2, {})
print(f"Input: {test2}")
print(f"Career Goals: {result2.get('career_goals')}")
print()

print("=== Test 3: Search Timing (should not auto-trigger) ===")
user_profile = {'name': 'Arthur', 'skills': ['English'], 'career_goals': 'Teacher', 'location': 'Remote', 'remote_ok': True}
history = [{'role': 'user', 'content': 'any'}]
response = llm._fallback_response(history, user_profile)
print(f"After 'any' for rate: Ready to search = {response['extracted_data'].get('ready_to_search')}")
print(f"Response: {response['response']}")
print()

print("=== Test 4: Search Timing (should trigger after hours) ===")
user_profile2 = {'name': 'Arthur', 'skills': ['English'], 'career_goals': 'Teacher', 'location': 'Remote', 'remote_ok': True, 'min_rate': 50.0}
history2 = [{'role': 'user', 'content': '40 hours per week'}]
response2 = llm._fallback_response(history2, user_profile2)
print(f"After '40 hours': Ready to search = {response2['extracted_data'].get('ready_to_search')}")
print(f"Response: {response2['response']}")
