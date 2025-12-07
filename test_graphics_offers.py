#!/usr/bin/env python3
"""Test new features: number of offers, improved graphics ready"""

from llm_service import LLMService

llm = LLMService()

print("=== Test 1: Number of Offers Extraction ===")
test_cases = [
    ("10 offers", 10),
    ("show me 20 jobs", 20),
    ("i want 15 positions", 15),
    ("30 vacancies please", 30),
    ("send me 50 opportunities", 50),
]

for test_input, expected in test_cases:
    result = llm._extract_with_regex(test_input, {})
    num = result.get('num_offers')
    status = "PASS" if num == expected else "FAIL"
    print(f"  [{status}] '{test_input}' -> {num} (expected {expected})")

print("\n=== Test 2: Complete Conversation with Offers ===")
user_profile = {}
history = []

# Full conversation
messages = [
    ("Arthur", "name"),
    ("Python developer", "skills"),
    ("Remote", "location"),
    ("remote", "remote_pref"),
    ("50", "rate"),
    ("40 hours", "hours"),
    ("20 offers", "num_offers"),
]

for msg, step in messages:
    history.append({"role": "user", "content": msg})
    response = llm._fallback_response(history, user_profile)
    user_profile.update(response['extracted_data'])
    ready = response['extracted_data'].get('ready_to_search')
    print(f"  Step {step}: ready_to_search = {ready}")

print("\n=== Test 3: User Profile Summary ===")
print(f"  Name: {user_profile.get('name')}")
print(f"  Skills: {user_profile.get('skills')}")
print(f"  Career Goals: {user_profile.get('career_goals')}")
print(f"  Location: {user_profile.get('location')}")
print(f"  Remote OK: {user_profile.get('remote_ok')}")
print(f"  Min Rate: ${user_profile.get('min_rate')}/hr")
print(f"  Max Hours: {user_profile.get('max_hours')} hrs/week")
print(f"  Num Offers: {user_profile.get('num_offers')}")
print(f"  Ready to Search: {user_profile.get('ready_to_search')}")

print("\n=== Test 4: Quick Offers Selection ===")
quick_cases = [
    "5 offers",
    "show 10",
    "i need 25 jobs",
]

for test in quick_cases:
    result = llm._extract_with_regex(test, {})
    num = result.get('num_offers')
    print(f"  '{test}' -> {num} offers" if num else f"  '{test}' -> NOT extracted")
