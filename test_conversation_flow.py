#!/usr/bin/env python3
"""Test complete conversation flow with multi-goal extraction"""

from llm_service import LLMService

llm = LLMService()

# Simulate a conversation with multiple messages
user_profile = {}
history = []

# Message 1: Name
user_msg1 = "Hi, I'm Arthur"
history.append({"role": "user", "content": user_msg1})
response1 = llm._fallback_response(history, user_profile)
print(f"\nUser: {user_msg1}")
print(f"AI: {response1['response']}")
user_profile.update(response1['extracted_data'])
print(f"Extracted: {response1['extracted_data']}")

# Message 2: Multiple career goals
user_msg2 = "I'm looking for English teacher and surgeon positions"
history.append({"role": "user", "content": user_msg2})
response2 = llm._fallback_response(history, user_profile)
print(f"\nUser: {user_msg2}")
print(f"AI: {response2['response']}")
user_profile.update(response2['extracted_data'])
print(f"Extracted: {response2['extracted_data']}")

# Message 3: Location
user_msg3 = "I'm based in Remote"
history.append({"role": "user", "content": user_msg3})
response3 = llm._fallback_response(history, user_profile)
print(f"\nUser: {user_msg3}")
print(f"AI: {response3['response']}")
user_profile.update(response3['extracted_data'])
print(f"Extracted: {response3['extracted_data']}")

# Message 4: Remote preference
user_msg4 = "I prefer remote work"
history.append({"role": "user", "content": user_msg4})
response4 = llm._fallback_response(history, user_profile)
print(f"\nUser: {user_msg4}")
print(f"AI: {response4['response']}")
user_profile.update(response4['extracted_data'])
print(f"Extracted: {response4['extracted_data']}")

# Message 5: Hourly rate
user_msg5 = "I'd like $50 per hour"
history.append({"role": "user", "content": user_msg5})
response5 = llm._fallback_response(history, user_profile)
print(f"\nUser: {user_msg5}")
print(f"AI: {response5['response']}")
user_profile.update(response5['extracted_data'])
print(f"Extracted: {response5['extracted_data']}")

# Message 6: Hours per week
user_msg6 = "I can work 40 hours per week"
history.append({"role": "user", "content": user_msg6})
response6 = llm._fallback_response(history, user_profile)
print(f"\nUser: {user_msg6}")
print(f"AI: {response6['response']}")
user_profile.update(response6['extracted_data'])
print(f"Extracted: {response6['extracted_data']}")
print(f"Ready to search: {response6['extracted_data'].get('ready_to_search')}")

print(f"\n=== Final User Profile ===")
print(f"   Name: {user_profile.get('name')}")
print(f"   Career Goals: {user_profile.get('career_goals')}")
print(f"   Location: {user_profile.get('location')}")
print(f"   Remote OK: {user_profile.get('remote_ok')}")
print(f"   Min Rate: {user_profile.get('min_rate')}")
print(f"   Max Hours: {user_profile.get('max_hours')}")

